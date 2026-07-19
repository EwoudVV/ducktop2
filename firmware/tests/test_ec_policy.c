#include "ducktop2/ec/ec_policy.h"

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

static bool outputs_are_passive(const ec_outputs_t *outputs) {
  size_t index;

  for (index = 0; index < EC_PD_PORT_COUNT; ++index) {
    if (outputs->pd_path_enable[index]) {
      return false;
    }
  }
  return !outputs->charger_enable && outputs->charger_iindpm_ma == 0u &&
         !outputs->mu_12v_enable && !outputs->keyboard_rgb_power_enable &&
         !outputs->radio_vhf_power_enable && !outputs->radio_uhf_power_enable &&
         !outputs->audio_amp_enable && !outputs->audio_mic_enable;
}

static void set_nominal_inputs(ec_inputs_t *inputs) {
  ec_inputs_init(inputs);
  inputs->source_manager_reset_released = true;
  inputs->service_mux_reset_released = true;
  inputs->service_bus_healthy = true;
  inputs->all_pd_paths_off = true;
  inputs->charger_config_valid = true;
  inputs->thermal_data_valid = true;
  inputs->pack_telemetry_valid = true;
  inputs->vsys_valid = true;
  inputs->vsys_mv = 12000u;
  inputs->estimated_mu_edp_power_valid = true;
  inputs->estimated_aux_power_valid = true;
  inputs->requested_charge_power_mw = 5000u;
}

static void set_pd_ready(ec_inputs_t *inputs, ec_source_id_t source,
                         uint16_t current_ma, bool path_good) {
  inputs->source[source].present = true;
  inputs->source[source].path_good = path_good;
  inputs->source[source].fault_n = true;
  inputs->source[source].negotiated_current_valid = true;
  inputs->source[source].negotiated_current_ma = current_ma;
  inputs->source[source].negotiated_voltage_mv = 15000u;
}

static void set_non_pd_ready(ec_inputs_t *inputs, ec_source_id_t source,
                             uint32_t available_power_mw) {
  inputs->source[source].present = true;
  inputs->source[source].path_good = true;
  inputs->source[source].fault_n = true;
  inputs->source[source].available_power_valid = true;
  inputs->source[source].available_power_mw = available_power_mw;
}

static void confirm_iindpm(ec_inputs_t *inputs, uint16_t applied_ma) {
  inputs->charger_iindpm_applied = true;
  inputs->applied_charger_iindpm_ma = applied_ma;
}

static void configure_mu_request(ec_inputs_t *inputs, uint32_t estimate_mw,
                                 uint32_t applied_budget_mw,
                                 bool limits_applied);

static void activate_pd(ec_controller_t *controller, ec_inputs_t *inputs,
                        ec_source_id_t source, uint16_t current_ma,
                        uint32_t start_ms) {
  const uint16_t expected_ma =
      ec_policy_iindpm_ma(&controller->config, current_ma);

  set_pd_ready(inputs, source, current_ma, false);
  CHECK(ec_controller_request_source(controller, source, start_ms));
  ec_controller_step(controller, inputs, start_ms);
  CHECK(ec_controller_source_state(controller, source) ==
        EC_SOURCE_STATE_VALIDATING);
  ec_controller_step(controller, inputs, start_ms + 20u);
  CHECK(controller->outputs.pd_path_enable[source - EC_SOURCE_PD1]);
  CHECK(controller->outputs.charger_iindpm_ma == 0u);
  inputs->source[source].path_good = true;
  inputs->all_pd_paths_off = false;
  ec_controller_step(controller, inputs, start_ms + 21u);
  CHECK(controller->outputs.charger_iindpm_ma == expected_ma);
  confirm_iindpm(inputs, expected_ma);
  ec_controller_step(controller, inputs, start_ms + 22u);
  CHECK(ec_controller_source_state(controller, source) ==
        EC_SOURCE_STATE_ACTIVE);
}

static void activate_non_pd(ec_controller_t *controller, ec_inputs_t *inputs,
                            ec_source_id_t source, uint32_t available_power_mw,
                            uint32_t start_ms) {
  set_non_pd_ready(inputs, source, available_power_mw);
  CHECK(ec_controller_request_source(controller, source, start_ms));
  ec_controller_step(controller, inputs, start_ms);
  ec_controller_step(controller, inputs, start_ms + 20u);
  CHECK(ec_controller_source_state(controller, source) ==
        EC_SOURCE_STATE_ACTIVE);
}

