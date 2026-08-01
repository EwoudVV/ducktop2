#include "ducktop2/ec/ec_oled.h"
#include "ducktop2/ec/ec_fan.h"
#include "ducktop2/ec/ec_policy.h"
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

#define LINE_EQ(screen, idx, expected)                                        \
  CHECK(strcmp((screen).lines[(idx)], (expected)) == 0)

static ec_oled_inputs_t in;
static ec_oled_pages_t pages;

static void reset(void) {
  ec_oled_inputs_init(&in);
}

/* Set the telemetry snapshot with all common valid flags + charging values. */
static void charging_snapshot(void) {
  ec_telemetry_snapshot_t *t = &in.telemetry;
  memset(t, 0, sizeof(*t));
  t->valid_flags =
      EC_TELEMETRY_VALID_SOC | EC_TELEMETRY_VALID_PACK_VOLTAGE |
      EC_TELEMETRY_VALID_PACK_CURRENT | EC_TELEMETRY_VALID_PACK_POWER |
      EC_TELEMETRY_VALID_TIME_TO_FULL |
      EC_TELEMETRY_VALID_REMAINING_CAPACITY |
      EC_TELEMETRY_VALID_FULL_CAPACITY | EC_TELEMETRY_VALID_CYCLE_COUNT |
      EC_TELEMETRY_VALID_HEALTH | EC_TELEMETRY_VALID_ACTIVE_INPUT;
  t->soc_percent = 80u;
  t->health_percent = 95u;
  t->pack_voltage_mv = 12400u;
  t->pack_current_ma = 1500;
  t->charge_power_mw = 18000u;
  t->time_to_full_s = 5400u;  /* 1h30m */
  t->remaining_capacity_mah = 4000u;
  t->full_capacity_mah = 5000u;
  t->cycle_count = 120u;
  t->active_input = EC_TELEMETRY_INPUT_PD1;
}

static void discharging_snapshot(void) {
  ec_telemetry_snapshot_t *t = &in.telemetry;
  memset(t, 0, sizeof(*t));
  t->valid_flags =
      EC_TELEMETRY_VALID_SOC | EC_TELEMETRY_VALID_PACK_VOLTAGE |
      EC_TELEMETRY_VALID_PACK_CURRENT | EC_TELEMETRY_VALID_PACK_POWER |
      EC_TELEMETRY_VALID_TIME_TO_EMPTY |
      EC_TELEMETRY_VALID_REMAINING_CAPACITY |
      EC_TELEMETRY_VALID_FULL_CAPACITY | EC_TELEMETRY_VALID_CYCLE_COUNT |
      EC_TELEMETRY_VALID_HEALTH | EC_TELEMETRY_VALID_ACTIVE_INPUT;
  t->soc_percent = 42u;
  t->health_percent = 95u;
  t->pack_voltage_mv = 11600u;
  t->pack_current_ma = -1200;
  t->discharge_power_mw = 14000u;
  t->time_to_empty_s = 7200u;  /* 2h0m */
  t->remaining_capacity_mah = 2100u;
  t->full_capacity_mah = 5000u;
  t->cycle_count = 120u;
  t->active_input = EC_TELEMETRY_INPUT_PACK;
}

static void test_initial_state_placeholders(void) {
  reset();
  ec_oled_compose(&pages, &in);
  /* Left: everything unknown. */
  LINE_EQ(pages.left, 0, "SRC none");
  LINE_EQ(pages.left, 1, "BAT --% IDLE");
  LINE_EQ(pages.left, 2, "V ----V");
  LINE_EQ(pages.left, 3, "I ----mA");
  LINE_EQ(pages.left, 4, "P ----mW");
  LINE_EQ(pages.left, 5, "T  --");
  LINE_EQ(pages.left, 6, "CAP ----/----mAh");
  LINE_EQ(pages.left, 7, "CYC -- H --");
  /* Right: defaults. */
  LINE_EQ(pages.right, 0, "FAN 0% STOP");
  LINE_EQ(pages.right, 1, "TSKIN ----C");
  LINE_EQ(pages.right, 2, "TMU  ----C");
  LINE_EQ(pages.right, 3, "THROTTLE ok");
  LINE_EQ(pages.right, 4, "RAD no DB");
  LINE_EQ(pages.right, 5, "MAKER offline");
  LINE_EQ(pages.right, 6, "EC ----");
  LINE_EQ(pages.right, 7, "FAULT none");
}

