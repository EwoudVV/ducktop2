#include "ducktop2/ec/ec_commit.h"

#include <string.h>

static bool driver_is_valid(const ec_commit_driver_t *driver) {
  return driver != NULL && driver->write != NULL;
}

static bool desired_is_valid(const ec_outputs_t *desired) {
  size_t index;
  unsigned int enabled_paths = 0u;
  bool controlled_load_enabled;

  if (desired == NULL) {
    return false;
  }
  for (index = 0; index < EC_PD_PORT_COUNT; ++index) {
    if (desired->pd_path_enable[index]) {
      ++enabled_paths;
    }
  }
  if (enabled_paths > 1u) {
    return false;
  }
  controlled_load_enabled =
      desired->charger_enable || desired->mu_12v_enable ||
      desired->keyboard_rgb_power_enable || desired->radio_vhf_power_enable ||
      desired->radio_uhf_power_enable || desired->audio_amp_enable ||
      desired->audio_mic_enable;
  if (enabled_paths != 0u && desired->charger_iindpm_ma == 0u &&
      (controlled_load_enabled || desired->charge_power_budget_mw != 0u ||
       desired->mu_edp_budget_mw != 0u || desired->power_policy_confirmed)) {
    return false;
  }
  if (desired->charger_enable &&
      (desired->charger_iindpm_ma == 0u ||
       desired->charge_power_budget_mw == 0u)) {
    return false;
  }
  if (desired->mu_12v_enable &&
      (!desired->power_policy_confirmed || desired->mu_edp_budget_mw == 0u)) {
    return false;
  }
  return true;
}

static bool write_value(const ec_commit_driver_t *driver,
                        ec_commit_command_t command, uint32_t value) {
  return driver->write(driver->context, command, value);
}

static bool write_safe_sequence(const ec_commit_driver_t *driver) {
  bool ok = true;

  ok = write_value(driver, EC_COMMIT_KEYBOARD_RGB_ENABLE, 0u) && ok;
  ok = write_value(driver, EC_COMMIT_RADIO_VHF_ENABLE, 0u) && ok;
  ok = write_value(driver, EC_COMMIT_RADIO_UHF_ENABLE, 0u) && ok;
  ok = write_value(driver, EC_COMMIT_AUDIO_AMP_ENABLE, 0u) && ok;
  ok = write_value(driver, EC_COMMIT_AUDIO_MIC_ENABLE, 0u) && ok;
  ok = write_value(driver, EC_COMMIT_MU_12V_ENABLE, 0u) && ok;
  ok = write_value(driver, EC_COMMIT_CHARGER_ENABLE, 0u) && ok;
  ok = write_value(driver, EC_COMMIT_PD1_PATH_ENABLE, 0u) && ok;
  ok = write_value(driver, EC_COMMIT_PD2_PATH_ENABLE, 0u) && ok;
  ok = write_value(driver, EC_COMMIT_PD3_PATH_ENABLE, 0u) && ok;
  ok = write_value(driver, EC_COMMIT_CHARGER_IINDPM_MA, 0u) && ok;
  ok = write_value(driver, EC_COMMIT_CHARGE_BUDGET_MW, 0u) && ok;
  ok = write_value(driver, EC_COMMIT_MU_EDP_BUDGET_MW, 0u) && ok;
  return ok;
}

void ec_commit_state_init(ec_commit_state_t *state) {
  if (state == NULL) {
    return;
  }
  memset(state, 0, sizeof(*state));
  state->initialized = false;
}

ec_commit_result_t ec_commit_force_safe(ec_commit_state_t *state,
                                        const ec_commit_driver_t *driver) {
  bool ok;

  if (state == NULL || !driver_is_valid(driver)) {
    return EC_COMMIT_INVALID_ARGUMENT;
  }
  ok = write_safe_sequence(driver);
  memset(&state->applied, 0, sizeof(state->applied));
  state->initialized = ok;
  return ok ? EC_COMMIT_OK : EC_COMMIT_SAFE_STATE_IO_ERROR;
}

static bool path_selection_changed(const ec_outputs_t *applied,
                                   const ec_outputs_t *desired) {
  size_t index;

  for (index = 0; index < EC_PD_PORT_COUNT; ++index) {
    if (applied->pd_path_enable[index] != desired->pd_path_enable[index]) {
      return true;
    }
  }
  return false;
}

