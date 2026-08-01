#ifndef DUCKTOP2_EC_FAN_H
#define DUCKTOP2_EC_FAN_H

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/*
 * Ducktop2 EC fan control policy.
 *
 * The EC drives a blower with 25 kHz open-drain PWM on PE9/TIM1_CH1 and reads
 * two thermistors: PA7 (skin/chassis) and PB0 (Mu heatsink coldplate).  This
 * pure module computes the duty cycle from the current temperatures; the
 * target side converts the NTC ADC counts to decidegrees Celsius and writes
 * the resulting PWM duty to the timer.
 *
 * User-verified behaviour (row 6):
 *   - "quiet at idle"          -> fan is OFF below the idle threshold
 *   - "performance-biased under load" -> ramp aggressively (never stay quiet if hot)
 *   - "never throttles"        -> reach 100% duty well below the Mu throttle point
 *
 * Design:
 *   - Control temperature is the hotter of the two thermistors, so the fan
 *     protects the CPU (coldplate) and the user (skin) simultaneously.
 *   - Hysteresis: below spin_up the fan stays in its current state across the
 *     idle_off..spin_up band, so a 39-44C workload oscillation never cycles it.
 *   - Anti-cycling: once spinning, the fan runs for at least min_runtime_ms
 *     even if the temperature drops back through idle_off, to avoid rapid
 *     start/stop.  Duty within that window is the normal ramp (not maxed).
 *   - Fail-safe: invalid temperature data forces 100% duty (cool hard when we
 *     cannot measure), matching the project's fail-safe philosophy (here the
 *     safe state for thermal is maximum cooling, not off).
 *   - Linear ramp from min_duty_pct (at spin_up) to max_duty_pct (at
 *     max_duty_temp); above max_duty_temp the duty stays at max.  A
 *     throttle_imminent flag asserts when the temperature reaches
 *     throttle_imminent_temp so higher-level policy (mu_edp_budget) can reduce
 *     PL1 before the Mu firmware throttles on its own.
 */

/*
 * Temperatures are decidegrees Celsius (350 = 35.0C).  int16_t so the module
 * also handles sub-zero readings cleanly, though the fan only warms.
 */
typedef int16_t ec_fan_temp_dc_t;

typedef struct {
  /* Both temperatures in decidegrees C, valid only when temps_valid is true. */
  ec_fan_temp_dc_t skin_dc;
  ec_fan_temp_dc_t mu_coldplate_dc;
  bool temps_valid;
} ec_fan_inputs_t;

/*
 * All temperatures in decidegrees C; all duty values percent 0..100.
 * Defaults (ec_fan_default_config) are deliberately conservative on the
 * quiet end and aggressive on the warm end:
 *
 *   idle_off        400 (40C)  - below this, a running fan can stop
 *   spin_up         450 (45C)  - above this, an idle fan must start
 *   max_duty_temp   700 (70C)  - 100% duty reached here (25-35C below throttle)
 *   throttle_immin  800 (80C)  - warn higher-level policy to reduce PL1
 *   min_duty_pct    30         - quiet but sufficient once running (no stall)
 *   max_duty_pct    100
 *   min_runtime_ms  2000       - anti-cycling minimum run time
 */
typedef struct {
  ec_fan_temp_dc_t idle_off_temp_dc;
  ec_fan_temp_dc_t spin_up_temp_dc;
  ec_fan_temp_dc_t max_duty_temp_dc;
  ec_fan_temp_dc_t throttle_imminent_temp_dc;
  uint8_t min_duty_pct;
  uint8_t max_duty_pct;
  uint32_t min_runtime_ms;
} ec_fan_config_t;

typedef struct {
  bool running;            /* current hysteresis state */
  uint32_t started_ms;     /* timestamp the fan last started (for anti-cycling) */
  bool anti_cycling_hold;  /* min-runtime window active */
} ec_fan_state_t;

typedef struct {
  uint8_t duty_pct;            /* 0..100 PWM duty to write to the timer */
  bool running;                /* fan currently commanded on */
  bool throttle_imminent;      /* temp at/above throttle warning; reduce PL1 */
  bool thermal_fault;          /* temperature data invalid (100% duty forced) */
} ec_fan_output_t;

ec_fan_config_t ec_fan_default_config(void);
void ec_fan_inputs_init(ec_fan_inputs_t *inputs);
void ec_fan_state_init(ec_fan_state_t *state);

/*
 * Advance the fan policy one tick.  now_ms is the EC monotonic timestamp in
 * milliseconds (same clock as ec_controller_step uses).  output is fully
 * rewritten each call.  Call at the EC step rate (e.g. 50 Hz / 20 ms).
 */
void ec_fan_step(const ec_fan_config_t *config,
                 const ec_fan_inputs_t *inputs,
                 ec_fan_state_t *state,
                 uint32_t now_ms,
                 ec_fan_output_t *output);

/* Default thresholds as documented above, exported for tests/target. */
#define EC_FAN_DEFAULT_IDLE_OFF_DC        ((ec_fan_temp_dc_t)400)
#define EC_FAN_DEFAULT_SPIN_UP_DC         ((ec_fan_temp_dc_t)450)
#define EC_FAN_DEFAULT_MAX_DUTY_TEMP_DC   ((ec_fan_temp_dc_t)700)
#define EC_FAN_DEFAULT_THROTTLE_IMMIN_DC  ((ec_fan_temp_dc_t)800)
#define EC_FAN_DEFAULT_MIN_DUTY_PCT       30u
#define EC_FAN_DEFAULT_MAX_DUTY_PCT       100u
#define EC_FAN_DEFAULT_MIN_RUNTIME_MS     2000u

#ifdef __cplusplus
}
#endif

#endif /* DUCKTOP2_EC_FAN_H */