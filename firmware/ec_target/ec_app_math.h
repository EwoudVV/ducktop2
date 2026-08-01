/*
 * Ducktop2 EC app pure math: NTC conversion and fan spin-up duty.
 * Host-tested; no hardware dependencies.
 */

#ifndef DUCKTOP2_EC_APP_MATH_H
#define DUCKTOP2_EC_APP_MATH_H

#include <stdbool.h>
#include <stdint.h>

#include "ducktop2/ec/ec_fan.h"

#ifdef __cplusplus
extern "C" {
#endif

/*
 * NTC conversion: 10 k pull-up to MCU_3V3 (R210/R215), external 10 k
 * NTC (B = 3435) to GND on the 12-bit ADC (VREF = 3.3 V).
 * counts must be 0..4095; returns decidegrees Celsius.
 * 0 counts (shorted) and 4095 counts (open) both map to an "invalid"
 * sentinel so the fan policy fails safe.
 */
#define EC_APP_NTC_ADC_FULL_SCALE   4095u
#define EC_APP_NTC_PULLUP_OHM       10000u
#define EC_APP_NTC_R0_OHM           10000u
#define EC_APP_NTC_BETA             3435u
#define EC_APP_NTC_T0_KELVIN        29815u   /* 25C in decidegrees K */
#define EC_APP_TEMP_INVALID_DC      ((ec_fan_temp_dc_t)-3000) /* invalid sentinel */

ec_fan_temp_dc_t ec_app_ntc_counts_to_temp_dc(uint16_t counts);

/* Fan spin-up: the Delta blower needs >=35% to start; the policy floor is
 * 30%.  Return the duty to write for a running fan that just started. */
#define EC_APP_FAN_MIN_START_DUTY_PCT  35u
#define EC_APP_FAN_SPIN_UP_WINDOW_MS   1000u
uint8_t ec_app_fan_start_duty(uint8_t policy_duty_pct, bool running,
                              uint32_t started_ms, uint32_t now_ms);

#ifdef __cplusplus
}
#endif

#endif /* DUCKTOP2_EC_APP_MATH_H */
