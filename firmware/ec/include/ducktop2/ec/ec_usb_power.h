#ifndef DUCKTOP2_EC_USB_POWER_H
#define DUCKTOP2_EC_USB_POWER_H
#include <stdbool.h>
#include <stdint.h>

/* Physical port order is part of the host and expander contract. */
typedef enum {
    EC_USB_J21 = 0, EC_USB_J11, EC_USB_J22, EC_USB_J23,
    EC_USB_J12, EC_USB_J24, EC_USB_J25, EC_USB_PORT_COUNT
} ec_usb_port_t;
#define EC_USB_ALL_PORTS 0x7fu

typedef struct {
    bool qualified;
    uint16_t admission_current_ma;
    uint16_t right_harness_current_ma;
    uint16_t rail_max_mv;
    uint8_t minimum_efficiency_percent;
} ec_usb_power_config_t;

typedef struct {
    bool host_lease_valid;
    bool system_safe;
    bool transfer_active;
    uint8_t requested_mask;
    uint8_t retained_mask;
    /* Only a verified Sink-only controller configuration can release its
     * potential 900 mA Source reservation. A live Sink role alone cannot. */
    uint8_t pd_sink_only_mask;
    uint32_t available_input_power_mw;
} ec_usb_power_inputs_t;

typedef struct {
    uint8_t allowed_mask;
    uint8_t denied_mask;
    uint16_t reserved_current_ma;
    uint16_t right_current_ma;
    uint32_t reserved_input_power_mw;
} ec_usb_power_plan_t;

uint16_t ec_usb_port_reservation_ma(ec_usb_port_t port, uint8_t pd_sink_only_mask);
bool ec_usb_power_plan(const ec_usb_power_config_t *config,
                       const ec_usb_power_inputs_t *inputs,
                       ec_usb_power_plan_t *plan);
#endif
