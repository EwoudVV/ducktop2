#include "fan_math.h"

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

static void test_rpm_period_conversion(void) {
  /* 0.6 s pulse period at 2 ppr = 50 RPM. */
  CHECK(fan_rpm_from_period_us(600000u, 2u) == 50u);
  /* 10 ms period = 3000 RPM (half the 6000 RPM/20 ms pair). */
  CHECK(fan_rpm_from_period_us(10000u, 2u) == 3000u);
  /* Delta BFB04512HHA maximum: 6100 RPM -> 4918 us per pulse (2 ppr). */
  CHECK(fan_rpm_from_period_us(4918u, 2u) == 6100u);
  /* 60 ms period = 500 RPM. */
  CHECK(fan_rpm_from_period_us(60000u, 2u) == 500u);
  /* A 4-pulse-per-rev fan at 10 ms pulses is twice the RPM. */
  CHECK(fan_rpm_from_period_us(10000u, 4u) == 1500u);
  /* One pulse per minute is 0.5 RPM, truncated to 0 RPM. */
  CHECK(fan_rpm_from_period_us(60000000u, 2u) == 0u);
}

static void test_rpm_edge_cases(void) {
  /* No signal / stalled fan: zero period reads as stopped. */
  CHECK(fan_rpm_from_period_us(0u, 2u) == 0u);
  /* Invalid pulses-per-rev factor. */
  CHECK(fan_rpm_from_period_us(10000u, 0u) == 0u);
  /* Absurdly short periods clamp at the uint16 ceiling: 30000000/457
   * exceeds 65535; 458 us already fits. */
  CHECK(fan_rpm_from_period_us(1u, 2u) == UINT16_MAX);
  CHECK(fan_rpm_from_period_us(100u, 2u) == UINT16_MAX); /* 300k RPM */
  CHECK(fan_rpm_from_period_us(457u, 2u) == UINT16_MAX);
  CHECK(fan_rpm_from_period_us(458u, 2u) == 65502u);
  CHECK(fan_rpm_from_period_us(459u, 2u) == 65359u);
}

static void test_freshness_window(void) {
  CHECK(fan_tach_is_fresh(100u, 349u, 250u));
  CHECK(fan_tach_is_fresh(100u, 350u, 250u) == false); /* boundary */
  CHECK(fan_tach_is_fresh(100u, 2000u, 250u) == false);
  CHECK(fan_tach_is_fresh(100u, 100u, 250u)); /* same tick */
  /* Tick wrap-around must not poison the window: 101 + 100 = 202 ms. */
  CHECK(fan_tach_is_fresh(UINT32_MAX - 100u, 101u, 250u));
  /* 101 + 200 = 302 ms across the wrap -> stale. */
  CHECK(fan_tach_is_fresh(UINT32_MAX - 200u, 101u, 250u) == false);
  /* Zero-length window: only a fresh edge in the same tick survives. */
  CHECK(fan_tach_is_fresh(5u, 5u, 0u) == false);
}

static void test_pwm_duty_complement(void) {
  const uint32_t period = 3360u; /* 84 MHz / 25 kHz */
  /* 100% speed -> pin held low (FET off, floating input = full speed). */
  CHECK(fan_pwm_ccr_from_duty(100u, period) == 0u);
  /* 0% speed -> pin held high (fan stopped). */
  CHECK(fan_pwm_ccr_from_duty(0u, period) == period);
  /* 50% -> half the period high. */
  CHECK(fan_pwm_ccr_from_duty(50u, period) == 1680u);
  /* Policy floor 30% and fan minimum start duty 35%. */
  CHECK(fan_pwm_ccr_from_duty(30u, period) == 2352u);
  CHECK(fan_pwm_ccr_from_duty(35u, period) == 2184u);
  /* Duty above 100 clamps to full speed. */
  CHECK(fan_pwm_ccr_from_duty(150u, period) == 0u);
  /* 1% steps: 99% of the period, truncated, not rounded up. */
  CHECK(fan_pwm_ccr_from_duty(1u, period) == 3326u);
  /* Odd periods keep the complement exact. */
  CHECK(fan_pwm_ccr_from_duty(0u, 3359u) == 3359u);
  CHECK(fan_pwm_ccr_from_duty(100u, 3359u) == 0u);
  /* Zero tick period: no timer, no output. */
  CHECK(fan_pwm_ccr_from_duty(50u, 0u) == 0u);
  /* Near-uint32 period_ticks must not overflow the multiplication. */
  CHECK(fan_pwm_ccr_from_duty(0u, UINT32_MAX) == UINT32_MAX);
  CHECK(fan_pwm_ccr_from_duty(100u, UINT32_MAX) == 0u);
  CHECK(fan_pwm_ccr_from_duty(50u, UINT32_MAX) == 2147483647u);
}

int main(void) {
  test_rpm_period_conversion();
  test_rpm_edge_cases();
  test_freshness_window();
  test_pwm_duty_complement();

  if (failures != 0) {
    fprintf(stderr, "fan_math_tests: %d failure(s)\n", failures);
    return 1;
  }
  puts("fan_math_tests: PASS");
  return 0;
}
