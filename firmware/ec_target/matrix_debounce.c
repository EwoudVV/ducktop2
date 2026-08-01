#include "matrix_scan.h"

/*
 * Pure keyboard debounce state machine (host-testable: no hardware, no
 * register access).  Compiled into the host test harness and linked into the
 * EC target through matrix_scan.c.
 *
 * Time is counted in elapsed ms between consecutive calls (the driver is
 * ticked at 1 kHz, so one call = 1 ms).  Each of the 70 keys owns a uint8_t
 * counter that accumulates consecutive-ms of deviation from its reported
 * state; reaching debounce_ms flips the state and resets the counter.  Any
 * sample that matches the reported state resets that key's counter to zero,
 * which is what filters contact bounce: a bouncing edge keeps returning to
 * the old level and never accumulates enough deviation to flip.
 */

void matrix_debounce_step(const uint16_t raw_rows[MATRIX_SCAN_ROWS],
                          uint16_t stable_rows[MATRIX_SCAN_ROWS],
                          uint8_t counters[MATRIX_SCAN_KEY_COUNT],
                          uint32_t *last_sample_ms,
                          uint32_t now_ms,
                          uint32_t debounce_ms)
{
    uint32_t elapsed = now_ms - *last_sample_ms;

    if (elapsed == 0u) {
        /* Duplicate tick (unchanged timestamp): nothing to accumulate. */
        return;
    }
    *last_sample_ms = now_ms;

    for (uint32_t r = 0u; r < MATRIX_SCAN_ROWS; r++) {
        for (uint32_t c = 0u; c < MATRIX_SCAN_COLS; c++) {
            const uint16_t bit = (uint16_t)(1u << c);
            const uint8_t idx = (uint8_t)(r * MATRIX_SCAN_COLS + c);

            if ((raw_rows[r] & bit) == (stable_rows[r] & bit)) {
                counters[idx] = 0u;
            } else {
                uint32_t acc = (uint32_t)counters[idx] + elapsed;
                if (acc >= debounce_ms) {
                    /* Enough continuous deviation: adopt the raw level. */
                    counters[idx] = 0u;
                    if ((raw_rows[r] & bit) != 0u) {
                        stable_rows[r] |= bit;
                    } else {
                        stable_rows[r] &= (uint16_t)~bit;
                    }
                } else {
                    /* Saturate so an odd tick gap cannot wrap the uint8_t
                     * counter backwards. */
                    counters[idx] =
                        (uint8_t)((acc > UINT8_MAX) ? UINT8_MAX : acc);
                }
            }
        }
    }
}
