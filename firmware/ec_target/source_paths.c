#include "source_paths.h"
#include "tca9537.h"
#include "i2c.h"
#include "gpio.h"
#include "ec_app.h"
#include <string.h>

bool source_paths_init(void)
{
    /* Both expanders reset with the EC. Failed writes require a reset;
     * their external pull-downs turn off all three source switches. */
    bool pd=tca9539_init_safe();
    bool aux=tca9537_init_safe();
    return pd && aux;
}

bool source_paths_read(source_paths_state_t *state,uint32_t now_ms)
{
    if(!state) return false;
    memset(state,0,sizeof(*state));
    bool pd=tca9539_read_inputs(&state->port0,&state->port1);
    bool aux=tca9537_read_inputs(&state->control);
    state->valid=pd && aux && (state->port0 & 3u)==(tca9539_output0() & 3u);
    ec_app_set_power_control(state->valid,state->control,now_ms);
    if(!state->valid) return false;
    state->pd_good[0]=(state->port0 & 8u) && !gpio_get_pd1_valid_n();
    state->pd_good[1]=(state->port0 & 16u) && !gpio_get_pd2_valid_n();
    state->aux_good=(state->port1 & 2u) && !(state->port1 & 8u);
    /* Use every off indication, not just the AND-combined path-good result.
     * Residual voltage or a stuck enabled switch blocks the next source. */
    state->all_off=(tca9539_output0() & 3u)==0u && !tca9537_aux_enabled() &&
        !(state->port0 & 24u) && gpio_get_pd1_valid_n() && gpio_get_pd2_valid_n() &&
        !(state->port1 & 2u) && (state->port1 & 8u);
    return true;
}

bool source_paths_set(ec_source_id_t source,bool enable,uint16_t voltage_mv,uint32_t now_ms)
{
    if(source!=EC_SOURCE_AUX && source!=EC_SOURCE_PD1 && source!=EC_SOURCE_PD2) return false;
    if(enable) {
        source_paths_state_t state;
        if(!source_paths_read(&state,now_ms) || !state.all_off ||
           !ec_app_prepare_source(voltage_mv,now_ms)) return false;
    }
    /* Off writes remain available even after a bad observation. */
    return source==EC_SOURCE_AUX ? tca9537_set_aux_enable(enable) :
        tca9539_set_pd_path_enable((uint8_t)(source-EC_SOURCE_PD1),enable);
}
