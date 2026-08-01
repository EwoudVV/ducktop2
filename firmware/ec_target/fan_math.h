#ifndef DUCKTOP2_FAN_MATH_H
#define DUCKTOP2_FAN_MATH_H

#include <stdbool.h>
#include <stdint.h>

/*
 * Pure, host-testable fan sensing math.  These helpers have no hardware
 * access; the target glue (gpio.c) and the host test suite share them.
 */

/*
 * RPM from the period between two consecutive tach pulses, in microseconds.
 * The Delta BFB04512HHA FG output emits pulses_per_rev (2) pulses per
 * revolution, so RPM = 60e6 / (pulses_per_rev * period_us).  Returns 0 for a
 * zero period or zero pulses_per_rev (no signal / stalled fan) and clamps at
 * UINT16_MAX for absurdly short periods.
 */
uint16_t fan_rpm_from_period_us(uint32_t period_us, uint16_t pulses_per_rev);

/*
 * True while the most recent tach edge is less than window_ms behind now_ms.
 * Both timestamps come from the monotonic EC millisecond tick, so the
 * unsigned subtraction is wrap-safe around the 32-bit tick counter.
 */
bool fan_tach_is_fresh(uint32_t last_edge_ms, uint32_t now_ms,
                       uint32_t window_ms);

/*
 * CCR1 value for TIM1_CH1 PWM1 (PE9) that commands duty_percent fan speed
 * through the open-drain sink stage (Q200, 2N7002KT1G): the fan's PWM input
 * is active-high (0% duty stops the fan, floating input = full speed) and
 * Q200 inverts the MCU pin, so the pin high-time must be the complement
 * (100 - duty_percent)%.  duty_percent is clamped to 0..100; period_ticks is
 * the timer period in ticks (ARR + 1).  Returns period_ticks for duty 0
 * (pin held high the whole period, fan stopped) and 0 for duty 100 (pin
 * held low, fan at full speed).  Exact for every uint32 period_ticks.
 */
uint32_t fan_pwm_ccr_from_duty(uint16_t duty_percent, uint32_t period_ticks);

#endif /* DUCKTOP2_FAN_MATH_H */