static void test_boot_defaults(void) {
  ec_controller_t controller;
  size_t index;

  ec_controller_init(&controller, NULL, 0u);
  CHECK(outputs_are_passive(ec_controller_outputs(&controller)));
  CHECK(controller.active_source == EC_SOURCE_NONE);
  CHECK(controller.candidate_source == EC_SOURCE_NONE);
  CHECK(controller.fault == EC_FAULT_NONE);
  CHECK(controller.config.low_pack_mu_edp_budget_mw == 15000u);
  for (index = 0; index < EC_SOURCE_COUNT; ++index) {
    CHECK(controller.source_state[index] == EC_SOURCE_STATE_OFF);
  }
  CHECK(ec_controller_one_hot_invariant(&controller));
}

static void test_iindpm_math(void) {
  ec_policy_config_t config = ec_policy_default_config();

  CHECK(ec_policy_iindpm_ma(&config, 3000u) == 2750u);
  CHECK(ec_policy_iindpm_ma(&config, 2000u) == 1750u);
  CHECK(ec_policy_iindpm_ma(&config, 500u) == 250u);
  CHECK(ec_policy_iindpm_ma(&config, 5000u) == 2750u);
  CHECK(ec_policy_iindpm_ma(&config, 250u) == 0u);
  CHECK(ec_policy_iindpm_ma(&config, 0u) == 0u);
}

static void test_reset_and_service_interlocks(void) {
  ec_controller_t controller;
  ec_inputs_t inputs;

  ec_inputs_init(&inputs);
  ec_controller_init(&controller, NULL, 0u);
  set_pd_ready(&inputs, EC_SOURCE_PD1, 3000u, false);
  CHECK(ec_controller_request_source(&controller, EC_SOURCE_PD1, 0u));
  ec_controller_step(&controller, &inputs, 0u);
  ec_controller_step(&controller, &inputs, 1u);
  CHECK(controller.fault == EC_FAULT_RESET_INTERLOCK);
  CHECK(outputs_are_passive(&controller.outputs));

  set_nominal_inputs(&inputs);
  ec_controller_init(&controller, NULL, 0u);
  set_pd_ready(&inputs, EC_SOURCE_PD1, 3000u, false);
  inputs.service_bus_healthy = false;
  CHECK(ec_controller_request_source(&controller, EC_SOURCE_PD1, 0u));
  ec_controller_step(&controller, &inputs, 0u);
  CHECK(controller.fault == EC_FAULT_SERVICE_BUS);

  set_nominal_inputs(&inputs);
  ec_controller_init(&controller, NULL, 0u);
  set_pd_ready(&inputs, EC_SOURCE_PD1, 3000u, false);
  inputs.all_pd_paths_off = false;
  CHECK(ec_controller_request_source(&controller, EC_SOURCE_PD1, 0u));
  ec_controller_step(&controller, &inputs, 0u);
  CHECK(controller.fault == EC_FAULT_NONE);
  ec_controller_step(&controller, &inputs, 1000u);
  CHECK(controller.fault == EC_FAULT_RESET_INTERLOCK);
}

static void test_pd_requires_negotiated_current(void) {
  ec_controller_t controller;
  ec_inputs_t inputs;

  set_nominal_inputs(&inputs);
  ec_controller_init(&controller, NULL, 0u);
  inputs.source[EC_SOURCE_PD1].present = true;
  CHECK(ec_controller_request_source(&controller, EC_SOURCE_PD1, 0u));
  ec_controller_step(&controller, &inputs, 0u);
  ec_controller_step(&controller, &inputs, 20u);
  CHECK(!controller.outputs.pd_path_enable[0]);
  CHECK(controller.outputs.charger_iindpm_ma == 0u);
  ec_controller_step(&controller, &inputs, 1000u);
  CHECK(controller.fault == EC_FAULT_NEGOTIATED_CURRENT_INVALID);
  CHECK(outputs_are_passive(&controller.outputs));
}

static void test_unsafe_telemetry_blocks_activation(void) {
  ec_controller_t controller;
  ec_inputs_t inputs;

  set_nominal_inputs(&inputs);
  ec_controller_init(&controller, NULL, 0u);
  set_pd_ready(&inputs, EC_SOURCE_PD1, 3000u, false);
  inputs.thermal_data_valid = false;
  CHECK(ec_controller_request_source(&controller, EC_SOURCE_PD1, 0u));
  ec_controller_step(&controller, &inputs, 0u);
  ec_controller_step(&controller, &inputs, 1u);
  CHECK(controller.fault == EC_FAULT_THERMAL_DATA_INVALID);
  CHECK(outputs_are_passive(&controller.outputs));

  set_nominal_inputs(&inputs);
  ec_controller_init(&controller, NULL, 0u);
  set_non_pd_ready(&inputs, EC_SOURCE_PACK, 45000u);
  inputs.pack_telemetry_valid = false;
  CHECK(ec_controller_request_source(&controller, EC_SOURCE_PACK, 0u));
  ec_controller_step(&controller, &inputs, 0u);
  ec_controller_step(&controller, &inputs, 1u);
  CHECK(controller.fault == EC_FAULT_PACK_TELEMETRY);
  CHECK(outputs_are_passive(&controller.outputs));
}

