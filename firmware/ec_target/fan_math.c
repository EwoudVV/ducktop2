#include "fan_math.h"

uint16_t fan_rpm_from_period_us(uint32_t period_us, uint16_t pulses_per_rev)
{
    if (period_us == 0u || pulses_per_rev == 0u) {
        return 0u;
    }
    uint32_t pulses_per_min = 60000000u / pulses_per_rev;
    uint32_t rpm = pulses_per_min / period_us;
    if (rpm > UINT16_MAX) {
        return UINT16_MAX;
    }
    return (uint16_t)rpm;
}

bool fan_tach_is_fresh(uint32_t last_edge_ms, uint32_t now_ms,
                       uint32_t window_ms)
{
    return (now_ms - last_edge_ms) < window_ms;
}

uint32_t fan_pwm_ccr_from_duty(uint16_t duty_percent, uint32_t period_ticks)
{
    uint32_t duty = (duty_percent > 100u) ? 100u : duty_percent;
    uint32_t complement = 100u - duty;
    return (period_ticks / 100u) * complement
         + (period_ticks % 100u) * complement / 100u;
}
