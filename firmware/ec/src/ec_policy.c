#include "ducktop2/ec/ec_policy.h"

#include <limits.h>
#include <string.h>

static bool source_is_valid(ec_source_id_t source) {
  return (unsigned int)source < EC_SOURCE_COUNT;
}

static bool source_is_pd(ec_source_id_t source) {
  return source >= EC_SOURCE_PD1 && source <= EC_SOURCE_PD3;
}

static size_t pd_index(ec_source_id_t source) {
  return (size_t)(source - EC_SOURCE_PD1);
}

static bool time_reached(uint32_t now_ms, uint32_t deadline_ms) {
  return (int32_t)(now_ms - deadline_ms) >= 0;
}

static uint32_t minimum_u32(uint32_t left, uint32_t right) {
  return left < right ? left : right;
}

static uint32_t subtract_saturating_u32(uint32_t value, uint32_t amount) {
  return value > amount ? value - amount : 0u;
}

static bool reset_domains_released(const ec_inputs_t *inputs) {
  return inputs->source_manager_reset_released &&
         inputs->service_mux_reset_released;
}

static void outputs_safe(ec_outputs_t *outputs) {
  memset(outputs, 0, sizeof(*outputs));
}

static void states_off(ec_controller_t *controller) {
  size_t index;

  for (index = 0; index < EC_SOURCE_COUNT; ++index) {
    controller->source_state[index] = EC_SOURCE_STATE_OFF;
  }
}

static void runtime_safe_reset(ec_controller_t *controller, uint32_t now_ms) {
  outputs_safe(&controller->outputs);
  states_off(controller);
  controller->candidate_source = EC_SOURCE_NONE;
  controller->active_source = EC_SOURCE_NONE;
  controller->fault_source = EC_SOURCE_NONE;
  controller->fault = EC_FAULT_NONE;
  controller->validation_started_ms = now_ms;
  controller->enable_not_before_ms = now_ms;
  controller->path_enable_started_ms = now_ms;
  controller->iindpm_command_started_ms = now_ms;
  controller->power_policy_started_ms = now_ms;
  controller->mu_enable_started_ms = now_ms;
  controller->path_commanded = false;
  controller->iindpm_commanded = false;
  controller->power_policy_waiting = false;
  controller->commanded_mu_edp_budget_mw = 0u;
  controller->reset_interlock_confirmed = false;
  controller->mu_waiting_for_pg = false;
  controller->mu_pg_confirmed = false;
}

static void enter_fault(ec_controller_t *controller, ec_source_id_t source,
                        ec_fault_t fault) {
  outputs_safe(&controller->outputs);
  states_off(controller);
  if (source_is_valid(source)) {
    controller->source_state[source] = EC_SOURCE_STATE_FAULT;
  }
  controller->candidate_source = EC_SOURCE_NONE;
  controller->active_source = EC_SOURCE_NONE;
  controller->fault_source = source;
  controller->fault = fault;
  controller->path_commanded = false;
  controller->iindpm_commanded = false;
  controller->power_policy_waiting = false;
  controller->commanded_mu_edp_budget_mw = 0u;
  controller->reset_interlock_confirmed = false;
  controller->mu_waiting_for_pg = false;
  controller->mu_pg_confirmed = false;
}

ec_policy_config_t ec_policy_default_config(void) {
  ec_policy_config_t config;

  config.source_deadtime_ms = 20u;
  config.validation_timeout_ms = 1000u;
  config.iindpm_apply_timeout_ms = 100u;
  config.path_good_timeout_ms = 250u;
  config.power_policy_apply_timeout_ms = 250u;
  config.mu_power_good_timeout_ms = 20u;
  config.minimum_pd_current_ma = 500u;
  config.iindpm_margin_ma = 250u;
  config.iindpm_cap_ma = 2750u;
  config.minimum_vsys_mv = 10000u;
  config.source_efficiency_permille =
      EC_DEFAULT_SOURCE_EFFICIENCY_PERMILLE;
  config.system_reserve_mw = EC_DEFAULT_SYSTEM_RESERVE_MW;
  config.minimum_charge_budget_mw = 2500u;
  config.maximum_charge_budget_mw = 10000u;
  config.normal_mu_edp_budget_mw =
      EC_DEFAULT_NORMAL_MU_EDP_BUDGET_MW;
  config.low_pack_mu_edp_budget_mw =
      EC_DEFAULT_LOW_PACK_MU_EDP_BUDGET_MW;
  return config;
}