static void test_charging_layout(void) {
  reset();
  charging_snapshot();
  in.active_source = EC_SOURCE_PD1;
  in.source_input_voltage_mv = 15000u;
  in.source_voltage_valid = true;
  in.charger_enable = true;
  in.fan.duty_pct = 45u;
  in.fan.running = true;
  in.fan.thermal_fault = false;
  in.fan.throttle_imminent = false;
  in.skin_dc = 305;   /* 30.5C */
  in.mu_coldplate_dc = 412; /* 41.2C */
  in.temps_valid = true;
  in.radio_db_present = true;
  in.radio_db_fault = false;
  in.maker_online = true;
  in.ec_fault = EC_FAULT_NONE;
  in.firmware_version = "0.3.0-policy";

  ec_oled_compose(&pages, &in);

  LINE_EQ(pages.left, 0, "SRC PD1 15.0V");
  LINE_EQ(pages.left, 1, "BAT 80% CHG");
  LINE_EQ(pages.left, 2, "V 12.4V");
  LINE_EQ(pages.left, 3, "I +1500mA");
  LINE_EQ(pages.left, 4, "P 18000mW CHG");
  LINE_EQ(pages.left, 5, "TTF 1h30m");
  LINE_EQ(pages.left, 6, "CAP 4000/5000mAh");
  LINE_EQ(pages.left, 7, "CYC 120 H 95%");

  LINE_EQ(pages.right, 0, "FAN 45% RUN");
  LINE_EQ(pages.right, 1, "TSKIN 30.5C");
  LINE_EQ(pages.right, 2, "TMU  41.2C");
  LINE_EQ(pages.right, 3, "THROTTLE ok");
  LINE_EQ(pages.right, 4, "RAD DB OK");
  LINE_EQ(pages.right, 5, "MAKER online");
  LINE_EQ(pages.right, 6, "EC 0.3.0-policy");
  LINE_EQ(pages.right, 7, "FAULT none");
}

static void test_discharging_layout(void) {
  reset();
  discharging_snapshot();
  in.active_source = EC_SOURCE_PACK;
  in.source_voltage_valid = false;  /* no external source */
  in.charger_enable = false;
  in.fan.duty_pct = 0u;
  in.fan.running = false;
  in.temps_valid = true;
  in.skin_dc = 280;
  in.mu_coldplate_dc = 390;

  ec_oled_compose(&pages, &in);

  LINE_EQ(pages.left, 0, "SRC PACK ----V");
  LINE_EQ(pages.left, 1, "BAT 42% DISC");
  LINE_EQ(pages.left, 2, "V 11.6V");
  LINE_EQ(pages.left, 3, "I -1200mA");
  LINE_EQ(pages.left, 4, "P 14000mW DISC");
  LINE_EQ(pages.left, 5, "TTE 2h0m");

  LINE_EQ(pages.right, 0, "FAN 0% STOP");
}

static void test_source_voltage_invalid_shows_dashes(void) {
  reset();
  in.active_source = EC_SOURCE_PD2;
  in.source_voltage_valid = false;
  ec_oled_compose(&pages, &in);
  LINE_EQ(pages.left, 0, "SRC PD2 ----V");
}

static void test_aux_source_with_voltage(void) {
  reset();
  in.active_source = EC_SOURCE_AUX;
  in.source_input_voltage_mv = 19200u;
  in.source_voltage_valid = true;
  ec_oled_compose(&pages, &in);
  LINE_EQ(pages.left, 0, "SRC AUX 19.2V");
}

static void test_thermal_fault_overrides_fan_line(void) {
  reset();
  in.fan.thermal_fault = true;
  ec_oled_compose(&pages, &in);
  LINE_EQ(pages.right, 0, "FAN 100% FAULT");
}

static void test_throttle_warn_renders(void) {
  reset();
  in.fan.throttle_imminent = true;
  ec_oled_compose(&pages, &in);
  LINE_EQ(pages.right, 3, "THROTTLE WARN");
}

