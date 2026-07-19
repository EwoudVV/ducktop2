#include "ducktop2/maker/maker_policy.h"

#include <string.h>

static bool mode_is_valid(maker_io_mode_t mode) {
  return mode >= MAKER_IO_HIGH_IMPEDANCE && mode <= MAKER_IO_ALTERNATE_FUNCTION;
}

static bool any_io_driven(const maker_outputs_t *outputs) {
  size_t index;

  for (index = 0; index < MAKER_USER_IO_COUNT; ++index) {
    if (outputs->io_mode[index] != MAKER_IO_HIGH_IMPEDANCE) {
      return true;
    }
  }
  return false;
}

static bool any_io_requested(const maker_controller_t *controller) {
  size_t index;

  for (index = 0; index < MAKER_USER_IO_COUNT; ++index) {
    if (controller->requested_io_mode[index] != MAKER_IO_HIGH_IMPEDANCE) {
      return true;
    }
  }
  return false;
}

static void outputs_safe(maker_outputs_t *outputs) {
  size_t index;

  outputs->user_rails_enable = false;
  for (index = 0; index < MAKER_USER_IO_COUNT; ++index) {
    outputs->io_mode[index] = MAKER_IO_HIGH_IMPEDANCE;
  }
}

static void requests_safe(maker_controller_t *controller) {
  size_t index;

  controller->user_rails_requested = false;
  for (index = 0; index < MAKER_USER_IO_COUNT; ++index) {
    controller->requested_io_mode[index] = MAKER_IO_HIGH_IMPEDANCE;
  }
}

static void enter_fault(maker_controller_t *controller, maker_fault_t fault) {
  outputs_safe(&controller->outputs);
  requests_safe(controller);
  controller->fault = fault;
}

void maker_inputs_init(maker_inputs_t *inputs) {
  memset(inputs, 0, sizeof(*inputs));
  inputs->watchdog_healthy = true;
  inputs->user_power_fault_n = true;
}

void maker_controller_init(maker_controller_t *controller) {
  memset(controller, 0, sizeof(*controller));
  requests_safe(controller);
  outputs_safe(&controller->outputs);
  controller->fault = MAKER_FAULT_NONE;
}

void maker_controller_request_user_rails(maker_controller_t *controller,
                                         bool enable) {
  if (controller->fault == MAKER_FAULT_NONE) {
    controller->user_rails_requested = enable;
  }
}

bool maker_controller_request_io_mode(maker_controller_t *controller,
                                      size_t index, maker_io_mode_t mode) {
  if (controller->fault != MAKER_FAULT_NONE || index >= MAKER_USER_IO_COUNT ||
      !mode_is_valid(mode)) {
    return false;
  }
  controller->requested_io_mode[index] = mode;
  return true;
}

void maker_controller_step(maker_controller_t *controller,
                           const maker_inputs_t *inputs) {
  if (inputs->reset_asserted) {
    maker_controller_init(controller);
    return;
  }
  if (!inputs->watchdog_healthy) {
    enter_fault(controller, MAKER_FAULT_WATCHDOG);
    return;
  }
  if (!inputs->user_power_fault_n) {
    enter_fault(controller, MAKER_FAULT_USER_POWER);
    return;
  }
  if (controller->fault != MAKER_FAULT_NONE) {
    outputs_safe(&controller->outputs);
    return;
  }

  if (!inputs->hardware_interlock_ready) {
    if (controller->user_rails_requested || any_io_requested(controller) ||
        controller->outputs.user_rails_enable ||
        any_io_driven(&controller->outputs)) {
      enter_fault(controller, MAKER_FAULT_INTERLOCK);
    } else {
      outputs_safe(&controller->outputs);
    }
    return;
  }
  if (controller->user_rails_requested && !inputs->user_power_authorized) {
    enter_fault(controller, MAKER_FAULT_USER_POWER);
    return;
  }
  if (any_io_requested(controller) && !inputs->user_io_authorized) {
    enter_fault(controller, MAKER_FAULT_IO_AUTHORIZATION);
    return;
  }
  if (controller->outputs.user_rails_enable &&
      !inputs->user_power_authorized) {
    enter_fault(controller, MAKER_FAULT_USER_POWER);
    return;
  }
  if (any_io_driven(&controller->outputs) &&
      !inputs->user_io_authorized) {
    enter_fault(controller, MAKER_FAULT_IO_AUTHORIZATION);
    return;
  }

  if (inputs->user_io_authorized) {
    memcpy(controller->outputs.io_mode, controller->requested_io_mode,
           sizeof(controller->outputs.io_mode));
  } else {
    size_t index;
    for (index = 0; index < MAKER_USER_IO_COUNT; ++index) {
      controller->outputs.io_mode[index] = MAKER_IO_HIGH_IMPEDANCE;
    }
  }
  controller->outputs.user_rails_enable =
      controller->user_rails_requested && inputs->user_power_authorized;
}

void maker_controller_watchdog_trip(maker_controller_t *controller) {
  enter_fault(controller, MAKER_FAULT_WATCHDOG);
}

bool maker_controller_clear_fault(maker_controller_t *controller,
                                  bool root_cause_removed) {
  if (!root_cause_removed || controller->fault == MAKER_FAULT_NONE) {
    return false;
  }
  maker_controller_init(controller);
  return true;
}

const maker_outputs_t *
maker_controller_outputs(const maker_controller_t *controller) {
  return &controller->outputs;
}