void ec_inputs_init(ec_inputs_t *inputs) {
  size_t index;

  memset(inputs, 0, sizeof(*inputs));
  inputs->watchdog_healthy = true;
  inputs->charger_fault_n = true;
  inputs->thermal_ok = true;
  for (index = 0; index < EC_SOURCE_COUNT; ++index) {
    inputs->source[index].fault_n = true;
  }
}

void ec_controller_init(ec_controller_t *controller,
                        const ec_policy_config_t *config, uint32_t now_ms) {
  memset(controller, 0, sizeof(*controller));
  controller->config = config != NULL ? *config : ec_policy_default_config();
  runtime_safe_reset(controller, now_ms);
}

uint16_t ec_policy_iindpm_ma(const ec_policy_config_t *config,
                             uint16_t negotiated_current_ma) {
  uint16_t available_ma;

  if (config == NULL || negotiated_current_ma <= config->iindpm_margin_ma) {
    return 0u;
  }
  available_ma = (uint16_t)(negotiated_current_ma - config->iindpm_margin_ma);
  return available_ma < config->iindpm_cap_ma ? available_ma
                                              : config->iindpm_cap_ma;
}

uint32_t ec_policy_pd_input_power_mw(const ec_policy_config_t *config,
                                     uint16_t negotiated_voltage_mv,
                                     uint16_t negotiated_current_ma) {
  uint16_t iindpm_ma = ec_policy_iindpm_ma(config, negotiated_current_ma);

  return ((uint32_t)negotiated_voltage_mv * (uint32_t)iindpm_ma) / 1000u;
}

uint32_t ec_policy_usable_power_mw(const ec_policy_config_t *config,
                                   uint32_t source_input_power_mw) {
  uint64_t scaled_power_mw;

  if (config == NULL || config->source_efficiency_permille > 1000u) {
    return 0u;
  }
  scaled_power_mw =
      ((uint64_t)source_input_power_mw * config->source_efficiency_permille) /
      1000u;
  return scaled_power_mw > UINT32_MAX ? UINT32_MAX
                                      : (uint32_t)scaled_power_mw;
}

static uint32_t source_input_power_mw(const ec_controller_t *controller,
                                      const ec_source_observation_t *source,
                                      ec_source_id_t source_id) {
  if (source_is_pd(source_id)) {
    if (!source->negotiated_current_valid ||
        source->negotiated_voltage_mv == 0u) {
      return 0u;
    }
    return ec_policy_pd_input_power_mw(&controller->config,
                                       source->negotiated_voltage_mv,
                                       source->negotiated_current_ma);
  }
  return source->available_power_valid ? source->available_power_mw : 0u;
}

static bool reset_interlock_ready(const ec_inputs_t *inputs) {
  return reset_domains_released(inputs) && inputs->service_bus_healthy &&
         inputs->all_pd_paths_off;
}

bool ec_controller_request_source(ec_controller_t *controller,
                                  ec_source_id_t source, uint32_t now_ms) {
  if (!source_is_valid(source) || controller->fault != EC_FAULT_NONE) {
    return false;
  }
  if (controller->active_source == source &&
      controller->source_state[source] == EC_SOURCE_STATE_ACTIVE) {
    return true;
  }

  outputs_safe(&controller->outputs);
  states_off(controller);
  controller->candidate_source = source;
  controller->active_source = EC_SOURCE_NONE;
  controller->fault_source = EC_SOURCE_NONE;
  controller->source_state[source] = EC_SOURCE_STATE_VALIDATING;
  controller->validation_started_ms = now_ms;
  controller->enable_not_before_ms =
      now_ms + controller->config.source_deadtime_ms;
  controller->path_enable_started_ms = now_ms;
  controller->iindpm_command_started_ms = now_ms;
  controller->power_policy_started_ms = now_ms;
  controller->path_commanded = false;
  controller->iindpm_commanded = false;
  controller->power_policy_waiting = false;
  controller->commanded_mu_edp_budget_mw = 0u;
  controller->reset_interlock_confirmed = false;
  controller->mu_waiting_for_pg = false;
  controller->mu_pg_confirmed = false;
  return true;
}