static bool controlled_state_equal(const ec_outputs_t *applied,
                                   const ec_outputs_t *desired) {
  return !path_selection_changed(applied, desired) &&
         applied->charger_enable == desired->charger_enable &&
         applied->charger_iindpm_ma == desired->charger_iindpm_ma &&
         applied->charge_power_budget_mw == desired->charge_power_budget_mw &&
         applied->mu_12v_enable == desired->mu_12v_enable &&
         applied->mu_edp_budget_mw == desired->mu_edp_budget_mw &&
         applied->keyboard_rgb_power_enable ==
             desired->keyboard_rgb_power_enable &&
         applied->radio_vhf_power_enable == desired->radio_vhf_power_enable &&
         applied->radio_uhf_power_enable == desired->radio_uhf_power_enable &&
         applied->audio_amp_enable == desired->audio_amp_enable &&
         applied->audio_mic_enable == desired->audio_mic_enable;
}

static ec_commit_result_t fail_safe(ec_commit_state_t *state,
                                    const ec_commit_driver_t *driver) {
  ec_commit_result_t safe_result = ec_commit_force_safe(state, driver);

  return safe_result == EC_COMMIT_OK ? EC_COMMIT_IO_ERROR : safe_result;
}

static bool write_if_changed(const ec_commit_driver_t *driver,
                             ec_commit_command_t command, uint32_t current,
                             uint32_t desired) {
  return current == desired || write_value(driver, command, desired);
}

