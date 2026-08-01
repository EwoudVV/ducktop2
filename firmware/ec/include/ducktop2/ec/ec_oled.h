#ifndef DUCKTOP2_EC_OLED_H
#define DUCKTOP2_EC_OLED_H

#include "ducktop2/ec/ec_fan.h"
#include "ducktop2/ec/ec_policy.h"
#include "ducktop2/ec/ec_telemetry.h"

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/*
 * Ducktop2 OLED status content composer.
 *
 * The mainboard carries two SSD1306 128x64 OLEDs behind a TCA9548A I2C mux
 * (ch0 = left, ch1 = right).  The user-verified behaviour (row 7/15) is that
 * both displays show "all system component status": battery % + charge state,
 * source in use + input voltage, fan duty + both thermistor temps, charging
 * current, radio/GNSS state (daughterboard installed), maker status, and EC
 * firmware version.
 *
 * This pure module composes that content into two 8-line text buffers (one per
 * screen).  The line buffers use a fixed 6x8 font assumption (21 chars fit a
 * 128px line, 8 lines fit 64px).  The target-only step that remains is the
 * SSD1306 I2C transaction plus the actual glyph rasterisation into the 128x64
 * 1bpp page buffers; the *content contract* is what is host-tested here.
 *
 * Invalid data renders as dashes so the display never shows a misleading zero
 * or a stale value when telemetry is unavailable (matches the project's
 * fail-safe/explicit-invalid philosophy).
 */

#define EC_OLED_LINE_CHARS 22u  /* 21 visible + NUL */
#define EC_OLED_LINE_COUNT 8u

typedef struct {
  char lines[EC_OLED_LINE_COUNT][EC_OLED_LINE_CHARS];
} ec_oled_screen_t;

typedef struct {
  ec_oled_screen_t left;   /* power & battery */
  ec_oled_screen_t right;  /* thermal, fan, system */
} ec_oled_pages_t;

/*
 * Compose input.  The target's main loop copies the relevant fields from the
 * telemetry snapshot, the policy/commit outputs, the fan step output, and the
 * radio/maker presence inputs.  Keeping this a plain struct (no pointers)
 * makes the composer pure and host-testable.
 */
typedef struct {
  ec_telemetry_snapshot_t telemetry;

  /* Charging source (distinct from telemetry.active_input because the source
   * manager can report a qualified source before the gauge does). */
  ec_source_id_t active_source;
  uint16_t source_input_voltage_mv;   /* qualified input voltage, 0 if none */
  bool source_voltage_valid;
  bool charger_enable;                 /* charger commanded on */

  /* Fan + thermal (from ec_fan step output + its inputs). */
  ec_fan_output_t fan;
  ec_fan_temp_dc_t skin_dc;
  ec_fan_temp_dc_t mu_coldplate_dc;
  bool temps_valid;

  /* Radio daughterboard (GNSS + VHF/UHF live here). */
  bool radio_db_present;
  bool radio_db_fault;

  /* Maker controller. */
  bool maker_online;

  /* EC policy fault state (top-line warning on the right screen). */
  ec_fault_t ec_fault;

  /* Firmware version string (DUCKTOP2_FIRMWARE_VERSION on target). */
  const char *firmware_version;
} ec_oled_inputs_t;

void ec_oled_inputs_init(ec_oled_inputs_t *inputs);
void ec_oled_compose(ec_oled_pages_t *pages, const ec_oled_inputs_t *inputs);

#ifdef __cplusplus
}
#endif

#endif /* DUCKTOP2_EC_OLED_H */