void ec_controller_stop_source(ec_controller_t *controller, uint32_t now_ms) {
  if (controller->fault != EC_FAULT_NONE) {
    outputs_safe(&controller->outputs);
    return;
  }
  runtime_safe_reset(controller, now_ms);
}

static void step_validating(ec_controller_t *controller,
                            const ec_inputs_t *inputs, uint32_t now_ms) {
  ec_source_id_t source = controller->candidate_source;
  const ec_source_observation_t *observation;
  uint16_t expected_iindpm_ma;

  if (!source_is_valid(source)) {
    return;
  }
  observation = &inputs->source[source];
  if (!reset_domains_released(inputs)) {
    enter_fault(controller, source, EC_FAULT_RESET_INTERLOCK);
    return;
  }
  if (!inputs->service_bus_healthy) {
    enter_fault(controller, source, EC_FAULT_SERVICE_BUS);
    return;
  }

  if (!controller->reset_interlock_confirmed) {
    if (reset_interlock_ready(inputs)) {
      controller->reset_interlock_confirmed = true;
    } else if (time_reached(now_ms,
                            controller->validation_started_ms +
                                controller->config.validation_timeout_ms)) {
      enter_fault(controller, source,
                  !reset_domains_released(inputs) ||
                          !inputs->all_pd_paths_off
                      ? EC_FAULT_RESET_INTERLOCK
                      : EC_FAULT_SERVICE_BUS);
    }
    return;
  }
  if (!reset_domains_released(inputs)) {
    enter_fault(controller, source, EC_FAULT_RESET_INTERLOCK);
    return;
  }
  if (!inputs->service_bus_healthy) {
    enter_fault(controller, source, EC_FAULT_SERVICE_BUS);
    return;
  }
  if (!controller->path_commanded && !inputs->all_pd_paths_off) {
    enter_fault(controller, source, EC_FAULT_RESET_INTERLOCK);
    return;
  }

  if (!observation->present) {
    if (controller->path_commanded) {
      enter_fault(controller, source, EC_FAULT_SOURCE_MISSING);
    } else if (time_reached(now_ms,
                            controller->validation_started_ms +
                                controller->config.validation_timeout_ms)) {
      enter_fault(controller, source, EC_FAULT_SOURCE_MISSING);
    }
    return;
  }
  if (!observation->fault_n) {
    enter_fault(controller, source, EC_FAULT_SOURCE_REPORTED);
    return;
  }
  if (!inputs->charger_fault_n) {
    enter_fault(controller, source, EC_FAULT_CHARGER);
    return;
  }
  if (!inputs->thermal_data_valid) {
    enter_fault(controller, source, EC_FAULT_THERMAL_DATA_INVALID);
    return;
  }
  if (!inputs->thermal_ok) {
    enter_fault(controller, source, EC_FAULT_THERMAL);
    return;
  }
  if (source == EC_SOURCE_PACK && !inputs->pack_telemetry_valid) {
    enter_fault(controller, source, EC_FAULT_PACK_TELEMETRY);
    return;
  }
  if (!source_is_pd(source) && !observation->available_power_valid) {
    enter_fault(controller, source,
                source == EC_SOURCE_PACK ? EC_FAULT_PACK_TELEMETRY
                                         : EC_FAULT_POWER_POLICY);
    return;
  }
  if (!time_reached(now_ms, controller->enable_not_before_ms)) {
    return;
  }

  if (source_is_pd(source)) {
    if (!observation->negotiated_current_valid ||
        observation->negotiated_voltage_mv == 0u ||
        observation->negotiated_current_ma <
            controller->config.minimum_pd_current_ma ||
        ec_policy_iindpm_ma(&controller->config,
                            observation->negotiated_current_ma) == 0u) {
      if (controller->path_commanded) {
        enter_fault(controller, source, EC_FAULT_NEGOTIATED_CURRENT_INVALID);
      } else if (time_reached(now_ms,
                              controller->validation_started_ms +
                                  controller->config.validation_timeout_ms)) {
        enter_fault(controller, source, EC_FAULT_NEGOTIATED_CURRENT_INVALID);
      }
      return;
    }

    expected_iindpm_ma = ec_policy_iindpm_ma(
        &controller->config, observation->negotiated_current_ma);
    if (!controller->path_commanded) {
      if (observation->path_good) {
        enter_fault(controller, source, EC_FAULT_PATH_GOOD_STUCK_HIGH);
        return;
      }
      controller->outputs.pd_path_enable[pd_index(source)] = true;
      controller->path_commanded = true;
      controller->path_enable_started_ms = now_ms;
      return;
    }
    if (!observation->path_good) {
      if (time_reached(now_ms, controller->path_enable_started_ms +
                                   controller->config.path_good_timeout_ms)) {
        enter_fault(controller, source, EC_FAULT_PATH_GOOD_TIMEOUT);
      }
      return;
    }
    controller->outputs.charger_iindpm_ma = expected_iindpm_ma;
    if (!controller->iindpm_commanded) {
      controller->iindpm_commanded = true;
      controller->iindpm_command_started_ms = now_ms;
      return;
    }
    if (!inputs->charger_iindpm_applied) {
      if (time_reached(now_ms, controller->iindpm_command_started_ms +
                                   controller->config.iindpm_apply_timeout_ms)) {
        enter_fault(controller, source, EC_FAULT_IINDPM_APPLY_TIMEOUT);
      }
      return;
    }
    if (inputs->applied_charger_iindpm_ma != expected_iindpm_ma) {
      enter_fault(controller, source, EC_FAULT_IINDPM_MISMATCH);
      return;
    }
  } else if (!observation->path_good) {
    if (time_reached(now_ms, controller->validation_started_ms +
                                 controller->config.validation_timeout_ms)) {
      enter_fault(controller, source, EC_FAULT_VALIDATION_TIMEOUT);
    }
    return;
  }

  controller->source_state[source] = EC_SOURCE_STATE_ACTIVE;
  controller->active_source = source;
  controller->candidate_source = EC_SOURCE_NONE;
}

