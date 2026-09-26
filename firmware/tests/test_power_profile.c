#include "power_profile.h"
#include <assert.h>
#include <stdio.h>
int main(void)
{
    ec_policy_config_t cfg=ec_target_power_config();
    assert(ec_policy_source_iindpm_ma(&cfg,EC_SOURCE_PD1,20000,5000)==4388);
    assert(ec_policy_source_iindpm_ma(&cfg,EC_SOURCE_PD1,20000,3000)==2392);
    assert(ec_policy_source_iindpm_ma(&cfg,EC_SOURCE_PD1,9000,3000)==1924);
    assert(ec_policy_source_iindpm_ma(&cfg,EC_SOURCE_PD1,5000,3000)==1164);
    assert(ec_policy_source_iindpm_ma(&cfg,EC_SOURCE_PD1,5000,1500)==0);
    ec_controller_t c;ec_inputs_t in;
    ec_controller_init(&c,&cfg,0);ec_inputs_init(&in);
    in.source_manager_reset_released=in.service_mux_reset_released=in.service_bus_healthy=true;
    in.all_source_paths_off=in.charger_config_valid=in.thermal_data_valid=true;
    in.estimated_aux_power_valid=true;in.estimated_aux_power_mw=1000;
    in.request_charger=true;in.requested_charge_power_mw=10000;
    in.source[EC_SOURCE_PD1]=(ec_source_observation_t){.present=true,.fault_n=true,
        .qualified_input_current_valid=true,.qualified_input_current_ma=3000,.negotiated_voltage_mv=5000};
    assert(ec_controller_request_source(&c,EC_SOURCE_PD1,0));
    ec_controller_step(&c,&in,0);ec_controller_step(&c,&in,20);
    assert(c.outputs.pd_path_enable[0] && c.outputs.charger_iindpm_ma==0);
    in.source[EC_SOURCE_PD1].path_good=true;in.all_source_paths_off=false;
    ec_controller_step(&c,&in,21);assert(c.outputs.charger_iindpm_ma==1164);
    in.charger_iindpm_applied=true;in.applied_charger_iindpm_ma=1164;
    ec_controller_step(&c,&in,22);ec_controller_step(&c,&in,23);
    assert(c.fault==EC_FAULT_NONE && c.outputs.charger_enable && c.outputs.charge_power_budget_mw==2056);
    /* Asking for an impossible cold boot must leave charging available. */
    in.request_mu_12v=true;in.external_boot_authorized=true;in.external_boot_budget_mw=20000;
    ec_controller_step(&c,&in,24);
    assert(c.fault==EC_FAULT_NONE && !c.outputs.mu_12v_enable && c.outputs.charger_enable);
    assert(c.outputs.charge_power_budget_mw==2056);
    /* A qualified battery can boot even when the attached adapter is weak. */
    ec_controller_init(&c,&cfg,0);in.all_source_paths_off=true;
    in.source[EC_SOURCE_PD1].path_good=false;
    in.pack_boot_authorized=in.pack_telemetry_valid=true;in.pack_boot_budget_mw=15000;
    in.source[EC_SOURCE_PACK]=(ec_source_observation_t){.present=true,.path_good=true,
        .fault_n=true,.available_power_valid=true,.available_power_mw=30000};
    ec_controller_arbitrate(&c,&in,0);assert(c.candidate_source==EC_SOURCE_PACK);
    puts("power profile: PASS (voltage-dependent AON reserve, 4 mA steps, weak input, charge while waiting to boot)");
}
