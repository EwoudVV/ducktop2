#include "ducktop2/ec/ec_lid.h"

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

static ec_lid_config_t cfg;
static ec_lid_inputs_t in;
static ec_lid_state_t st;
static ec_lid_output_t out;

static void reset(void) {
  cfg = ec_lid_default_config();
  ec_lid_inputs_init(&in);
  ec_lid_state_init(&st);
  /* out is fully overwritten each call. */
}

static void step(uint32_t now_ms) {
  ec_lid_step(&cfg, &in, &st, now_ms, &out);
}

static void test_initial_state_is_open(void) {
  reset();
  /* ec_lid_inputs_init set lid_open_raw = true; fresh state should read open. */
  step(0u);
  CHECK(!out.lid_closed);
  CHECK(!out.just_closed);
  CHECK(!out.just_opened);
  CHECK(!st.timer_running);
}

static void test_raw_closed_starts_debounce_no_transition(void) {
  reset();
  in.lid_open_raw = false; /* lid reads closed */
  step(0u);
  /* First disagreement: timer starts, no transition yet. */
  CHECK(!out.lid_closed);
  CHECK(!st.lid_closed);
  CHECK(st.timer_running);

  /* Inside the window: still no transition. */
  step(20u); /* < 30ms debounce */
  CHECK(!out.lid_closed);
  CHECK(st.timer_running);
}

static void test_debounce_completes_to_closed(void) {
  reset();
  in.lid_open_raw = false; /* closed */
  step(0u);
  step(30u); /* exactly debounce_ms */
  CHECK(out.lid_closed);
  CHECK(st.lid_closed);
  CHECK(out.just_closed);
  CHECK(!out.just_opened);
  CHECK(!st.timer_running);
}

static void test_just_closed_is_one_shot(void) {
  reset();
  in.lid_open_raw = false;
  step(0u);
  step(40u); /* past debounce */
  CHECK(out.just_closed);
  /* Next call with stable closed (raw still closed): edge clears. */
  step(60u);
  CHECK(out.lid_closed);
  CHECK(!out.just_closed);
  CHECK(!out.just_opened);
}

static void test_bounce_cancels_transition(void) {
  reset();
  in.lid_open_raw = false; /* starts a closed candidate */
  step(0u);
  step(15u); /* halfway */
  in.lid_open_raw = true;  /* bounces back to open (agrees with stable) */
  step(20u);
  /* Timer canceled, still open. */
  CHECK(!out.lid_closed);
  CHECK(!st.timer_running);
}

static void test_reversed_bounce_restarts_timer(void) {
  reset();
  in.lid_open_raw = false; /* candidate: closed */
  step(0u);
  step(10u);
  /* Raw oscillates back to open, then to closed again — restart not resume. */
  in.lid_open_raw = true;
  step(15u);
  in.lid_open_raw = false;
  step(30u); /* only 15ms since the restart, < 30ms */
  CHECK(!out.lid_closed);
  CHECK(st.timer_running);
  /* Complete the window from the restart (timer started at t=30, need 30ms). */
  step(61u); /* 31ms since restart */
  CHECK(out.lid_closed);
  CHECK(st.lid_closed);
}

static void test_open_to_closed_to_open_full_cycle(void) {
  reset();
  /* Close. */
  in.lid_open_raw = false;
  step(0u);
  step(35u);
  CHECK(out.lid_closed);
  CHECK(out.just_closed);
  CHECK(!out.just_opened);

  /* Open again. */
  in.lid_open_raw = true;
  step(100u);
  /* Disagreement starts (raw open, stable closed). */
  CHECK(out.lid_closed); /* stable not yet changed */
  step(140u); /* 40ms > 30ms debounce */
  CHECK(!out.lid_closed);
  CHECK(st.lid_closed == false);
  CHECK(out.just_opened);
  CHECK(!out.just_closed);

  /* Edge clears next call. */
  step(160u);
  CHECK(!out.lid_closed);
  CHECK(!out.just_opened);
  CHECK(!out.just_closed);
}

static void test_stable_open_no_churn(void) {
  reset();
  in.lid_open_raw = true;
  for (uint32_t t = 0u; t < 500u; t += 20u) {
    step(t);
    CHECK(!out.lid_closed);
    CHECK(!out.just_closed);
    CHECK(!out.just_opened);
    CHECK(!st.timer_running);
  }
}

static void test_stable_closed_no_churn(void) {
  reset();
  in.lid_open_raw = false;
  step(0u);
  step(40u);
  CHECK(out.lid_closed);
  /* Continue reporting closed with no further edges. */
  for (uint32_t t = 60u; t < 1000u; t += 20u) {
    step(t);
    CHECK(out.lid_closed);
    CHECK(!out.just_closed);
    CHECK(!out.just_opened);
  }
}

static void test_fail_safe_open_when_sensor_reads_open(void) {
  reset();
  /* A disconnected sensor: R209 pulls LID_CLOSED_N high -> raw reads open.
   * The debouncer must honestly report open (display on) — the safe default. */
  in.lid_open_raw = true;
  step(0u);
  step(100u);
  CHECK(!out.lid_closed);
  CHECK(!out.just_closed);
}

static void test_reset_to_known_state(void) {
  reset();
  in.lid_open_raw = false;
  step(0u);
  step(40u);
  CHECK(st.lid_closed);

  ec_lid_state_init(&st);
  ec_lid_inputs_init(&in);
  step(1u);
  CHECK(!out.lid_closed);
  CHECK(!out.just_closed);
  CHECK(!out.just_opened);
  CHECK(!st.timer_running);
}

static void test_default_config_constant(void) {
  cfg = ec_lid_default_config();
  CHECK(cfg.debounce_ms == EC_LID_DEFAULT_DEBOUNCE_MS);
  CHECK(EC_LID_DEFAULT_DEBOUNCE_MS == 30u);
}

int main(void) {
  test_initial_state_is_open();
  test_raw_closed_starts_debounce_no_transition();
  test_debounce_completes_to_closed();
  test_just_closed_is_one_shot();
  test_bounce_cancels_transition();
  test_reversed_bounce_restarts_timer();
  test_open_to_closed_to_open_full_cycle();
  test_stable_open_no_churn();
  test_stable_closed_no_churn();
  test_fail_safe_open_when_sensor_reads_open();
  test_reset_to_known_state();
  test_default_config_constant();

  if (failures != 0) {
    fprintf(stderr, "ec_lid_tests: %d failure(s)\n", failures);
    return 1;
  }
  puts("ec_lid_tests: PASS");
  return 0;
}