static void apply_load_policy(ec_controller_t *controller,
                              const ec_inputs_t *inputs, uint32_t now_ms) {
  const bool low_pack_mode = controller->active_source == EC_SOURCE_PACK &&
                             inputs->pack_low;
  const bool source_external = controller->active_source != EC_SOURCE_PACK;
  const ec_source_observation_t *active =
      &inputs->source[controller->active_source];
  const uint32_t source_power_mw = source_input_power_mw(
      controller, active, controller->active_source);
  const uint32_t usable_power_mw =
      ec_policy_usable_power_mw(&controller->config, source_power_mw);
  const uint32_t ceiling_mw =
      low_pack_mode ? controller->config.low_pack_mu_edp_budget_mw
                    : controller->config.normal_mu_edp_budget_mw;
  uint32_t system_budget_mw = subtract_saturating_u32(
      usable_power_mw, controller->config.system_reserve_mw);
  uint32_t mu_budget_mw;
  uint32_t charge_budget_mw = 0u;
  uint32_t remaining_after_loads_mw;
  bool optional_loads_permitted;

  if (inputs->estimated_aux_power_valid) {
    system_budget_mw = subtract_saturating_u32(
        system_budget_mw, inputs->estimated_aux_power_mw);
  } else {
    system_budget_mw = 0u;
  }
  mu_budget_mw = minimum_u32(system_budget_mw, ceiling_mw);

  if (source_external && active->negotiated_current_valid) {
    controller->outputs.charger_iindpm_ma =
        ec_policy_iindpm_ma(&controller->config, active->negotiated_current_ma);
  } else {
    controller->outputs.charger_iindpm_ma = 0u;
  }

  controller->outputs.source_input_power_mw = source_power_mw;
  controller->outputs.source_usable_power_mw = usable_power_mw;
  controller->outputs.mu_edp_budget_mw = mu_budget_mw;
  controller->outputs.power_policy_confirmed =
      inputs->estimated_mu_edp_power_valid &&
      inputs->estimated_aux_power_valid && inputs->power_limits_applied &&
      inputs->applied_mu_edp_budget_mw > 0u &&
      inputs->applied_mu_edp_budget_mw <= mu_budget_mw &&
      inputs->estimated_mu_edp_power_mw <=
          inputs->applied_mu_edp_budget_mw;
  controller->outputs.power_budget_limited =
      !controller->outputs.power_policy_confirmed;

  remaining_after_loads_mw = system_budget_mw;
  if (inputs->estimated_mu_edp_power_valid) {
    remaining_after_loads_mw = subtract_saturating_u32(
        remaining_after_loads_mw, inputs->estimated_mu_edp_power_mw);
  } else {
    remaining_after_loads_mw = 0u;
  }
  if (source_external && inputs->request_charger && !low_pack_mode) {
    charge_budget_mw = minimum_u32(inputs->requested_charge_power_mw,
                                   remaining_after_loads_mw);
    charge_budget_mw = minimum_u32(
        charge_budget_mw, controller->config.maximum_charge_budget_mw);
  }
  controller->outputs.charge_power_budget_mw = charge_budget_mw;

  controller->outputs.charger_enable =
      inputs->request_charger && source_external && inputs->charger_fault_n &&
      inputs->charger_config_valid && active->negotiated_current_valid &&
      controller->outputs.charger_iindpm_ma > 0u &&
      inputs->charger_iindpm_applied &&
      inputs->applied_charger_iindpm_ma ==
          controller->outputs.charger_iindpm_ma &&
      !low_pack_mode;
  if (charge_budget_mw < controller->config.minimum_charge_budget_mw) {
    controller->outputs.charger_enable = false;
  }

  optional_loads_permitted = inputs->estimated_aux_power_valid &&
                             inputs->estimated_aux_power_mw <=
                                 subtract_saturating_u32(
                                     usable_power_mw,
                                     controller->config.system_reserve_mw) &&
                             !low_pack_mode;
  controller->outputs.keyboard_rgb_power_enable =
      inputs->request_keyboard_rgb && optional_loads_permitted;
  controller->outputs.radio_vhf_power_enable =
      inputs->request_radio_vhf && optional_loads_permitted;
  controller->outputs.radio_uhf_power_enable =
      inputs->request_radio_uhf && optional_loads_permitted;
  controller->outputs.audio_amp_enable =
      inputs->request_audio_amp && optional_loads_permitted;
  controller->outputs.audio_mic_enable =
      inputs->request_audio_mic && optional_loads_permitted;

  if (!inputs->request_mu_12v) {
    controller->outputs.mu_12v_enable = false;
    controller->power_policy_waiting = false;
    controller->commanded_mu_edp_budget_mw = 0u;
    controller->mu_waiting_for_pg = false;
    controller->mu_pg_confirmed = false;
    return;
  }
  if (!inputs->vsys_valid ||
      inputs->vsys_mv < controller->config.minimum_vsys_mv) {
    enter_fault(controller, controller->active_source, EC_FAULT_VSYS_INVALID);
    return;
  }
  if (!inputs->estimated_mu_edp_power_valid ||
      inputs->estimated_mu_edp_power_mw > mu_budget_mw || mu_budget_mw == 0u) {
    enter_fault(controller, controller->active_source, EC_FAULT_POWER_POLICY);
    return;
  }
  if (!controller->power_policy_waiting ||
      controller->commanded_mu_edp_budget_mw != mu_budget_mw) {
    if (controller->outputs.mu_12v_enable) {
      enter_fault(controller, controller->active_source, EC_FAULT_POWER_POLICY);
      return;
    }
    controller->power_policy_waiting = true;
    controller->commanded_mu_edp_budget_mw = mu_budget_mw;
    controller->power_policy_started_ms = now_ms;
  }
  if (!inputs->power_limits_applied) {
    if (time_reached(now_ms, controller->power_policy_started_ms +
                                 controller->config.power_policy_apply_timeout_ms)) {
      enter_fault(controller, controller->active_source,
                  EC_FAULT_POWER_POLICY_APPLY_TIMEOUT);
    }
    return;
  }
  if (!controller->outputs.power_policy_confirmed) {
    enter_fault(controller, controller->active_source, EC_FAULT_POWER_POLICY);
    return;
  }

  if (!controller->outputs.mu_12v_enable) {
    if (inputs->mu_12v_pg) {
      enter_fault(controller, controller->active_source,
                  EC_FAULT_MU_POWER_GOOD_STUCK_HIGH);
      return;
    }
    controller->outputs.mu_12v_enable = true;
    controller->mu_waiting_for_pg = true;
    controller->mu_pg_confirmed = false;
    controller->mu_enable_started_ms = now_ms;
  }
  if (inputs->mu_12v_pg) {
    controller->mu_waiting_for_pg = false;
    controller->mu_pg_confirmed = true;
  } else if (controller->mu_pg_confirmed) {
    enter_fault(controller, controller->active_source,
                EC_FAULT_MU_POWER_GOOD_LOST);
  } else if (controller->mu_waiting_for_pg &&
             time_reached(now_ms,
                          controller->mu_enable_started_ms +
                              controller->config.mu_power_good_timeout_ms)) {
    enter_fault(controller, controller->active_source,
                EC_FAULT_MU_POWER_GOOD_TIMEOUT);
  }
}

