#include "ec_app.h"
#include "board_profile.h"
#include "pack_current.h"
#include "isl9241.h"
#include "tca9537.h"
#include "i2c_mock.h"
#include <assert.h>
#include <stdio.h>
static bool charging,throttle_release;
static void check_current(const ec_inputs_t *in,int16_t nominal)
{
    assert(in->pack_current_valid);
#if DUCKTOP2_PACK_HARDWARE_REVISION == DUCKTOP2_PACK_REV_GUARDED_8A
    int32_t upper;
    assert(ec_pack_current_upper_bound(nominal,&upper) && in->pack_current_ma==upper);
#else
    assert(in->pack_current_ma==nominal);
#endif
}
void gpio_set_charger_enable(bool on) { charging=on; }
void gpio_set_mu_throttle_release(bool on) { throttle_release=on; }
uint16_t gpio_read_adc_thermal_skin(void) { return 2048; }
uint16_t gpio_read_adc_thermal_mu(void) { return 2048; }
void gpio_set_fan_pwm_duty(uint16_t duty) { (void)duty; }
void gpio_fan_tach_update(void) {}
uint16_t gpio_fan_tach_rpm(void) { return 0; }
static void seed(void)
{
    i2c_mock.isl_words[0xfe]=0x49;i2c_mock.isl_words[0xff]=0x0e;
    i2c_mock.isl_words[0x4d]=0x4c0c;
    i2c_mock.isl_words[0x81]=172u<<6;i2c_mock.isl_words[0x86]=125u<<6;
    i2c_mock.isl_words[0x87]=208u<<6;
    i2c_mock.gauge_emulated=true;i2c_mock.gauge[2]=55;
    i2c_mock.gauge[8]=0xf8;i2c_mock.gauge[9]=0x2a; /* 11 V */
}
static void permission(uint32_t now)
{
    ec_app_set_power_control(true,TCA9537_CHARGER_BIAS_GOOD | TCA9537_PACK_CHARGE_PERMIT,now);
}
int main(void)
{
    ec_inputs_t in;ec_telemetry_inputs_t t;
    i2c_mock_begin();ec_app_init();i2c_mock.nack_all=true;
    ec_inputs_init(&in);permission(0);ec_app_read_power_inputs(&in,&t,0);
    assert(!in.charger_config_valid && !in.vsys_valid && !charging && !throttle_release);
    assert(!ec_app_prepare_source(5000,20)); /* powered charger does not ACK */
    ec_app_set_power_control(true,0,20);
    assert(ec_app_prepare_source(5000,20)); /* sensor proves reset/default 200 mA */
    assert(!ec_app_prepare_source(5000,121)); /* stale proof */
    ec_app_set_power_control(true,0,0);assert(!ec_app_prepare_source(5000,9));
    i2c_mock.nack_all=false;seed();permission(100);
    ec_app_read_power_inputs(&in,&t,100);assert(!in.charger_config_valid);
    ec_app_read_power_inputs(&in,&t,219);assert(!in.charger_config_valid);
    ec_app_read_power_inputs(&in,&t,220);
    assert(in.charger_config_valid && in.vsys_valid && in.vsys_mv==12000);
    check_current(&in,0); /* no invented standby load; high-current mode includes measurement uncertainty */
    if(!DUCKTOP2_GAUGE_QUALIFIED) assert(t.valid_flags==0);
    permission(220);assert(!ec_app_apply_charger_iindpm_ma(2750));
    assert(ec_app_apply_charger_iindpm_ma(2752));
    ec_app_read_power_inputs(&in,&t,240);
    assert(in.charger_iindpm_applied && in.applied_charger_iindpm_ma==2752);
    if(DUCKTOP2_CHARGING_QUALIFIED) {
        assert(!ec_app_apply_charge_budget_mw(1000) && !charging);
        assert(ec_app_apply_charge_budget_mw(1850));
        assert(i2c_mock.isl_words[0x14]>=64 && i2c_mock.isl_words[0x14]%4==0);
        assert(((1020u*i2c_mock.isl_words[0x14]+60000u)*12591ull+868999u)/869000u<=1850);

        assert(ec_app_apply_charge_budget_mw(6264) && ec_app_set_charging(true));
        assert(charging && i2c_mock.isl_words[0x14]==360 && i2c_mock.isl_words[0x15]==12528);
        assert((1020u*i2c_mock.isl_words[0x14]+60000u+868u)/869u<=500);
        assert(((1020u*i2c_mock.isl_words[0x14]+60000u)*12591ull+868999u)/869000u<=6264);
        if(DUCKTOP2_PACK_CHARGE_CURRENT_MA==3000) {
            /* Even an excessive requested watt budget cannot command >3A
             * after the independent shunt/gain/offset upper-bound calculation. */
            assert(ec_app_apply_charge_budget_mw(100000));
            assert(i2c_mock.isl_words[0x14]==2496);
            assert((1020u*i2c_mock.isl_words[0x14]+60000u+868u)/869u<=3000);
            assert(ec_app_set_charging(true));
        }
        i2c_mock.gauge[0x0f]=2;ec_app_read_power_inputs(&in,&t,340);
        assert(ec_app_gauge_full() && !ec_app_set_charging(true) && !charging);
        i2c_mock.gauge[0x0f]=0;permission(460);ec_app_read_power_inputs(&in,&t,460);
        assert(ec_app_apply_charge_budget_mw(6264) && ec_app_set_charging(true));
        ec_app_set_power_control(true,TCA9537_CHARGER_BIAS_GOOD,460);
        assert(!charging && !ec_app_set_charging(true));
    } else {
        assert(!ec_app_apply_charge_budget_mw(6264) && !ec_app_set_charging(true));
        ec_app_read_power_inputs(&in,&t,340);ec_app_read_power_inputs(&in,&t,460);
    }
    assert(ec_app_apply_charge_budget_mw(0) && ec_app_set_charging(false));
    permission(480);assert(ec_app_prepare_source(9000,480));
    assert(!charging && !throttle_release && i2c_mock.isl_words[0x3f]==200 && i2c_mock.isl_words[0x3b]==200);
    assert(i2c_mock.isl_words[0x14]==0 && i2c_mock.isl_words[0x3e]==0);
    assert(ec_app_apply_charger_iindpm_ma(2000));
    i2c_mock.isl_words[0x3f]=200; /* ACOK reload keeps the rest of the setup */
    ec_app_read_power_inputs(&in,&t,480);
    assert(in.charger_config_valid && in.charger_iindpm_applied && in.applied_charger_iindpm_ma==200);
    assert(i2c_mock.isl_words[0x3b]==200);
    assert(ec_app_apply_charger_iindpm_ma(2000));
    i2c_mock.isl_words[0x3f]=i2c_mock.isl_words[0x3b]=200;
    i2c_mock.isl_words[0x3d]=0; /* real POR also loses temperature settings */
    ec_app_read_power_inputs(&in,&t,500);
    assert(!in.charger_config_valid && !in.charger_iindpm_applied && !charging);
    seed();ec_app_read_power_inputs(&in,&t,600);ec_app_read_power_inputs(&in,&t,720);
    assert(in.charger_config_valid);
    ec_app_init();ec_app_read_power_inputs(&in,&t,0);
    ec_app_read_power_inputs(&in,&t,251);assert(!ec_app_charger_configured());
    i2c_mock_begin();seed();ec_app_init();permission(0);
    i2c_mock.isl_words[0x84]=20; /* 20 discharge counts = 888 mA including standby */
    i2c_mock.isl_words[0x85]=77; /* an older charge sample must not cancel discharge */
    ec_app_read_power_inputs(&in,&t,0);ec_app_read_power_inputs(&in,&t,120);
    check_current(&in,-888);
    i2c_mock.isl_words[0x84]=0;i2c_mock.isl_words[0x85]=25;
    ec_app_read_power_inputs(&in,&t,240);
    check_current(&in,555);
    i2c_mock.isl_words[0x84]=255;permission(360);
    ec_app_read_power_inputs(&in,&t,360);
    assert(!in.pack_current_valid && !in.charger_config_valid && !charging);
    puts("ec app: PASS (cold/powered NACK, bias freshness, continuous ADC, current steps, FC/temperature, pre-enable limit and reset)");
}
