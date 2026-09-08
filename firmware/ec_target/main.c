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
#include "watchdog.h"
#include "board_profile.h"
#include "tps25751.h"
#include "host_link.h"
#include "usb_power.h"
#include "audio.h"
#include "ssd1306.h"
#include "ducktop2/ec/ec_fan_monitor.h"
#include "ducktop2/ec/ec_lid.h"

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
    while ((GetTick() - start) < ms) {
        usb_hid_poll();
        __WFI();
    }
}

/* U44 wiring is defined in sheet 02. A failed read invalidates every input. */
#define U44_PACK_OK (1u << 6)
#define U44_AUX_OK (1u << 7)
#define U44_AON_OK (1u << 4)
static bool want_power = true;
static bool headphone_present;
static bool fan_healthy = true;
static usb_power_state_t usb_power;
static uint32_t other_auxiliary_mw;

static bool commit_write(void *context, ec_commit_command_t command, uint32_t value)
{
    (void)context;
    switch (command) {
    case EC_COMMIT_PD1_PATH_ENABLE: return tca9539_set_pd_path_enable(0, value != 0);
    case EC_COMMIT_PD2_PATH_ENABLE: return tca9539_set_pd_path_enable(1, value != 0);
    case EC_COMMIT_CHARGER_IINDPM_MA: return ec_app_apply_charger_iindpm_ma((uint16_t)value);
    case EC_COMMIT_CHARGE_BUDGET_MW: return ec_app_apply_charge_budget_mw(value);
    case EC_COMMIT_MU_EDP_BUDGET_MW: return ec_host_request_budget(value);
    case EC_COMMIT_CHARGER_ENABLE: return ec_app_set_charging(value != 0);
    case EC_COMMIT_MU_12V_ENABLE: gpio_set_mu_12v_enable(value != 0); return true;
    case EC_COMMIT_KEYBOARD_RGB_ENABLE: gpio_set_keyboard_rgb_enable(value != 0); return true;
    case EC_COMMIT_RADIO_DB_ENABLE: gpio_set_radio_db_power_enable(value != 0); return true;
    case EC_COMMIT_AUDIO_AMP_ENABLE: gpio_set_audio_amp_enable(value != 0); return true;
    case EC_COMMIT_AUDIO_MIC_ENABLE: gpio_set_audio_mic_enable(value != 0); return true;
    default: return false;
    }
}

