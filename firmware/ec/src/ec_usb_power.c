#include "ducktop2/ec/ec_usb_power.h"
#include <stddef.h>
#include <string.h>

uint16_t ec_usb_port_reservation_ma(ec_usb_port_t port, uint8_t sink_only)
{
    /* VBUS + permitted VCONN, including the source-only 249 ohm bleed and
     * control current. Data-role and instantaneous VCONN observations do not
     * lower these reservations. A PDO Source contract remains a promise. */
    static const uint16_t current[EC_USB_PORT_COUNT] = {
        1215u, 1215u, 1175u, 1175u, 775u, 900u, 500u
    };
    if ((unsigned)port >= EC_USB_PORT_COUNT) return 0u;
    if (port <= EC_USB_J11 && (sink_only & (1u << port))) return 315u;
    return current[port];
}

static uint32_t input_power(const ec_usb_power_config_t *c, uint16_t ma)
{
    if (!ma) return 0u;
    uint64_t numerator = (uint64_t)ma * c->rail_max_mv * 100u;
    uint32_t divisor = (uint32_t)c->minimum_efficiency_percent * 1000u;
    return (uint32_t)((numerator + divisor - 1u) / divisor);
}

bool ec_usb_power_plan(const ec_usb_power_config_t *c,
                       const ec_usb_power_inputs_t *in,
                       ec_usb_power_plan_t *out)
{
    static const uint8_t priority[] = {
        EC_USB_J21, EC_USB_J11, EC_USB_J24, EC_USB_J22,
        EC_USB_J23, EC_USB_J25, EC_USB_J12
    };
    if (!out) return false;
    memset(out, 0, sizeof(*out));
    if (!c || !in) return false;
    out->denied_mask = in->requested_mask;
    if ((in->requested_mask & ~EC_USB_ALL_PORTS) ||
        (in->retained_mask & ~EC_USB_ALL_PORTS) || (in->pd_sink_only_mask & ~3u) ||
        c->minimum_efficiency_percent == 0u || c->minimum_efficiency_percent > 100u ||
        c->rail_max_mv < 4900u || c->rail_max_mv > 5250u ||
        c->admission_current_ma > 10000u || c->right_harness_current_ma > 10000u)
        return false;
    if (!c->qualified || !in->host_lease_valid || !in->system_safe || in->transfer_active)
        return true;

    /* Existing admitted ports have priority. Changes are made only by the
     * target's verified disable/reserve/enable sequence, never by this plan. */
    uint16_t total = 25u; /* bounded common control and sensing allowance */
    uint16_t right = 0u;
    for (unsigned pass = 0; pass < 2; ++pass) {
        for (unsigned n = 0; n < EC_USB_PORT_COUNT; ++n) {
            uint8_t port = priority[n], bit = (uint8_t)(1u << port);
            bool retained = (in->retained_mask & bit) != 0u;
            if (!(in->requested_mask & bit) || retained != (pass == 0)) continue;
            uint16_t cost = ec_usb_port_reservation_ma((ec_usb_port_t)port, in->pd_sink_only_mask);
            uint16_t next = (uint16_t)(total + cost);
            uint16_t next_right = (uint16_t)(right +
                ((port == EC_USB_J11 || port == EC_USB_J12) ? (uint16_t)(cost+(right?0u:25u)) : 0u));
            uint32_t power = input_power(c, next);
            if (next > c->admission_current_ma || next_right > c->right_harness_current_ma ||
                power > in->available_input_power_mw) continue;
            total = next;
            right = next_right;
            out->allowed_mask |= bit;
        }
    }
    if (out->allowed_mask) {
        out->reserved_current_ma = total;
        out->right_current_ma = right;
        out->reserved_input_power_mw = input_power(c, total);
    }
    out->denied_mask = in->requested_mask & (uint8_t)~out->allowed_mask;
    return true;
}