static void test_path_bootstrap_precedes_iindpm_ack(void) {
  ec_controller_t controller;
  ec_inputs_t inputs;

  set_nominal_inputs(&inputs);
  ec_controller_init(&controller, NULL, 0u);
  set_pd_ready(&inputs, EC_SOURCE_PD1, 3000u, false);
  CHECK(ec_controller_request_source(&controller, EC_SOURCE_PD1, 0u));
  ec_controller_step(&controller, &inputs, 0u);
  ec_controller_step(&controller, &inputs, 20u);
  CHECK(controller.outputs.pd_path_enable[0]);
  CHECK(controller.outputs.charger_iindpm_ma == 0u);
  inputs.source[EC_SOURCE_PD1].path_good = true;
  inputs.all_pd_paths_off = false;
  ec_controller_step(&controller, &inputs, 21u);
  CHECK(controller.outputs.pd_path_enable[0]);
  CHECK(controller.outputs.charger_iindpm_ma == 2750u);
  confirm_iindpm(&inputs, 2750u);
  ec_controller_step(&controller, &inputs, 22u);
  CHECK(controller.outputs.pd_path_enable[0]);
  CHECK(!controller.outputs.pd_path_enable[1]);
  CHECK(!controller.outputs.pd_path_enable[2]);
}

static void test_all_paths_off_interlock_is_continuous_until_enable(void) {
  ec_controller_t controller;
  ec_inputs_t inputs;

  set_nominal_inputs(&inputs);
  ec_controller_init(&controller, NULL, 0u);
  set_pd_ready(&inputs, EC_SOURCE_PD1, 3000u, false);
  CHECK(ec_controller_request_source(&controller, EC_SOURCE_PD1, 0u));
  ec_controller_step(&controller, &inputs, 0u);
  CHECK(controller.fault == EC_FAULT_NONE);

  inputs.all_pd_paths_off = false;
  ec_controller_step(&controller, &inputs, 20u);
  CHECK(controller.fault == EC_FAULT_RESET_INTERLOCK);
  CHECK(outputs_are_passive(&controller.outputs));
}

static void test_iindpm_timeout_and_mismatch_fail_off(void) {
  ec_controller_t controller;
  ec_inputs_t inputs;

  set_nominal_inputs(&inputs);
  ec_controller_init(&controller, NULL, 0u);
  set_pd_ready(&inputs, EC_SOURCE_PD1, 3000u, false);
  CHECK(ec_controller_request_source(&controller, EC_SOURCE_PD1, 0u));
  ec_controller_step(&controller, &inputs, 0u);
  ec_controller_step(&controller, &inputs, 20u);
  CHECK(controller.outputs.pd_path_enable[0]);
  inputs.source[EC_SOURCE_PD1].path_good = true;
  inputs.all_pd_paths_off = false;
  ec_controller_step(&controller, &inputs, 21u);
  CHECK(controller.outputs.charger_iindpm_ma == 2750u);
  ec_controller_step(&controller, &inputs, 121u);
  CHECK(controller.fault == EC_FAULT_IINDPM_APPLY_TIMEOUT);
  CHECK(outputs_are_passive(&controller.outputs));

  set_nominal_inputs(&inputs);
  ec_controller_init(&controller, NULL, 0u);
  set_pd_ready(&inputs, EC_SOURCE_PD2, 2000u, false);
  CHECK(ec_controller_request_source(&controller, EC_SOURCE_PD2, 0u));
  ec_controller_step(&controller, &inputs, 0u);
  ec_controller_step(&controller, &inputs, 20u);
  inputs.source[EC_SOURCE_PD2].path_good = true;
  inputs.all_pd_paths_off = false;
  ec_controller_step(&controller, &inputs, 21u);
  confirm_iindpm(&inputs, 1800u);
  ec_controller_step(&controller, &inputs, 22u);
  CHECK(controller.fault == EC_FAULT_IINDPM_MISMATCH);
  CHECK(outputs_are_passive(&controller.outputs));
}