static void read_inputs(ec_inputs_t *in, ec_telemetry_inputs_t *telemetry, uint32_t now)
{
    ec_inputs_init(in);
    ec_telemetry_inputs_init(telemetry);
    uint8_t p0=0, p1=0;
    bool expander = tca9539_read_inputs(&p0, &p1);
    in->source_manager_reset_released = expander;
    in->service_mux_reset_released = true;
    in->service_bus_healthy = expander && i2c1_probe(I2C_TCA9548A_ADDR);
    in->all_pd_paths_off = expander && (tca9539_output0() & 3u) == 0u &&
                           gpio_get_pd1_valid_n() && gpio_get_pd2_valid_n();
    in->radio_db_present_n = !expander || (p1 & (1u<<7)) != 0;
    in->radio_db_fault_n = expander && (p1 & (1u<<6)) != 0;
    in->radio_db_power_good = expander && (p1 & (1u<<5)) != 0;
    headphone_present = expander && (p0 & (1u<<2)) != 0;
    ec_app_read_power_inputs(in, telemetry, now);
    in->thermal_ok = in->thermal_ok && fan_healthy;
    in->mu_12v_pg = gpio_get_mu_12v_pg();
    if (in->service_bus_healthy) {
        for (uint8_t port=0; port<2; ++port) {
            tps25751_contract_t contract;
            bool valid=tca9548a_select_channel((uint8_t)(port+2)) &&
                       tps25751_read_contract((uint8_t)(0x20+port), &contract);
            if (!tca9548a_deselect_all()) {
                in->service_bus_healthy=false;
                break;
            }
            if (!valid) continue;
            ec_source_observation_t *obs=&in->source[EC_SOURCE_PD1+port];
            obs->present=contract.connected;
            obs->fault_n=gpio_get_pd_protect_fault_n() && (p1 & U44_AON_OK) &&
                          (p0 & (1u<<(port+3)));
            obs->path_good=port ? !gpio_get_pd2_valid_n() : !gpio_get_pd1_valid_n();
            obs->negotiated_voltage_mv=contract.voltage_mv;
            obs->qualified_input_current_valid=contract.valid;
            obs->qualified_input_current_ma=contract.current_ma;
        }
    }
    ec_source_observation_t *pack=&in->source[EC_SOURCE_PACK];
    pack->present=DUCKTOP2_PACK_QUALIFIED && ec_app_battery_present() &&
                  (telemetry->valid_flags & EC_TELEMETRY_VALID_PACK_VOLTAGE);
    pack->fault_n=expander && (p0 & U44_PACK_OK);
    pack->path_good=pack->present && pack->fault_n;
    pack->negotiated_voltage_mv=in->pack_voltage_mv;
    pack->available_power_mw=(uint32_t)in->pack_voltage_mv * DUCKTOP2_PACK_USABLE_CURRENT_MA / 1000u;
    pack->available_power_valid=pack->path_good && in->pack_telemetry_valid && pack->available_power_mw>0;
    in->pack_bridge_qualified=DUCKTOP2_PACK_BRIDGE_QUALIFIED && DUCKTOP2_PACK_QUALIFIED;
    in->pack_discharge_limit_ma=DUCKTOP2_PACK_USABLE_CURRENT_MA;
    uint16_t aux_mv;
    ec_source_observation_t *aux=&in->source[EC_SOURCE_AUX];
    if (expander && ec_app_aux_counts_to_mv(gpio_read_adc_aux_dc(), &aux_mv)) {
        aux->present=(p1 & (1u<<1)) && aux_mv>=7000 && aux_mv<=22000;
        aux->path_good=(p1 & (1u<<3)) == 0;
        aux->fault_n=(p0 & U44_AUX_OK) && (p1 & U44_AON_OK);
        aux->negotiated_voltage_mv=aux_mv;
        aux->qualified_input_current_valid=aux->present && aux->fault_n;
        aux->qualified_input_current_ma=DUCKTOP2_AUX_QUALIFIED_CURRENT_MA;
        /* Use the same IINDPM margin as the command, not full source current. */
        ec_policy_config_t config=ec_policy_default_config();
        config.iindpm_cap_ma=DUCKTOP2_IINDPM_CAP_MA;
        config.pd_iindpm_margin_ma=DUCKTOP2_PD_IINDPM_MARGIN_MA;
        aux->available_power_mw=(uint32_t)aux_mv*ec_policy_iindpm_ma(&config,aux->qualified_input_current_ma)/1000u;
        aux->available_power_valid=aux->qualified_input_current_valid;
    }
    ec_host_state_t host=ec_host_state(now);
    if (host.valid && (host.requests & EC_HOST_REQUEST_OFF)) want_power=false;
    if (gpio_get_power_button_pressed()) want_power=true;
    in->request_mu_12v=want_power && (DUCKTOP2_EXTERNAL_BOOT_QUALIFIED ||
                      DUCKTOP2_PACK_BOOT_QUALIFIED || host.valid);
    in->external_boot_authorized=DUCKTOP2_EXTERNAL_BOOT_QUALIFIED && !host.valid;
    in->external_boot_budget_mw=DUCKTOP2_EXTERNAL_BOOT_BUDGET_MW;
    in->pack_boot_authorized=DUCKTOP2_PACK_BOOT_QUALIFIED && DUCKTOP2_PACK_QUALIFIED && !host.valid;
    in->pack_boot_budget_mw=DUCKTOP2_PACK_BOOT_BUDGET_MW;
    in->estimated_mu_edp_power_valid=host.valid;
    in->estimated_mu_edp_power_mw=host.estimated_mu_mw;
    in->estimated_aux_power_valid=DUCKTOP2_AUX_LOADS_QUALIFIED;
    in->estimated_aux_power_mw=DUCKTOP2_AUX_WORST_CASE_MW;
    if (host.valid && host.estimated_aux_mw>in->estimated_aux_power_mw)
        in->estimated_aux_power_mw=host.estimated_aux_mw;
    other_auxiliary_mw=in->estimated_aux_power_mw;
    in->estimated_aux_power_mw+=usb_power_reservation_mw(&usb_power);
    in->power_limits_applied=host.valid;
    in->applied_mu_edp_budget_mw=host.budget_mw;
    in->request_charger=DUCKTOP2_CHARGING_QUALIFIED && DUCKTOP2_PACK_QUALIFIED &&
                        pack->fault_n && in->pack_telemetry_valid && host.valid &&
                        (host.requests & EC_HOST_REQUEST_CHARGE);
    in->requested_charge_power_mw=in->request_charger ? 10000u : 0u;
    in->request_audio_amp=host.valid && (host.requests & EC_HOST_REQUEST_SPEAKER) && !headphone_present;
    in->request_audio_mic=host.valid && (host.requests & EC_HOST_REQUEST_MIC);
    in->request_keyboard_rgb=host.valid && (host.requests & EC_HOST_REQUEST_RGB);
    in->request_radio_db=host.valid && (host.requests & EC_HOST_REQUEST_RADIO);
}

