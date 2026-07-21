#ifndef DUCKTOP2_EC_POLICY_H
#define DUCKTOP2_EC_POLICY_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define EC_PD_PORT_COUNT 2u
#define EC_SOURCE_COUNT 4u

#define EC_DEFAULT_LOW_PACK_MU_EDP_BUDGET_MW 15000u
#define EC_DEFAULT_NORMAL_MU_EDP_BUDGET_MW 30000u
#define EC_DEFAULT_SYSTEM_RESERVE_MW 6000u
#define EC_DEFAULT_SOURCE_EFFICIENCY_PERMILLE 850u

typedef enum {
  EC_SOURCE_PACK = 0,
  EC_SOURCE_AUX,
  EC_SOURCE_PD1,
  EC_SOURCE_PD2,
  EC_SOURCE_NONE = 0xff
} ec_source_id_t;

typedef enum {
  EC_SOURCE_STATE_OFF = 0,
  EC_SOURCE_STATE_VALIDATING,
  EC_SOURCE_STATE_ACTIVE,
  EC_SOURCE_STATE_FAULT
} ec_source_state_t;

typedef enum {
  EC_FAULT_NONE = 0,
  EC_FAULT_WATCHDOG,
  EC_FAULT_SOURCE_MISSING,
  EC_FAULT_SOURCE_REPORTED,
  EC_FAULT_INPUT_CURRENT_INVALID,
  EC_FAULT_VALIDATION_TIMEOUT,
  EC_FAULT_IINDPM_APPLY_TIMEOUT,
  EC_FAULT_IINDPM_MISMATCH,
  EC_FAULT_PATH_GOOD_STUCK_HIGH,
  EC_FAULT_PATH_GOOD_TIMEOUT,
  EC_FAULT_PATH_GOOD_LOST,
  EC_FAULT_CHARGER,
  EC_FAULT_THERMAL,
  EC_FAULT_THERMAL_DATA_INVALID,
  EC_FAULT_RESET_INTERLOCK,
  EC_FAULT_SERVICE_BUS,
  EC_FAULT_POWER_POLICY,
  EC_FAULT_POWER_POLICY_APPLY_TIMEOUT,
  EC_FAULT_PACK_TELEMETRY,
  EC_FAULT_VSYS_INVALID,
  EC_FAULT_MU_POWER_GOOD_STUCK_HIGH,
  EC_FAULT_MU_POWER_GOOD_TIMEOUT,
  EC_FAULT_MU_POWER_GOOD_LOST
} ec_fault_t;

typedef struct {
  bool present;
  bool path_good;
  bool fault_n;
  bool qualified_input_current_valid;
  uint16_t qualified_input_current_ma;
  uint16_t negotiated_voltage_mv;
  bool available_power_valid;
  uint32_t available_power_mw;
} ec_source_observation_t;

typedef struct {
  bool reset_asserted;
  bool watchdog_healthy;
  bool charger_fault_n;
  bool thermal_ok;
  bool thermal_data_valid;
  bool pack_only;
  bool pack_low;
  bool pack_telemetry_valid;
  bool mu_12v_pg;
  bool vsys_valid;
  uint16_t vsys_mv;

  bool source_manager_reset_released;
  bool service_mux_reset_released;
  bool service_bus_healthy;
  bool all_pd_paths_off;
  bool charger_config_valid;
  bool charger_iindpm_applied;
  uint16_t applied_charger_iindpm_ma;

  bool request_charger;
  bool request_mu_12v;
  bool request_keyboard_rgb;
  bool radio_db_present_n;
  bool radio_db_power_good;
  bool radio_db_fault_n;
  bool request_radio_db;
  bool request_audio_amp;
  bool request_audio_mic;
  bool estimated_mu_edp_power_valid;
  uint32_t estimated_mu_edp_power_mw;
  bool estimated_aux_power_valid;
  uint32_t estimated_aux_power_mw;
  uint32_t requested_charge_power_mw;
  bool power_limits_applied;
  uint32_t applied_mu_edp_budget_mw;

  ec_source_observation_t source[EC_SOURCE_COUNT];
} ec_inputs_t;