ec_commit_result_t ec_commit_apply(ec_commit_state_t *state,
                                   const ec_commit_driver_t *driver,
                                   const ec_outputs_t *desired) {
  ec_outputs_t current;
  bool path_changed;
  bool sequencing_change;
  bool current_path_enabled = false;
  bool desired_path_enabled = false;
  size_t index;

  if (state == NULL || !driver_is_valid(driver) || desired == NULL) {
    return EC_COMMIT_INVALID_ARGUMENT;
  }
  if (!desired_is_valid(desired)) {
    ec_commit_result_t safe_result = ec_commit_force_safe(state, driver);
    return safe_result == EC_COMMIT_OK ? EC_COMMIT_INVALID_DESIRED_STATE
                                      : safe_result;
  }

  current = state->applied;
  if (state->initialized && controlled_state_equal(&current, desired)) {
    state->applied = *desired;
    return EC_COMMIT_OK;
  }
  path_changed = !state->initialized ||
                 path_selection_changed(&current, desired);
  for (index = 0; index < EC_PD_PORT_COUNT; ++index) {
    current_path_enabled = current_path_enabled || current.pd_path_enable[index];
    desired_path_enabled = desired_path_enabled || desired->pd_path_enable[index];
  }
  if (path_changed && current_path_enabled && desired_path_enabled) {
    ec_commit_result_t safe_result = ec_commit_force_safe(state, driver);
    return safe_result == EC_COMMIT_OK ? EC_COMMIT_INVALID_DESIRED_STATE
                                      : safe_result;
  }
  if (path_changed && desired->charger_iindpm_ma != 0u) {
    if (desired_path_enabled) {
      ec_commit_result_t safe_result = ec_commit_force_safe(state, driver);
      return safe_result == EC_COMMIT_OK ? EC_COMMIT_INVALID_DESIRED_STATE
                                        : safe_result;
    }
  }
  sequencing_change =
      path_changed || current.charger_iindpm_ma != desired->charger_iindpm_ma ||
      current.charge_power_budget_mw != desired->charge_power_budget_mw ||
      current.mu_edp_budget_mw != desired->mu_edp_budget_mw;
  if (path_changed) {
    ec_commit_result_t safe_result = ec_commit_force_safe(state, driver);
    if (safe_result != EC_COMMIT_OK) {
      return safe_result;
    }
    current = state->applied;
  }

#define COMMIT_OR_SAFE(command, old_value, new_value)                          \
  do {                                                                         \
    if (!write_if_changed(driver, (command), (old_value), (new_value))) {       \
      return fail_safe(state, driver);                                          \
    }                                                                          \
  } while (0)

  if (current.keyboard_rgb_power_enable &&
      (sequencing_change || !desired->keyboard_rgb_power_enable)) {
    COMMIT_OR_SAFE(EC_COMMIT_KEYBOARD_RGB_ENABLE, 1u, 0u);
    current.keyboard_rgb_power_enable = false;
  }
  if (current.radio_vhf_power_enable &&
      (sequencing_change || !desired->radio_vhf_power_enable)) {
    COMMIT_OR_SAFE(EC_COMMIT_RADIO_VHF_ENABLE, 1u, 0u);
    current.radio_vhf_power_enable = false;
  }
  if (current.radio_uhf_power_enable &&
      (sequencing_change || !desired->radio_uhf_power_enable)) {
    COMMIT_OR_SAFE(EC_COMMIT_RADIO_UHF_ENABLE, 1u, 0u);
    current.radio_uhf_power_enable = false;
  }
  if (current.audio_amp_enable &&
      (sequencing_change || !desired->audio_amp_enable)) {
    COMMIT_OR_SAFE(EC_COMMIT_AUDIO_AMP_ENABLE, 1u, 0u);
    current.audio_amp_enable = false;
  }
  if (current.audio_mic_enable &&
      (sequencing_change || !desired->audio_mic_enable)) {
    COMMIT_OR_SAFE(EC_COMMIT_AUDIO_MIC_ENABLE, 1u, 0u);
    current.audio_mic_enable = false;
  }
  if (current.mu_12v_enable &&
      (sequencing_change || !desired->mu_12v_enable)) {
    COMMIT_OR_SAFE(EC_COMMIT_MU_12V_ENABLE, 1u, 0u);
    current.mu_12v_enable = false;
  }
  if (current.charger_enable &&
      (sequencing_change || !desired->charger_enable)) {
    COMMIT_OR_SAFE(EC_COMMIT_CHARGER_ENABLE, 1u, 0u);
    current.charger_enable = false;
  }

  COMMIT_OR_SAFE(EC_COMMIT_CHARGER_IINDPM_MA, current.charger_iindpm_ma,
                 desired->charger_iindpm_ma);
  COMMIT_OR_SAFE(EC_COMMIT_CHARGE_BUDGET_MW,
                 current.charge_power_budget_mw,
                 desired->charge_power_budget_mw);
  COMMIT_OR_SAFE(EC_COMMIT_MU_EDP_BUDGET_MW, current.mu_edp_budget_mw,
                 desired->mu_edp_budget_mw);

  for (index = 0; index < EC_PD_PORT_COUNT; ++index) {
    ec_commit_command_t command =
        (ec_commit_command_t)(EC_COMMIT_PD1_PATH_ENABLE + index);
    COMMIT_OR_SAFE(command, current.pd_path_enable[index],
                   desired->pd_path_enable[index]);
  }

  COMMIT_OR_SAFE(EC_COMMIT_CHARGER_ENABLE, current.charger_enable,
                 desired->charger_enable);
  COMMIT_OR_SAFE(EC_COMMIT_MU_12V_ENABLE, current.mu_12v_enable,
                 desired->mu_12v_enable);
  COMMIT_OR_SAFE(EC_COMMIT_KEYBOARD_RGB_ENABLE,
                 current.keyboard_rgb_power_enable,
                 desired->keyboard_rgb_power_enable);
  COMMIT_OR_SAFE(EC_COMMIT_RADIO_VHF_ENABLE,
                 current.radio_vhf_power_enable,
                 desired->radio_vhf_power_enable);
  COMMIT_OR_SAFE(EC_COMMIT_RADIO_UHF_ENABLE,
                 current.radio_uhf_power_enable,
                 desired->radio_uhf_power_enable);
  COMMIT_OR_SAFE(EC_COMMIT_AUDIO_AMP_ENABLE, current.audio_amp_enable,
                 desired->audio_amp_enable);
  COMMIT_OR_SAFE(EC_COMMIT_AUDIO_MIC_ENABLE, current.audio_mic_enable,
                 desired->audio_mic_enable);

#undef COMMIT_OR_SAFE

  state->applied = *desired;
  state->initialized = true;
  return EC_COMMIT_OK;
}
