#include "ec_app.h"
#include "isl9241.h"
#include "bq34z100.h"
#include "board_profile.h"
#include "gpio.h"
#include "tca9537.h"
#include <string.h>

static bool configured, gauge_present, iindpm_applied, battery_present;
static bool sample_pending, sample_valid, charge_budget_applied, gauge_status_valid;
static uint16_t iindpm_ma, prepared_source_mv;
static bool power_io_valid, charger_bias_good, pack_charge_permit, gauge_full;
static bool throttle_released;
static uint32_t power_io_at;
static uint32_t probe_at, gauge_at, sample_at, sample_good_at, sample_good_started_ms;
static isl9241_telemetry_t sample;
static ec_telemetry_inputs_t gauge;

static void charger_lost(void)
{
    gpio_set_charger_enable(false);
    gpio_set_mu_throttle_release(false);
    throttle_released=false;
    configured = iindpm_applied = sample_valid = sample_pending = false;
    charge_budget_applied = battery_present = false;
    iindpm_ma = 0;
}

void ec_app_init(void)
{
    charger_lost();
    gauge_present = gauge_status_valid = gauge_full = false;
    power_io_valid=charger_bias_good=pack_charge_permit=false;
    prepared_source_mv=0;power_io_at=0;
    probe_at = gauge_at = 0;
    ec_telemetry_inputs_init(&gauge);
}

bool ec_app_charger_configured(void) { return configured; }
bool ec_app_gauge_present(void) { return gauge_present; }
bool ec_app_gauge_full(void) { return gauge_status_valid && gauge_full; }
bool ec_app_battery_present(void) { return battery_present; }
bool ec_app_charging_active(void) { return sample_valid && isl9241_is_charge_in_progress(sample.charge_status); }

void ec_app_set_power_control(bool valid,uint8_t inputs,uint32_t now_ms)
{
    power_io_valid=valid;
    charger_bias_good=valid && (inputs & TCA9537_CHARGER_BIAS_GOOD)!=0;
    pack_charge_permit=valid && (inputs & TCA9537_PACK_CHARGE_PERMIT)!=0;
    power_io_at=now_ms;
    if(!valid || !pack_charge_permit) gpio_set_charger_enable(false);
}

bool ec_app_prepare_source(uint16_t source_mv,uint32_t now_ms)
{
    gpio_set_charger_enable(false);
    gpio_set_mu_throttle_release(false);
    throttle_released=false;charge_budget_applied=false;iindpm_applied=false;
    iindpm_ma=0;
    if(source_mv<5000u || source_mv>22000u || !power_io_valid || now_ms-power_io_at>100u)
        return false;
    prepared_source_mv=source_mv;
    uint16_t actual;
    if(configured && isl9241_set_charge_enable(false) &&
       isl9241_set_input_current_ma(ISL9241_BOOT_INPUT_MA) &&
       isl9241_read_input_current_limit_ma(&actual) && actual==ISL9241_BOOT_INPUT_MA &&
       isl9241_set_adapter_alarm(source_mv) && isl9241_configuration_ok()) return true;
    /* TPS3700 has a 450 us maximum startup delay. The source dead time
     * already exceeds this; keep a separate 10 ms floor for a cold EC.
     * A NACK while bias is high cannot authorize another supply. */
    charger_lost();
    return now_ms>=10u && !charger_bias_good;
}

void ec_app_update_throttle(bool allow_release,bool battery_mode)
{
    if(!allow_release || !DUCKTOP2_MU_THROTTLE_QUALIFIED || !configured ||
       !power_io_valid || !sample_valid || sample.fault) {
        gpio_set_mu_throttle_release(false);throttle_released=false;return;
    }
    if(!throttle_released) {
        if(!isl9241_set_adapter_alarm(battery_mode ? 0u : prepared_source_mv) ||
           !isl9241_clear_throttle()) return;
        gpio_set_mu_throttle_release(true);throttle_released=true;
    }
    /* Hardware current alarms remain latched. A trip is not cleared on
     * every poll; source revalidation or a deliberate restart is required. */
}