static void test_transfer_is_break_before_make(void) {
  ec_controller_t controller;
  ec_inputs_t inputs;

  set_nominal_inputs(&inputs);
  ec_controller_init(&controller, NULL, 0u);
  activate_pd(&controller, &inputs, EC_SOURCE_PD1, 3000u, 0u);
  inputs.all_pd_paths_off = true;
  inputs.charger_iindpm_applied = false;
  set_pd_ready(&inputs, EC_SOURCE_PD2, 2000u, false);
  CHECK(ec_controller_request_source(&controller, EC_SOURCE_PD2, 100u));
  CHECK(outputs_are_passive(&controller.outputs));
  ec_controller_step(&controller, &inputs, 100u);
  ec_controller_step(&controller, &inputs, 119u);
  CHECK(outputs_are_passive(&controller.outputs));
  ec_controller_step(&controller, &inputs, 120u);
  CHECK(!controller.outputs.pd_path_enable[0]);
  CHECK(controller.outputs.pd_path_enable[1]);
  CHECK(controller.outputs.charger_iindpm_ma == 0u);
  inputs.source[EC_SOURCE_PD2].path_good = true;
  inputs.all_pd_paths_off = false;
  ec_controller_step(&controller, &inputs, 121u);
  CHECK(controller.outputs.charger_iindpm_ma == 1750u);
  confirm_iindpm(&inputs, 1750u);
  ec_controller_step(&controller, &inputs, 122u);
  CHECK(!controller.outputs.pd_path_enable[0]);
  CHECK(controller.outputs.pd_path_enable[1]);
  CHECK(!controller.outputs.pd_path_enable[2]);
  CHECK(controller.source_state[EC_SOURCE_PD2] == EC_SOURCE_STATE_ACTIVE);
  CHECK(ec_controller_one_hot_invariant(&controller));
}

static void test_path_good_faults(void) {
  ec_controller_t controller;
  ec_inputs_t inputs;

  set_nominal_inputs(&inputs);
  ec_controller_init(&controller, NULL, 0u);
  set_pd_ready(&inputs, EC_SOURCE_PD3, 3000u, false);
  CHECK(ec_controller_request_source(&controller, EC_SOURCE_PD3, 0u));
  ec_controller_step(&controller, &inputs, 0u);
  ec_controller_step(&controller, &inputs, 20u);
  CHECK(controller.outputs.pd_path_enable[2]);
  CHECK(controller.outputs.charger_iindpm_ma == 0u);
  ec_controller_step(&controller, &inputs, 270u);
  CHECK(controller.fault == EC_FAULT_PATH_GOOD_TIMEOUT);
  CHECK(outputs_are_passive(&controller.outputs));

  set_nominal_inputs(&inputs);
  ec_controller_init(&controller, NULL, 0u);
  set_pd_ready(&inputs, EC_SOURCE_PD2, 3000u, true);
  CHECK(ec_controller_request_source(&controller, EC_SOURCE_PD2, 0u));
  ec_controller_step(&controller, &inputs, 0u);
  ec_controller_step(&controller, &inputs, 20u);
  CHECK(controller.fault == EC_FAULT_PATH_GOOD_STUCK_HIGH);
  CHECK(outputs_are_passive(&controller.outputs));
}

static void test_active_pd_faults_and_charging(void) {
  ec_controller_t controller;
  ec_inputs_t inputs;

  set_nominal_inputs(&inputs);
  ec_controller_init(&controller, NULL, 0u);
  activate_pd(&controller, &inputs, EC_SOURCE_PD1, 3000u, 0u);
  inputs.request_charger = true;
  ec_controller_step(&controller, &inputs, 23u);
  CHECK(controller.outputs.charger_enable);
  CHECK(controller.outputs.charge_power_budget_mw == 5000u);

  inputs.source[EC_SOURCE_PD1].negotiated_current_ma = 499u;
  ec_controller_step(&controller, &inputs, 24u);
  CHECK(controller.fault == EC_FAULT_NEGOTIATED_CURRENT_INVALID);
  CHECK(outputs_are_passive(&controller.outputs));

  set_nominal_inputs(&inputs);
  ec_controller_init(&controller, NULL, 0u);
  activate_pd(&controller, &inputs, EC_SOURCE_PD1, 3000u, 0u);
  inputs.applied_charger_iindpm_ma = 2000u;
  ec_controller_step(&controller, &inputs, 23u);
  CHECK(controller.fault == EC_FAULT_IINDPM_MISMATCH);
  CHECK(outputs_are_passive(&controller.outputs));
}

