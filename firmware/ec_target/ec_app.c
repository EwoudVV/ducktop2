/*
 * Ducktop2 EC target glue (implementation).  See ec_app.h for the contract.
 */

#include "ec_app.h"

#include "bq25798.h"
#include "bq34z100.h"
#include "gpio.h"

static bool s_charger_configured = false;
static bool s_gauge_present = false;
static bool s_iindpm_applied = false;
static uint16_t s_iindpm_ma = 0u;
static bool s_battery_present = false;

/* ------------------------------------------------------------------------- */
/* Init and probes                                                            */
/* ------------------------------------------------------------------------- */

void ec_app_init(void)
{
    s_charger_configured = bq25798_probe() && bq25798_init();
    s_gauge_present = bq34z100_probe();
    s_iindpm_applied = false;
    s_iindpm_ma = 0u;
}

bool ec_app_charger_configured(void)
{
    return s_charger_configured;
}

bool ec_app_gauge_present(void)
{
    return s_gauge_present;
}

bool ec_app_battery_present(void)
{
    return s_battery_present;
}

/* ------------------------------------------------------------------------- */
/* Power/battery/thermal inputs                                               */
/* ------------------------------------------------------------------------- */

void ec_app_read_power_inputs(ec_inputs_t *inputs,
                              ec_telemetry_inputs_t *telemetry)
{
    inputs->charger_config_valid = s_charger_configured;
    inputs->charger_iindpm_applied = s_iindpm_applied;
    inputs->applied_charger_iindpm_ma = s_iindpm_ma;

    /* --- Charger / VSYS / pack presence --- */
    if (s_charger_configured) {
        bq25798_telemetry_t charge_telemetry;
        if (bq25798_read_telemetry(&charge_telemetry)) {
            s_battery_present = charge_telemetry.battery_present;

            /*
             * No MCU ADC channel senses VSYS on this board (PA6 AUX_DC,
             * PA7 skin NTC, PB0 Mu NTC only).  In NVDC topology the
             * charger regulates SYS at or above VBAT, so the fresh
             * VBAT reading is a conservative lower bound.  It is only
             * treated as valid with power-good or an attached pack:
             * a collapsed SYS under current limit can no longer ride a
             * healthy 15 V VBUS through this gate (the previous code
             * fed raw VBUS here, which always passed).
             */
            inputs->vsys_valid = (charge_telemetry.battery_present ||
                                  charge_telemetry.power_good);
            inputs->vsys_mv = charge_telemetry.vbat_mv;
            /* REG20/REG21 fault status, not the shared INT level: a
             * serviced interrupt must not read as a charger fault, and
             * a fault that persists after INT deasserts is caught. */
            inputs->charger_fault_n = !charge_telemetry.fault;
        } else {
            s_battery_present = false;
            inputs->vsys_valid = false;
            inputs->vsys_mv = 0u;
            inputs->charger_fault_n = false; /* unread == unproven */
        }
    } else {
        s_battery_present = false;
        inputs->vsys_valid = false;
        inputs->vsys_mv = 0u;
        inputs->charger_fault_n = false;
    }

    /* --- Battery gauge --- */
    telemetry->valid_flags = 0u;
    if (s_gauge_present) {
        uint8_t soc = 0u;
        uint16_t voltage_mv = 0u;
        int16_t current_ma = 0;
        uint16_t flags = 0u;
        uint16_t remaining_mah = 0u;
        uint16_t full_mah = 0u;
        uint16_t minutes_empty = 0u;
        uint16_t minutes_full = 0u;
        uint16_t cycle_count = 0u;
        uint8_t health = 0u;

        bool soc_ok = bq34z100_read_soc_percent(&soc);
        bool voltage_ok = bq34z100_read_voltage_mv(&voltage_mv);
        bool current_ok = bq34z100_read_current_ma(&current_ma);
        bool flags_ok = bq34z100_read_flags(&flags);

        telemetry->soc_percent = soc_ok ? soc : 0u;
        telemetry->health_percent = (bq34z100_read_health_percent(&health) ? health : 0u);
        telemetry->pack_voltage_mv = voltage_ok ? voltage_mv : 0u;
        telemetry->pack_current_ma = current_ok ? current_ma : 0;
        telemetry->remaining_capacity_mah = (bq34z100_read_remaining_capacity_mah(&remaining_mah)
                                             ? remaining_mah : 0u);
        telemetry->full_capacity_mah = (bq34z100_read_full_capacity_mah(&full_mah)
                                        ? full_mah : 0u);
        telemetry->time_to_empty_s = (bq34z100_read_time_to_empty(&minutes_empty)
                                      ? (uint32_t)minutes_empty * 60u : 0u);
        telemetry->time_to_full_s = (bq34z100_read_time_to_full(&minutes_full)
                                     ? (uint32_t)minutes_full * 60u : 0u);
        telemetry->cycle_count = (bq34z100_read_cycle_count(&cycle_count) ? cycle_count : 0u);

        inputs->pack_telemetry_valid = soc_ok && voltage_ok && current_ok && flags_ok;
        /* Pack low when SOC is at/below 10% or the battery reports low/EMPTY. */
        inputs->pack_low = (soc_ok && soc <= 10u)
                        || (flags_ok && bq34z100_flags_full(flags) == false
                            && bq34z100_flags_discharging(flags)
                            && voltage_ok && voltage_mv <= 9000u);
    } else {
        inputs->pack_telemetry_valid = false;
        inputs->pack_low = false;
        telemetry->soc_percent = 0u;
        telemetry->health_percent = 0u;
        telemetry->pack_voltage_mv = 0u;
        telemetry->pack_current_ma = 0;
    }

    /* --- Thermal --- */
    ec_fan_temp_dc_t skin_dc = ec_app_ntc_counts_to_temp_dc(gpio_read_adc_thermal_skin());
    ec_fan_temp_dc_t mu_dc = ec_app_ntc_counts_to_temp_dc(gpio_read_adc_thermal_mu());
    bool valid = (skin_dc != EC_APP_TEMP_INVALID_DC) && (mu_dc != EC_APP_TEMP_INVALID_DC);
    inputs->thermal_data_valid = valid;
    /* 90C hard ceiling: above it the board is outside the operating envelope. */
    inputs->thermal_ok = valid && skin_dc <= 900 && mu_dc <= 900;
}