static uint32_t age_forward(uint32_t age,uint32_t elapsed)
{
    return UINT32_MAX-age<elapsed ? UINT32_MAX : age+elapsed;
}

static void refresh_transfer_interlocks(ec_inputs_t *in,uint32_t sampled_at,uint32_t *now)
{
    if(in->pack_bridge_qualified && in->request_mu_12v) {
        uint8_t p0,p1;
        if(!tca9539_read_inputs(&p0,&p1))in->service_bus_healthy=false;
        else {
            in->source[EC_SOURCE_PACK].fault_n=(p0 & U44_PACK_OK)!=0;
            in->source[EC_SOURCE_PACK].path_good &= in->source[EC_SOURCE_PACK].fault_n;
            for(unsigned p=0;p<2;p++)in->source[EC_SOURCE_PD1+p].fault_n=
                (p0 & (1u<<(p+3))) && (p1 & U44_AON_OK) && gpio_get_pd_protect_fault_n();
        }
    }
    in->mu_12v_pg=gpio_get_mu_12v_pg();
    in->source[EC_SOURCE_PD1].path_good=!gpio_get_pd1_valid_n();
    in->source[EC_SOURCE_PD2].path_good=!gpio_get_pd2_valid_n();
    in->all_pd_paths_off=in->source_manager_reset_released && (tca9539_output0()&3u)==0 &&
        !in->source[EC_SOURCE_PD1].path_good && !in->source[EC_SOURCE_PD2].path_good;
    *now=GetTick();
    in->pack_sample_age_ms=age_forward(in->pack_sample_age_ms,*now-sampled_at);
    in->vsys_sample_age_ms=age_forward(in->vsys_sample_age_ms,*now-sampled_at);
    if(!ec_host_state(*now).valid) {
        in->power_limits_applied=false;
        in->estimated_mu_edp_power_valid=false;
        in->request_charger=false;
    }
}

