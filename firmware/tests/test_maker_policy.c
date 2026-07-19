#include "ducktop2/maker/maker_policy.h"

#include <stdint.h>
#include <stdio.h>

static int failures;

#define CHECK(expression)                                                      \
  do {                                                                         \
    if (!(expression)) {                                                       \
      fprintf(stderr, "%s:%d: CHECK failed: %s\n", __FILE__, __LINE__,         \
              #expression);                                                    \
      ++failures;                                                              \
    }                                                                          \
  } while (0)

static bool all_io_high_impedance(const maker_outputs_t *outputs) {
  size_t index;

  for (index = 0; index < MAKER_USER_IO_COUNT; ++index) {
    if (outputs->io_mode[index] != MAKER_IO_HIGH_IMPEDANCE) {
      return false;
    }
  }
  return true;
}

static void authorize_maker(maker_inputs_t *inputs) {
  inputs->hardware_interlock_ready = true;
  inputs->user_power_authorized = true;
  inputs->user_io_authorized = true;
}

static void test_boot_defaults(void) {
  maker_controller_t controller;

  maker_controller_init(&controller);
  CHECK(!controller.outputs.user_rails_enable);
  CHECK(all_io_high_impedance(&controller.outputs));
  CHECK(controller.fault == MAKER_FAULT_NONE);
}

static void test_rails_need_explicit_request_and_authorization(void) {
  maker_controller_t controller;
  maker_inputs_t inputs;

  maker_inputs_init(&inputs);
  maker_controller_init(&controller);
  maker_controller_step(&controller, &inputs);
  CHECK(!controller.outputs.user_rails_enable);

  maker_controller_request_user_rails(&controller, true);
  maker_controller_step(&controller, &inputs);
  CHECK(!controller.outputs.user_rails_enable);
  CHECK(controller.fault == MAKER_FAULT_INTERLOCK);

  CHECK(maker_controller_clear_fault(&controller, true));
  inputs.hardware_interlock_ready = true;
  inputs.user_power_authorized = true;
  maker_controller_request_user_rails(&controller, true);
  maker_controller_step(&controller, &inputs);
  CHECK(controller.outputs.user_rails_enable);

  maker_controller_request_user_rails(&controller, false);
  maker_controller_step(&controller, &inputs);
  CHECK(!controller.outputs.user_rails_enable);
}

static void test_unauthorized_io_request_is_not_queued(void) {
  maker_controller_t controller;
  maker_inputs_t inputs;

  maker_inputs_init(&inputs);
  maker_controller_init(&controller);
  inputs.hardware_interlock_ready = true;
  CHECK(maker_controller_request_io_mode(&controller, 4u,
                                         MAKER_IO_OUTPUT_HIGH));
  maker_controller_step(&controller, &inputs);
  CHECK(controller.fault == MAKER_FAULT_IO_AUTHORIZATION);
  CHECK(all_io_high_impedance(&controller.outputs));

  CHECK(maker_controller_clear_fault(&controller, true));
  inputs.user_io_authorized = true;
  maker_controller_step(&controller, &inputs);
  CHECK(all_io_high_impedance(&controller.outputs));
}

static void test_gpio_stays_high_z_until_requested(void) {
  maker_controller_t controller;
  maker_inputs_t inputs;

  maker_inputs_init(&inputs);
  maker_controller_init(&controller);
  inputs.hardware_interlock_ready = true;
  inputs.user_io_authorized = true;
  CHECK(maker_controller_request_io_mode(&controller, 0u,
                                         MAKER_IO_ALTERNATE_FUNCTION));
  CHECK(maker_controller_request_io_mode(&controller, 25u,
                                         MAKER_IO_ANALOG_INPUT));
  CHECK(!maker_controller_request_io_mode(&controller, MAKER_USER_IO_COUNT,
                                          MAKER_IO_OUTPUT_HIGH));
  maker_controller_step(&controller, &inputs);
  CHECK(controller.outputs.io_mode[0] == MAKER_IO_ALTERNATE_FUNCTION);
  CHECK(controller.outputs.io_mode[25] == MAKER_IO_ANALOG_INPUT);
  CHECK(controller.outputs.io_mode[1] == MAKER_IO_HIGH_IMPEDANCE);
}

static void test_power_fault_is_latched_safe(void) {
  maker_controller_t controller;
  maker_inputs_t inputs;

  maker_inputs_init(&inputs);
  maker_controller_init(&controller);
  authorize_maker(&inputs);
  maker_controller_request_user_rails(&controller, true);
  CHECK(
      maker_controller_request_io_mode(&controller, 3u, MAKER_IO_OUTPUT_HIGH));
  maker_controller_step(&controller, &inputs);
  CHECK(controller.outputs.user_rails_enable);

  inputs.user_power_fault_n = false;
  maker_controller_step(&controller, &inputs);
  CHECK(controller.fault == MAKER_FAULT_USER_POWER);
  CHECK(!controller.outputs.user_rails_enable);
  CHECK(all_io_high_impedance(&controller.outputs));

  inputs.user_power_fault_n = true;
  maker_controller_step(&controller, &inputs);
  CHECK(!controller.outputs.user_rails_enable);
  CHECK(!maker_controller_clear_fault(&controller, false));
  CHECK(maker_controller_clear_fault(&controller, true));
  CHECK(all_io_high_impedance(&controller.outputs));
}

static void test_watchdog_and_reset_are_safe(void) {
  maker_controller_t controller;
  maker_inputs_t inputs;

  maker_inputs_init(&inputs);
  maker_controller_init(&controller);
  authorize_maker(&inputs);
  maker_controller_request_user_rails(&controller, true);
  CHECK(maker_controller_request_io_mode(&controller, 5u, MAKER_IO_OUTPUT_LOW));
  maker_controller_step(&controller, &inputs);
  CHECK(controller.outputs.user_rails_enable);

  maker_controller_watchdog_trip(&controller);
  CHECK(controller.fault == MAKER_FAULT_WATCHDOG);
  CHECK(!controller.outputs.user_rails_enable);
  CHECK(all_io_high_impedance(&controller.outputs));

  CHECK(maker_controller_clear_fault(&controller, true));
  maker_controller_request_user_rails(&controller, true);
  CHECK(maker_controller_request_io_mode(&controller, 5u, MAKER_IO_OUTPUT_LOW));
  maker_controller_step(&controller, &inputs);
  inputs.reset_asserted = true;
  maker_controller_step(&controller, &inputs);
  CHECK(controller.fault == MAKER_FAULT_NONE);
  CHECK(!controller.outputs.user_rails_enable);
  CHECK(all_io_high_impedance(&controller.outputs));
}

static void test_interlock_and_authorization_loss_latch_safe(void) {
  maker_controller_t controller;
  maker_inputs_t inputs;

  maker_inputs_init(&inputs);
  maker_controller_init(&controller);
  authorize_maker(&inputs);
  maker_controller_request_user_rails(&controller, true);
  CHECK(maker_controller_request_io_mode(&controller, 2u,
                                         MAKER_IO_OUTPUT_HIGH));
  maker_controller_step(&controller, &inputs);
  CHECK(controller.outputs.user_rails_enable);
  CHECK(controller.outputs.io_mode[2] == MAKER_IO_OUTPUT_HIGH);

  inputs.user_io_authorized = false;
  maker_controller_step(&controller, &inputs);
  CHECK(controller.fault == MAKER_FAULT_IO_AUTHORIZATION);
  CHECK(!controller.outputs.user_rails_enable);
  CHECK(all_io_high_impedance(&controller.outputs));

  CHECK(maker_controller_clear_fault(&controller, true));
  authorize_maker(&inputs);
  maker_controller_request_user_rails(&controller, true);
  CHECK(maker_controller_request_io_mode(&controller, 2u,
                                         MAKER_IO_OUTPUT_HIGH));
  maker_controller_step(&controller, &inputs);
  inputs.hardware_interlock_ready = false;
  maker_controller_step(&controller, &inputs);
  CHECK(controller.fault == MAKER_FAULT_INTERLOCK);
  CHECK(!controller.outputs.user_rails_enable);
  CHECK(all_io_high_impedance(&controller.outputs));
}

static uint32_t next_random(uint32_t *state) {
  *state = *state * 1664525u + 1013904223u;
  return *state;
}

static void test_deterministic_transition_properties(void) {
  maker_controller_t controller;
  maker_inputs_t inputs;
  uint32_t random_state = 0x4d414b45u;
  size_t iteration;

  maker_inputs_init(&inputs);
  maker_controller_init(&controller);
  for (iteration = 0; iteration < 10000u; ++iteration) {
    size_t index = next_random(&random_state) % MAKER_USER_IO_COUNT;
    maker_io_mode_t mode =
        (maker_io_mode_t)(next_random(&random_state) %
                          (MAKER_IO_ALTERNATE_FUNCTION + 1u));

    if (controller.fault != MAKER_FAULT_NONE) {
      CHECK(maker_controller_clear_fault(&controller, true));
    }
    maker_controller_request_user_rails(
        &controller, (next_random(&random_state) & 1u) != 0u);
    CHECK(maker_controller_request_io_mode(&controller, index, mode));
    maker_inputs_init(&inputs);
    inputs.hardware_interlock_ready =
        (next_random(&random_state) & 1u) != 0u;
    inputs.user_power_authorized = (next_random(&random_state) & 1u) != 0u;
    inputs.user_io_authorized = (next_random(&random_state) & 1u) != 0u;
    inputs.user_power_fault_n = (next_random(&random_state) % 101u) != 0u;
    inputs.watchdog_healthy = (next_random(&random_state) % 127u) != 0u;
    inputs.reset_asserted = (next_random(&random_state) % 151u) == 0u;
    maker_controller_step(&controller, &inputs);

    if (controller.fault != MAKER_FAULT_NONE || inputs.reset_asserted) {
      CHECK(!controller.outputs.user_rails_enable);
      CHECK(all_io_high_impedance(&controller.outputs));
    }
    if (controller.outputs.user_rails_enable) {
      CHECK(inputs.hardware_interlock_ready);
      CHECK(inputs.user_power_authorized);
      CHECK(inputs.user_power_fault_n);
      CHECK(inputs.watchdog_healthy);
    }
    if (!all_io_high_impedance(&controller.outputs)) {
      CHECK(inputs.hardware_interlock_ready);
      CHECK(inputs.user_io_authorized);
    }
  }
}

int main(void) {
  test_boot_defaults();
  test_rails_need_explicit_request_and_authorization();
  test_gpio_stays_high_z_until_requested();
  test_unauthorized_io_request_is_not_queued();
  test_power_fault_is_latched_safe();
  test_watchdog_and_reset_are_safe();
  test_interlock_and_authorization_loss_latch_safe();
  test_deterministic_transition_properties();

  if (failures != 0) {
    fprintf(stderr, "maker_policy_tests: %d failure(s)\n", failures);
    return 1;
  }
  puts("maker_policy_tests: PASS");
  return 0;
}
