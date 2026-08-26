#include "ducktop2/ec/ec_policy.h"
#include "ducktop2/ec/ec_commit.h"
#include "ducktop2/ec/ec_telemetry.h"
#include "ducktop2/ec/ec_keymap.h"
#include "ec_app.h"
#include "gpio.h"
#include "i2c.h"
#include "matrix_scan.h"
#include "stm32f4xx.h"
#include "usb_hid.h"

static volatile uint32_t g_tick_ms = 0;

void SysTick_Handler(void)
{
    g_tick_ms++;
    matrix_scan_tick(g_tick_ms);
}

static inline uint32_t read_primask(void)
{
    uint32_t result;
    __asm volatile("MRS %0, PRIMASK" : "=r" (result));
    return result;
}

static inline void disable_irq(void)
{
    __asm volatile("CPSID I");
}

static inline void enable_irq(void)
{
    __asm volatile("CPSIE I");
}

uint32_t GetTick(void)
{
    uint32_t tick;
    uint32_t primask = read_primask();
    disable_irq();
    tick = g_tick_ms;
    if (!primask) enable_irq();
    return tick;
}

void DelayMs(uint32_t ms)
{
    uint32_t start = GetTick();
    while ((GetTick() - start) < ms);
}

static bool commit_write(void *context, ec_commit_command_t command, uint32_t value)
{
    (void)context;

    switch (command) {
    case EC_COMMIT_PD1_PATH_ENABLE:
        gpio_set_pd_path_enable_a(value ? true : false);

        value = (value ? 1u : 0u);
        {
            uint8_t port0;
            if (!tca9539_read_register(0x06, &port0)) {
                return false;
            }
            if (value) {
                port0 |= (1u << 0);
            } else {
                port0 &= ~(1u << 0);
            }
            if (!tca9539_write_register(0x06, port0)) {
                return false;
            }
        }
        return true;

    case EC_COMMIT_PD2_PATH_ENABLE:
        gpio_set_pd_path_enable_b(value ? true : false);

        value = (value ? 1u : 0u);
        {
            uint8_t port0;
            if (!tca9539_read_register(0x06, &port0)) {
                return false;
            }
            if (value) {
                port0 |= (1u << 1);
            } else {
                port0 &= ~(1u << 1);
            }
            if (!tca9539_write_register(0x06, port0)) {
                return false;
            }
        }
        return true;

    case EC_COMMIT_CHARGER_IINDPM_MA:
        return ec_app_apply_charger_iindpm_ma((uint16_t)value);

    case EC_COMMIT_CHARGE_BUDGET_MW:
        /* Charge-current setpoint from the budget needs a pack-voltage
         * reference; the gauge telemetry feeds it in a later pass.  The
         * policy still validates and reports the budget through telemetry. */
        return true;

    case EC_COMMIT_MU_EDP_BUDGET_MW:

        return true;

    case EC_COMMIT_CHARGER_ENABLE:
        gpio_set_charger_enable(value ? true : false);
        return true;

    case EC_COMMIT_MU_12V_ENABLE:
        gpio_set_mu_12v_enable(value ? true : false);
        return true;

    case EC_COMMIT_KEYBOARD_RGB_ENABLE:
        gpio_set_keyboard_rgb_enable(value ? true : false);
        return true;

    case EC_COMMIT_RADIO_DB_ENABLE:
        gpio_set_radio_db_power_enable(value ? true : false);
        return true;

    case EC_COMMIT_AUDIO_AMP_ENABLE:
        gpio_set_audio_amp_enable(value ? true : false);
        return true;

    case EC_COMMIT_AUDIO_MIC_ENABLE:
        gpio_set_audio_mic_enable(value ? true : false);
        return true;

    default:
        return false;
    }
}

static void read_pd_contract(ec_inputs_t *inputs, uint8_t pd_index)
{
    uint8_t channel = (pd_index == 0) ? 2 : 3;
    uint8_t addr = (pd_index == 0) ? I2C_PD1_TCPC_ADDR : I2C_PD2_TCPC_ADDR;
    uint8_t pd_data[6];
    ec_source_observation_t *obs = &inputs->source[EC_SOURCE_PD1 + pd_index];

    if (!tca9548a_select_channel(channel)) {
        tca9548a_deselect_all();
        obs->present = false;
        return;
    }

    obs->present = true;
    obs->fault_n = true;

    {
        uint8_t pd_status;
        if (i2c1_read(addr, 0x35, &pd_status, 1)) {
            obs->present = (pd_status & 0x01) ? true : false;
        } else {
            obs->present = false;
        }
    }

    if (obs->present) {
        if (i2c1_read(addr, 0x31, pd_data, 4)) {
            uint32_t pdo = (uint32_t)pd_data[0]
                         | ((uint32_t)pd_data[1] << 8)
                         | ((uint32_t)pd_data[2] << 16)
                         | ((uint32_t)pd_data[3] << 24);
            obs->negotiated_voltage_mv = (uint16_t)(((pdo >> 10) & 0x3FF) * 50);
            uint16_t current_raw = (uint16_t)((pdo >> 0) & 0x3FF);
            obs->qualified_input_current_ma = current_raw * 10;
            obs->qualified_input_current_valid = (current_raw > 0);
        } else {
            obs->negotiated_voltage_mv = 0;
            obs->qualified_input_current_ma = 0;
            obs->qualified_input_current_valid = false;
        }

        obs->path_good = true;

        obs->available_power_valid = false;
        obs->available_power_mw = 0;
    }

    tca9548a_deselect_all();
}