static void test_invalid_temps_render_dashes(void) {
  reset();
  in.temps_valid = false;
  ec_oled_compose(&pages, &in);
  LINE_EQ(pages.right, 1, "TSKIN ----C");
  LINE_EQ(pages.right, 2, "TMU  ----C");
}

static void test_negative_temp_format(void) {
  reset();
  in.temps_valid = true;
  in.skin_dc = -50;   /* -5.0C */
  in.mu_coldplate_dc = -55; /* -5.5C */
  ec_oled_compose(&pages, &in);
  LINE_EQ(pages.right, 1, "TSKIN -5.0C");
  LINE_EQ(pages.right, 2, "TMU  -5.5C");
}

static void test_radio_present_ok_and_fault(void) {
  reset();
  in.radio_db_present = true;
  in.radio_db_fault = false;
  ec_oled_compose(&pages, &in);
  LINE_EQ(pages.right, 4, "RAD DB OK");

  in.radio_db_fault = true;
  ec_oled_compose(&pages, &in);
  LINE_EQ(pages.right, 4, "RAD DB FAULT");
}

static void test_radio_absent(void) {
  reset();
  in.radio_db_present = false;
  ec_oled_compose(&pages, &in);
  LINE_EQ(pages.right, 4, "RAD no DB");
}

static void test_maker_online_offline(void) {
  reset();
  in.maker_online = true;
  ec_oled_compose(&pages, &in);
  LINE_EQ(pages.right, 5, "MAKER online");

  in.maker_online = false;
  ec_oled_compose(&pages, &in);
  LINE_EQ(pages.right, 5, "MAKER offline");
}

static void test_fault_names_render(void) {
  reset();
  in.ec_fault = EC_FAULT_CHARGER;
  ec_oled_compose(&pages, &in);
  LINE_EQ(pages.right, 7, "FAULT CHARGER");

  in.ec_fault = EC_FAULT_THERMAL;
  ec_oled_compose(&pages, &in);
  LINE_EQ(pages.right, 7, "FAULT THERMAL");
}

static void test_reset_between_calls(void) {
  reset();
  charging_snapshot();
  in.active_source = EC_SOURCE_PD1;
  in.source_input_voltage_mv = 15000u;
  in.source_voltage_valid = true;
  in.firmware_version = "0.3.0-policy";
  ec_oled_compose(&pages, &in);
  CHECK(strcmp(pages.left.lines[0], "SRC none") != 0);
  LINE_EQ(pages.left, 0, "SRC PD1 15.0V");

  /* Second compose from a blank input must fully overwrite every line. */
  ec_oled_inputs_init(&in);
  ec_oled_compose(&pages, &in);
  LINE_EQ(pages.left, 0, "SRC none");
  LINE_EQ(pages.right, 6, "EC ----");
}

static void test_firmware_version_null_renders_placeholder(void) {
  reset();
  in.firmware_version = NULL;
  ec_oled_compose(&pages, &in);
  LINE_EQ(pages.right, 6, "EC ----");
}

static void test_hhmm_cap_at_99h(void) {
  reset();
  discharging_snapshot();
  in.telemetry.time_to_empty_s = 400000u;  /* > 99h */
  ec_oled_compose(&pages, &in);
  LINE_EQ(pages.left, 5, "TTE 99h+");
}

int main(void) {
  test_initial_state_placeholders();
  test_charging_layout();
  test_discharging_layout();
  test_source_voltage_invalid_shows_dashes();
  test_aux_source_with_voltage();
  test_thermal_fault_overrides_fan_line();
  test_throttle_warn_renders();
  test_invalid_temps_render_dashes();
  test_negative_temp_format();
  test_radio_present_ok_and_fault();
  test_radio_absent();
  test_maker_online_offline();
  test_fault_names_render();
  test_reset_between_calls();
  test_firmware_version_null_renders_placeholder();
  test_hhmm_cap_at_99h();

  if (failures != 0) {
    fprintf(stderr, "ec_oled_tests: %d failure(s)\n", failures);
    return 1;
  }
  puts("ec_oled_tests: PASS");
  return 0;
}