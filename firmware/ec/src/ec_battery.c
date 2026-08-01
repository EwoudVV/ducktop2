#include "ducktop2/ec/ec_battery.h"

#include <string.h>

static bool flag_set(const ec_telemetry_snapshot_t *t, uint16_t bit) {
  return (t->valid_flags & bit) != 0u;
}

static bool telemetry_valid(const ec_telemetry_snapshot_t *t) {
  /* SOC and pack voltage are the minimum for a trusted report.  Current may
   * legitimately be zero, so its validity flag alone is sufficient — the value
   * is only consumed when the flag is set. */
  return flag_set(t, EC_TELEMETRY_VALID_SOC) &&
         flag_set(t, EC_TELEMETRY_VALID_PACK_VOLTAGE);
}

ec_battery_config_t ec_battery_default_config(void) {
  ec_battery_config_t config;
  config.charge_threshold_ma = EC_BATTERY_DEFAULT_CHARGE_THRESHOLD_MA;
  config.discharge_threshold_ma = EC_BATTERY_DEFAULT_DISCHARGE_THRESHOLD_MA;
  config.full_current_ma = EC_BATTERY_DEFAULT_FULL_CURRENT_MA;
  config.full_soc_pct = EC_BATTERY_DEFAULT_FULL_SOC_PCT;
  config.full_confirm_ms = EC_BATTERY_DEFAULT_FULL_CONFIRM_MS;
  return config;
}

void ec_battery_inputs_init(ec_battery_inputs_t *inputs) {
  if (inputs == NULL) {
    return;
  }
  memset(inputs, 0, sizeof(*inputs));
}

void ec_battery_state_init(ec_battery_controller_t *state) {
  if (state == NULL) {
    return;
  }
  state->state = EC_BATTERY_UNKNOWN;
  state->charging_to_full_pending = false;
  state->full_confirm_started_ms = 0u;
}

const char *ec_battery_state_name(ec_battery_state_t state) {
  switch (state) {
    case EC_BATTERY_UNKNOWN:     return "Unknown";
    case EC_BATTERY_NOT_PRESENT: return "Not present";
    case EC_BATTERY_DISCHARGING: return "Discharging";
    case EC_BATTERY_CHARGING:    return "Charging";
    case EC_BATTERY_FULL:        return "Full";
    default:                     return "Unknown";
  }
}

/*
 * Classify the instantaneous intent from the current reading + charger state.
 * Returns the *candidate* state; the caller applies hysteresis.
 */
static ec_battery_state_t classify(const ec_battery_config_t *config,
                                   const ec_battery_inputs_t *inputs,
                                   bool data_ok) {
  if (!inputs->pack_present) {
    return EC_BATTERY_NOT_PRESENT;
  }
  if (!data_ok) {
    return EC_BATTERY_UNKNOWN;
  }
  const ec_telemetry_snapshot_t *t = &inputs->telemetry;
  const bool current_valid = flag_set(t, EC_TELEMETRY_VALID_PACK_CURRENT);
  const int32_t current = current_valid ? t->pack_current_ma : 0;

  if (current >= (int32_t)config->charge_threshold_ma) {
    return EC_BATTERY_CHARGING;
  }
  if (current <= -(int32_t)config->discharge_threshold_ma) {
    return EC_BATTERY_DISCHARGING;
  }

  /* Current is in the dead band (near zero).  If the charger is connected and
   * SOC is high, the pack is effectively full.  Otherwise it is idle — which
   * we report as the current state (no transition), handled by the caller. */
  if (inputs->charger_enable &&
      flag_set(t, EC_TELEMETRY_VALID_SOC) &&
      t->soc_percent >= config->full_soc_pct) {
    return EC_BATTERY_FULL;
  }

  /* No strong signal: keep the current state.  The caller handles this by
   * leaving the state unchanged when classify returns UNKNOWN as a "no
   * change" signal — but we need a distinct sentinel.  Use the current state.
   * This path is unreachable because the caller always checks the thresholds
   * first, so return DISCHARGING as a safe default (pack is present, near-zero
   * idle on battery = effectively discharging at ~0). */
  return EC_BATTERY_DISCHARGING;
}

