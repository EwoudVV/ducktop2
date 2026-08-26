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

/*
 * TCA9539 (U44) input-port bit map, sheet 02:
 *   P0.6 PACK_FAULT_N   P0.7 AUX_FAULT_N      (low = faulted)
 *   P1.1 AUX_PGOOD      P1.3 MAIN_AUX_VALID_N P1.4 AON_FAULT_N
 *   P1.5 RADIO_DB_PG    P1.6 RADIO_DB_FAULT_N P1.7 RADIO_DB_PRESENT_N
 */
#define U44_BIT_AUX_PGOOD          (1u << 1)
#define U44_BIT_MAIN_AUX_VALID_N   (1u << 3)
#define U44_BIT_AON_FAULT_N        (1u << 4)
#define U44_BIT_RADIO_DB_PG        (1u << 5)
#define U44_BIT_RADIO_DB_FAULT_N   (1u << 6)
#define U44_BIT_RADIO_DB_PRESENT_N (1u << 7)

/* AUX starts at the released 500 mA qualification current (250 mA IINDPM);
 * raising it requires fresh ICO/VINDPM evidence per firmware/release. */
#define EC_TARGET_AUX_QUALIFIED_CURRENT_MA 500u

/* Pack usable power basis: LTC4368 breaker worst-case minimum 3.60 A,
 * derated to 80 percent (verify_electrical_calculations.py), at the live
 * pack voltage. */
#define EC_TARGET_PACK_USABLE_CURRENT_MA 2880u

/* Boot arbitration priority: USB-PD selector beats AUX; PD1 edge annotated
 * ahead of PD2; PACK is the NVDC fallback. */
static const ec_source_id_t k_source_priority[] = {
    EC_SOURCE_PD1, EC_SOURCE_PD2, EC_SOURCE_AUX, EC_SOURCE_PACK,
};

static bool source_eligible(const ec_inputs_t *inputs, ec_source_id_t source)
{
    const ec_source_observation_t *obs = &inputs->source[source];

    if (!obs->present || !obs->fault_n) {
        return false;
    }
    if (source == EC_SOURCE_PD1 || source == EC_SOURCE_PD2 ||
        source == EC_SOURCE_AUX) {
        return obs->qualified_input_current_valid;
    }
    return obs->available_power_valid;
}

static bool u44_read(uint8_t *port0, uint8_t *port1)
{
    return tca9539_read_inputs(port0, port1);
}

