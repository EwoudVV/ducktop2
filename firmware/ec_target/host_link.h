#ifndef DUCKTOP2_HOST_LINK_H
#define DUCKTOP2_HOST_LINK_H
#include <stdbool.h>
#include <stdint.h>
#include "ducktop2/ec/ec_battery.h"
#define EC_HOST_REPORT_BYTES 64u
#define EC_HOST_REQUEST_OFF (1u << 0)
#define EC_HOST_REQUEST_CHARGE (1u << 1)
#define EC_HOST_REQUEST_SPEAKER (1u << 2)
#define EC_HOST_REQUEST_MIC (1u << 3)
#define EC_HOST_REQUEST_RADIO (1u << 4)
#define EC_HOST_REQUEST_RGB (1u << 5)
#define EC_HOST_REQUEST_BMS_RETRY (1u << 6)
#define EC_HOST_REQUEST_USB_CLEAR (1u << 7)

typedef struct {
    bool valid;
    uint8_t usb_requested_mask;
    uint32_t budget_mw, estimated_mu_mw, estimated_aux_mw, requests;
} ec_host_state_t;
typedef struct {
    uint8_t applied_mask, denied_mask, phase, pd_roles;
    uint16_t current_upper_ma, voltage_mv;
    uint32_t reservation_mw;
} ec_host_usb_status_t;
void ec_host_init(void);
bool ec_host_take_usb_clear(uint32_t now_ms);
void ec_host_publish_usb(const ec_host_usb_status_t *status);
/* Sets the desired limit and advances its generation only on change. */
bool ec_host_request_budget(uint32_t mw);
void ec_host_receive(const uint8_t *packet, uint16_t size, uint32_t now_ms);
ec_host_state_t ec_host_state(uint32_t now_ms);
void ec_host_publish(const ec_telemetry_snapshot_t *telemetry,
                      const ec_battery_report_t *battery, uint16_t flags,
                      uint16_t fault, uint16_t fan_rpm, uint32_t now_ms);
const uint8_t *ec_host_report(void);
#endif
