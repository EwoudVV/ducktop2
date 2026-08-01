#include "ducktop2/ec/ec_fan.h"

#include <stdio.h>

static int failures;

#define CHECK(expression)                                                      \
  do {                                                                        \
    if (!(expression)) {                                                      \
      fprintf(stderr, "%s:%d: CHECK failed: %s\n", __FILE__, __LINE__,         \
              #expression);                                                   \
      ++failures;                                                             \
    }                                                                         \
  } while (0)

static ec_fan_config_t cfg;
static ec_fan_inputs_t in;
static ec_fan_state_t st;
static ec_fan_output_t out;

static void reset(void) {
  cfg = ec_fan_default_config();
  ec_fan_inputs_init(&in);
  ec_fan_state_init(&st);
  /* out is overwritten by ec_fan_step each call. */
}

static void step(uint32_t now_ms) {
  ec_fan_step(&cfg, &in, &st, now_ms, &out);
}

static void set_temps(int16_t skin, int16_t mu) {
  in.skin_dc = skin;
  in.mu_coldplate_dc = mu;
  in.temps_valid = true;
}

static void test_invalid_temps_force_full_duty(void) {
  reset();
  ec_fan_inputs_init(&in); /* temps_valid = false */
  step(0u);
  CHECK(out.thermal_fault);
  CHECK(out.duty_pct == 100u);
  CHECK(out.running);
  CHECK(!out.throttle_imminent);
}

static void test_cold_idle_fan_off(void) {
  reset();
  set_temps(250, 300); /* 25C skin, 30C coldplate - well under 40C idle */
  step(0u);
  CHECK(!out.thermal_fault);
  CHECK(out.duty_pct == 0u);
  CHECK(!out.running);
  CHECK(!out.throttle_imminent);
}

static void test_below_spin_up_stays_off(void) {
  reset();
  set_temps(420, 430); /* in the 40-45C hysteresis band, starting from off */
  step(0u);
  CHECK(!out.running);
  CHECK(out.duty_pct == 0u);
}

static void test_at_spin_up_starts_running(void) {
  reset();
  set_temps(440, 450); /* 45C control = spin_up */
  step(0u);
  CHECK(out.running);
  CHECK(out.duty_pct == cfg.min_duty_pct); /* 30% */
}

static void test_hysteresis_keeps_running_in_band(void) {
  reset();
  /* Start the fan at 45C. */
  set_temps(450, 450);
  step(0u);
  CHECK(out.running);
  /* Drop into the 40-45 band after the anti-cycling window clears; must keep
   * running (hysteresis) rather than stop/start oscillating. */
  set_temps(420, 430);
  step(3000u);
  CHECK(out.running);
  CHECK(out.duty_pct == cfg.min_duty_pct); /* floor duty while running */
}

static void test_drops_below_idle_off_stops(void) {
  reset();
  set_temps(450, 450);
  step(0u);
  /* Cool to 30C after anti-cycling window */
  set_temps(280, 300);
  step(3000u);
  CHECK(!out.running);
  CHECK(out.duty_pct == 0u);
}

static void test_anti_cycling_prevents_immediate_stop(void) {
  reset();
  set_temps(450, 450);
  step(0u);
  CHECK(out.running);
  /* Instantly drop to 30C (well below idle_off) but inside 2s window. */
  set_temps(280, 300);
  step(500u); /* 500ms < 2000ms */
  CHECK(out.running);
  /* Anti-cycling holds the running flag set; ramp floor (min_duty) still
   * applies, so the blower keeps spinning quietly rather than stalling. */
  CHECK(out.duty_pct == cfg.min_duty_pct);
  /* Wait out the 2s window: now the stop is allowed. */
  step(2500u);
  CHECK(!out.running);
  CHECK(out.duty_pct == 0u);
}

static void test_ramp_increases_with_temperature(void) {
  reset();
  set_temps(450, 450); /* 45C -> 30% (min_duty) */
  step(0u);
  CHECK(out.duty_pct == 30u);

  set_temps(500, 500); /* 50C, mid window */
  step(1u);
  const uint8_t duty_50 = out.duty_pct;
  CHECK(duty_50 > 30u);
  CHECK(duty_50 < 100u);

  set_temps(600, 600); /* 60C, high window */
  step(2u);
  const uint8_t duty_60 = out.duty_pct;
  CHECK(duty_60 > duty_50);
  CHECK(duty_60 < 100u);

  set_temps(700, 700); /* 70C = max_duty_temp */
  step(3u);
  CHECK(out.duty_pct == 100u);
}

static void test_above_max_duty_temp_stays_at_max(void) {
  reset();
  set_temps(720, 710);
  step(0u);
  CHECK(out.running);
  CHECK(out.duty_pct == 100u);
}

static void test_throttle_imminent_flag(void) {
  reset();
  set_temps(800, 790); /* 80C control = throttle threshold */
  step(0u);
  CHECK(out.throttle_imminent);
  CHECK(out.duty_pct == 100u);

  /* Below the throttle threshold, flag is clear even at max duty. */
  set_temps(750, 750);
  step(1u);
  CHECK(!out.throttle_imminent);
  CHECK(out.duty_pct == 100u);
}

static void test_control_temp_uses_hotter_of_two(void) {
  reset();
  /* Hot coldplate, cool skin: fan must spin (coldplate drives). */
  set_temps(300, 460);
  step(0u);
  CHECK(out.running);

  /* Hot skin, cool coldplate: fan must also spin (skin drives). */
  set_temps(460, 300);
  ec_fan_state_init(&st);
  step(1u);
  CHECK(out.running);
}

static void test_skin_hot_enough_to_force_max(void) {
  reset();
  set_temps(700, 300); /* 70C skin, 30C coldplate */
  step(0u);
  CHECK(out.duty_pct == 100u);
}

static void test_reset_to_known_state(void) {
  reset();
  /* Run up the state, then reset. */
  set_temps(800, 800);
  step(0u);
  CHECK(out.throttle_imminent);

  ec_fan_state_init(&st);
  ec_fan_inputs_init(&in);
  set_temps(300, 300);
  step(1u);
  CHECK(!out.running);
  CHECK(out.duty_pct == 0u);
  CHECK(!out.thermal_fault);
}

static void test_ramp_then_cool_resumes_off_after_window(void) {
  reset();
  set_temps(680, 680); /* high (68C), fan ramps near max */
  step(0u);
  CHECK(out.running);
  const uint8_t hot_duty = out.duty_pct;
  CHECK(hot_duty >= 90u);

  /* Cool below idle but inside anti-cycling: keeps running. */
  set_temps(350, 350);
  step(1000u);
  CHECK(out.running);

  /* Past the window: stops cleanly. */
  step(3500u);
  CHECK(!out.running);
  CHECK(out.duty_pct == 0u);
}

static void test_min_duty_floor_when_running_above_idle(void) {
  reset();
  set_temps(450, 450); /* exactly spin_up -> min_duty */
  step(0u);
  CHECK(out.running);
  CHECK(out.duty_pct == cfg.min_duty_pct);
  /* Slightly above spin_up, duty is already above min. */
  set_temps(455, 455);
  step(1u);
  CHECK(out.duty_pct > cfg.min_duty_pct);
}

static void test_default_config_constants(void) {
  cfg = ec_fan_default_config();
  CHECK(cfg.idle_off_temp_dc == EC_FAN_DEFAULT_IDLE_OFF_DC);
  CHECK(cfg.spin_up_temp_dc == EC_FAN_DEFAULT_SPIN_UP_DC);
  CHECK(cfg.max_duty_temp_dc == EC_FAN_DEFAULT_MAX_DUTY_TEMP_DC);
  CHECK(cfg.throttle_imminent_temp_dc == EC_FAN_DEFAULT_THROTTLE_IMMIN_DC);
  CHECK(cfg.min_duty_pct == EC_FAN_DEFAULT_MIN_DUTY_PCT);
  CHECK(cfg.max_duty_pct == EC_FAN_DEFAULT_MAX_DUTY_PCT);
  CHECK(cfg.min_runtime_ms == EC_FAN_DEFAULT_MIN_RUNTIME_MS);
}

int main(void) {
  test_invalid_temps_force_full_duty();
  test_cold_idle_fan_off();
  test_below_spin_up_stays_off();
  test_at_spin_up_starts_running();
  test_hysteresis_keeps_running_in_band();
  test_drops_below_idle_off_stops();
  test_anti_cycling_prevents_immediate_stop();
  test_ramp_increases_with_temperature();
  test_above_max_duty_temp_stays_at_max();
  test_throttle_imminent_flag();
  test_control_temp_uses_hotter_of_two();
  test_skin_hot_enough_to_force_max();
  test_reset_to_known_state();
  test_ramp_then_cool_resumes_off_after_window();
  test_min_duty_floor_when_running_above_idle();
  test_default_config_constants();

  if (failures != 0) {
    fprintf(stderr, "ec_fan_tests: %d failure(s)\n", failures);
    return 1;
  }
  puts("ec_fan_tests: PASS");
  return 0;
}