static void step_active(ec_controller_t *controller, const ec_inputs_t *inputs,
                        uint32_t now_ms) {
  ec_source_id_t source = controller->active_source;
  const ec_source_observation_t *observation;

  if (!source_is_valid(source)) {
    return;
  }
  observation = &inputs->source[source];
  if (!reset_domains_released(inputs)) {
    enter_fault(controller, source, EC_FAULT_RESET_INTERLOCK);
    return;
  }
  if (!inputs->service_bus_healthy) {
    enter_fault(controller, source, EC_FAULT_SERVICE_BUS);
    return;
  }
  if (!observation->present) {
    enter_fault(controller, source, EC_FAULT_SOURCE_MISSING);
    return;
  }
  if (!observation->fault_n) {
    enter_fault(controller, source, EC_FAULT_SOURCE_REPORTED);
    return;
  }
  if (!observation->path_good) {
    enter_fault(controller, source, EC_FAULT_PATH_GOOD_LOST);
    return;
  }
  if (source_is_pd(source) &&
      (!observation->negotiated_current_valid ||
       observation->negotiated_voltage_mv == 0u ||
       observation->negotiated_current_ma <
           controller->config.minimum_pd_current_ma ||
       ec_policy_iindpm_ma(&controller->config,
                           observation->negotiated_current_ma) == 0u)) {
    enter_fault(controller, source, EC_FAULT_NEGOTIATED_CURRENT_INVALID);
    return;
  }
  if (!inputs->charger_fault_n) {
    enter_fault(controller, source, EC_FAULT_CHARGER);
    return;
  }
  if (!inputs->thermal_data_valid) {
    enter_fault(controller, source, EC_FAULT_THERMAL_DATA_INVALID);
    return;
  }
  if (!inputs->thermal_ok) {
    enter_fault(controller, source, EC_FAULT_THERMAL);
    return;
  }
  if (source == EC_SOURCE_PACK && !inputs->pack_telemetry_valid) {
    enter_fault(controller, source, EC_FAULT_PACK_TELEMETRY);
    return;
  }
  if (!source_is_pd(source) && !observation->available_power_valid) {
    enter_fault(controller, source,
                source == EC_SOURCE_PACK ? EC_FAULT_PACK_TELEMETRY
                                         : EC_FAULT_POWER_POLICY);
    return;
  }

  if (source_is_pd(source)) {
    const uint16_t expected_iindpm_ma = ec_policy_iindpm_ma(
        &controller->config, observation->negotiated_current_ma);

    controller->outputs.charger_iindpm_ma = expected_iindpm_ma;
    if (!inputs->charger_iindpm_applied) {
      enter_fault(controller, source, EC_FAULT_IINDPM_APPLY_TIMEOUT);
      return;
    }
    if (inputs->applied_charger_iindpm_ma != expected_iindpm_ma) {
      enter_fault(controller, source, EC_FAULT_IINDPM_MISMATCH);
      return;
    }
    controller->outputs.pd_path_enable[pd_index(source)] = true;
  }
  apply_load_policy(controller, inputs, now_ms);
}