/* ------------------------------------------------------------------------- */
/* Commit-side charger commands                                               */
/* ------------------------------------------------------------------------- */

bool ec_app_apply_charger_iindpm_ma(uint16_t ma)
{
    uint16_t readback_ma;

    if (!s_charger_configured) {
        s_iindpm_applied = false;
        s_iindpm_ma = 0u;
        return false;
    }
    if (!bq25798_set_input_current_ma(ma)) {
        s_iindpm_applied = false;
        s_iindpm_ma = 0u;
        return false;
    }
    /* An acknowledged write is not an applied limit: read the register
     * back and confirm it re-encodes to the requested step before the
     * policy may trust inputs.applied_charger_iindpm_ma. */
    if (!bq25798_read_input_current_limit_ma(&readback_ma) ||
        bq25798_encode_input_current(readback_ma) !=
            bq25798_encode_input_current(ma)) {
        s_iindpm_applied = false;
        s_iindpm_ma = 0u;
        return false;
    }
    s_iindpm_applied = true;
    s_iindpm_ma = ma;
    return true;
}

uint16_t ec_app_applied_charger_iindpm_ma(void)
{
    return s_iindpm_ma;
}

bool ec_app_charger_iindpm_applied(void)
{
    return s_iindpm_applied;
}

/* ------------------------------------------------------------------------- */
/* Fan loop                                                                   */
/* ------------------------------------------------------------------------- */

uint8_t ec_app_fan_step(const ec_fan_config_t *config, ec_fan_state_t *state,
                        uint32_t now_ms, uint16_t *rpm_out)
{
    ec_fan_inputs_t fan_inputs;
    ec_fan_inputs_init(&fan_inputs);

    ec_fan_temp_dc_t skin_dc = ec_app_ntc_counts_to_temp_dc(gpio_read_adc_thermal_skin());
    ec_fan_temp_dc_t mu_dc = ec_app_ntc_counts_to_temp_dc(gpio_read_adc_thermal_mu());

    fan_inputs.temps_valid = (skin_dc != EC_APP_TEMP_INVALID_DC)
                          && (mu_dc != EC_APP_TEMP_INVALID_DC);
    fan_inputs.skin_dc = skin_dc;
    fan_inputs.mu_coldplate_dc = mu_dc;

    ec_fan_output_t output;
    ec_fan_step(config, &fan_inputs, state, now_ms, &output);

    uint8_t duty = ec_app_fan_start_duty(output.duty_pct, output.running,
                                         state->started_ms, now_ms);
    gpio_set_fan_pwm_duty(duty);
    gpio_fan_tach_update();

    if (rpm_out != NULL) {
        *rpm_out = gpio_fan_tach_rpm();
    }
    return duty;
}