static bool commit_write(void *context, ec_commit_command_t command, uint32_t value)
{
    (void)context;

    switch (command) {
    case EC_COMMIT_PD1_PATH_ENABLE:
        return tca9539_set_pd_path_enable(0u, value != 0u);

    case EC_COMMIT_PD2_PATH_ENABLE:
        return tca9539_set_pd_path_enable(1u, value != 0u);

    case EC_COMMIT_CHARGER_IINDPM_MA:
        return ec_app_apply_charger_iindpm_ma((uint16_t)value);

    case EC_COMMIT_CHARGE_BUDGET_MW:
        /* No host transport programs a charge-current setpoint yet: an
         * unimplemented acknowledgement would let the policy believe a
         * budget was committed while the charger stayed at POR values. */
        return false;

    case EC_COMMIT_MU_EDP_BUDGET_MW:
        /* Same reasoning as the charge budget above; the Mu 12 V enable
         * must not be granted against an acknowledged-but-fake limit. */
        return false;

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
    uint8_t channel = (pd_index == 0) ? 2u : 3u;
    uint8_t addr = (pd_index == 0) ? I2C_PD1_TCPC_ADDR : I2C_PD2_TCPC_ADDR;
    uint8_t pdo_data[4];
    uint8_t rdo_data[4];
    uint8_t pd_status;
    ec_source_observation_t *obs = &inputs->source[EC_SOURCE_PD1 + pd_index];

    if (!tca9548a_select_channel(channel)) {
        tca9548a_deselect_all();
        return;
    }

    do {
        if (!i2c1_read(addr, EC_TPS25751_PD_STATUS_REGISTER, &pd_status, 1)) {
            break;
        }
        obs->present = (pd_status & 0x01) != 0;
        if (!obs->present) {
            break;
        }
        /* Fresh Active PDO and Active RDO are both mandatory: the release
         * contract rejects validation from a partial or stale snapshot. */
        if (!i2c1_read(addr, EC_TPS25751_ACTIVE_PDO_REGISTER, pdo_data, 4) ||
            !i2c1_read(addr, EC_TPS25751_ACTIVE_RDO_REGISTER, rdo_data, 4)) {
            obs->present = false;
            break;
        }

        {
            uint32_t pdo = (uint32_t)pdo_data[0] |
                           ((uint32_t)pdo_data[1] << 8) |
                           ((uint32_t)pdo_data[2] << 16) |
                           ((uint32_t)pdo_data[3] << 24);
            uint32_t rdo = (uint32_t)rdo_data[0] |
                           ((uint32_t)rdo_data[1] << 8) |
                           ((uint32_t)rdo_data[2] << 16) |
                           ((uint32_t)rdo_data[3] << 24);
            uint16_t current_raw =
                (uint16_t)((rdo >> 10) & 0x3FF); /* RDO op current, 10 mA */

            obs->negotiated_voltage_mv =
                (uint16_t)(((pdo >> 10) & 0x3FF) * 50u);
            obs->qualified_input_current_ma = (uint16_t)(current_raw * 10u);
            obs->qualified_input_current_valid = current_raw > 0;
        }

        /* path_good is the physical source-valid indication (PDx_VALID_N,
         * active low), never merely "the TCPC answered". */
        obs->path_good = (pd_index == 0)
                             ? !gpio_get_pd1_valid_n()
                             : !gpio_get_pd2_valid_n();
        /* Aggregate connector protection plus the always-on eFuse. */
        obs->fault_n = gpio_get_pd_protect_fault_n();
    } while (false);

    tca9548a_deselect_all();
}

static void read_pack_source(ec_inputs_t *inputs,
                             const ec_telemetry_inputs_t *telemetry)
{
    ec_source_observation_t *obs = &inputs->source[EC_SOURCE_PACK];
    uint16_t pack_mv;

    if (telemetry->valid_flags & EC_TELEMETRY_VALID_PACK_VOLTAGE) {
        pack_mv = telemetry->pack_voltage_mv;
    } else if (inputs->vsys_valid) {
        pack_mv = inputs->vsys_mv; /* charger VBAT lower-bound proxy */
    } else {
        return;
    }

    obs->present = ec_app_battery_present() || inputs->vsys_valid;
    obs->negotiated_voltage_mv = pack_mv;
    obs->path_good = obs->present;
    obs->fault_n = gpio_get_pd_protect_fault_n(); /* /PACK_FAULT_N aggregate */
    obs->available_power_mw =
        (uint32_t)pack_mv * EC_TARGET_PACK_USABLE_CURRENT_MA / 1000u;
    obs->available_power_valid = obs->present && obs->fault_n;
}

static void read_aux_source(ec_inputs_t *inputs)
{
    ec_source_observation_t *obs = &inputs->source[EC_SOURCE_AUX];
    uint8_t port0;
    uint8_t port1;
    uint16_t aux_mv;

    if (!u44_read(&port0, &port1)) {
        return;
    }
    if (!ec_app_aux_counts_to_mv(gpio_read_adc_aux_dc(), &aux_mv)) {
        return;
    }

    obs->present = (port1 & U44_BIT_AUX_PGOOD) != 0 &&
                   aux_mv >= 7000 && aux_mv <= 22000;
    if (!obs->present) {
        return;
    }
    obs->negotiated_voltage_mv = aux_mv;
    obs->path_good = (port1 & U44_BIT_MAIN_AUX_VALID_N) == 0;
    obs->fault_n = (port0 & U44_BIT_AON_FAULT_N) != 0;
    obs->qualified_input_current_ma = EC_TARGET_AUX_QUALIFIED_CURRENT_MA;
    obs->qualified_input_current_valid = true;
    obs->available_power_mw =
        (uint32_t)aux_mv * obs->qualified_input_current_ma / 1000u;
    obs->available_power_valid = obs->fault_n;
}

static void read_inputs(ec_inputs_t *inputs, ec_telemetry_inputs_t *telemetry)
{
    uint8_t port0 = 0xFFu;
    uint8_t port1 = 0xFFu;

    ec_inputs_init(inputs);
    ec_telemetry_inputs_init(telemetry);

    /* The independent IWDG is armed and reloaded below this loop; a stale
     * tick is reported by hardware resetting into the passive boot state,
     * so the software flag stays true only across a fed iteration. */
    inputs->watchdog_healthy = true;
    inputs->reset_asserted = false;

    inputs->service_mux_reset_released = true;
    inputs->service_bus_healthy = i2c1_probe(I2C_TCA9548A_ADDR);
    inputs->source_manager_reset_released = tca9539_ready();

    ec_app_read_power_inputs(inputs, telemetry);
    u44_read(&port0, &port1);

    inputs->radio_db_present_n = (port1 & U44_BIT_RADIO_DB_PRESENT_N) != 0;
    inputs->radio_db_fault_n = (port1 & U44_BIT_RADIO_DB_FAULT_N) != 0;
    inputs->radio_db_power_good = (port1 & U44_BIT_RADIO_DB_PG) != 0;

    /* All paths off requires both commanded output bits low and both
     * physical valid indications high. */
    inputs->all_pd_paths_off =
        (tca9539_output0() & 0x03u) == 0u &&
        gpio_get_pd1_valid_n() && gpio_get_pd2_valid_n();

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

    read_pd_contract(inputs, 0);
    read_pd_contract(inputs, 1);
    read_pack_source(inputs, telemetry);
    read_aux_source(inputs);
}

static void arm_watchdog(void)
{
    /* LSI ~32 kHz / 256 = 125..15.6 kHz class timer; RLR 3125 gives roughly
     * 200 ms at the 15.625 kHz tick.  Expiry hard-resets into the passive
     * boot state, which is the released fail-safe behavior. */
    IWDG->KR = IWDG_KR_KEY_ENABLE;
    IWDG->KR = IWDG_KR_KEY_ACCESS;
    IWDG->PR = IWDG_PR_DIV256;
    IWDG->RLR = 3125u;
}

int main(void)
{
    gpio_init_all();

    matrix_scan_init();

    i2c1_init();

    if (!tca9539_init_safe()) {
        for (;;) {
        }
    }

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

    arm_watchdog();

    gpio_set_service_mux_reset(true);

    gpio_set_gnss_reset_n(true);

    DelayMs(10);

    bool bus_ok = i2c1_probe(I2C_TCA9548A_ADDR);
    (void)bus_ok;

    tca9548a_deselect_all();

    uint32_t now_ms = GetTick();
    ec_source_id_t requested_source = EC_SOURCE_NONE;

    while (1) {
        now_ms = GetTick();

        read_inputs(&inputs, &telemetry_inputs);
        IWDG->KR = IWDG_KR_KEY_RELOAD;

        /* Boot-time arbitration, priority PD1 > PD2 > AUX > PACK: request
         * the first eligible source exactly once.  A latched fault keeps
         * every source state non-OFF, so no further requests are issued
         * until reset; policy faults are never auto-cleared here. */
        if (requested_source == EC_SOURCE_NONE &&
            inputs.service_bus_healthy && inputs.service_mux_reset_released &&
            tca9539_ready() && inputs.all_pd_paths_off) {
            bool controller_idle = true;
            for (unsigned i = 0; i < EC_SOURCE_COUNT; ++i) {
                if (ec_controller_source_state(
                        &controller, (ec_source_id_t)i) !=
                    EC_SOURCE_STATE_OFF) {
                    controller_idle = false;
                    break;
                }
            }
            if (controller_idle) {
                for (size_t p = 0;
                     p < sizeof(k_source_priority) / sizeof(k_source_priority[0]);
                     ++p) {
                    ec_source_id_t source = k_source_priority[p];
                    if (source_eligible(&inputs, source) &&
                        ec_controller_request_source(&controller, source,
                                                     now_ms)) {
                        requested_source = source;
                        break;
                    }
                }
            }
        }

        /* Publish PD contracts and the owned active-source decision into
         * telemetry so downstream consumers see target-owned values. */
        for (uint8_t idx = 0; idx < EC_PD_PORT_COUNT; ++idx) {
            const ec_source_observation_t *obs =
                &inputs.source[EC_SOURCE_PD1 + idx];
            if (obs->qualified_input_current_valid) {
                telemetry_inputs.pd[idx].valid = true;
                telemetry_inputs.pd[idx].voltage_mv =
                    obs->negotiated_voltage_mv;
                telemetry_inputs.pd[idx].current_ma =
                    obs->qualified_input_current_ma;
                telemetry_inputs.valid_flags |= EC_TELEMETRY_VALID_ACTIVE_INPUT;
            }
        }
        for (unsigned i = 0; i < EC_SOURCE_COUNT; ++i) {
            if (ec_controller_source_state(&controller,
                                           (ec_source_id_t)i) ==
                EC_SOURCE_STATE_ACTIVE) {
                telemetry_inputs.valid_flags |= EC_TELEMETRY_VALID_ACTIVE_INPUT;
                telemetry_inputs.active_source = (ec_source_id_t)i;
                break;
            }
        }

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
