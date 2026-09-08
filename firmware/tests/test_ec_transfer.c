#include "ducktop2/ec/ec_policy.h"
#include "ducktop2/ec/ec_commit.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
typedef struct { bool mu,pd[2]; unsigned mu_off,budget_changes; uint16_t iindpm; bool fail_next; } bus_t;
static bool write_command(void *ctx,ec_commit_command_t cmd,uint32_t value)
{
    bus_t *bus=ctx;
    if(bus->fail_next){bus->fail_next=false;return false;}
    if(cmd==EC_COMMIT_MU_12V_ENABLE){bus->mu=value!=0;if(!value)bus->mu_off++;}
    if(cmd==EC_COMMIT_PD1_PATH_ENABLE)bus->pd[0]=value!=0;
    if(cmd==EC_COMMIT_PD2_PATH_ENABLE)bus->pd[1]=value!=0;
    if(cmd==EC_COMMIT_CHARGER_IINDPM_MA)bus->iindpm=(uint16_t)value;
    if(cmd==EC_COMMIT_MU_EDP_BUDGET_MW)bus->budget_changes++;
    assert(!(bus->pd[0] && bus->pd[1]));
    return true;
}
static void fixture(ec_controller_t *c,ec_inputs_t *in,ec_commit_state_t *state,bus_t *bus)
{
    ec_controller_init(c,NULL,0);ec_inputs_init(in);memset(bus,0,sizeof(*bus));
    in->source_manager_reset_released=in->service_mux_reset_released=in->service_bus_healthy=true;
    in->charger_config_valid=in->charger_fault_n=in->thermal_data_valid=in->thermal_ok=true;
    in->vsys_valid=true;in->vsys_mv=12000;in->mu_12v_pg=true;
    in->pack_bridge_qualified=in->pack_telemetry_valid=in->pack_current_valid=true;
    in->pack_current_ma=-500;in->pack_discharge_limit_ma=5000;
    in->estimated_mu_edp_power_valid=in->estimated_aux_power_valid=in->power_limits_applied=true;
    in->estimated_mu_edp_power_mw=18000;in->applied_mu_edp_budget_mw=20000;in->estimated_aux_power_mw=5000;
    in->request_mu_12v=true;
    for(unsigned p=0;p<2;p++){
        ec_source_observation_t *s=&in->source[EC_SOURCE_PD1+p];
        s->present=s->fault_n=s->qualified_input_current_valid=true;
        s->qualified_input_current_ma=3000;s->negotiated_voltage_mv=15000;
    }
    ec_source_observation_t *pack=&in->source[EC_SOURCE_PACK];
    pack->present=pack->path_good=pack->fault_n=pack->available_power_valid=true;pack->available_power_mw=60000;
    c->active_source=EC_SOURCE_PD1;c->source_state[EC_SOURCE_PD1]=EC_SOURCE_STATE_ACTIVE;
    c->outputs.pd_path_enable[0]=true;c->outputs.charger_iindpm_ma=2750;
    c->outputs.mu_12v_enable=c->outputs.power_policy_confirmed=true;c->outputs.mu_edp_budget_mw=20000;
    c->power_policy_waiting=true;c->commanded_mu_edp_budget_mw=20000;c->mu_pg_confirmed=true;
    ec_commit_state_init(state);state->initialized=true;state->applied=c->outputs;
    bus->mu=bus->pd[0]=true;bus->iindpm=2750;
}
static ec_commit_result_t step(ec_controller_t *c,ec_inputs_t *in,ec_commit_state_t *state,bus_t *bus,uint32_t now)
{
    in->all_pd_paths_off=!bus->pd[0] && !bus->pd[1];
    for(unsigned p=0;p<2;p++)in->source[EC_SOURCE_PD1+p].path_good=bus->pd[p] && in->source[EC_SOURCE_PD1+p].present;
    in->charger_iindpm_applied=bus->iindpm!=0;in->applied_charger_iindpm_ma=bus->iindpm;
    ec_controller_arbitrate(c,in,now);ec_controller_step(c,in,now);
    assert(ec_controller_one_hot_invariant(c));
    ec_commit_driver_t driver={.context=bus,.write=write_command};
    return ec_commit_apply(state,&driver,&c->outputs);
}
int main(void)
{
    ec_controller_t c;ec_inputs_t in;ec_commit_state_t state;bus_t bus;
    ec_policy_config_t target_limits=ec_policy_default_config();
    target_limits.iindpm_cap_ma=2500;target_limits.pd_iindpm_margin_ma=500;
    assert(ec_policy_pd_input_power_mw(&target_limits,20000,3000)==50000);
    assert(ec_policy_pd_input_power_mw(&target_limits,15000,3000)==37500);
    assert(ec_policy_pd_input_power_mw(&target_limits,15000,1000)==7500);
    assert(ec_policy_iindpm_ma(&target_limits,500)==250); /* AUX keeps its own margin */
    fixture(&c,&in,&state,&bus);in.source[EC_SOURCE_PD1].present=false;
    assert(step(&c,&in,&state,&bus,1)==EC_COMMIT_OK && c.transfer_active && bus.mu && !bus.pd[0]);
    assert(step(&c,&in,&state,&bus,10)==EC_COMMIT_OK);
    assert(step(&c,&in,&state,&bus,29)==EC_COMMIT_OK && !bus.pd[1]);
    in.pack_sample_age_ms=in.vsys_sample_age_ms=21;
    assert(step(&c,&in,&state,&bus,30)==EC_COMMIT_OK && !bus.pd[1]);
    in.pack_sample_age_ms=in.vsys_sample_age_ms=0;
    assert(step(&c,&in,&state,&bus,31)==EC_COMMIT_OK && bus.pd[1] && bus.iindpm==0);
    assert(step(&c,&in,&state,&bus,32)==EC_COMMIT_OK && bus.iindpm==2750);
    assert(step(&c,&in,&state,&bus,33)==EC_COMMIT_OK && c.active_source==EC_SOURCE_PD2);
    assert(bus.mu_off==0 && bus.budget_changes==0);
    for(unsigned cycle=0;cycle<8;cycle++){
        in.source[EC_SOURCE_PD1].present=(cycle%2)==0;
        in.source[EC_SOURCE_PD2].present=(cycle%2)!=0;
        for(unsigned t=0;t<60;t++)assert(step(&c,&in,&state,&bus,100+cycle*100+t)==EC_COMMIT_OK);
        assert(bus.mu && c.fault==EC_FAULT_NONE && !c.transfer_active);
    }
    assert(bus.mu_off==0 && bus.budget_changes==0);
    in.source[EC_SOURCE_PD1].present=in.source[EC_SOURCE_PD2].present=false;
    assert(step(&c,&in,&state,&bus,1000)==EC_COMMIT_OK && c.active_source==EC_SOURCE_PACK && bus.mu);
    in.pack_current_ma=-5001;
    assert(step(&c,&in,&state,&bus,1001)==EC_COMMIT_OK && !bus.mu);

    for(unsigned failure=0;failure<5;failure++){
        fixture(&c,&in,&state,&bus);
        if(failure==0)in.source[EC_SOURCE_PACK].present=false;
        if(failure==1)in.source[EC_SOURCE_PACK].available_power_mw=10000;
        if(failure==2)in.pack_sample_age_ms=251;
        if(failure==3)in.power_limits_applied=false;
        if(failure==4)in.vsys_mv=9000;
        in.source[EC_SOURCE_PD1].present=false;
        assert(step(&c,&in,&state,&bus,1)==EC_COMMIT_OK && !bus.mu);
    }
    fixture(&c,&in,&state,&bus);in.source[EC_SOURCE_PD1].qualified_input_current_valid=false;
    assert(step(&c,&in,&state,&bus,1)==EC_COMMIT_OK && c.transfer_active && bus.mu);
    in.source[EC_SOURCE_PD2].qualified_input_current_valid=false;
    assert(step(&c,&in,&state,&bus,2)==EC_COMMIT_OK && c.active_source==EC_SOURCE_PACK && bus.mu);
    fixture(&c,&in,&state,&bus);in.source[EC_SOURCE_PD1].present=false;
    assert(step(&c,&in,&state,&bus,1)==EC_COMMIT_OK);in.vsys_sample_age_ms=251;
    assert(step(&c,&in,&state,&bus,2)==EC_COMMIT_OK && !bus.mu);
    fixture(&c,&in,&state,&bus);in.source[EC_SOURCE_PD1].present=false;bus.fail_next=true;
    assert(step(&c,&in,&state,&bus,1)!=EC_COMMIT_OK && !bus.mu);
    puts("pack-backed transfer: PASS (break-before-make, repeated changes, role loss, fresh envelopes, passive fallbacks)");
}