static void test_source_aware_charge_budget(void) {
  ec_controller_t controller;
  ec_inputs_t inputs;

  set_nominal_inputs(&inputs);
  ec_controller_init(&controller, NULL, 0u);
  activate_pd(&controller, &inputs, EC_SOURCE_PD1, 2000u, 0u);
  inputs.request_charger = true;
  inputs.requested_charge_power_mw = 10000u;
  inputs.estimated_aux_power_mw = 1000u;
  inputs.estimated_mu_edp_power_mw = 12000u;
  ec_controller_step(&controller, &inputs, 23u);
  CHECK(controller.outputs.source_input_power_mw == 26250u);
  CHECK(controller.outputs.source_usable_power_mw == 22312u);
  CHECK(controller.outputs.charge_power_budget_mw == 3312u);
  CHECK(controller.outputs.charger_enable);

  inputs.estimated_aux_power_mw = 2000u;
  ec_controller_step(&controller, &inputs, 24u);
  CHECK(controller.outputs.charge_power_budget_mw == 2312u);
  CHECK(!controller.outputs.charger_enable);
}

static void test_weak_pd_contract_cannot_start_mu(void) {
  ec_controller_t controller;
  ec_inputs_t inputs;

  set_nominal_inputs(&inputs);
  ec_controller_init(&controller, NULL, 0u);
  activate_pd(&controller, &inputs, EC_SOURCE_PD3, 500u, 0u);
  ec_controller_step(&controller, &inputs, 23u);
  CHECK(controller.outputs.source_input_power_mw == 3750u);
  CHECK(controller.outputs.source_usable_power_mw == 3187u);
  CHECK(controller.outputs.mu_edp_budget_mw == 0u);
  configure_mu_request(&inputs, 1u, 1u, true);
  ec_controller_step(&controller, &inputs, 24u);
  CHECK(controller.fault == EC_FAULT_POWER_POLICY);
  CHECK(outputs_are_passive(&controller.outputs));
}

static void test_aux_charging_requires_applied_limit(void) {
  ec_controller_t controller;
  ec_inputs_t inputs;

  set_nominal_inputs(&inputs);
  ec_controller_init(&controller, NULL, 0u);
  activate_non_pd(&controller, &inputs, EC_SOURCE_AUX, 45000u, 0u);
  inputs.source[EC_SOURCE_AUX].negotiated_current_valid = true;
  inputs.source[EC_SOURCE_AUX].negotiated_current_ma = 1800u;
  inputs.request_charger = true;
  ec_controller_step(&controller, &inputs, 21u);
  CHECK(controller.outputs.charger_iindpm_ma == 1550u);
  CHECK(!controller.outputs.charger_enable);
  confirm_iindpm(&inputs, 1550u);
  ec_controller_step(&controller, &inputs, 22u);
  CHECK(controller.outputs.charger_enable);
  inputs.source[EC_SOURCE_AUX].negotiated_current_valid = false;
  ec_controller_step(&controller, &inputs, 23u);
  CHECK(controller.outputs.charger_iindpm_ma == 0u);
  CHECK(!controller.outputs.charger_enable);
}

static void configure_mu_request(ec_inputs_t *inputs, uint32_t estimate_mw,
                                 uint32_t applied_budget_mw,
                                 bool limits_applied) {
  inputs->request_mu_12v = true;
  inputs->estimated_mu_edp_power_valid = true;
  inputs->estimated_mu_edp_power_mw = estimate_mw;
  inputs->power_limits_applied = limits_applied;
  inputs->applied_mu_edp_budget_mw = applied_budget_mw;
}

