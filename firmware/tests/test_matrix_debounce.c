#include "matrix_scan.h"

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

static uint16_t s_raw[MATRIX_SCAN_ROWS];
static uint16_t s_stable[MATRIX_SCAN_ROWS];
static uint8_t s_counters[MATRIX_SCAN_KEY_COUNT];
static uint32_t s_last_ms;

/* Reset all debounce state.  base_ms is the wall-clock time of the last
 * sample tick: every later step must use a strictly increasing timestamp so
 * the elapsed-time semantics of the state machine see 1 ms per tick (a big
 * forward jump is legal but counts as that many ms of deviation). */
static void state_reset(uint32_t base_ms) {
  for (uint32_t r = 0; r < MATRIX_SCAN_ROWS; r++) {
    s_raw[r] = 0u;
    s_stable[r] = 0u;
  }
  for (uint32_t i = 0; i < MATRIX_SCAN_KEY_COUNT; i++) {
    s_counters[i] = 0u;
  }
  s_last_ms = base_ms;
}

static void press(uint32_t row, uint32_t col) {
  s_raw[row] |= (uint16_t)(1u << col);
}

static void release(uint32_t row, uint32_t col) {
  s_raw[row] &= (uint16_t)~(1u << col);
}

static void step_at(uint32_t now_ms, uint32_t debounce_ms) {
  matrix_debounce_step(s_raw, s_stable, s_counters, &s_last_ms, now_ms,
                       debounce_ms);
}

static void step(uint32_t now_ms) {
  step_at(now_ms, MATRIX_SCAN_DEBOUNCE_MS);
}

static bool is_down(uint32_t row, uint32_t col) {
  return (s_stable[row] & (uint16_t)(1u << col)) != 0u;
}

/* base_ms must equal s_last_ms (the timestamp of the previous tick).  Steps
 * once per ms while raw stays deviated from the reported state; verify the
 * key does not report until the 15th consecutive sample and reports exactly
 * then. */
static void hold_until_reported(uint32_t base_ms, uint32_t row, uint32_t col) {
  for (uint32_t i = 0u; i + 1u < MATRIX_SCAN_DEBOUNCE_MS; i++) {
    step(base_ms + 1u + i);
    CHECK(is_down(row, col) == false);
  }
  step(base_ms + MATRIX_SCAN_DEBOUNCE_MS);
  CHECK(is_down(row, col));
}

/* Mirror image of hold_until_reported for a sustained release. */
static void hold_released_until_clear(uint32_t base_ms, uint32_t row,
                                      uint32_t col) {
  for (uint32_t i = 0u; i + 1u < MATRIX_SCAN_DEBOUNCE_MS; i++) {
    step(base_ms + 1u + i);
    CHECK(is_down(row, col));
  }
  step(base_ms + MATRIX_SCAN_DEBOUNCE_MS);
  CHECK(is_down(row, col) == false);
}

static void test_hold_reports_after_threshold(void) {
  state_reset(1000u);
  press(0u, 0u);
  hold_until_reported(1000u, 0u, 0u);
  /* Held: stays reported. */
  for (uint32_t t = MATRIX_SCAN_DEBOUNCE_MS + 1u; t <= 30u; t++) {
    step(1000u + t);
    CHECK(is_down(0u, 0u));
  }
  /* Corner key on the opposite edge of the matrix. */
  state_reset(2000u);
  press(4u, 13u);
  hold_until_reported(2000u, 4u, 13u);
  CHECK(is_down(0u, 0u) == false); /* no cross-talk */
}

static void test_bounce_is_filtered(void) {
  state_reset(3000u);
  press(2u, 7u);
  /* Chattering edge: alternate pressed/released every ms.  Each time the
   * sample matches the reported state the counter resets, so the deviation
   * never accumulates to the threshold. */
  for (uint32_t t = 1u; t <= 40u; t++) {
    if ((t % 2u) != 0u) {
      press(2u, 7u);
    } else {
      release(2u, 7u);
    }
    step(3000u + t);
    CHECK(is_down(2u, 7u) == false);
  }
  /* Settle pressed: reports after a fresh full window. */
  press(2u, 7u);
  hold_until_reported(3040u, 2u, 7u);
}

static void test_release_with_bounce(void) {
  state_reset(4000u);
  press(1u, 1u);
  hold_until_reported(4000u, 1u, 1u); /* down at 4015 */
  /* Short release below the window: still reported. */
  release(1u, 1u);
  step(4016u);
  step(4017u);
  step(4018u);
  CHECK(is_down(1u, 1u));
  /* Bounce back down: the release counter resets, key stays reported. */
  press(1u, 1u);
  step(4019u);
  step(4020u);
  CHECK(is_down(1u, 1u));
  /* Sustained release clears after the full window. */
  release(1u, 1u);
  hold_released_until_clear(4020u, 1u, 1u); /* cleared at 4035 */
  /* Bounce back down after release: < window of presses must not
   * resurrect. */
  press(1u, 1u);
  step(4036u);
  step(4037u);
  CHECK(is_down(1u, 1u) == false);
}