static void read_gauge(void)
{
    ec_telemetry_inputs_init(&gauge);
    gauge_status_valid = gauge_full = false;
    gauge_present = bq34z100_probe();
    if (!gauge_present) return;
    /* A responsive gauge is not a calibrated gauge. Keep raw values private
     * until the exact profile, scaling and polarity have been qualified. */
    if (!DUCKTOP2_GAUGE_QUALIFIED) return;
    uint8_t soc, health;
    uint16_t value, flags;
    gauge_status_valid = bq34z100_read_flags(&flags) &&
        (flags & (BQ34Z100_FLAG_OTD | BQ34Z100_FLAG_OTC | BQ34Z100_FLAG_BATHI)) == 0;
    gauge_full=gauge_status_valid && (flags & BQ34Z100_FLAG_FC)!=0;
    int16_t current;
    if (bq34z100_read_soc_percent(&soc) && soc <= 100) {
        gauge.soc_percent = soc; gauge.valid_flags |= EC_TELEMETRY_VALID_SOC;
    }
    if (bq34z100_read_voltage_mv(&value)) {
        gauge.pack_voltage_mv = value; gauge.valid_flags |= EC_TELEMETRY_VALID_PACK_VOLTAGE;
    }
    if (bq34z100_read_current_ma(&current)) {
        gauge.pack_current_ma = current; gauge.valid_flags |= EC_TELEMETRY_VALID_PACK_CURRENT;
    }
    if (bq34z100_read_health_percent(&health) && health <= 100) {
        gauge.health_percent = health; gauge.valid_flags |= EC_TELEMETRY_VALID_HEALTH;
    }
    if (bq34z100_read_remaining_capacity_mah(&value)) {
        gauge.remaining_capacity_mah = value; gauge.valid_flags |= EC_TELEMETRY_VALID_REMAINING_CAPACITY;
    }
    if (bq34z100_read_full_capacity_mah(&value)) {
        gauge.full_capacity_mah = value; gauge.valid_flags |= EC_TELEMETRY_VALID_FULL_CAPACITY;
    }
    if (bq34z100_read_cycle_count(&value)) {
        gauge.cycle_count = value; gauge.valid_flags |= EC_TELEMETRY_VALID_CYCLE_COUNT;
    }
    if (bq34z100_read_time_to_empty(&value) &&
        ec_telemetry_bq34z100_minutes_to_seconds(value, &gauge.time_to_empty_s))
        gauge.valid_flags |= EC_TELEMETRY_VALID_TIME_TO_EMPTY;
    if (bq34z100_read_time_to_full(&value) &&
        ec_telemetry_bq34z100_minutes_to_seconds(value, &gauge.time_to_full_s))
        gauge.valid_flags |= EC_TELEMETRY_VALID_TIME_TO_FULL;
}

