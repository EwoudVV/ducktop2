#include "ducktop2/ec/ec_battery.h"
#include "ducktop2/ec/ec_telemetry.h"

#include <stdio.h>
#include <string.h>

static int failures;

#define CHECK(expression)                                                      \
  do {                                                                        \
    if (!(expression)) {                                                      \
      fprintf(stderr, "%s:%d: CHECK failed: %s\n", __FILE__, __LINE__,         \
              #expression);                                                   \
      ++failures;                                                             \
    }                                                                         \
  } while (0)

static ec_battery_config_t cfg;
static ec_battery_inputs_t in;
static ec_battery_controller_t st;
static ec_battery_report_t rpt;

static void reset(void) {
  cfg = ec_battery_default_config();
  ec_battery_inputs_init(&in);
  ec_battery_state_init(&st);
}

static void step(uint32_t now_ms) {
  ec_battery_step(&cfg, &in, &st, now_ms, &rpt);
}

/* Build a telemetry snapshot with the common valid flags set. */
static void snapshot(uint8_t soc, uint16_t voltage_mv, int32_t current_ma,
                     bool charger_on) {
  ec_telemetry_snapshot_t *t = &in.telemetry;
  memset(t, 0, sizeof(*t));
  t->valid_flags = EC_TELEMETRY_VALID_SOC | EC_TELEMETRY_VALID_PACK_VOLTAGE |
                   EC_TELEMETRY_VALID_PACK_CURRENT |
                   EC_TELEMETRY_VALID_TIME_TO_EMPTY |
                   EC_TELEMETRY_VALID_TIME_TO_FULL |
                   EC_TELEMETRY_VALID_HEALTH | EC_TELEMETRY_VALID_CYCLE_COUNT;
  t->soc_percent = soc;
  t->pack_voltage_mv = voltage_mv;
  t->pack_current_ma = current_ma;
  t->time_to_empty_s = 7200u;
  t->time_to_full_s = 3600u;
  t->health_percent = 95u;
  t->cycle_count = 50u;
  in.pack_present = true;
  in.charger_enable = charger_on;
}

static void test_initial_unknown(void) {
  reset();
  in.pack_present = true;
  /* No valid telemetry yet -> UNKNOWN (not NOT_PRESENT, pack exists). */
  memset(&in.telemetry, 0, sizeof(in.telemetry));
  step(0u);
  CHECK(rpt.state == EC_BATTERY_UNKNOWN);
  CHECK(rpt.present);
  CHECK(!rpt.data_valid);
}

static void test_not_present_overrides(void) {
  reset();
  in.pack_present = false;
  step(0u);
  CHECK(rpt.state == EC_BATTERY_NOT_PRESENT);
  CHECK(!rpt.present);
  CHECK(!rpt.data_valid);

  /* Even with full telemetry, NOT_PRESENT wins. */
  snapshot(80, 12400, 1500, true);
  in.pack_present = false;
  step(1u);
  CHECK(rpt.state == EC_BATTERY_NOT_PRESENT);
  CHECK(!rpt.present);
}

static void test_invalid_data_after_present_is_unknown(void) {
  reset();
  in.pack_present = true;
  /* No valid_flags set -> invalid data. */
  memset(&in.telemetry, 0, sizeof(in.telemetry));
  step(0u);
  CHECK(rpt.state == EC_BATTERY_UNKNOWN);
  CHECK(rpt.present);
  CHECK(!rpt.data_valid);
}

static void test_unknown_to_discharging(void) {
  reset();
  snapshot(50, 11600, -800, false);
  step(0u);
  CHECK(rpt.state == EC_BATTERY_DISCHARGING);
  CHECK(rpt.present);
  CHECK(rpt.data_valid);
  CHECK(rpt.soc_percent == 50u);
  CHECK(rpt.current_ma == -800);
  CHECK(rpt.time_to_empty_s == 7200u);
  CHECK(rpt.time_to_full_s == 0u);  /* not charging */
}

static void test_unknown_to_charging(void) {
  reset();
  snapshot(50, 12400, 1500, true);
  step(0u);
  CHECK(rpt.state == EC_BATTERY_CHARGING);
  CHECK(rpt.time_to_full_s == 3600u);
  CHECK(rpt.time_to_empty_s == 0u);
}

static void test_discharging_to_charging(void) {
  reset();
  snapshot(50, 11600, -800, false);
  step(0u);
  CHECK(rpt.state == EC_BATTERY_DISCHARGING);

  /* Plug in, current goes positive. */
  snapshot(50, 12400, 1500, true);
  step(1u);
  CHECK(rpt.state == EC_BATTERY_CHARGING);
}

static void test_charging_to_discharging(void) {
  reset();
  snapshot(50, 12400, 1500, true);
  step(0u);
  CHECK(rpt.state == EC_BATTERY_CHARGING);

  /* Unplug, current goes negative. */
  snapshot(50, 11600, -800, false);
  step(1u);
  CHECK(rpt.state == EC_BATTERY_DISCHARGING);
}

static void test_charging_to_full_needs_confirm(void) {
  reset();
  /* Start charging at 96% with moderate current. */
  snapshot(96, 12400, 200, true);
  step(0u);
  CHECK(rpt.state == EC_BATTERY_CHARGING);

  /* Current drops below full_current_ma (30), SOC 96 >= 95, charger on.
   * This starts the FULL confirmation timer. */
  snapshot(96, 12500, 10, true);
  step(100u);
  CHECK(rpt.state == EC_BATTERY_FULL);
  CHECK(st.charging_to_full_pending); /* timer still running */

  /* Before confirm_ms (2000): if current rises back above charge_threshold,
   * FULL -> CHARGING. */
  snapshot(96, 12500, 100, true);
  step(500u);
  CHECK(rpt.state == EC_BATTERY_CHARGING);
}

static void test_charging_to_full_confirmed(void) {
  reset();
  snapshot(96, 12400, 200, true);
  step(0u);
  CHECK(rpt.state == EC_BATTERY_CHARGING);

  snapshot(96, 12500, 10, true);
  step(100u);
  CHECK(rpt.state == EC_BATTERY_FULL);
  CHECK(st.charging_to_full_pending);

  /* Hold the full condition past the confirm window. */
  step(2200u); /* 2100ms > 2000ms */
  CHECK(rpt.state == EC_BATTERY_FULL);
  CHECK(!st.charging_to_full_pending); /* timer cleared */
}

static void test_full_stays_full_with_flicker(void) {
  reset();
  /* Get to confirmed FULL. */
  snapshot(96, 12400, 200, true);
  step(0u);
  snapshot(96, 12500, 10, true);
  step(100u);
  step(2200u);
  CHECK(rpt.state == EC_BATTERY_FULL);
  CHECK(!st.charging_to_full_pending);

  /* Current bounces slightly within the dead band (< 30mA, > -50mA): stays
   * FULL.  No flicker. */
  snapshot(96, 12500, 20, true);
  step(2300u);
  CHECK(rpt.state == EC_BATTERY_FULL);
  snapshot(96, 12500, 0, true);
  step(2400u);
  CHECK(rpt.state == EC_BATTERY_FULL);
  snapshot(96, 12500, -20, true);
  step(2500u);
  CHECK(rpt.state == EC_BATTERY_FULL); /* still in dead band, charger on */
}

static void test_full_to_charging(void) {
  reset();
  /* Confirm FULL. */
  snapshot(96, 12400, 200, true);
  step(0u);
  snapshot(96, 12500, 10, true);
  step(100u);
  step(2200u);
  CHECK(rpt.state == EC_BATTERY_FULL);

  /* Current rises above charge_threshold -> charging. */
  snapshot(96, 12500, 100, true);
  step(2300u);
  CHECK(rpt.state == EC_BATTERY_CHARGING);
}

static void test_full_to_discharging_on_unplug(void) {
  reset();
  snapshot(96, 12400, 200, true);
  step(0u);
  snapshot(96, 12500, 10, true);
  step(100u);
  step(2200u);
  CHECK(rpt.state == EC_BATTERY_FULL);

  /* Charger off + negative current -> discharging. */
  snapshot(96, 11600, -800, false);
  step(2300u);
  CHECK(rpt.state == EC_BATTERY_DISCHARGING);
}

static void test_full_to_discharging_soc_drop(void) {
  reset();
  snapshot(96, 12400, 200, true);
  step(0u);
  snapshot(96, 12500, 10, true);
  step(100u);
  step(2200u);
  CHECK(rpt.state == EC_BATTERY_FULL);

  /* SOC drops below 95 while charger on + dead-band current: leave FULL.
   * Near-zero current with charger on but SOC < 95 means the pack is not
   * discharging (charger is holding it), so transition to CHARGING is wrong.
   * The state machine falls to DISCHARGING as the safe default for dead-band
   * on battery; with charger on this is conservative. */
  snapshot(90, 12500, 10, true);
  step(2300u);
  CHECK(rpt.state == EC_BATTERY_DISCHARGING);
}

static void test_not_present_returns_to_unknown(void) {
  reset();
  in.pack_present = false;
  step(0u);
  CHECK(rpt.state == EC_BATTERY_NOT_PRESENT);

  /* Pack returns with valid data; UNKNOWN first, then classifies next step. */
  snapshot(50, 11600, -800, false);
  step(1u);
  CHECK(rpt.state == EC_BATTERY_UNKNOWN);

  /* Second step: classifies to DISCHARGING. */
  snapshot(50, 11600, -800, false);
  step(2u);
  CHECK(rpt.state == EC_BATTERY_DISCHARGING);
}

static void test_report_fields_populated(void) {
  reset();
  snapshot(80, 12400, 1500, true);
  step(0u);
  CHECK(rpt.state == EC_BATTERY_CHARGING);
  CHECK(rpt.present);
  CHECK(rpt.data_valid);
  CHECK(rpt.soc_percent == 80u);
  CHECK(rpt.voltage_mv == 12400u);
  CHECK(rpt.current_ma == 1500);
  CHECK(rpt.health_percent == 95u);
  CHECK(rpt.cycle_count == 50u);
  CHECK(rpt.time_to_full_s == 3600u);
}

static void test_reset_to_known_state(void) {
  reset();
  snapshot(96, 12400, 200, true);
  step(0u);
  snapshot(96, 12500, 10, true);
  step(100u);
  step(2200u);
  CHECK(rpt.state == EC_BATTERY_FULL);

  ec_battery_state_init(&st);
  ec_battery_inputs_init(&in);
  in.pack_present = true;       /* pack restored but data invalidated */
  memset(&in.telemetry, 0, sizeof(in.telemetry));
  step(1u);
  CHECK(rpt.state == EC_BATTERY_UNKNOWN);
  CHECK(rpt.present);           /* pack present but data invalid */
}

static void test_state_name_strings(void) {
  CHECK(strcmp(ec_battery_state_name(EC_BATTERY_UNKNOWN), "Unknown") == 0);
  CHECK(strcmp(ec_battery_state_name(EC_BATTERY_NOT_PRESENT), "Not present") == 0);
  CHECK(strcmp(ec_battery_state_name(EC_BATTERY_DISCHARGING), "Discharging") == 0);
  CHECK(strcmp(ec_battery_state_name(EC_BATTERY_CHARGING), "Charging") == 0);
  CHECK(strcmp(ec_battery_state_name(EC_BATTERY_FULL), "Full") == 0);
}

static void test_default_config_constants(void) {
  cfg = ec_battery_default_config();
  CHECK(cfg.charge_threshold_ma == EC_BATTERY_DEFAULT_CHARGE_THRESHOLD_MA);
  CHECK(cfg.discharge_threshold_ma == EC_BATTERY_DEFAULT_DISCHARGE_THRESHOLD_MA);
  CHECK(cfg.full_current_ma == EC_BATTERY_DEFAULT_FULL_CURRENT_MA);
  CHECK(cfg.full_soc_pct == EC_BATTERY_DEFAULT_FULL_SOC_PCT);
  CHECK(cfg.full_confirm_ms == EC_BATTERY_DEFAULT_FULL_CONFIRM_MS);
}

int main(void) {
  test_initial_unknown();
  test_not_present_overrides();
  test_invalid_data_after_present_is_unknown();
  test_unknown_to_discharging();
  test_unknown_to_charging();
  test_discharging_to_charging();
  test_charging_to_discharging();
  test_charging_to_full_needs_confirm();
  test_charging_to_full_confirmed();
  test_full_stays_full_with_flicker();
  test_full_to_charging();
  test_full_to_discharging_on_unplug();
  test_full_to_discharging_soc_drop();
  test_not_present_returns_to_unknown();
  test_report_fields_populated();
  test_reset_to_known_state();
  test_state_name_strings();
  test_default_config_constants();

  if (failures != 0) {
    fprintf(stderr, "ec_battery_tests: %d failure(s)\n", failures);
    return 1;
  }
  puts("ec_battery_tests: PASS");
  return 0;
}