/*
 * Ducktop2 EC USB HID keyboard device stack (STM32 OTG_FS, device mode).
 *
 * The EC enumerates as a boot-protocol keyboard plus a consumer-control
 * interface over OTG_FS (PA11/PA12, internal FS PHY, self-powered, VBUS
 * sensing disabled).  Reports produced by ec_keymap_process() are staged
 * here and sent on the interrupt IN endpoints when the host polls.
 *
 * Servicing model: the OTG_FS global interrupt is the primary driver
 * (OTG_FS_IRQHandler); usb_hid_poll() is an idempotent fallback callable
 * from the main loop.
 */

#ifndef DUCKTOP2_EC_USB_HID_H
#define DUCKTOP2_EC_USB_HID_H

#include <stdbool.h>
#include <stdint.h>

#include "ducktop2/ec/ec_keymap.h"

#ifdef __cplusplus
extern "C" {
#endif

void usb_hid_init(void);

/* True after the host completes SET_CONFIGURATION. */
bool usb_hid_configured(void);

/* Stage the latest reports; sent on the next free IN token.  A zero report
 * (all released) is transmitted exactly like any other report so the host
 * never holds a stuck key. */
void usb_hid_send_keyboard(const ec_hid_keyboard_report_t *report);
void usb_hid_send_consumer(const ec_hid_consumer_report_t *report);

/* Idempotent service routine for the main loop (safe to call every 20 ms). */
void usb_hid_poll(void);

#ifdef __cplusplus
}
#endif

#endif /* DUCKTOP2_EC_USB_HID_H */
