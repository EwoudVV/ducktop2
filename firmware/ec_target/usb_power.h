#ifndef DUCKTOP2_USB_POWER_H
#define DUCKTOP2_USB_POWER_H
#include "ducktop2/ec/ec_usb_power.h"
#include "usb_power_hw.h"
#include "tps25751.h"
#include "host_link.h"

typedef enum { USB_POWER_OFF=0, USB_POWER_STARTING, USB_POWER_READY,
               USB_POWER_FAULT, USB_POWER_PENDING } usb_power_phase_t;
typedef enum { USB_POWER_NO_FAULT=0, USB_POWER_OVERCURRENT,
               USB_POWER_STALE, USB_POWER_VOLTAGE, USB_POWER_GATE_TIMEOUT,
               USB_POWER_PD_PATH, USB_POWER_SYSTEM_RAIL, USB_POWER_LATCHED_FAULT } usb_power_fault_t;
typedef struct {
    ec_usb_power_config_t budget;
    uint16_t startup_ceiling_ma, pd_inrush_ma, branch_inrush_ma;
    uint16_t rail_min_mv, rail_max_mv;
    uint16_t vsys_max_overestimate_mv, vsys_max_fall_mv;
    uint32_t startup_timeout_ms, gate_timeout_ms, sample_max_age_ms;
} usb_power_config_t;
typedef struct {
    bool host_lease_valid, system_safe, transfer_active, clear_fault;
    uint8_t requested_mask, active_source;
    bool vsys_measurement_valid;
    uint16_t vsys_measured_mv;
    uint32_t vsys_age_ms;
    uint32_t available_input_power_mw;
    /* USB demand already included in this cycle's EC/charger allocation. */
    uint32_t committed_reservation_mw;
} usb_power_request_t;
typedef struct {
    usb_power_config_t config;
    usb_power_sample_t sample;
    tps25751_port_state_t pd[2];
    ec_usb_power_plan_t plan;
    usb_power_phase_t phase;
    usb_power_fault_t fault;
    uint8_t applied_mask, starting_port, last_source;
    uint32_t started_ms, gate_started_ms, polled_ms, rail_sequence, gate_sequence;
    bool initialized, have_source;
} usb_power_state_t;

bool usb_power_init(usb_power_state_t *state,const usb_power_config_t *config,uint32_t now_ms);
/* False means safe outputs cannot be verified: main must assert system reset. */
bool usb_power_disable(usb_power_state_t *state);
bool usb_power_poll(usb_power_state_t *state,uint32_t now_ms);
bool usb_power_step(usb_power_state_t *state,const usb_power_request_t *request,uint32_t now_ms);
uint32_t usb_power_reservation_mw(const usb_power_state_t *state);
ec_host_usb_status_t usb_power_status(const usb_power_state_t *state,uint32_t now_ms);
#endif
