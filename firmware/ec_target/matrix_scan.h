#ifndef DUCKTOP2_MATRIX_SCAN_H
#define DUCKTOP2_MATRIX_SCAN_H

/*
 * Ducktop2 EC keyboard matrix scan driver (5x14).
 *
 * Scan contract (locked by the schematic,
 * gen/generate_keyboard_daughterboard_sheet.py): the fabricated MX ULP
 * keyboard is a 5x14 diode matrix (rows 0-4, columns 0-13; KB_ROW5-7 and
 * KB_COL14-15 stay routed as spare EC GPIO).  Each key path is
 *
 *     KB_ROWn -> diode (anode on KB_ROWn, cathode at the per-key switch
 *                node) -> switch -> KB_COLm
 *
 * so the only valid scan is: drive one column LOW at a time (every other
 * column HIGH), read the rows with pull-ups; a pressed key pulls its row LOW
 * while its column is driven LOW.  The reversed polarity (drive rows, read
 * columns) cannot work with this diode orientation.
 *
 * The scan produces the row-major debounced matrix consumed by the pure
 * keymap layer (ec_keymap.h): bit m of rows[r] set means key (r, m) is
 * pressed.  matrix_scan_tick() is the hardware half and must be called at
 * 1 kHz from the SysTick context (one column pass per tick, no blocking
 * waits, no I2C); matrix_debounce_step() is the pure, host-testable debounce
 * state machine and is compiled into the host test harness.
 */

#include <stdbool.h>
#include <stdint.h>

#include "ducktop2/ec/ec_keymap.h"

/* 5x14 matrix contract (verified against the schematic and the EC MCU pin
 * mapping; see matrix_scan.c for the port/pin table). */
#define MATRIX_SCAN_ROWS 5u
#define MATRIX_SCAN_COLS 14u
#define MATRIX_SCAN_KEY_COUNT (MATRIX_SCAN_ROWS * MATRIX_SCAN_COLS)

/* A key state changes only after this many consecutive identical samples
 * (15 samples = 15 ms at the 1 kHz scan rate). */
#define MATRIX_SCAN_DEBOUNCE_MS 15u

/*
 * Configure the matrix GPIOs: rows as inputs with pull-ups, columns as
 * push-pull outputs driven HIGH (inactive).  Self-guarding (init-once flag);
 * on a second call it is a no-op.  If the static port/pin configuration
 * fails validation the driver stays un-initialized and every tick reports an
 * all-release matrix (fail-safe: never report a stuck key).
 */
void matrix_scan_init(void);

/*
 * One full scan pass: drive each column low in turn, sample the five rows,
 * restore the column, then feed the raw snapshot through the debounce state
 * machine.  Callable at 1 kHz from SysTick; the raw pass is a few
 * microseconds so the whole tick stays short.  Until matrix_scan_init() has
 * succeeded the reported matrix is all-release.
 */
void matrix_scan_tick(uint32_t now_ms);

/*
 * Copy the latest debounced matrix.  The owner calls this at policy rate
 * (e.g. 50 Hz) and hands the result to ec_keymap_process().
 */
void matrix_scan_get_matrix(ec_keymap_matrix_t *out);

/*
 * Pure debounce step (no hardware): updates the debounced row bitmask from a
 * raw row-major snapshot.  raw_rows is one freshly scanned 5x14 snapshot;
 * stable_rows and counters hold persistent state owned by the caller.
 *
 * Semantics: a key's reported state changes only after debounce_ms of
 * continuous deviation from its current reported state, where time is
 * measured as the elapsed ms between consecutive calls (now_ms -
 * *last_sample_ms, wrap-safe).  Each key keeps its own uint8_t counter of
 * accumulated deviation ms; the counter resets to zero whenever the raw
 * sample matches the reported state, so a bouncing edge (which repeatedly
 * returns to the old level) never accumulates and never reports.  At the
 * 1 kHz contract rate this is exactly "15 consecutive identical samples".
 *
 * debounce_ms is bounded by 255 (the counters are uint8_t); debounce_ms == 0
 * reports any deviation on the next sample.  last_sample_ms is updated to
 * now_ms on every call (an unchanged timestamp is a duplicate tick and is
 * ignored).  Callers must not read/write stable_rows/counters from multiple
 * contexts without their own synchronization.
 */
void matrix_debounce_step(const uint16_t raw_rows[MATRIX_SCAN_ROWS],
                          uint16_t stable_rows[MATRIX_SCAN_ROWS],
                          uint8_t counters[MATRIX_SCAN_KEY_COUNT],
                          uint32_t *last_sample_ms,
                          uint32_t now_ms,
                          uint32_t debounce_ms);

#endif /* DUCKTOP2_MATRIX_SCAN_H */