void ec_app_read_power_inputs(ec_inputs_t *inputs, ec_telemetry_inputs_t *telemetry,
                              uint32_t now_ms)
{
    if (!configured && (int32_t)(now_ms - probe_at) >= 0) {
        probe_at = now_ms + 100u;
        configured = isl9241_probe() && isl9241_init() &&
                     isl9241_set_adapter_alarm(prepared_source_mv);
        if (configured) { sample_pending=true; sample_at=now_ms; }
    }
    if (configured && sample_pending && now_ms-sample_at>=ISL9241_SAMPLE_WAIT_MS) {
        isl9241_telemetry_t next;
        if (now_ms-sample_at>250u || !isl9241_read_sample(&next)) {
            charger_lost();
        } else {
            sample=next; sample_valid=true; sample_good_at=now_ms;
            sample_good_started_ms=sample_at; sample_pending=false;
        }
    }
    if (configured && !sample_pending && now_ms-sample_at>=100u) {
        sample_pending=true; sample_at=now_ms;
    }
    if (sample_valid && now_ms - sample_good_at > 300u) charger_lost();
    /* Detect an unannounced charger POR/watchdog register reset. */
    if (configured && iindpm_applied) {
        uint16_t actual;
        if(!isl9241_read_input_current_limit_ma(&actual)) charger_lost();
        else if(actual!=iindpm_ma) {
            /* An ACOK drop reloads the 200 mA strap without resetting the
             * chip. Revalidate that source; a real register reset fails off. */
            if(actual==ISL9241_BOOT_INPUT_MA && isl9241_configuration_ok()) {
                iindpm_ma=actual;
                gpio_set_charger_enable(false);charge_budget_applied=false;
            } else charger_lost();
        }
    }
    inputs->charger_config_valid = configured && sample_valid;
    inputs->charger_iindpm_applied = configured && iindpm_applied;
    inputs->applied_charger_iindpm_ma = iindpm_ma;
    battery_present = sample_valid && sample.battery_present;
    inputs->vsys_valid = sample_valid && sample.vsys_mv >= 2500u && sample.vsys_mv <= 16000u;
    inputs->vsys_mv = inputs->vsys_valid ? sample.vsys_mv : 0u;
    /* Unknown charger state can qualify its input with the NTC inhibit active. The policy
     * requires configured+sample-valid before activating the source. */
    inputs->charger_fault_n = !sample_valid || !sample.fault;
    if ((int32_t)(now_ms - gauge_at) >= 0) {
        gauge_at = now_ms + 100u;
        read_gauge();
    }
    *telemetry = gauge;
    /* The continuous ADC's 100 ms battery-voltage period is covered by the
     * 120 ms sampling window. The VSYS standby feed now passes through the
     * same battery shunt, so do not add its budget to this measurement. */
    inputs->pack_current_valid=sample_valid && battery_present;
    inputs->pack_current_ma=sample_valid ? (int32_t)sample.ibat_ma : 0;
    inputs->pack_voltage_mv=sample_valid ? sample.vbat_mv : 0;
    inputs->pack_sample_age_ms=sample_valid ? now_ms-sample_good_started_ms : UINT32_MAX;
    inputs->vsys_sample_age_ms=sample_valid ? now_ms-sample_good_started_ms : UINT32_MAX;
    const uint16_t required = EC_TELEMETRY_VALID_SOC | EC_TELEMETRY_VALID_PACK_VOLTAGE |
                               EC_TELEMETRY_VALID_PACK_CURRENT;
    inputs->pack_telemetry_valid = gauge_status_valid && (gauge.valid_flags & required) == required;
    inputs->pack_low = inputs->pack_telemetry_valid &&
                       (gauge.soc_percent <= 10u || gauge.pack_voltage_mv <= 9600u);
    ec_fan_temp_dc_t skin = ec_app_ntc_counts_to_temp_dc(gpio_read_adc_thermal_skin());
    ec_fan_temp_dc_t mu = ec_app_ntc_counts_to_temp_dc(gpio_read_adc_thermal_mu());
    inputs->thermal_data_valid = skin != EC_APP_TEMP_INVALID_DC && mu != EC_APP_TEMP_INVALID_DC;
    inputs->thermal_ok = inputs->thermal_data_valid && skin <= 900 && mu <= 900;
}

bool ec_app_apply_charger_iindpm_ma(uint16_t ma)
{
    iindpm_applied = false;
    iindpm_ma = 0;
    if (ma == 0u) {
        gpio_set_charger_enable(false);
        /* Zero releases the command; it is not a 0 mA IINDPM register value. */
        if(!configured) return true;
        bool disabled=isl9241_set_charge_enable(false);
        bool limited=isl9241_set_input_current_ma(ISL9241_BOOT_INPUT_MA);
        return disabled && limited;
    }
    uint16_t actual;
    if(ma%4u) return false;
    if (!configured || !isl9241_set_input_current_ma(ma) ||
        !isl9241_read_input_current_limit_ma(&actual) ||
        actual != (ma / 4u) * 4u) return false;
    iindpm_applied = true; iindpm_ma = actual;
    return true;
}