static void test_multiple_simultaneous(void) {
  state_reset(5000u);
  press(0u, 0u);
  press(1u, 7u);
  press(4u, 13u);
  /* All three deviate from the same base tick; the first hits its threshold
   * at the end of the window and so must the other two (independent per-key
   * counters). */
  hold_until_reported(5000u, 0u, 0u);
  CHECK(is_down(1u, 7u));
  CHECK(is_down(4u, 13u));
  /* Keep stepping past the window: every key stays reported, the per-key
   * bitmasks stay exact, and no other cell ever reports. */
  for (uint32_t t = MATRIX_SCAN_DEBOUNCE_MS + 16u; t <= 40u; t++) {
    step(5000u + t);
  }
  CHECK(s_stable[0] == (uint16_t)(1u << 0));
  CHECK(s_stable[1] == (uint16_t)(1u << 7));
  CHECK(s_stable[4] == (uint16_t)(1u << 13));
  CHECK(is_down(3u, 5u) == false);
}

static void test_counter_reset_on_change(void) {
  state_reset(6000u);
  press(0u, 3u);
  /* 14 deviating samples: not yet reported. */
  for (uint32_t i = 0u; i < 14u; i++) {
    step(6000u + 1u + i);
  }
  CHECK(is_down(0u, 3u) == false);
  /* One sample back at the reported level resets the counter, so the key
   * needs a fresh full window instead of reporting one sample later. */
  release(0u, 3u);
  step(6015u);
  CHECK(is_down(0u, 3u) == false);
  press(0u, 3u);
  for (uint32_t i = 0u; i < 14u; i++) {
    step(6016u + i);
    CHECK(is_down(0u, 3u) == false);
  }
  step(6016u + 14u);
  CHECK(is_down(0u, 3u));
}

static void test_threshold_semantics(void) {
  /* Short windows behave exactly: debounce_ms == 3 reports on the 3rd
   * consecutive deviating sample. */
  state_reset(7000u);
  press(1u, 2u);
  step_at(7001u, 3u);
  CHECK(is_down(1u, 2u) == false);
  step_at(7002u, 3u);
  CHECK(is_down(1u, 2u) == false);
  step_at(7003u, 3u);
  CHECK(is_down(1u, 2u));

  /* debounce_ms == 0 reports any deviation immediately. */
  state_reset(7010u);
  press(2u, 5u);
  step_at(7011u, 0u);
  CHECK(is_down(2u, 5u));

  /* A tick gap counts elapsed ms, not calls: three spaced calls with 10 ms
   * gaps accumulate 10+10+10 against a 25 ms window. */
  state_reset(7020u);
  press(0u, 0u);
  step_at(7030u, 25u);
  CHECK(is_down(0u, 0u) == false);
  step_at(7040u, 25u);
  CHECK(is_down(0u, 0u) == false);
  step_at(7050u, 25u);
  CHECK(is_down(0u, 0u));

  /* A gap longer than the window must flip instead of wrapping the uint8_t
   * counter: 1 + 300 = 301 >= 250 reports on this call (a wrapped counter
   * would read 45 and stay silent). */
  state_reset(7060u);
  press(0u, 0u);
  step_at(7061u, 250u);
  CHECK(is_down(0u, 0u) == false);
  step_at(7361u, 250u);
  CHECK(is_down(0u, 0u));
}

static void test_duplicate_timestamp_ignored(void) {
  state_reset(8000u);
  press(3u, 9u);
  /* A repeated timestamp is a duplicate tick and must not advance the
   * counters: 15 calls with the same ms keep the key unreported. */
  for (uint32_t i = 0u; i < MATRIX_SCAN_DEBOUNCE_MS; i++) {
    step(8000u);
  }
  CHECK(is_down(3u, 9u) == false);
  /* 14 valid samples plus one duplicate must still not report; the 15th
   * valid sample does. */
  state_reset(8100u);
  press(3u, 9u);
  for (uint32_t i = 1u; i <= 14u; i++) {
    step(8100u + i);
  }
  step(8114u); /* duplicate timestamp of the last step */
  CHECK(is_down(3u, 9u) == false);
  step(8115u);
  CHECK(is_down(3u, 9u));
}

static void test_tick_wrap_around(void) {
  /* now_ms wraps: elapsed 3 - (UINT32_MAX - 5) = 9 ms, then +5, then +1. */
  state_reset(1000u);
  press(0u, 0u);
  s_last_ms = UINT32_MAX - 5u;
  step_at(3u, MATRIX_SCAN_DEBOUNCE_MS);
  CHECK(is_down(0u, 0u) == false);
  step_at(8u, MATRIX_SCAN_DEBOUNCE_MS);
  CHECK(is_down(0u, 0u) == false);
  step_at(9u, MATRIX_SCAN_DEBOUNCE_MS);
  CHECK(is_down(0u, 0u));
}

static void test_bits_beyond_matrix_ignored(void) {
  /* Noise on bit 15 of a raw row is outside the 5x14 contract and must
   * never appear in the reported matrix. */
  state_reset(9000u);
  s_raw[0] |= (uint16_t)0x8000u;
  for (uint32_t i = 0u; i < 20u; i++) {
    step(9000u + i);
  }
  CHECK(s_stable[0] == 0u);
}

int main(void) {
  test_hold_reports_after_threshold();
  test_bounce_is_filtered();
  test_release_with_bounce();
  test_multiple_simultaneous();
  test_counter_reset_on_change();
  test_threshold_semantics();
  test_duplicate_timestamp_ignored();
  test_tick_wrap_around();
  test_bits_beyond_matrix_ignored();

  if (failures != 0) {
    fprintf(stderr, "matrix_debounce_tests: %d failure(s)\n", failures);
    return 1;
  }
  puts("matrix_debounce_tests: PASS");
  return 0;
}
