#include "source_paths.h"
#include "tca9537.h"
#include "i2c_mock.h"
#include "i2c.h"
#include <assert.h>
#include <stdio.h>
static bool pd_valid_n[2]={true,true},permit;
static unsigned preparations;
bool gpio_get_pd1_valid_n(void) {return pd_valid_n[0];}
bool gpio_get_pd2_valid_n(void) {return pd_valid_n[1];}
void ec_app_set_power_control(bool valid,uint8_t bits,uint32_t now) {(void)valid;(void)bits;(void)now;}
bool ec_app_prepare_source(uint16_t mv,uint32_t now) {(void)now;preparations++;return permit && mv>=5000;}
static void fixture(void)
{
    i2c_mock_begin();i2c_mock.expander_pins_emulated=true;
    i2c_mock.regfile[1]=8; /* AUX VALID inactive */
    pd_valid_n[0]=pd_valid_n[1]=true;permit=true;preparations=0;
    assert(source_paths_init());
}
int main(void)
{
    source_paths_state_t s;fixture();
    assert(source_paths_read(&s,20) && s.all_off);
    permit=false;assert(!source_paths_set(EC_SOURCE_PD1,true,20000,20));
    assert((tca9539_output0()&3u)==0 && !tca9537_aux_enabled());
    permit=true;assert(source_paths_set(EC_SOURCE_AUX,true,12000,20));
    assert(tca9537_aux_enabled() && !source_paths_set(EC_SOURCE_PD1,true,20000,21));
    assert(source_paths_set(EC_SOURCE_AUX,false,0,22));
    assert(source_paths_set(EC_SOURCE_PD1,true,20000,23));
    assert(!source_paths_set(EC_SOURCE_PD2,true,9000,24));
    assert(!source_paths_set(EC_SOURCE_AUX,true,12000,24));
    assert(source_paths_set(EC_SOURCE_PD1,false,0,25));
    pd_valid_n[0]=false; /* gate off but its charged output has not decayed */
    assert(!source_paths_set(EC_SOURCE_PD2,true,9000,26));
    pd_valid_n[0]=true;i2c_mock.regfile[0]|=8u;
    assert(!source_paths_set(EC_SOURCE_PD2,true,9000,27));
    i2c_mock.regfile[0]&=(uint8_t)~8u;
    assert(source_paths_set(EC_SOURCE_PD2,true,9000,28));
    assert(source_paths_read(&s,29) && !s.pd_good[1]); /* ramping is not PG */
    i2c_mock.regfile[0]|=16u;pd_valid_n[1]=false;
    assert(source_paths_read(&s,30) && s.pd_good[1]);
    assert(source_paths_set(EC_SOURCE_PD2,false,0,31));
    fixture();i2c_mock.tca37[3]=0xff;assert(!source_paths_read(&s,32));
    assert(!source_paths_set(EC_SOURCE_PD1,true,20000,33));
    fixture();i2c_mock.nack_address=0x49;assert(!source_paths_read(&s,34));
    assert(!source_paths_set(EC_SOURCE_PD1,true,20000,35));
    puts("source paths: PASS (three-source exclusion, prepare-before-enable, ramp/PG, residual voltage, expander reset/NACK)");
}