bool ec_app_apply_charge_budget_mw(uint32_t mw)
{
    gpio_set_charger_enable(false);
    charge_budget_applied = false;
    if (mw == 0u) return !configured || isl9241_set_charge_enable(false);
    uint16_t charge_mv = DUCKTOP2_PACK_CHARGE_VOLTAGE_MV;
    if (!DUCKTOP2_CHARGING_QUALIFIED || !DUCKTOP2_PACK_QUALIFIED ||
        !configured || !sample_valid || !battery_present || sample.fault ||
        charge_mv == 0u) return false;
    /* Include regulation error, shunt drift and current-loop error before
     * deriving the command. Qualification must cover the full model envelope. */
    uint32_t high_mv=((uint32_t)charge_mv*1005u+999u)/1000u;
    uint32_t allowed_ma=((uint64_t)mw*1000u)/high_mv;
    if(allowed_ma>DUCKTOP2_PACK_CHARGE_CURRENT_MA) allowed_ma=DUCKTOP2_PACK_CHARGE_CURRENT_MA;
    uint32_t sensed_ma=allowed_ma*DUCKTOP2_CHARGE_SENSE_MIN_PERMILLE/1000u;
    /* The 64mA trickle setting can reach100mA before shunt tolerance. */
    if(sensed_ma<100u || sensed_ma<=DUCKTOP2_CHARGE_OFFSET_MA) return false;
    uint32_t ma=(sensed_ma-DUCKTOP2_CHARGE_OFFSET_MA)*1000u/DUCKTOP2_CHARGE_GAIN_MAX_PERMILLE;
    ma=ma/4u*4u;
    if(ma<ISL9241_CHARGE_CURRENT_MIN_MA) return false;
    uint16_t actual_v, actual_i;
    charge_budget_applied = isl9241_program_charge_limits(DUCKTOP2_PACK_CHARGE_VOLTAGE_MV,(uint16_t)ma) &&
        isl9241_read_charge_limits(&actual_v, &actual_i) &&
        actual_v == DUCKTOP2_PACK_CHARGE_VOLTAGE_MV && actual_i == ma;
    return charge_budget_applied;
}

bool ec_app_set_charging(bool enable)
{
    gpio_set_charger_enable(false);
    if (!enable) return !configured || isl9241_set_charge_enable(false);
    if (!DUCKTOP2_CHARGING_QUALIFIED || !power_io_valid || !pack_charge_permit || !gauge_status_valid || ec_app_gauge_full() ||
        !configured || !charge_budget_applied ||
        !iindpm_applied || !sample_valid || sample.fault || !battery_present ||
        !isl9241_set_charge_enable(true)) return false;
    gpio_set_charger_enable(true);
    return true;
}
uint16_t ec_app_applied_charger_iindpm_ma(void) { return iindpm_ma; }
bool ec_app_charger_iindpm_applied(void) { return iindpm_applied; }

uint8_t ec_app_fan_step(const ec_fan_config_t *config, ec_fan_state_t *state,
                        uint32_t now_ms, uint16_t *rpm_out)
{
    ec_fan_inputs_t in;
    ec_fan_inputs_init(&in);
    in.skin_dc = ec_app_ntc_counts_to_temp_dc(gpio_read_adc_thermal_skin());
    in.mu_coldplate_dc = ec_app_ntc_counts_to_temp_dc(gpio_read_adc_thermal_mu());
    in.temps_valid = in.skin_dc != EC_APP_TEMP_INVALID_DC &&
                     in.mu_coldplate_dc != EC_APP_TEMP_INVALID_DC;
    ec_fan_output_t output;
    ec_fan_step(config, &in, state, now_ms, &output);
    uint8_t duty = ec_app_fan_start_duty(output.duty_pct, output.running, state->started_ms, now_ms);
    gpio_set_fan_pwm_duty(duty);
    gpio_fan_tach_update();
    if (rpm_out) *rpm_out = gpio_fan_tach_rpm();
    return duty;
}