static void test_low_pack_15w_policy(void) {
  ec_controller_t controller;
  ec_inputs_t inputs;

  set_nominal_inputs(&inputs);
  ec_controller_init(&controller, NULL, 0u);
  activate_non_pd(&controller, &inputs, EC_SOURCE_PACK, 37530u, 0u);
  inputs.pack_only = false;
  inputs.pack_low = true;
  inputs.request_keyboard_rgb = true;
  inputs.request_radio_vhf = true;
  inputs.request_radio_uhf = true;
  inputs.request_audio_amp = true;
  inputs.request_audio_mic = true;
  configure_mu_request(&inputs, 15000u, 15000u, true);
  ec_controller_step(&controller, &inputs, 21u);
  CHECK(controller.outputs.source_input_power_mw == 37530u);
  CHECK(controller.outputs.source_usable_power_mw == 31900u);
  CHECK(controller.outputs.mu_edp_budget_mw == 15000u);
  CHECK(controller.outputs.power_policy_confirmed);
  CHECK(controller.outputs.mu_12v_enable);
  CHECK(!controller.outputs.charger_enable);
  CHECK(!controller.outputs.keyboard_rgb_power_enable);
  CHECK(!controller.outputs.radio_vhf_power_enable);
  CHECK(!controller.outputs.radio_uhf_power_enable);
  CHECK(!controller.outputs.audio_amp_enable);
  CHECK(!controller.outputs.audio_mic_enable);

  set_nominal_inputs(&inputs);
  ec_controller_init(&controller, NULL, 0u);
  activate_non_pd(&controller, &inputs, EC_SOURCE_PACK, 37530u, 0u);
  inputs.pack_only = false;
  inputs.pack_low = true;
  configure_mu_request(&inputs, 15001u, 15000u, true);
  ec_controller_step(&controller, &inputs, 21u);
  CHECK(controller.fault == EC_FAULT_POWER_POLICY);
  CHECK(outputs_are_passive(&controller.outputs));
}

static void test_power_policy_ack_and_mu_pg_faults(void) {
  ec_controller_t controller;
  ec_inputs_t inputs;

  set_nominal_inputs(&inputs);
  ec_controller_init(&controller, NULL, 0u);
  activate_non_pd(&controller, &inputs, EC_SOURCE_PACK, 45000u, 0u);
  configure_mu_request(&inputs, 20000u, 0u, false);
  ec_controller_step(&controller, &inputs, 21u);
  CHECK(!controller.outputs.mu_12v_enable);
  CHECK(controller.fault == EC_FAULT_NONE);
  ec_controller_step(&controller, &inputs, 271u);
  CHECK(controller.fault == EC_FAULT_POWER_POLICY_APPLY_TIMEOUT);
  CHECK(outputs_are_passive(&controller.outputs));

  set_nominal_inputs(&inputs);
  ec_controller_init(&controller, NULL, 0u);
  activate_non_pd(&controller, &inputs, EC_SOURCE_PACK, 45000u, 0u);
  configure_mu_request(&inputs, 20000u, 30000u, true);
  ec_controller_step(&controller, &inputs, 21u);
  CHECK(controller.outputs.mu_12v_enable);
  ec_controller_step(&controller, &inputs, 41u);
  CHECK(controller.fault == EC_FAULT_MU_POWER_GOOD_TIMEOUT);

  set_nominal_inputs(&inputs);
  ec_controller_init(&controller, NULL, 0u);
  activate_non_pd(&controller, &inputs, EC_SOURCE_PACK, 45000u, 0u);
  configure_mu_request(&inputs, 20000u, 30000u, true);
  inputs.mu_12v_pg = true;
  ec_controller_step(&controller, &inputs, 21u);
  CHECK(controller.fault == EC_FAULT_MU_POWER_GOOD_STUCK_HIGH);

  set_nominal_inputs(&inputs);
  ec_controller_init(&controller, NULL, 0u);
  activate_non_pd(&controller, &inputs, EC_SOURCE_PACK, 45000u, 0u);
  configure_mu_request(&inputs, 20000u, 30000u, true);
  ec_controller_step(&controller, &inputs, 21u);
  inputs.mu_12v_pg = true;
  ec_controller_step(&controller, &inputs, 22u);
  inputs.mu_12v_pg = false;
  ec_controller_step(&controller, &inputs, 23u);
  CHECK(controller.fault == EC_FAULT_MU_POWER_GOOD_LOST);
  CHECK(outputs_are_passive(&controller.outputs));
}

static void test_runtime_safety_inputs_fail_off(void) {
  ec_controller_t controller;
  ec_inputs_t inputs;

  set_nominal_inputs(&inputs);
  ec_controller_init(&controller, NULL, 0u);
  activate_non_pd(&controller, &inputs, EC_SOURCE_PACK, 45000u, 0u);
  inputs.thermal_data_valid = false;
  ec_controller_step(&controller, &inputs, 21u);
  CHECK(controller.fault == EC_FAULT_THERMAL_DATA_INVALID);
  CHECK(outputs_are_passive(&controller.outputs));

  set_nominal_inputs(&inputs);
  ec_controller_init(&controller, NULL, 0u);
  activate_non_pd(&controller, &inputs, EC_SOURCE_PACK, 45000u, 0u);
  inputs.pack_telemetry_valid = false;
  ec_controller_step(&controller, &inputs, 21u);
  CHECK(controller.fault == EC_FAULT_PACK_TELEMETRY);

  set_nominal_inputs(&inputs);
  ec_controller_init(&controller, NULL, 0u);
  activate_non_pd(&controller, &inputs, EC_SOURCE_PACK, 45000u, 0u);
  inputs.request_mu_12v = true;
  inputs.vsys_valid = false;
  ec_controller_step(&controller, &inputs, 21u);
  CHECK(controller.fault == EC_FAULT_VSYS_INVALID);
}

