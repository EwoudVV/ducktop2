/*
 * Ducktop2 EC USB HID descriptors (static tables, host-testable).
 *
 * Layout: one configuration, two interfaces:
 *   Interface 0: boot keyboard (HID, boot subclass 1, protocol 1),
 *                EP1 IN interrupt 8 bytes / 1 ms.
 *   Interface 1: consumer control (HID), EP2 IN interrupt 8 bytes / 1 ms.
 *
 * The descriptor tables live in this header so the host test can validate
 * the chain without compiling the hardware stack (usb_hid.c).
 */

#ifndef DUCKTOP2_EC_USB_HID_DESC_H
#define DUCKTOP2_EC_USB_HID_DESC_H

#include <stdint.h>

/* USB class/spec constants */
#define USB_DT_DEVICE           0x01u
#define USB_DT_CONFIG           0x02u
#define USB_DT_STRING           0x03u
#define USB_DT_HID              0x21u
#define USB_DT_HID_REPORT       0x22u
#define USB_DT_INTERFACE        0x04u
#define USB_DT_ENDPOINT         0x05u

#define USB_CLASS_HID           0x03u
#define USB_HID_SUBCLASS_BOOT   0x01u
#define USB_HID_PROTOCOL_BOOT   0x01u

#define USB_ENDPOINT_IN         0x80u
#define USB_EP_ATTR_INTERRUPT   0x03u

#define USB_HID_KEYBOARD_EP     0x81u
#define USB_HID_CONSUMER_EP     0x82u
#define USB_HID_REPORT_SIZE     8u
#define USB_HID_BINTERVAL       1u

#define USB_VID_DUCKTOP2        0x1209u   /* pid.codes test VID */
#define USB_PID_EC_KEYBOARD     0x2328u

#define USB_STR_MANUFACTURER    0x01u
#define USB_STR_PRODUCT         0x02u
#define USB_STR_SERIAL          0x03u

extern const uint8_t usb_hid_device_descriptor[18];
extern const uint8_t usb_hid_config_descriptor[59];
extern const uint8_t usb_hid_keyboard_report_descriptor[63];
extern const uint8_t usb_hid_consumer_report_descriptor[23];
extern const uint8_t usb_hid_string_langid[4];
extern const uint8_t usb_hid_string_manufacturer[22];
extern const uint8_t usb_hid_string_product[24];
extern const uint8_t usb_hid_string_serial[28];

#define USB_HID_CONFIG_TOTAL_LENGTH 59u

/* Validate descriptor chain structure; returns 0 on success, or the offset
 * of the first inconsistency.  Host-test entry point. */
uint32_t usb_hid_desc_check(void);

/* Report-descriptor total size walk; returns the reported input size in
 * bytes for the given report descriptor, or 0 on malformed input. */
uint32_t usb_hid_report_input_size(const uint8_t *desc, uint32_t len);

#endif /* DUCKTOP2_EC_USB_HID_DESC_H */
