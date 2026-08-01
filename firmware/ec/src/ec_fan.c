#include "ducktop2/ec/ec_fan.h"

/*
 * Internal clamping: the target may have written config values outside the
 * valid range (0..100 duty, ordered temperatures), so every read is clamped.
 * This keeps the test vectors simple and never trusts the caller.
 */

static uint8_t clamp_duty(uint8_t value) {
  if (value > 100u) {
    return 100u;
  }
  return value;
}

static ec_fan_temp_dc_t max_temp(ec_fan_temp_dc_t a, ec_fan_temp_dc_t b) {
  return (a >= b) ? a : b;
}

/*
 * Linear interpolation of duty across the [spin_up, max_duty_temp] window.
 * Below the window the min duty applies (floor once running); above it the
 * max duty applies.  Computed in scaled integer (permille of the duty span)
 * to avoid floating point.
 */
static uint8_t ramp_duty(const ec_fan_config_t *config,
                         ec_fan_temp_dc_t temp) {
  const uint8_t lo = clamp_duty(config->min_duty_pct);
  const uint8_t hi = clamp_duty(config->max_duty_pct);
  const ec_fan_temp_dc_t lo_temp = config->spin_up_temp_dc;
  const ec_fan_temp_dc_t hi_temp = config->max_duty_temp_dc;

  if (hi_temp <= lo_temp) {
    /* Degenerate config: jump straight to max once spinning. */
    return hi;
  }
  if (temp <= lo_temp) {
    return lo;
  }
  if (temp >= hi_temp) {
    return hi;
  }

  /* temp in (lo_temp, hi_temp): interpolate lo..hi. */
  const int32_t span_temp = (int32_t)(hi_temp - lo_temp);
  const int32_t span_duty = (int32_t)hi - (int32_t)lo;
  const int32_t above_lo = (int32_t)temp - (int32_t)lo_temp;
  /* Round to nearest by adding half the span_temp before dividing. */
  const int32_t scaled = (above_lo * span_duty * 1000) +
                         (span_temp * 500);
  const int32_t interp = lo + (scaled / (span_temp * 1000));
  if (interp < (int32_t)lo) {
    return lo;
  }
  if (interp > (int32_t)hi) {
    return hi;
  }
  return (uint8_t)interp;
}

ec_fan_config_t ec_fan_default_config(void) {
  ec_fan_config_t config;
  config.idle_off_temp_dc = EC_FAN_DEFAULT_IDLE_OFF_DC;
  config.spin_up_temp_dc = EC_FAN_DEFAULT_SPIN_UP_DC;
  config.max_duty_temp_dc = EC_FAN_DEFAULT_MAX_DUTY_TEMP_DC;
  config.throttle_imminent_temp_dc = EC_FAN_DEFAULT_THROTTLE_IMMIN_DC;
  config.min_duty_pct = EC_FAN_DEFAULT_MIN_DUTY_PCT;
  config.max_duty_pct = EC_FAN_DEFAULT_MAX_DUTY_PCT;
  config.min_runtime_ms = EC_FAN_DEFAULT_MIN_RUNTIME_MS;
  return config;
}

void ec_fan_inputs_init(ec_fan_inputs_t *inputs) {
  inputs->skin_dc = 0;
  inputs->mu_coldplate_dc = 0;
  inputs->temps_valid = false;
}

void ec_fan_state_init(ec_fan_state_t *state) {
  state->running = false;
  state->started_ms = 0u;
  state->anti_cycling_hold = false;
}

void ec_fan_step(const ec_fan_config_t *config,
                 const ec_fan_inputs_t *inputs,
                 ec_fan_state_t *state,
                 uint32_t now_ms,
                 ec_fan_output_t *output) {
  /* Fail-safe: invalid temperature data forces maximum cooling.  The fan
   * state is left as-is so that once telemetry recovers, normal hysteresis
   * resumes from wherever it was. */
  output->thermal_fault = !inputs->temps_valid;
  output->throttle_imminent = false;
  if (output->thermal_fault) {
    output->duty_pct = 100u;
    output->running = true;
    return;
  }

  const ec_fan_temp_dc_t control =
      max_temp(inputs->skin_dc, inputs->mu_coldplate_dc);
  const ec_fan_temp_dc_t idle_off = config->idle_off_temp_dc;
  const ec_fan_temp_dc_t spin_up = config->spin_up_temp_dc;

  /* Hysteresis state transitions.  Between idle_off and spin_up the fan
   * keeps its current state; this is the anti-hunt band. */
  if (!state->running) {
    if (control >= spin_up) {
      state->running = true;
      state->started_ms = now_ms;
      state->anti_cycling_hold = true;
    }
  } else {
    /* Honour a minimum run time before allowing stop, even if cold. */
    const bool within_min_runtime = state->anti_cycling_hold &&
        ((now_ms - state->started_ms) < config->min_runtime_ms);
    if (control <= idle_off && !within_min_runtime) {
      state->running = false;
      state->anti_cycling_hold = false;
    } else if (control <= idle_off && within_min_runtime) {
      /* Still inside the anti-cycling window: keep the running flag set so
       * the ramp duty (not 0) is emitted.  The hold clears once the window
       * elapses; the next step re-evaluates the stop. */
    }
    if (!within_min_runtime) {
      state->anti_cycling_hold = false;
    }
  }

  if (state->running) {
    output->duty_pct = ramp_duty(config, control);
    output->running = true;
  } else {
    output->duty_pct = 0u;
    output->running = false;
  }

  if (control >= config->throttle_imminent_temp_dc) {
    output->throttle_imminent = true;
  }
}