void ec_controller_step(ec_controller_t *controller, const ec_inputs_t *inputs,
                        uint32_t now_ms) {
  if (inputs->reset_asserted) {
    runtime_safe_reset(controller, now_ms);
    return;
  }
  if (!inputs->watchdog_healthy) {
    enter_fault(controller,
                source_is_valid(controller->active_source)
                    ? controller->active_source
                    : controller->candidate_source,
                EC_FAULT_WATCHDOG);
    return;
  }
  if (controller->fault != EC_FAULT_NONE) {
    outputs_safe(&controller->outputs);
    return;
  }
  if (source_is_valid(controller->candidate_source)) {
    step_validating(controller, inputs, now_ms);
  } else if (source_is_valid(controller->active_source)) {
    step_active(controller, inputs, now_ms);
  } else {
    outputs_safe(&controller->outputs);
  }
}

void ec_controller_watchdog_trip(ec_controller_t *controller) {
  enter_fault(controller,
              source_is_valid(controller->active_source)
                  ? controller->active_source
                  : controller->candidate_source,
              EC_FAULT_WATCHDOG);
}

bool ec_controller_clear_fault(ec_controller_t *controller,
                               bool root_cause_removed, uint32_t now_ms) {
  if (!root_cause_removed || controller->fault == EC_FAULT_NONE) {
    return false;
  }
  runtime_safe_reset(controller, now_ms);
  return true;
}

