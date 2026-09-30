#include "power_profile.h"
#include <assert.h>
#include <stdio.h>
int main(void)
{
    ec_policy_config_t cfg=ec_target_power_config();
    assert(ec_policy_source_iindpm_ma(&cfg,EC_SOURCE_PD1,20000,5000)==3884);
    assert(ec_policy_source_iindpm_ma(&cfg,EC_SOURCE_PD1,20000,3000)==2096);
    assert(ec_policy_source_iindpm_ma(&cfg,EC_SOURCE_PD1,9000,3000)==1676);
    assert(ec_policy_source_iindpm_ma(&cfg,EC_SOURCE_PD1,5000,3000)==992);
    assert(ec_policy_source_iindpm_ma(&cfg,EC_SOURCE_PD1,5000,1500)==0);
    /* Independently check the upper draw and lower power for each offered
     * fixed voltage/current, including integer and4mA rounding. */
    const unsigned voltages[]={5000,9000,15000,20000};
    for(unsigned v=0;v<4;v++) for(unsigned offered=500;offered<=5000;offered+=100) {
        if(offered>3000 && voltages[v]!=20000) continue;
        unsigned cmd=ec_policy_source_iindpm_ma(&cfg,EC_SOURCE_PD1,voltages[v],offered);
        if(!cmd) continue;
        unsigned floor=voltages[v]*95/100-150-(offered>3000 ? 750 : 500);
        unsigned reserve=(6500000u+floor-1)/floor;
        unsigned high=(1025u*cmd+50000u+918u)/919u;
        unsigned low=cmd*975/1000;
        low=low>50 ? (low-50)*1000/1081 : 0;
        assert(cmd%4==0 && cmd>=200 && cmd<=4400);
        assert(high+reserve+250<=offered);
        assert(ec_policy_charger_current_floor_ma(&cfg,cmd)<=low);
        assert(ec_policy_pd_input_power_mw(&cfg,voltages[v],offered)<=floor*low/1000);
    }
    ec_policy_config_t bad=cfg;bad.input_shunt_min_permille=0;
    assert(ec_policy_source_iindpm_ma(&bad,EC_SOURCE_PD1,20000,5000)==0);
    bad=cfg;bad.input_current_gain_max_permille=999;
    assert(ec_policy_source_iindpm_ma(&bad,EC_SOURCE_PD1,20000,5000)==0);
    ec_controller_t c;ec_inputs_t in;
    ec_controller_init(&c,&cfg,0);ec_inputs_init(&in);
    in.source_manager_reset_released=in.service_mux_reset_released=in.service_bus_healthy=true;
    in.all_source_paths_off=in.charger_config_valid=in.thermal_data_valid=true;
    in.estimated_aux_power_valid=true;in.estimated_aux_power_mw=0;
    in.request_charger=true;in.requested_charge_power_mw=10000;
    in.source[EC_SOURCE_PD1]=(ec_source_observation_t){.present=true,.fault_n=true,
        .qualified_input_current_valid=true,.qualified_input_current_ma=3000,.negotiated_voltage_mv=5000};
    assert(ec_controller_request_source(&c,EC_SOURCE_PD1,0));
    ec_controller_step(&c,&in,0);ec_controller_step(&c,&in,20);
    assert(c.outputs.pd_path_enable[0] && c.outputs.charger_iindpm_ma==0);
    in.source[EC_SOURCE_PD1].path_good=true;in.all_source_paths_off=false;
    ec_controller_step(&c,&in,21);assert(c.outputs.charger_iindpm_ma==992);
    in.charger_iindpm_applied=true;in.applied_charger_iindpm_ma=992;
    ec_controller_step(&c,&in,22);ec_controller_step(&c,&in,23);
    assert(c.fault==EC_FAULT_NONE && c.outputs.charger_enable && c.outputs.charge_power_budget_mw==1954);
    /* Asking for an impossible cold boot must leave charging available. */
    in.request_mu_12v=true;in.external_boot_authorized=true;in.external_boot_budget_mw=20000;
    ec_controller_step(&c,&in,24);
    assert(c.fault==EC_FAULT_NONE && !c.outputs.mu_12v_enable && c.outputs.charger_enable);
    assert(c.outputs.charge_power_budget_mw==1954);
    /* Extra idle loads consume this small charger's remaining margin. */
    in.estimated_aux_power_mw=1000;
    ec_controller_step(&c,&in,25);
    assert(!c.outputs.charger_enable && c.outputs.charge_power_budget_mw==0);
    /* A qualified battery can boot even when the attached adapter is weak. */
    ec_controller_init(&c,&cfg,0);in.all_source_paths_off=true;
    in.source[EC_SOURCE_PD1].path_good=false;
    in.pack_boot_authorized=in.pack_telemetry_valid=true;in.pack_boot_budget_mw=15000;
    in.source[EC_SOURCE_PACK]=(ec_source_observation_t){.present=true,.path_good=true,
        .fault_n=true,.available_power_valid=true,.available_power_mw=30000};
    ec_controller_arbitrate(&c,&in,0);assert(c.candidate_source==EC_SOURCE_PACK);
    puts("power profile: PASS (current-transfer bounds, source reserve,4mA steps,weak input and idle-charge margin)");
}
