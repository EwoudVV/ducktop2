#ifndef DUCKTOP2_PACK_CURRENT_H
#define DUCKTOP2_PACK_CURRENT_H
#include "board_profile.h"
#include <stdbool.h>
#include <stdint.h>

/* Measurement contract, in nominal 10mOhm/x1 current units:
 * reported >= actual * shunt_min * ADC_gain_min - offset - one ADC code.
 * Coefficients must cover the installed discharge ADC, not just BMON's
 * named analog accuracy points. The separate dynamic reserve covers rise
 * between measurement and effective load reduction/turnoff. */
static inline bool ec_pack_current_upper_bound(int16_t nominal_ma,
                                               int32_t *signed_bound_ma)
{
#if !DUCKTOP2_PACK_DISCHARGE_SENSE_QUALIFIED || !DUCKTOP2_DISCHARGE_SENSE_MIN_PERMILLE || !DUCKTOP2_DISCHARGE_GAIN_MIN_PERMILLE
    (void)nominal_ma;
    (void)signed_bound_ma;
    return false;
#else
    if (!signed_bound_ma) return false;
    const uint32_t denominator=(uint32_t)DUCKTOP2_DISCHARGE_SENSE_MIN_PERMILLE *
        DUCKTOP2_DISCHARGE_GAIN_MIN_PERMILLE;
    if (!denominator) return false;
    /* A positive sample is charging. Its independent <=3A regulation and
     * hardware charge guard remain separate from this discharge estimate. */
    if (nominal_ma > 0) {
        *signed_bound_ma=nominal_ma;
        return true;
    }
    uint32_t magnitude=(uint32_t)(-(int32_t)nominal_ma);
    /* 44.4mA/code, rounded outwards. Include zero-code quantization too. */
    uint64_t numerator=((uint64_t)magnitude+45u+DUCKTOP2_DISCHARGE_OFFSET_MA)*1000000u;
    uint64_t upper=(numerator+denominator-1u)/denominator;
    if (upper > 32767u) return false;
    *signed_bound_ma=-(int32_t)upper;
    return true;
#endif
}
#endif