typedef struct {
  bool pd_path_enable[EC_PD_PORT_COUNT];
  bool charger_enable;
  uint16_t charger_iindpm_ma;
  bool mu_12v_enable;
  uint32_t mu_edp_budget_mw;
  uint32_t source_input_power_mw;
  uint32_t source_usable_power_mw;
  uint32_t charge_power_budget_mw;
  bool power_budget_limited;
  bool power_policy_confirmed;
  bool keyboard_rgb_power_enable;
  bool radio_db_power_enable;
  bool audio_amp_enable;
  bool audio_mic_enable;
} ec_outputs_t;

typedef struct {
  uint32_t source_deadtime_ms;
  uint32_t validation_timeout_ms;
  uint32_t iindpm_apply_timeout_ms;
  uint32_t path_good_timeout_ms;
  uint32_t power_policy_apply_timeout_ms;
  uint32_t mu_power_good_timeout_ms;
  uint32_t radio_db_power_good_timeout_ms;
  uint16_t minimum_pd_current_ma;
  uint16_t iindpm_margin_ma;
  uint16_t iindpm_cap_ma;
  uint16_t minimum_vsys_mv;
  uint16_t source_efficiency_permille;
  uint32_t system_reserve_mw;
  uint32_t minimum_charge_budget_mw;
  uint32_t maximum_charge_budget_mw;
  uint32_t normal_mu_edp_budget_mw;
  uint32_t low_pack_mu_edp_budget_mw;
} ec_policy_config_t;

typedef struct {
  ec_policy_config_t config;
  ec_source_state_t source_state[EC_SOURCE_COUNT];
  ec_source_id_t candidate_source;
  ec_source_id_t active_source;
  ec_source_id_t fault_source;
  ec_fault_t fault;
  uint32_t validation_started_ms;
  uint32_t enable_not_before_ms;
  uint32_t path_enable_started_ms;
  uint32_t iindpm_command_started_ms;
  uint32_t power_policy_started_ms;
  uint32_t mu_enable_started_ms;
  uint32_t radio_db_enable_started_ms;
  bool path_commanded;
  bool iindpm_commanded;
  bool power_policy_waiting;
  uint32_t commanded_mu_edp_budget_mw;
  bool reset_interlock_confirmed;
  bool mu_waiting_for_pg;
  bool mu_pg_confirmed;
  bool radio_db_waiting_for_pg;
  bool radio_db_pg_confirmed;
  bool radio_db_request_blocked;
  ec_outputs_t outputs;
} ec_controller_t;

ec_policy_config_t ec_policy_default_config(void);
void ec_inputs_init(ec_inputs_t *inputs);
void ec_controller_init(ec_controller_t *controller,
                        const ec_policy_config_t *config, uint32_t now_ms);
bool ec_controller_request_source(ec_controller_t *controller,
                                  ec_source_id_t source, uint32_t now_ms);
void ec_controller_stop_source(ec_controller_t *controller, uint32_t now_ms);
void ec_controller_step(ec_controller_t *controller, const ec_inputs_t *inputs,
                        uint32_t now_ms);
void ec_controller_watchdog_trip(ec_controller_t *controller);
bool ec_controller_clear_fault(ec_controller_t *controller,
                               bool root_cause_removed, uint32_t now_ms);

uint16_t ec_policy_iindpm_ma(const ec_policy_config_t *config,
                             uint16_t qualified_input_current_ma);
uint32_t ec_policy_pd_input_power_mw(const ec_policy_config_t *config,
                                     uint16_t negotiated_voltage_mv,
                                     uint16_t negotiated_current_ma);
uint32_t ec_policy_usable_power_mw(const ec_policy_config_t *config,
                                   uint32_t source_input_power_mw);
ec_source_state_t ec_controller_source_state(const ec_controller_t *controller,
                                             ec_source_id_t source);
const ec_outputs_t *ec_controller_outputs(const ec_controller_t *controller);
bool ec_controller_one_hot_invariant(const ec_controller_t *controller);

#ifdef __cplusplus
}
#endif

#endif
