#include "ec_app.h"
#include "board_profile.h"
#include "bq25798.h"
#include "i2c_mock.h"
#include <assert.h>
#include <stdio.h>
static bool charging;
void gpio_set_charger_enable(bool on) { charging=on; }
uint16_t gpio_read_adc_thermal_skin(void) { return 2048; }
uint16_t gpio_read_adc_thermal_mu(void) { return 2048; }
void gpio_set_fan_pwm_duty(uint16_t duty) { (void)duty; }
void gpio_fan_tach_update(void) {}
uint16_t gpio_fan_tach_rpm(void) { return 0; }
static void seed(void)
{
    i2c_mock.regfile[0x48]=0x18;
    i2c_mock.regfile[0x1b]=8;
    i2c_mock.regfile[0x1d]=1;
    i2c_mock.regfile[0x3d]=0x2e; i2c_mock.regfile[0x3e]=0xe0; /* 12000 mV SYS */
    i2c_mock.regfile[0x3b]=0x2a; i2c_mock.regfile[0x3c]=0xf8; /* 11000 mV BAT */
}
int main(void)
{
    ec_inputs_t input; ec_telemetry_inputs_t telemetry;
    i2c_mock_begin(); ec_app_init(); i2c_mock.nack_all=true;
    ec_inputs_init(&input); ec_app_read_power_inputs(&input,&telemetry,0);
    assert(!input.charger_config_valid && !input.vsys_valid && !charging);
    i2c_mock.nack_all=false;seed();
    ec_app_read_power_inputs(&input,&telemetry,100);
    assert(input.charger_config_valid && input.vsys_valid && input.vsys_mv==12000);
    assert(telemetry.valid_flags==0); /* no qualified gauge */
    assert(ec_app_apply_charger_iindpm_ma(2750));
    ec_app_read_power_inputs(&input,&telemetry,120);
    assert(input.charger_iindpm_applied && input.applied_charger_iindpm_ma==2750);
    if (DUCKTOP2_CHARGING_QUALIFIED) {
        assert(ec_app_apply_charge_budget_mw(6300) && ec_app_set_charging(true));
        assert(charging && i2c_mock.regfile[0x01]==0x04 && i2c_mock.regfile[0x02]==0xec);
        assert(i2c_mock.regfile[0x03]==0 && i2c_mock.regfile[0x04]==0x32);
    } else assert(!ec_app_apply_charge_budget_mw(6300) && !ec_app_set_charging(true));
    assert(ec_app_apply_charge_budget_mw(0) && ec_app_set_charging(false));
    i2c_mock.regfile[0x06]=0; i2c_mock.regfile[0x07]=50; /* charger POR changed IINDPM */
    ec_app_read_power_inputs(&input,&telemetry,140);
    assert(!input.charger_iindpm_applied && !input.charger_config_valid && !charging);
    seed();ec_app_read_power_inputs(&input,&telemetry,300);
    assert(input.charger_config_valid); /* retry after an actual power cycle */
    ec_app_init();i2c_mock.adc_done_autoset=false;i2c_mock.regfile[0x1e]=0;
    ec_app_read_power_inputs(&input,&telemetry,0);
    assert(!input.charger_config_valid && !input.vsys_valid);
    ec_app_read_power_inputs(&input,&telemetry,251);
    assert(!ec_app_charger_configured());
    puts("ec app: PASS (cold power, VSYS, charger reset/retry, pending ADC timeout, unqualified charge gate)");
}
