#include "ducktop2/ec/ec_policy.h"
#include <assert.h>
#include <stdio.h>

static void fixture(ec_controller_t *c,ec_inputs_t *in)
{
    ec_controller_init(c,0,0);ec_inputs_init(in);
    c->config.enforce_pack_current_limit=true;
    in->source_manager_reset_released=in->service_mux_reset_released=true;
    in->service_bus_healthy=in->all_source_paths_off=true;
    in->watchdog_healthy=in->thermal_data_valid=in->thermal_ok=true;
    in->charger_config_valid=in->charger_fault_n=true;
    in->pack_telemetry_valid=in->pack_current_valid=true;
    in->pack_current_ma=-8000;in->pack_discharge_limit_ma=8000;
    in->vsys_valid=true;in->vsys_mv=11000;
    in->estimated_aux_power_valid=true;
    in->source[EC_SOURCE_PACK]=(ec_source_observation_t){.present=true,.fault_n=true,
        .path_good=true,.available_power_valid=true,.available_power_mw=80000};
}
int main(void)
{
    for(unsigned phase=0;phase<2;phase++) for(unsigned failure=0;failure<4;failure++) {
        ec_controller_t c;ec_inputs_t in;fixture(&c,&in);
        if(phase==0) assert(ec_controller_request_source(&c,EC_SOURCE_PACK,0));
        else {
            c.active_source=EC_SOURCE_PACK;
            c.source_state[EC_SOURCE_PACK]=EC_SOURCE_STATE_ACTIVE;
            c.outputs.mu_12v_enable=true;
            /* No host-confirmed bridge yet: the current check still applies. */
        }
        if(failure==0)in.pack_current_ma=-8001;
        if(failure==1)in.pack_current_valid=false;
        if(failure==2)in.pack_sample_age_ms=251;
        if(failure==3)in.pack_discharge_limit_ma=0;
        if(phase==0) {
            ec_controller_step(&c,&in,0); /* establish the reset interlock */
            assert(c.fault==EC_FAULT_NONE && !c.outputs.mu_12v_enable);
        }
        ec_controller_step(&c,&in,1);
        if(c.fault!=EC_FAULT_PACK_TELEMETRY) fprintf(stderr,"phase=%u failure=%u fault=%u\n",phase,failure,(unsigned)c.fault);
        assert(c.fault==EC_FAULT_PACK_TELEMETRY);
        assert(!c.outputs.mu_12v_enable && !c.outputs.charger_enable);
    }
    ec_controller_t c;ec_inputs_t in;fixture(&c,&in);
    c.active_source=EC_SOURCE_PACK;c.source_state[EC_SOURCE_PACK]=EC_SOURCE_STATE_ACTIVE;
    ec_controller_step(&c,&in,0);assert(c.fault==EC_FAULT_NONE);
    puts("pack policy: PASS (bounded current enforced before boot and during pack operation)");
}
