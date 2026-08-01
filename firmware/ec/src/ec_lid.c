#include "ducktop2/ec/ec_lid.h"

ec_lid_config_t ec_lid_default_config(void) {
  ec_lid_config_t config;
  config.debounce_ms = EC_LID_DEFAULT_DEBOUNCE_MS;
  return config;
}

void ec_lid_inputs_init(ec_lid_inputs_t *inputs) {
  /* The safe default before the target has read the GPIO is "lid open" so the
   * display stays on until the first real reading.  R209 also pulls here. */
  inputs->lid_open_raw = true;
}

void ec_lid_state_init(ec_lid_state_t *state) {
  state->lid_closed = false;
  state->pending_state = false;
  state->timer_running = false;
  state->started_ms = 0u;
  state->just_closed = false;
  state->just_opened = false;
}

void ec_lid_step(const ec_lid_config_t *config,
                 const ec_lid_inputs_t *inputs,
                 ec_lid_state_t *state,
                 uint32_t now_ms,
                 ec_lid_output_t *output) {
  /* Clear last call's edge latches first; each edge is reported once. */
  state->just_closed = false;
  state->just_opened = false;

  const bool raw_closed = !inputs->lid_open_raw;
  const bool stable = state->lid_closed;
  const bool raw_agrees = (raw_closed == stable);

  /* Carry last call's pending edge flags into the output only if set this
   * call; we cleared them above, so a stable transition below sets them. */
  output->lid_closed = stable;
  output->just_closed = false;
  output->just_opened = false;

  if (raw_agrees) {
    /* Raw agrees with stable: cancel any in-progress bounce timer.  No transition. */
    state->timer_running = false;
    return;
  }

  /* Raw disagrees with stable.  Either start the timer or keep counting. */
  if (!state->timer_running) {
    state->timer_running = true;
    state->started_ms = now_ms;
    state->pending_state = raw_closed;
    return;
  }

  /* Timer already running: if the raw reading changed its mind again, restart
   * the timer for the new candidate (classic bounce — only the most recent
   * stable disagreement counts). */
  if (raw_closed != state->pending_state) {
    state->started_ms = now_ms;
    state->pending_state = raw_closed;
    return;
  }

  /* Same disagreement as before: check elapsed time.  Handle the monotonic
   * wrap case by treating elapsed as zero if now < started (rare at 32-bit ms
   * but defensive — a wrap should not cause a spurious transition). */
  uint32_t elapsed;
  if (now_ms >= state->started_ms) {
    elapsed = now_ms - state->started_ms;
  } else {
    elapsed = 0u;
  }

  if (elapsed >= config->debounce_ms) {
    /* Disagreement persisted long enough: commit the stable transition. */
    state->lid_closed = raw_closed;
    state->timer_running = false;
    output->lid_closed = raw_closed;
    if (raw_closed) {
      state->just_closed = true;
      output->just_closed = true;
    } else {
      state->just_opened = true;
      output->just_opened = true;
    }
  }
  /* Else: still inside the debounce window, keep waiting. */
}