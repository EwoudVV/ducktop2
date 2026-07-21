#include "ducktop2/ec/ec_commit.h"

#include <stdint.h>
#include <stdio.h>
#include <string.h>

#define LOG_CAPACITY 256u
#define NO_FAILURE UINT32_MAX

typedef struct {
  ec_commit_command_t command;
  uint32_t value;
} log_entry_t;

typedef struct {
  log_entry_t log[LOG_CAPACITY];
  size_t count;
  uint32_t fail_call;
} mock_driver_t;

static int failures;

#define CHECK(expression)                                                      \
  do {                                                                         \
    if (!(expression)) {                                                       \
      fprintf(stderr, "%s:%d: CHECK failed: %s\n", __FILE__, __LINE__,         \
              #expression);                                                    \
      ++failures;                                                              \
    }                                                                          \
  } while (0)

static bool mock_write(void *context, ec_commit_command_t command,
                       uint32_t value) {
  mock_driver_t *mock = context;
  size_t call = mock->count;

  if (mock->count < LOG_CAPACITY) {
    mock->log[mock->count].command = command;
    mock->log[mock->count].value = value;
  }
  ++mock->count;
  return call != mock->fail_call;
}

static ec_commit_driver_t driver_for(mock_driver_t *mock) {
  ec_commit_driver_t driver;

  driver.context = mock;
  driver.write = mock_write;
  return driver;
}

static void mock_init(mock_driver_t *mock) {
  memset(mock, 0, sizeof(*mock));
  mock->fail_call = NO_FAILURE;
}

static size_t find_command(const mock_driver_t *mock,
                           ec_commit_command_t command, uint32_t value) {
  size_t index;

  for (index = 0; index < mock->count && index < LOG_CAPACITY; ++index) {
    if (mock->log[index].command == command && mock->log[index].value == value) {
      return index;
    }
  }
  return LOG_CAPACITY;
}

static bool outputs_are_safe(const ec_outputs_t *outputs) {
  ec_outputs_t safe;

  memset(&safe, 0, sizeof(safe));
  return memcmp(outputs, &safe, sizeof(safe)) == 0;
}

static ec_outputs_t powered_pd2_outputs(void) {
  ec_outputs_t outputs;

  memset(&outputs, 0, sizeof(outputs));
  outputs.pd_path_enable[1] = true;
  outputs.charger_iindpm_ma = 1750u;
  outputs.charge_power_budget_mw = 5000u;
  outputs.mu_edp_budget_mw = 15000u;
  outputs.power_policy_confirmed = true;
  outputs.charger_enable = true;
  outputs.mu_12v_enable = true;
  outputs.keyboard_rgb_power_enable = true;
  outputs.radio_db_power_enable = true;
  return outputs;
}

static ec_outputs_t bootstrap_pd2_outputs(void) {
  ec_outputs_t outputs;

  memset(&outputs, 0, sizeof(outputs));
  outputs.pd_path_enable[1] = true;
  return outputs;
}

static void apply_powered_pd2(ec_commit_state_t *state,
                              const ec_commit_driver_t *driver) {
  ec_outputs_t bootstrap = bootstrap_pd2_outputs();
  ec_outputs_t powered = powered_pd2_outputs();

  CHECK(ec_commit_apply(state, driver, &bootstrap) == EC_COMMIT_OK);
  CHECK(ec_commit_apply(state, driver, &powered) == EC_COMMIT_OK);
}

static void test_first_apply_proves_safe_hardware_state(void) {
  ec_commit_state_t state;
  mock_driver_t mock;
  ec_commit_driver_t driver;
  ec_outputs_t desired;

  memset(&desired, 0, sizeof(desired));
  ec_commit_state_init(&state);
  CHECK(!state.initialized);
  mock_init(&mock);
  driver = driver_for(&mock);
  CHECK(ec_commit_apply(&state, &driver, &desired) == EC_COMMIT_OK);
  CHECK(state.initialized);
  CHECK(outputs_are_safe(&state.applied));
  CHECK(mock.count == EC_COMMIT_COMMAND_COUNT);
}

static void test_staged_adapter_only_commit(void) {
  ec_commit_state_t state;
  mock_driver_t mock;
  ec_commit_driver_t driver;
  ec_outputs_t bootstrap = bootstrap_pd2_outputs();
  ec_outputs_t desired = powered_pd2_outputs();
  size_t iindpm;
  size_t path;
  size_t charge;
  size_t power_budget;
  size_t mu;
  size_t optional_load;

  ec_commit_state_init(&state);
  mock_init(&mock);
  driver = driver_for(&mock);
  CHECK(ec_commit_apply(&state, &driver, &bootstrap) == EC_COMMIT_OK);
  CHECK(ec_commit_apply(&state, &driver, &desired) == EC_COMMIT_OK);
  iindpm = find_command(&mock, EC_COMMIT_CHARGER_IINDPM_MA, 1750u);
  path = find_command(&mock, EC_COMMIT_PD2_PATH_ENABLE, 1u);
  charge = find_command(&mock, EC_COMMIT_CHARGER_ENABLE, 1u);
  power_budget = find_command(&mock, EC_COMMIT_MU_EDP_BUDGET_MW, 15000u);
  mu = find_command(&mock, EC_COMMIT_MU_12V_ENABLE, 1u);
  optional_load =
      find_command(&mock, EC_COMMIT_KEYBOARD_RGB_ENABLE, 1u);
  CHECK(path < iindpm);
  CHECK(iindpm < charge);
  CHECK(power_budget < mu);
  CHECK(mu < optional_load);
  CHECK(mu < find_command(&mock, EC_COMMIT_RADIO_DB_ENABLE, 1u));
  CHECK(state.applied.pd_path_enable[1]);
  CHECK(state.applied.charger_enable);
  CHECK(state.applied.mu_12v_enable);
}

static void test_transfer_disables_old_path_first(void) {
  ec_commit_state_t state;
  mock_driver_t mock;
  ec_commit_driver_t driver;
  ec_outputs_t off;
  ec_outputs_t bootstrap;
  ec_outputs_t second = powered_pd2_outputs();
  size_t old_off;
  size_t new_on;
  size_t iindpm;

  ec_commit_state_init(&state);
  mock_init(&mock);
  driver = driver_for(&mock);
  apply_powered_pd2(&state, &driver);

  mock_init(&mock);
  memset(&off, 0, sizeof(off));
  memset(&bootstrap, 0, sizeof(bootstrap));
  bootstrap.pd_path_enable[0] = true;
  CHECK(ec_commit_apply(&state, &driver, &off) == EC_COMMIT_OK);
  CHECK(ec_commit_apply(&state, &driver, &bootstrap) == EC_COMMIT_OK);
  second.pd_path_enable[1] = false;
  second.pd_path_enable[0] = true;
  second.charger_iindpm_ma = 2750u;
  CHECK(ec_commit_apply(&state, &driver, &second) == EC_COMMIT_OK);
  old_off = find_command(&mock, EC_COMMIT_PD2_PATH_ENABLE, 0u);
  iindpm = find_command(&mock, EC_COMMIT_CHARGER_IINDPM_MA, 2750u);
  new_on = find_command(&mock, EC_COMMIT_PD1_PATH_ENABLE, 1u);
  CHECK(old_off < new_on);
  CHECK(new_on < iindpm);
  CHECK(!state.applied.pd_path_enable[1]);
  CHECK(state.applied.pd_path_enable[0]);
}

static void test_unstaged_powered_path_is_rejected(void) {
  ec_commit_state_t state;
  mock_driver_t mock;
  ec_commit_driver_t driver;
  ec_outputs_t desired = powered_pd2_outputs();

  ec_commit_state_init(&state);
  mock_init(&mock);
  driver = driver_for(&mock);
  CHECK(ec_commit_apply(&state, &driver, &desired) ==
        EC_COMMIT_INVALID_DESIRED_STATE);
  CHECK(outputs_are_safe(&state.applied));
  CHECK(state.initialized);
  CHECK(find_command(&mock, EC_COMMIT_PD2_PATH_ENABLE, 1u) == LOG_CAPACITY);
}

static void test_invalid_desired_state_is_forced_safe(void) {
  ec_commit_state_t state;
  mock_driver_t mock;
  ec_commit_driver_t driver;
  ec_outputs_t invalid = powered_pd2_outputs();

  ec_commit_state_init(&state);
  mock_init(&mock);
  driver = driver_for(&mock);
  invalid.pd_path_enable[0] = true;
  CHECK(ec_commit_apply(&state, &driver, &invalid) ==
        EC_COMMIT_INVALID_DESIRED_STATE);
  CHECK(outputs_are_safe(&state.applied));
  CHECK(find_command(&mock, EC_COMMIT_PD1_PATH_ENABLE, 0u) < LOG_CAPACITY);
  CHECK(find_command(&mock, EC_COMMIT_PD2_PATH_ENABLE, 0u) < LOG_CAPACITY);
}

static void test_load_enables_require_committed_limits(void) {
  ec_commit_state_t state;
  mock_driver_t mock;
  ec_commit_driver_t driver;
  ec_outputs_t invalid = powered_pd2_outputs();

  ec_commit_state_init(&state);
  mock_init(&mock);
  driver = driver_for(&mock);
  invalid.charge_power_budget_mw = 0u;
  CHECK(ec_commit_apply(&state, &driver, &invalid) ==
        EC_COMMIT_INVALID_DESIRED_STATE);
  CHECK(outputs_are_safe(&state.applied));

  mock_init(&mock);
  invalid = powered_pd2_outputs();
  invalid.power_policy_confirmed = false;
  CHECK(ec_commit_apply(&state, &driver, &invalid) ==
        EC_COMMIT_INVALID_DESIRED_STATE);
  CHECK(outputs_are_safe(&state.applied));
}

static void test_io_error_rolls_back_to_safe(void) {
  ec_commit_state_t state;
  mock_driver_t mock;
  ec_commit_driver_t driver;
  ec_outputs_t desired = powered_pd2_outputs();

  ec_commit_state_init(&state);
  mock_init(&mock);
  driver = driver_for(&mock);
  CHECK(ec_commit_apply(&state, &driver, &(ec_outputs_t){
      .pd_path_enable = {false, true},
  }) == EC_COMMIT_OK);
  mock_init(&mock);
  mock.fail_call = 0u;
  CHECK(ec_commit_apply(&state, &driver, &desired) == EC_COMMIT_IO_ERROR);
  CHECK(outputs_are_safe(&state.applied));
  CHECK(state.initialized);
  CHECK(mock.count > EC_COMMIT_COMMAND_COUNT);
}

static void test_repeated_commit_is_a_no_op(void) {
  ec_commit_state_t state;
  mock_driver_t mock;
  ec_commit_driver_t driver;
  ec_outputs_t desired = powered_pd2_outputs();

  ec_commit_state_init(&state);
  mock_init(&mock);
  driver = driver_for(&mock);
  apply_powered_pd2(&state, &driver);
  mock_init(&mock);
  desired.source_input_power_mw += 100u;
  CHECK(ec_commit_apply(&state, &driver, &desired) == EC_COMMIT_OK);
  CHECK(mock.count == 0u);
}

static void test_safe_state_write_failure_is_visible(void) {
  ec_commit_state_t state;
  mock_driver_t mock;
  ec_commit_driver_t driver;

  ec_commit_state_init(&state);
  mock_init(&mock);
  driver = driver_for(&mock);
  mock.fail_call = 0u;
  CHECK(ec_commit_force_safe(&state, &driver) ==
        EC_COMMIT_SAFE_STATE_IO_ERROR);
  CHECK(outputs_are_safe(&state.applied));
  CHECK(!state.initialized);
  CHECK(mock.count == EC_COMMIT_COMMAND_COUNT);
}

int main(void) {
  test_first_apply_proves_safe_hardware_state();
  test_staged_adapter_only_commit();
  test_transfer_disables_old_path_first();
  test_unstaged_powered_path_is_rejected();
  test_invalid_desired_state_is_forced_safe();
  test_load_enables_require_committed_limits();
  test_io_error_rolls_back_to_safe();
  test_repeated_commit_is_a_no_op();
  test_safe_state_write_failure_is_visible();

  if (failures != 0) {
    fprintf(stderr, "ec_commit_tests: %d failure(s)\n", failures);
    return 1;
  }
  puts("ec_commit_tests: PASS");
  return 0;
}