int main(void)
{
    gpio_init_all(); matrix_scan_init(); i2c1_init(); ec_app_init(); ec_host_init();
    usb_hid_init();
    if (!tca9539_init_safe()) NVIC_SystemReset();
    ec_policy_config_t config=ec_policy_default_config();
    config.iindpm_cap_ma=DUCKTOP2_IINDPM_CAP_MA;
        config.pd_iindpm_margin_ma=DUCKTOP2_PD_IINDPM_MARGIN_MA;
    uint32_t boot_budget=DUCKTOP2_EXTERNAL_BOOT_BUDGET_MW;
    uint32_t pack_boot_budget=DUCKTOP2_PACK_BOOT_BUDGET_MW;
    if (pack_boot_budget>boot_budget) boot_budget=pack_boot_budget;
    if (boot_budget>config.normal_mu_edp_budget_mw) config.normal_mu_edp_budget_mw=boot_budget;
    ec_controller_t controller; ec_controller_init(&controller,&config,GetTick());
    ec_commit_state_t commits; ec_commit_state_init(&commits);
    ec_commit_driver_t driver={.context=NULL,.write=commit_write};
    if (ec_commit_force_safe(&commits,&driver) != EC_COMMIT_OK) NVIC_SystemReset();
    gpio_set_service_mux_reset(true); DelayMs(2); tca9548a_deselect_all();
    usb_power_config_t uc={
        .budget={.qualified=DUCKTOP2_USB_POWER_QUALIFIED,
                 .admission_current_ma=DUCKTOP2_USB_ADMISSION_MA,
                 .right_harness_current_ma=DUCKTOP2_USB_RIGHT_HARNESS_MA,
                 .rail_max_mv=5239u,.minimum_efficiency_percent=DUCKTOP2_USB_EFFICIENCY_PERCENT},
        .startup_ceiling_ma=5700u,.pd_inrush_ma=DUCKTOP2_USB_PD_INRUSH_MA,
        .branch_inrush_ma=DUCKTOP2_USB_BRANCH_INRUSH_MA,
        .rail_min_mv=5000u,.rail_max_mv=5250u,
        .startup_timeout_ms=500u,.gate_timeout_ms=200u,.sample_max_age_ms=100u
    };
    if (!usb_power_init(&usb_power,&uc,GetTick())) NVIC_SystemReset();
    ec_fan_config_t fc=ec_fan_default_config(); ec_fan_state_t fs; ec_fan_state_init(&fs);
    ec_fan_monitor_t fan_monitor; ec_fan_monitor_init(&fan_monitor);
    ec_lid_config_t lc=ec_lid_default_config(); ec_lid_state_t ls; ec_lid_state_init(&ls);
    ec_battery_config_t bc=ec_battery_default_config(); ec_battery_controller_t bs; ec_battery_state_init(&bs);
    bool retry_active=false, retry_consumed=false; uint32_t retry_started=0;
    for (;;) {
        uint32_t now=GetTick();
        if (!usb_power_poll(&usb_power,now)) NVIC_SystemReset();
        now=GetTick();
        uint16_t rpm=0; uint8_t duty=ec_app_fan_step(&fc,&fs,now,&rpm);
        fan_healthy=ec_fan_monitor_step(&fan_monitor,gpio_get_mu_12v_pg(),duty,rpm,now);
        if (!fan_healthy) gpio_set_fan_pwm_duty(100);
        ec_inputs_t in; ec_telemetry_inputs_t ti; read_inputs(&in,&ti,now);
        refresh_transfer_interlocks(&in,now,&now);
        ec_controller_arbitrate(&controller,&in,now); ec_controller_step(&controller,&in,now);
        const ec_outputs_t *out=ec_controller_outputs(&controller);
        if ((!out->mu_12v_enable || controller.transfer_active || !in.thermal_ok ||
             !in.power_limits_applied || !in.service_bus_healthy ||
             (usb_power.have_source && usb_power.last_source!=(uint8_t)controller.active_source)) &&
            !usb_power_disable(&usb_power)) NVIC_SystemReset();
        if (ec_commit_apply(&commits,&driver,out) != EC_COMMIT_OK) NVIC_SystemReset();
        /* U44 /RESET follows NRST, so a failed safe write resets both domains. */
        now=GetTick();
        ec_host_state_t host=ec_host_state(now);
        uint64_t used=(uint64_t)config.system_reserve_mw+host.budget_mw+other_auxiliary_mw;
        usb_power_request_t ur={
            .host_lease_valid=host.valid,
            .system_safe=out->mu_12v_enable && gpio_get_mu_12v_pg() && in.thermal_ok &&
                         in.service_bus_healthy && out->power_policy_confirmed &&
                         in.estimated_aux_power_valid,
            .transfer_active=controller.transfer_active,
            .clear_fault=ec_host_take_usb_clear(now),
            .requested_mask=host.usb_requested_mask,.active_source=(uint8_t)controller.active_source,
            .available_input_power_mw=out->source_usable_power_mw>used ?
                                      (uint32_t)(out->source_usable_power_mw-used) : 0u,
            .committed_reservation_mw=in.estimated_aux_power_mw-other_auxiliary_mw
        };
        if (!usb_power_step(&usb_power,&ur,now)) NVIC_SystemReset();
        ec_host_usb_status_t us=usb_power_status(&usb_power,now);
        ec_host_publish_usb(&us);
        bool retry_request=host.valid && (host.requests & EC_HOST_REQUEST_BMS_RETRY);
        bool external=controller.active_source!=EC_SOURCE_NONE && controller.active_source!=EC_SOURCE_PACK;
        if (!retry_request) retry_consumed=false;
        if (!retry_active && !retry_consumed && retry_request && external &&
            !out->mu_12v_enable && !out->charger_enable && DUCKTOP2_PACK_QUALIFIED) {
            if (!tca9539_set_bms_retry(true)) NVIC_SystemReset();
            retry_active=true; retry_consumed=true; retry_started=now;
        }
        if (retry_active && (!external || now-retry_started>=100u)) {
            if (!tca9539_set_bms_retry(false)) NVIC_SystemReset();
            retry_active=false;
        }
        ec_keymap_matrix_t matrix; ec_hid_keyboard_report_t kb; ec_hid_consumer_report_t consumer;
        matrix_scan_get_matrix(&matrix); ec_keymap_process(&matrix,&kb,&consumer);
        usb_hid_send_keyboard(&kb); usb_hid_send_consumer(&consumer);
        ec_lid_inputs_t li={.lid_open_raw=gpio_get_lid_open()}; ec_lid_output_t lid;
        ec_lid_step(&lc,&li,&ls,now,&lid);
        ti.active_source=controller.transfer_active ? EC_SOURCE_PACK : controller.active_source;
        if (ti.active_source!=EC_SOURCE_NONE) ti.valid_flags|=EC_TELEMETRY_VALID_ACTIVE_INPUT;
        for (uint8_t p=0;p<2;p++) {
            const ec_source_observation_t *obs=&in.source[EC_SOURCE_PD1+p];
            ti.pd[p].valid=obs->qualified_input_current_valid;
            ti.pd[p].voltage_mv=obs->negotiated_voltage_mv;
            ti.pd[p].current_ma=obs->qualified_input_current_ma;
        }
        ec_telemetry_snapshot_t snapshot; ec_telemetry_build_snapshot(&snapshot,&ti);
        ec_battery_inputs_t bi={.telemetry=snapshot,.pack_present=ec_app_battery_present(),.charger_enable=out->charger_enable};
        ec_battery_report_t battery; ec_battery_step(&bc,&bi,&bs,now,&battery);
        uint16_t flags=(battery.present?1u:0u) | (lid.lid_closed?2u:0u) | (!fan_healthy?4u:0u) |
                       (headphone_present?8u:0u) | (external?16u:0u) | (out->mu_boot_authorized?32u:0u) |
                       (ec_app_charging_active()?64u:0u) | (host.valid?128u:0u);
        ec_host_publish(&snapshot,&battery,flags,(uint16_t)controller.fault,rpm,now);
        static uint32_t audio_due;
        if ((int32_t)(now-audio_due)>=0) {
            audio_due=now+500u;
            bool headphones=headphone_present && host.valid && out->mu_12v_enable &&
                             (host.requests & EC_HOST_REQUEST_SPEAKER);
            if (!audio_headphones(headphones)) gpio_set_audio_amp_enable(false);
        }
        ssd1306_status_step(&snapshot,flags,(uint16_t)controller.fault,rpm,duty,
            ec_app_ntc_counts_to_temp_dc(gpio_read_adc_thermal_skin()),
            ec_app_ntc_counts_to_temp_dc(gpio_read_adc_thermal_mu()),now);
        usb_hid_poll(); ec_watchdog_pet(); DelayMs(20);
    }
}