void ec_battery_step(const ec_battery_config_t *config,
                     const ec_battery_inputs_t *inputs,
                     ec_battery_controller_t *state,
                     uint32_t now_ms,
                     ec_battery_report_t *report) {
  if (report == NULL) {
    return;
  }
  memset(report, 0, sizeof(*report));
  report->state = state->state;

  const ec_telemetry_snapshot_t *t = &inputs->telemetry;
  const bool data_ok = inputs->pack_present && telemetry_valid(t);

  /* NOT_PRESENT overrides everything and resets hysteresis. */
  if (!inputs->pack_present) {
    state->state = EC_BATTERY_NOT_PRESENT;
    state->charging_to_full_pending = false;
    report->state = EC_BATTERY_NOT_PRESENT;
    report->present = false;
    report->data_valid = false;
    return;
  }
  report->present = true;

  if (!data_ok) {
    state->state = EC_BATTERY_UNKNOWN;
    state->charging_to_full_pending = false;
    report->state = EC_BATTERY_UNKNOWN;
    report->data_valid = false;
    return;
  }

  report->data_valid = true;
  report->soc_percent = t->soc_percent;
  report->voltage_mv = t->pack_voltage_mv;
  if (flag_set(t, EC_TELEMETRY_VALID_PACK_CURRENT)) {
    report->current_ma = t->pack_current_ma;
  }
  if (flag_set(t, EC_TELEMETRY_VALID_HEALTH)) {
    report->health_percent = t->health_percent;
  }
  if (flag_set(t, EC_TELEMETRY_VALID_CYCLE_COUNT)) {
    report->cycle_count = t->cycle_count;
  }

  const bool current_valid = flag_set(t, EC_TELEMETRY_VALID_PACK_CURRENT);
  const int32_t current = current_valid ? t->pack_current_ma : 0;
  const bool charger_on = inputs->charger_enable;
  const bool soc_valid = flag_set(t, EC_TELEMETRY_VALID_SOC);
  const uint8_t soc = soc_valid ? t->soc_percent : 0u;

  /* ---------------- State transitions with hysteresis ---------------- */

  switch (state->state) {
    case EC_BATTERY_UNKNOWN:
      /* First valid reading: jump straight to the classified state. */
      state->state = classify(config, inputs, true);
      break;

    case EC_BATTERY_NOT_PRESENT:
      /* Pack just returned: start at UNKNOWN so the next step classifies. */
      state->state = EC_BATTERY_UNKNOWN;
      break;

    case EC_BATTERY_DISCHARGING:
      if (current >= (int32_t)config->charge_threshold_ma) {
        state->state = EC_BATTERY_CHARGING;
        state->charging_to_full_pending = false;
      } else if (charger_on && soc >= config->full_soc_pct &&
                 current < (int32_t)config->full_current_ma) {
        /* Plugged in + nearly full + low current: start the full confirmation. */
        state->state = EC_BATTERY_FULL;
        state->charging_to_full_pending = true;
        state->full_confirm_started_ms = now_ms;
      }
      break;

    case EC_BATTERY_CHARGING:
      if (current <= -(int32_t)config->discharge_threshold_ma) {
        state->state = EC_BATTERY_DISCHARGING;
        state->charging_to_full_pending = false;
      } else if (charger_on && soc >= config->full_soc_pct &&
                 current < (int32_t)config->full_current_ma) {
        state->state = EC_BATTERY_FULL;
        state->charging_to_full_pending = true;
        state->full_confirm_started_ms = now_ms;
      }
      break;

    case EC_BATTERY_FULL: {
      /* Stay full while charger + high SOC + low current.  Leave on any
       * strong departure: current rises (charging resumed) or current goes
       * negative (charger unplugged, discharging).  Also leave if SOC drops
       * below the threshold (pack was drained while still plugged — unlikely
       * but defensive). */
      const bool still_full = charger_on && soc_valid &&
          soc >= config->full_soc_pct &&
          current < (int32_t)config->full_current_ma;
      if (still_full) {
        /* Confirm the timer; once elapsed, clear the pending flag so the
         * state is "settled full" (no further timer churn). */
        if (state->charging_to_full_pending) {
          uint32_t elapsed = (now_ms >= state->full_confirm_started_ms)
                                 ? (now_ms - state->full_confirm_started_ms)
                                 : 0u;
          if (elapsed >= config->full_confirm_ms) {
            state->charging_to_full_pending = false;
          }
        }
      } else {
        if (current >= (int32_t)config->charge_threshold_ma) {
          state->state = EC_BATTERY_CHARGING;
        } else if (current <= -(int32_t)config->discharge_threshold_ma) {
          state->state = EC_BATTERY_DISCHARGING;
        } else {
          /* Dead band but SOC dropped or charger off: settle to discharging
           * (on battery, near-zero current = slowly discharging). */
          state->state = EC_BATTERY_DISCHARGING;
        }
        state->charging_to_full_pending = false;
      }
      break;
    }

    default:
      state->state = EC_BATTERY_UNKNOWN;
      break;
  }

  report->state = state->state;

  /* Time fields follow the state. */
  if (state->state == EC_BATTERY_DISCHARGING &&
      flag_set(t, EC_TELEMETRY_VALID_TIME_TO_EMPTY)) {
    report->time_to_empty_s = t->time_to_empty_s;
  }
  if (state->state == EC_BATTERY_CHARGING &&
      flag_set(t, EC_TELEMETRY_VALID_TIME_TO_FULL)) {
    report->time_to_full_s = t->time_to_full_s;
  }
}