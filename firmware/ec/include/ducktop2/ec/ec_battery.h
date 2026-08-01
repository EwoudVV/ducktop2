#ifndef DUCKTOP2_EC_BATTERY_H
#define DUCKTOP2_EC_BATTERY_H

#include "ducktop2/ec/ec_telemetry.h"

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/*
 * Ducktop2 EC battery state machine + OS report.
 *
 * The BQ34Z100-G1 fuel gauge (sheet 01) reports SOC, voltage, current, etc.
 * into ec_telemetry_snapshot_t.  The user-verified behaviour (row 5) is
 * "trusted OS percentage + OLED status": the OLED side is ec_oled; this module
 * produces the trusted battery report that the target forwards to the Mu OS
 * so /sys/class/power_supply/BAT0 shows a real battery (not just a display).
 *
 * What this module adds over the raw telemetry snapshot:
 *  - A proper state enum (DISCHARGING / CHARGING / FULL / NOT_PRESENT / UNKNOWN)
 *    with hysteresis so the state does not flicker at near-zero current
 *    (a full, plugged-in pack alternates CHG/IDLE every call without this).
 *  - Pack presence: the BQ34Z100 is on the protected external pack; if it is
 *    absent the EC must report "no battery" to the OS, not stale data.
 *  - A clean report struct the target sends over USB / I2C-target as the
 *    Linux power_supply class input.
 *
 * Transport (USB HID / CDC / I2C target + the Mu-side driver) is target-only;
 * the state machine + report are what is host-tested here.
 */

typedef enum {
  EC_BATTERY_UNKNOWN = 0,     /* no valid telemetry yet, or just recovered */
  EC_BATTERY_NOT_PRESENT,    /* pack absent (BQ34Z100 probe failed) */
  EC_BATTERY_DISCHARGING,    /* current negative past the discharge threshold */
  EC_BATTERY_CHARGING,       /* current positive past the charge threshold */
  EC_BATTERY_FULL            /* charger connected, current near-zero, SOC high */
} ec_battery_state_t;

/*
 * The report the target forwards to the Mu OS.  All numeric fields are 0 when
 * data_valid is false; the target's power_supply driver maps these to
 * /sys/class/power_supply/BAT0/{capacity,voltage_now,current_now,status,...}.
 */
typedef struct {
  ec_battery_state_t state;
  bool present;              /* pack physically present */
  bool data_valid;           /* critical telemetry fields present */
  uint8_t soc_percent;       /* 0..100 (clamped) */
  uint16_t voltage_mv;       /* pack voltage millivolts */
  int32_t current_ma;        /* signed: + charging, - discharging */
  uint32_t time_to_empty_s;  /* 0 if not discharging or unavailable */
  uint32_t time_to_full_s;   /* 0 if not charging or unavailable */
  uint8_t health_percent;    /* 0..100 */
  uint16_t cycle_count;
} ec_battery_report_t;

/*
 * Inputs.  The target copies the telemetry snapshot from ec_telemetry_step,
 * sets pack_present from the BQ34Z100 I2C probe, and charger_enable from the
 * policy commit output.  Keeping this a plain struct makes the module pure.
 */
typedef struct {
  ec_telemetry_snapshot_t telemetry;
  bool pack_present;         /* BQ34Z100 responded to I2C probe */
  bool charger_enable;      /* charger commanded on by ec_policy */
} ec_battery_inputs_t;

/*
 * Hysteresis config.  The BQ34Z100 current can sit at a few mA when the pack
 * is full + plugged in, so a hard "current > 0 = charging" rule flickers.
 * Thresholds and a confirmation window prevent that.
 *
 * Defaults (ec_battery_default_config):
 *   charge_threshold_ma    50   - above this -> charging
 *   discharge_threshold_ma 50   - below -this -> discharging
 *   full_current_ma        30   - below this (with charger + high SOC) -> full
 *   full_soc_pct           95   - SOC at/above this for the full state
 *   full_confirm_ms        2000 - full condition must hold this long
 */
typedef struct {
  uint16_t charge_threshold_ma;
  uint16_t discharge_threshold_ma;
  uint16_t full_current_ma;
  uint8_t full_soc_pct;
  uint32_t full_confirm_ms;
} ec_battery_config_t;

typedef struct {
  ec_battery_state_t state;
  bool charging_to_full_pending;  /* full-confirmation timer active */
  uint32_t full_confirm_started_ms;
} ec_battery_controller_t;

ec_battery_config_t ec_battery_default_config(void);
void ec_battery_inputs_init(ec_battery_inputs_t *inputs);
void ec_battery_state_init(ec_battery_controller_t *state);

void ec_battery_step(const ec_battery_config_t *config,
                     const ec_battery_inputs_t *inputs,
                     ec_battery_controller_t *state,
                     uint32_t now_ms,
                     ec_battery_report_t *report);

const char *ec_battery_state_name(ec_battery_state_t state);

#define EC_BATTERY_DEFAULT_CHARGE_THRESHOLD_MA    50u
#define EC_BATTERY_DEFAULT_DISCHARGE_THRESHOLD_MA 50u
#define EC_BATTERY_DEFAULT_FULL_CURRENT_MA        30u
#define EC_BATTERY_DEFAULT_FULL_SOC_PCT          95u
#define EC_BATTERY_DEFAULT_FULL_CONFIRM_MS        2000u

#ifdef __cplusplus
}
#endif

#endif /* DUCKTOP2_EC_BATTERY_H */