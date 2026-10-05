#include "ec_app.h"
#include "ec_pack_monitor.h"
#include "bq76922_charge.h"
#include "isl9241.h"
#include "tca9537.h"
#include "i2c_mock.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

/* monitor data and qualification here are synthetic; charger writes are mocked. */
static const bq76922_config_row_t rows[]={{0x9278,1,{82}},{0x91d6,2,{255,255}}};
static const bq76922_profile_t profile={.rows=rows,.row_count=2,.complete=true,.qualified=true,
    .cell_voltage_qualified=true,.charge_voltage_qualified=true,.termination_qualified=true,
    .charge_voltage_mv=12120,.charge_cell_max_mv=4100,.charge_spread_max_mv=30,
    .cell_voltage_error_mv=15,.charge_max_rise_mv=9,
    .discharge_cell_min_mv=3100,.normal_charge_cell_min_mv=3100,.cell_max_mv=4200,.pack_min_mv=9000,
    .current_gain_min_permille=1000,.current_lsb_ma=1,.discharge_limit_ma=8000,.charge_limit_ma=3000,
    .dynamic_reserve_ma=100,.sample_max_age_ms=200,.config_max_age_ms=10000};
static bq76922_t monitor;
static bq76922_charge_state_t state;
static bool charging, ready=true;
static uint16_t cell=4040;
void gpio_set_charger_enable(bool on){charging=on;}
void gpio_set_mu_throttle_release(bool on){(void)on;}
uint16_t gpio_read_adc_thermal_skin(void){return 2048;}
uint16_t gpio_read_adc_thermal_mu(void){return 2048;}
void gpio_set_fan_pwm_duty(uint16_t x){(void)x;}
void gpio_fan_tach_update(void){}
uint16_t gpio_fan_tach_rpm(void){return 0;}
void ec_pack_monitor_init(void)
{
    memset(&monitor,0,sizeof(monitor));monitor.profile=&profile;
    bq76922_charge_init(&state);
}
void ec_pack_monitor_poll(uint32_t now)
{
    monitor.config_valid=monitor.sample.valid=true;monitor.config_at_ms=monitor.sample.at_ms=now;
    monitor.sample.cell_mv[0]=monitor.sample.cell_mv[1]=monitor.sample.cell_mv[2]=cell;
    monitor.sample.stack_mv=cell*3;monitor.sample.fet_status=BQ76922_CHG_FET|BQ76922_DSG_FET;
    monitor.sample.current_ma=100;monitor.sample.charge_upper_ma=101;
}
bool ec_pack_monitor_charge_allowed(uint32_t now,uint16_t request)
{return !state.complete&&!state.fault_latched&&bq76922_charge_admitted(&monitor,now,ready,true,now,request);}
bool ec_pack_monitor_current(uint32_t now,int32_t *out){(void)now;*out=100;return ready;}
bool ec_pack_monitor_charge_complete(void){return state.complete;}
bool ec_pack_monitor_charge_step(uint32_t now,bool valid,uint32_t at,bool cv,bool on)
{return bq76922_charge_step(&state,&monitor,now,ready,true,now,valid,at,12120,cv,on);}
static void poll(uint32_t now)
{
    ec_inputs_t in;ec_telemetry_inputs_t telemetry;ec_inputs_init(&in);
    ec_app_set_power_control(true,TCA9537_CHARGER_BIAS_GOOD,now);
    ec_app_read_power_inputs(&in,&telemetry,now);
}
int main(void)
{
    i2c_mock_begin();i2c_mock.isl_words[0xfe]=0x49;i2c_mock.isl_words[0xff]=0x0e;
    i2c_mock.isl_words[0x4d]=0x460c;i2c_mock.isl_words[0x81]=189u<<6;
    i2c_mock.isl_words[0x86]=125u<<6;i2c_mock.isl_words[0x87]=208u<<6;
    i2c_mock.isl_words[0x85]=4;
    i2c_mock.gauge_emulated=true;i2c_mock.gauge[2]=55;
    i2c_mock.gauge[8]=0x40;i2c_mock.gauge[9]=0x2f;
    ec_app_init();poll(0);poll(120);assert(ec_app_charger_configured());
    assert(ec_app_apply_charger_iindpm_ma(2752));
    assert(ec_app_apply_charge_budget_mw(10000) && ec_app_set_charging(true));
    assert(charging && i2c_mock.isl_words[0x15]==12120);
    for(uint32_t t=130;t<=30200;t+=10)poll(t);
    assert(ec_app_charge_complete() && !ec_app_gauge_full() && i2c_mock.gauge[2]==55);
    assert(!charging && i2c_mock.isl_words[0x14]==0 && i2c_mock.isl_words[0x3e]==0);
    assert(!ec_app_set_charging(true));
    /* charger loss does not discard the completed-session latch. */
    i2c_mock.nack_address=9;poll(30320);assert(ec_app_charge_complete() && !charging);
    i2c_mock.nack_address=0;cell=3950;
    for(uint32_t t=30440;t<=35800;t+=10)poll(t);
    assert(!ec_app_charge_complete());
    assert(ec_app_apply_charger_iindpm_ma(2752));
    assert(ec_app_apply_charge_budget_mw(10000) && ec_app_set_charging(true) && charging);
    ready=false;poll(35810);
    assert(!charging && i2c_mock.isl_words[0x14]==0 && i2c_mock.isl_words[0x3e]==0);
    assert(!ec_app_set_charging(true));
    puts("ec bq charge: pass (real inhibit/zero registers, honest gauge, persistent EOC, recharge, READY loss)");
}