static void read_inputs(ec_inputs_t *inputs, ec_telemetry_inputs_t *telemetry)
{
    ec_inputs_init(inputs);
    ec_telemetry_inputs_init(telemetry);

    inputs->watchdog_healthy = true;
    inputs->reset_asserted = false;

    inputs->source_manager_reset_released = true;
    inputs->service_mux_reset_released = true;
    inputs->service_bus_healthy = i2c1_probe(I2C_TCA9548A_ADDR);

    inputs->all_pd_paths_off = true;

    inputs->charger_fault_n = gpio_get_charger_int_n();

    ec_app_read_power_inputs(inputs, telemetry);

    inputs->mu_12v_pg = gpio_get_mu_12v_pg();

    inputs->estimated_mu_edp_power_valid = false;
    inputs->estimated_mu_edp_power_mw = 0;
    inputs->estimated_aux_power_valid = false;
    inputs->estimated_aux_power_mw = 0;
    inputs->requested_charge_power_mw = 0;
    inputs->request_charger = false;
    inputs->request_mu_12v = false;
    inputs->power_limits_applied = false;
    inputs->applied_mu_edp_budget_mw = 0;

    inputs->request_keyboard_rgb = false;
    inputs->request_audio_amp = false;
    inputs->request_audio_mic = false;
    inputs->radio_db_present_n = true;
    inputs->radio_db_fault_n = true;
    inputs->radio_db_power_good = false;
    inputs->request_radio_db = false;

    read_pd_contract(inputs, 0);
    read_pd_contract(inputs, 1);
}

int main(void)
{
    gpio_init_all();

    matrix_scan_init();

    i2c1_init();

    ec_app_init();

    usb_hid_init();

    gpio_set_gnss_reset_n(false);
    gpio_set_service_mux_reset(false);

    ec_policy_config_t config = ec_policy_default_config();
    ec_controller_t controller;
    ec_commit_state_t commit_state;
    ec_telemetry_inputs_t telemetry_inputs;
    ec_telemetry_snapshot_t telemetry_snapshot;
    ec_inputs_t inputs;
    ec_fan_config_t fan_config = ec_fan_default_config();
    ec_fan_state_t fan_state;
    ec_fan_state_init(&fan_state);

    ec_controller_init(&controller, &config, 0);
    ec_commit_state_init(&commit_state);
    ec_telemetry_inputs_init(&telemetry_inputs);

    ec_commit_driver_t commit_driver;
    commit_driver.context = NULL;
    commit_driver.write = commit_write;

    ec_commit_force_safe(&commit_state, &commit_driver);

    gpio_set_service_mux_reset(true);

    gpio_set_gnss_reset_n(true);

    DelayMs(10);

    bool bus_ok = i2c1_probe(I2C_TCA9548A_ADDR);
    (void)bus_ok;

    tca9548a_deselect_all();

    uint32_t now_ms = GetTick();

    while (1) {
        now_ms = GetTick();

        read_inputs(&inputs, &telemetry_inputs);

        ec_controller_step(&controller, &inputs, now_ms);

        const ec_outputs_t *outputs = ec_controller_outputs(&controller);
        ec_commit_apply(&commit_state, &commit_driver, outputs);

        uint16_t fan_rpm;
        uint8_t fan_duty = ec_app_fan_step(&fan_config, &fan_state, now_ms, &fan_rpm);
        (void)fan_duty;
        (void)fan_rpm;

        ec_keymap_matrix_t matrix;
        ec_hid_keyboard_report_t keyboard_report;
        ec_hid_consumer_report_t consumer_report;
        matrix_scan_get_matrix(&matrix);
        ec_keymap_process(&matrix, &keyboard_report, &consumer_report);
        usb_hid_send_keyboard(&keyboard_report);
        usb_hid_send_consumer(&consumer_report);
        usb_hid_poll();

        ec_telemetry_build_snapshot(&telemetry_snapshot, &telemetry_inputs);

        DelayMs(20);
    }
}
