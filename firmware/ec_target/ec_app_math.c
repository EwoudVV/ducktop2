/*
 * Ducktop2 EC app pure math (implementation).  See ec_app_math.h.
 *
 * The NTC conversion uses a fixed lookup table (integer arithmetic only:
 * the target builds freestanding with -nostdinc, so libm is unavailable).
 * The table is generated from the analytic 10k-NTC model and verified by
 * the host tests against that model.
 */

#include "ec_app_math.h"

#include "ntc_temp_table.inc"

ec_fan_temp_dc_t ec_app_ntc_counts_to_temp_dc(uint16_t counts)
{
    if (counts == 0u || counts >= EC_APP_NTC_ADC_FULL_SCALE) {
        return EC_APP_TEMP_INVALID_DC;
    }

    const uint16_t step = 16u;   /* counts per table entry */
    uint16_t index = counts / step;
    uint16_t fraction = counts % step;
    if (index + 1u >= 257u) {
        return EC_APP_TEMP_INVALID_DC;
    }

    int32_t lo = k_ntc_temp_dc_table[index];
    int32_t hi = k_ntc_temp_dc_table[index + 1u];
    int32_t interpolated = lo + ((hi - lo) * (int32_t)fraction) / (int32_t)step;
    if (interpolated == EC_APP_TEMP_INVALID_DC) {
        return EC_APP_TEMP_INVALID_DC;
    }
    return (ec_fan_temp_dc_t)interpolated;
}

uint8_t ec_app_fan_start_duty(uint8_t policy_duty_pct, bool running,
                              uint32_t started_ms, uint32_t now_ms)
{
    if (!running) {
        return 0u;
    }
    if (policy_duty_pct >= EC_APP_FAN_MIN_START_DUTY_PCT) {
        return policy_duty_pct;
    }
    /* Running below the Delta start threshold: hold the start duty during
     * the spin-up window, then hand back to the policy value. */
    if ((now_ms - started_ms) < EC_APP_FAN_SPIN_UP_WINDOW_MS) {
        return EC_APP_FAN_MIN_START_DUTY_PCT;
    }
    return policy_duty_pct;
}