ec_source_state_t ec_controller_source_state(const ec_controller_t *controller,
                                             ec_source_id_t source) {
  return source_is_valid(source) ? controller->source_state[source]
                                 : EC_SOURCE_STATE_OFF;
}

const ec_outputs_t *ec_controller_outputs(const ec_controller_t *controller) {
  return &controller->outputs;
}

bool ec_controller_one_hot_invariant(const ec_controller_t *controller) {
  size_t index;
  unsigned int non_off_states = 0u;
  unsigned int enabled_pd_paths = 0u;
  bool state_mapping_valid = true;

  for (index = 0; index < EC_SOURCE_COUNT; ++index) {
    ec_source_state_t state = controller->source_state[index];
    if (state != EC_SOURCE_STATE_OFF) {
      ++non_off_states;
    }
    if (state == EC_SOURCE_STATE_VALIDATING &&
        controller->candidate_source != (ec_source_id_t)index) {
      state_mapping_valid = false;
    } else if (state == EC_SOURCE_STATE_ACTIVE &&
               controller->active_source != (ec_source_id_t)index) {
      state_mapping_valid = false;
    } else if (state == EC_SOURCE_STATE_FAULT &&
               controller->fault_source != (ec_source_id_t)index) {
      state_mapping_valid = false;
    }
  }
  for (index = 0; index < EC_PD_PORT_COUNT; ++index) {
    if (controller->outputs.pd_path_enable[index]) {
      ec_source_id_t source = (ec_source_id_t)(EC_SOURCE_PD1 + index);
      ++enabled_pd_paths;
      if (controller->source_state[source] != EC_SOURCE_STATE_VALIDATING &&
          controller->source_state[source] != EC_SOURCE_STATE_ACTIVE) {
        state_mapping_valid = false;
      }
    }
  }
  if (source_is_valid(controller->candidate_source) &&
      source_is_valid(controller->active_source)) {
    state_mapping_valid = false;
  }
  if (source_is_valid(controller->candidate_source) &&
      controller->source_state[controller->candidate_source] !=
          EC_SOURCE_STATE_VALIDATING) {
    state_mapping_valid = false;
  }
  if (source_is_valid(controller->active_source) &&
      controller->source_state[controller->active_source] !=
          EC_SOURCE_STATE_ACTIVE) {
    state_mapping_valid = false;
  }
  if (source_is_valid(controller->fault_source) &&
      controller->source_state[controller->fault_source] !=
          EC_SOURCE_STATE_FAULT) {
    state_mapping_valid = false;
  }
  return non_off_states <= 1u && enabled_pd_paths <= 1u && state_mapping_valid;
}