static void test_watchdog_reset_and_fault_recovery(void) {
  ec_controller_t controller;
  ec_inputs_t inputs;

  set_nominal_inputs(&inputs);
  ec_controller_init(&controller, NULL, 0u);
  activate_pd(&controller, &inputs, EC_SOURCE_PD1, 3000u, 0u);
  inputs.watchdog_healthy = false;
  ec_controller_step(&controller, &inputs, 30u);
  CHECK(controller.fault == EC_FAULT_WATCHDOG);
  CHECK(outputs_are_passive(&controller.outputs));
  ec_controller_stop_source(&controller, 31u);
  CHECK(controller.fault == EC_FAULT_WATCHDOG);
  CHECK(!ec_controller_clear_fault(&controller, false, 31u));
  CHECK(ec_controller_clear_fault(&controller, true, 32u));
  CHECK(outputs_are_passive(&controller.outputs));

  set_nominal_inputs(&inputs);
  activate_pd(&controller, &inputs, EC_SOURCE_PD1, 3000u, 40u);
  inputs.reset_asserted = true;
  ec_controller_step(&controller, &inputs, 70u);
  CHECK(controller.fault == EC_FAULT_NONE);
  CHECK(controller.active_source == EC_SOURCE_NONE);
  CHECK(outputs_are_passive(&controller.outputs));
}

static uint32_t next_random(uint32_t *state) {
  *state = *state * 1664525u + 1013904223u;
  return *state;
}

