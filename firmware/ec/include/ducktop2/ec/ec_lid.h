#ifndef DUCKTOP2_EC_LID_H
#define DUCKTOP2_EC_LID_H

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/*
 * Ducktop2 EC lid switch debouncer + edge detector.
 *
 * The lid sensor is a hall/reed switch on J53 (sheet 08) with R209 10k
 * pull-up to MCU_3V3.  LID_CLOSED_N is active-low: HIGH (logic 1) = lid open,
 * LOW (logic 0) = lid closed.  The EC reads this on pin 41 (PE10).
 *
 * User-verified behaviour (row 1): closing the lid turns the *display* off but
 * the Mu keeps running (NOT sleep/S3); opening it brings the display back
 * instantly (no power cycle).  The EC never sequences the Mu power on lid
 * events — that is the OS's job via an ACPI lid switch input.  "Mu keeps
 * running" means the EC must NOT trigger S3/S5; the display-off is an OS-side
 * policy (HandleLidSwitch turns the backlight off, not suspend).
 *
 * This module supplies the host-tested pure-C core: it debounces the noisy
 * hall/reed reading into a stable `lid_closed` bool and emits one-shot edge
 * flags the target forwards as ACPI lid events.  The target side (reading the
 * GPIO + dispatching the ACPI report) is a later step; the debouncer contract
 * is what is host-tested here.
 *
 * Fail-safe: R209 pulls LID_CLOSED_N HIGH when the sensor disconnects, so a
 * broken cable reads "lid open" (display on).  This is the correct safe
 * default and requires no special code here — the module honestly reports
 * whatever its (debounced) input says.
 */

/*
 * Raw reading of LID_CLOSED_N.  true = logic HIGH = lid open; false = logic
 * LOW = lid closed.  The target inverts the GPIO input level to this bool if
 * its read returns active-low-when-closed directly.
 */
typedef struct {
  bool lid_open_raw;   /* true = open (LID_CLOSED_N high), false = closed (low) */
} ec_lid_inputs_t;

typedef struct {
  uint32_t debounce_ms;   /* raw reading must persist this long before the
                            * stable state changes (anti-bounce). */
} ec_lid_config_t;

typedef struct {
  bool lid_closed;         /* stable debounced state: true = lid closed */
  bool just_closed;        /* one-shot: transitioned open->closed this call */
  bool just_opened;        /* one-shot: transitioned closed->open this call */
} ec_lid_output_t;

/*
 * Internal state.  The target keeps one of these between calls; tests can
 * inspect it.  Invariant: once stable, `lid_closed` only changes when a raw
 * reading disagrees with it for at least debounce_ms.
 */
typedef struct {
  bool lid_closed;          /* current stable state */
  bool pending_state;       /* the candidate state if a raw disagreement is in
                             * progress (valid while timer_running) */
  bool timer_running;       /* a disagreement timer is active */
  uint32_t started_ms;      /* timestamp the disagreement started */
  /* Edge latches: set on a stable transition, cleared on the next step so
   * each edge is reported exactly once. */
  bool just_closed;
  bool just_opened;
} ec_lid_state_t;

ec_lid_config_t ec_lid_default_config(void);
void ec_lid_inputs_init(ec_lid_inputs_t *inputs);
void ec_lid_state_init(ec_lid_state_t *state);

/*
 * Advance the lid policy one tick.  now_ms is the EC monotonic timestamp
 * (same clock as ec_controller_step).  output is fully rewritten each call;
 * edge flags reflect transitions that became stable during *this* call and
 * clear on the next.  Call at the EC step rate (e.g. 50 Hz / 20 ms).
 */
void ec_lid_step(const ec_lid_config_t *config,
                 const ec_lid_inputs_t *inputs,
                 ec_lid_state_t *state,
                 uint32_t now_ms,
                 ec_lid_output_t *output);

#define EC_LID_DEFAULT_DEBOUNCE_MS 30u

#ifdef __cplusplus
}
#endif

#endif /* DUCKTOP2_EC_LID_H */