static void test_deterministic_transition_properties(void) {
  ec_controller_t controller;
  ec_inputs_t inputs;
  uint32_t random_state = 0x4455434bu;
  uint32_t now_ms = 0u;
  size_t iteration;

  ec_controller_init(&controller, NULL, now_ms);
  for (iteration = 0; iteration < 20000u; ++iteration) {
    const ec_outputs_t previous_outputs = controller.outputs;
    const ec_outputs_t *outputs;
    size_t index;
    unsigned int enabled_paths = 0u;

    set_nominal_inputs(&inputs);
    for (index = 0; index < EC_SOURCE_COUNT; ++index) {
      uint32_t bits = next_random(&random_state);
      inputs.source[index].present = (bits & 1u) != 0u;
      inputs.source[index].path_good = (bits & 2u) != 0u;
      inputs.source[index].fault_n = (bits & 4u) != 0u;
      inputs.source[index].negotiated_current_valid = (bits & 8u) != 0u;
      inputs.source[index].negotiated_current_ma =
          (uint16_t)(250u + (bits % 5000u));
      inputs.source[index].negotiated_voltage_mv = 15000u;
      inputs.source[index].available_power_valid = true;
      inputs.source[index].available_power_mw = 45000u;
    }
    if (previous_outputs.charger_iindpm_ma > 0u &&
        (next_random(&random_state) & 3u) != 0u) {
      confirm_iindpm(&inputs, previous_outputs.charger_iindpm_ma);
    }
    inputs.pack_only = (next_random(&random_state) & 1u) != 0u;
    inputs.pack_low = (next_random(&random_state) & 1u) != 0u;
    inputs.mu_12v_pg = (next_random(&random_state) & 1u) != 0u;
    inputs.request_charger = (next_random(&random_state) & 1u) != 0u;
    inputs.request_mu_12v = (next_random(&random_state) & 1u) != 0u;
    inputs.request_keyboard_rgb = (next_random(&random_state) & 1u) != 0u;
    inputs.request_radio_vhf = (next_random(&random_state) & 1u) != 0u;
    inputs.request_radio_uhf = (next_random(&random_state) & 1u) != 0u;
    inputs.request_audio_amp = (next_random(&random_state) & 1u) != 0u;
    inputs.request_audio_mic = (next_random(&random_state) & 1u) != 0u;
    inputs.estimated_mu_edp_power_mw =
        10000u + (next_random(&random_state) % 30000u);
    if (previous_outputs.mu_edp_budget_mw > 0u &&
        (next_random(&random_state) & 1u) != 0u) {
      inputs.power_limits_applied = true;
      inputs.applied_mu_edp_budget_mw = previous_outputs.mu_edp_budget_mw;
    }

    if (controller.fault != EC_FAULT_NONE) {
      CHECK(ec_controller_clear_fault(&controller, true, now_ms));
    }
    if (controller.active_source == EC_SOURCE_NONE &&
        controller.candidate_source == EC_SOURCE_NONE) {
      ec_source_id_t requested =
          (ec_source_id_t)(next_random(&random_state) % EC_SOURCE_COUNT);
      CHECK(ec_controller_request_source(&controller, requested, now_ms));
    } else if ((next_random(&random_state) % 97u) == 0u) {
      ec_source_id_t requested =
          (ec_source_id_t)(next_random(&random_state) % EC_SOURCE_COUNT);
      CHECK(ec_controller_request_source(&controller, requested, now_ms));
    }

    now_ms += 1u + (next_random(&random_state) % 31u);
    ec_controller_step(&controller, &inputs, now_ms);
    outputs = ec_controller_outputs(&controller);
    CHECK(ec_controller_one_hot_invariant(&controller));
    for (index = 0; index < EC_PD_PORT_COUNT; ++index) {
      if (outputs->pd_path_enable[index]) {
        ec_source_id_t source = (ec_source_id_t)(EC_SOURCE_PD1 + index);
        ++enabled_paths;
        CHECK(inputs.source[source].negotiated_current_valid);
        CHECK(inputs.source[source].negotiated_current_ma >=
              controller.config.minimum_pd_current_ma);
        if (outputs->charger_iindpm_ma == 0u) {
          CHECK(!outputs->charger_enable);
          CHECK(!outputs->mu_12v_enable);
          CHECK(!outputs->keyboard_rgb_power_enable);
          CHECK(!outputs->radio_vhf_power_enable);
          CHECK(!outputs->radio_uhf_power_enable);
          CHECK(!outputs->audio_amp_enable);
          CHECK(!outputs->audio_mic_enable);
        } else {
          CHECK(inputs.charger_iindpm_applied);
          CHECK(inputs.applied_charger_iindpm_ma ==
                outputs->charger_iindpm_ma);
        }
      }
    }
    CHECK(enabled_paths <= 1u);
    if (controller.fault != EC_FAULT_NONE) {
      CHECK(outputs_are_passive(outputs));
    }
    if (outputs->charger_enable) {
      CHECK(inputs.charger_iindpm_applied);
      CHECK(inputs.applied_charger_iindpm_ma ==
            outputs->charger_iindpm_ma);
      CHECK(inputs.charger_config_valid);
      CHECK(inputs.charger_fault_n);
    }
    if (outputs->mu_12v_enable) {
      CHECK(inputs.request_mu_12v);
      CHECK(inputs.power_limits_applied);
      CHECK(inputs.applied_mu_edp_budget_mw <= outputs->mu_edp_budget_mw);
      CHECK(inputs.estimated_mu_edp_power_mw <=
            inputs.applied_mu_edp_budget_mw);
      CHECK(inputs.vsys_valid);
    }
    if (controller.active_source == EC_SOURCE_PACK && inputs.pack_low) {
      CHECK(outputs->mu_edp_budget_mw <= 15000u);
      CHECK(!outputs->charger_enable);
      CHECK(!outputs->keyboard_rgb_power_enable);
      CHECK(!outputs->radio_vhf_power_enable);
      CHECK(!outputs->radio_uhf_power_enable);
      CHECK(!outputs->audio_amp_enable);
      CHECK(!outputs->audio_mic_enable);
    }
  }
}

int main(void) {
  test_boot_defaults();
  test_iindpm_math();
  test_reset_and_service_interlocks();
  test_pd_requires_negotiated_current();
  test_unsafe_telemetry_blocks_activation();
  test_path_bootstrap_precedes_iindpm_ack();
  test_all_paths_off_interlock_is_continuous_until_enable();
  test_iindpm_timeout_and_mismatch_fail_off();
  test_transfer_is_break_before_make();
  test_path_good_faults();
  test_active_pd_faults_and_charging();
  test_source_aware_charge_budget();
  test_weak_pd_contract_cannot_start_mu();
  test_aux_charging_requires_applied_limit();
  test_low_pack_15w_policy();
  test_power_policy_ack_and_mu_pg_faults();
  test_runtime_safety_inputs_fail_off();
  test_watchdog_reset_and_fault_recovery();
  test_deterministic_transition_properties();

  if (failures != 0) {
    fprintf(stderr, "ec_policy_tests: %d failure(s)\n", failures);
    return 1;
  }
  puts("ec_policy_tests: PASS");
  return 0;
}
