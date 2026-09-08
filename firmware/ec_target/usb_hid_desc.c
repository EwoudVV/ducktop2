/*
 * Ducktop2 EC USB HID descriptors (implementation).
 */

#include "usb_hid_desc.h"

const uint8_t usb_hid_device_descriptor[18] = {
    18u,                    /* bLength */
    USB_DT_DEVICE,          /* bDescriptorType */
    0x00u, 0x02u,           /* bcdUSB 2.00 */
    0x00u,                  /* bDeviceClass (per interface) */
    0x00u,                  /* bDeviceSubClass */
    0x00u,                  /* bDeviceProtocol */
    64u,                    /* bMaxPacketSize0 */
    (USB_VID_DUCKTOP2 & 0xFFu), (USB_VID_DUCKTOP2 >> 8u),
    (USB_PID_EC_KEYBOARD & 0xFFu), (USB_PID_EC_KEYBOARD >> 8u),
    0x00u, 0x01u,           /* bcdDevice 1.00 */
    USB_STR_MANUFACTURER,   /* iManufacturer */
    USB_STR_PRODUCT,        /* iProduct */
    USB_STR_SERIAL,         /* iSerialNumber */
    0x01u,                  /* bNumConfigurations */
};

const uint8_t usb_hid_config_descriptor[84] = {
    /* Configuration descriptor */
    9u, USB_DT_CONFIG,
    84u, 0x00u,             /* wTotalLength */
    0x03u,                  /* bNumInterfaces */
    0x01u,                  /* bConfigurationValue */
    0x00u,                  /* iConfiguration */
    0xc0u,                  /* self-powered from the always-on rail */
    0u,                     /* no VBUS load allocated to this function */

    /* Interface 0: boot keyboard */
    9u, USB_DT_INTERFACE,
    0x00u,                  /* bInterfaceNumber */
    0x00u,                  /* bAlternateSetting */
    0x01u,                  /* bNumEndpoints */
    USB_CLASS_HID,
    USB_HID_SUBCLASS_BOOT,
    USB_HID_PROTOCOL_BOOT,
    0x00u,                  /* iInterface */

    /* HID class descriptor */
    9u, USB_DT_HID,
    0x11u, 0x01u,           /* bcdHID 1.11 */
    0x00u,                  /* bCountryCode */
    0x01u,                  /* bNumDescriptors */
    USB_DT_HID_REPORT,
    63u, 0x00u,             /* wDescriptorLength */

    /* EP1 IN interrupt */
    7u, USB_DT_ENDPOINT,
    USB_HID_KEYBOARD_EP,
    USB_EP_ATTR_INTERRUPT,
    USB_HID_REPORT_SIZE, 0x00u,
    USB_HID_BINTERVAL,

    /* Interface 1: consumer control */
    9u, USB_DT_INTERFACE,
    0x01u,                  /* bInterfaceNumber */
    0x00u,                  /* bAlternateSetting */
    0x01u,                  /* bNumEndpoints */
    USB_CLASS_HID,
    0x00u,                  /* bInterfaceSubClass */
    0x00u,                  /* bInterfaceProtocol */
    0x00u,                  /* iInterface */

    /* HID class descriptor */
    9u, USB_DT_HID,
    0x11u, 0x01u,           /* bcdHID 1.11 */
    0x00u,                  /* bCountryCode */
    0x01u,                  /* bNumDescriptors */
    USB_DT_HID_REPORT,
    23u, 0x00u,             /* wDescriptorLength */

    /* EP2 IN interrupt */
    7u, USB_DT_ENDPOINT,
    USB_HID_CONSUMER_EP,
    USB_EP_ATTR_INTERRUPT,
    USB_HID_REPORT_SIZE, 0x00u,
    USB_HID_BINTERVAL,
    /* Interface 2: status input and control feature reports, no report IDs. */
    9u, USB_DT_INTERFACE, 2u, 0u, 1u, USB_CLASS_HID, 0u, 0u, 0u,
    9u, USB_DT_HID, 0x11u, 0x01u, 0u, 1u, USB_DT_HID_REPORT, 25u, 0u,
    7u, USB_DT_ENDPOINT, USB_HID_STATUS_EP, USB_EP_ATTR_INTERRUPT, 64u, 0u, 20u,
};

const uint8_t usb_hid_status_report_descriptor[25] = {
    0x06, 0x00, 0xff, 0x09, 0x01, 0xa1, 0x01,
    0x15, 0x00, 0x26, 0xff, 0x00, 0x75, 0x08, 0x95, 0x40,
    0x09, 0x01, 0x81, 0x02, 0x09, 0x02, 0xb1, 0x02, 0xc0
};

const uint8_t usb_hid_keyboard_report_descriptor[63] = {
    0x05u, 0x01u,           /* Usage Page (Generic Desktop) */
    0x09u, 0x06u,           /* Usage (Keyboard) */
    0xA1u, 0x01u,           /* Collection (Application) */
    0x05u, 0x07u,           /*   Usage Page (Keyboard) */
    0x19u, 0xE0u,           /*   Usage Minimum (0xE0) */
    0x29u, 0xE7u,           /*   Usage Maximum (0xE7) */
    0x15u, 0x00u,           /*   Logical Minimum (0) */
    0x25u, 0x01u,           /*   Logical Maximum (1) */
    0x75u, 0x01u,           /*   Report Size (1) */
    0x95u, 0x08u,           /*   Report Count (8) */
    0x81u, 0x02u,           /*   Input (Data,Var,Abs) - modifier byte */
    0x95u, 0x01u,           /*   Report Count (1) */
    0x75u, 0x08u,           /*   Report Size (8) */
    0x81u, 0x01u,           /*   Input (Const) - reserved byte */
    0x95u, 0x05u,           /*   Report Count (5) */
    0x75u, 0x01u,           /*   Report Size (1) */
    0x05u, 0x08u,           /*   Usage Page (LEDs) */
    0x19u, 0x01u,           /*   Usage Minimum (1) */
    0x29u, 0x05u,           /*   Usage Maximum (5) */
    0x91u, 0x02u,           /*   Output (Data,Var,Abs) - LED report */
    0x95u, 0x01u,           /*   Report Count (1) */
    0x75u, 0x03u,           /*   Report Size (3) */
    0x91u, 0x01u,           /*   Output (Const) */
    0x95u, 0x06u,           /*   Report Count (6) */
    0x75u, 0x08u,           /*   Report Size (8) */
    0x15u, 0x00u,           /*   Logical Minimum (0) */
    0x25u, 0x65u,           /*   Logical Maximum (101) */
    0x05u, 0x07u,           /*   Usage Page (Keyboard) */
    0x19u, 0x00u,           /*   Usage Minimum (0) */
    0x29u, 0x65u,           /*   Usage Maximum (101) */
    0x81u, 0x00u,           /*   Input (Data,Array) - 6 keycodes */
    0xC0u,                  /* End Collection */
};

const uint8_t usb_hid_consumer_report_descriptor[23] = {
    0x05u, 0x0Cu,           /* Usage Page (Consumer) */
    0x09u, 0x01u,           /* Usage (Consumer Control) */
    0xA1u, 0x01u,           /* Collection (Application) */
    0x19u, 0x01u,           /*   Usage Minimum (1) */
    0x2Au, 0x9Cu, 0x02u,    /*   Usage Maximum (0x029C) */
    0x15u, 0x00u,           /*   Logical Minimum (0) */
    0x26u, 0x9Cu, 0x02u,    /*   Logical Maximum (0x029C) */
    0x75u, 0x10u,           /*   Report Size (16) */
    0x95u, 0x04u,           /*   Report Count (4) */
    0x81u, 0x00u,           /*   Input (Data,Array) - 4 consumer usages */
    0xC0u,                  /* End Collection */
};

const uint8_t usb_hid_string_langid[4] = {
    4u, USB_DT_STRING, 0x09u, 0x04u,
};

const uint8_t usb_hid_string_manufacturer[22] = {
    22u, USB_DT_STRING,
    'D', 0x00u, 'u', 0x00u, 'c', 0x00u, 'k', 0x00u,
    ' ', 0x00u, 'I', 0x00u, 'n', 0x00u, 'd', 0x00u,
    's', 0x00u, '.', 0x00u,
};

const uint8_t usb_hid_string_product[24] = {
    24u, USB_DT_STRING,
    'D', 0x00u, 'u', 0x00u, 'c', 0x00u, 'k', 0x00u,
    't', 0x00u, 'o', 0x00u, 'p', 0x00u, '2', 0x00u,
    ' ', 0x00u, 'E', 0x00u, 'C', 0x00u,
};

const uint8_t usb_hid_string_serial[28] = {
    28u, USB_DT_STRING,
    '0', 0x00u, '0', 0x00u, '0', 0x00u, '0', 0x00u,
    '0', 0x00u, '0', 0x00u, '0', 0x00u, '0', 0x00u,
    '0', 0x00u, '0', 0x00u, '0', 0x00u, '0', 0x00u,
    '1', 0x00u,
};

uint32_t usb_hid_desc_check_buffer(const uint8_t *config, uint32_t size)
{
    if (!config || size < 9u || config[0] != 9u || config[1] != USB_DT_CONFIG) {
        return 1u;
    }
    uint32_t total = (uint32_t)config[2] | ((uint32_t)config[3] << 8u);
    if (total != USB_HID_CONFIG_TOTAL_LENGTH || total != size) {
        return 2u;
    }
    uint32_t offset = 9u;   /* skip configuration header */
    uint32_t interfaces = 0u;
    uint32_t hid_class = 0u;
    uint32_t endpoints = 0u;
    while (offset < total) {
        if (total - offset < 2u) return offset;
        uint8_t len = config[offset];
        uint8_t type = config[offset + 1u];
        if (len < 2u || offset + len > total) {
            return offset;
        }
        if (type == USB_DT_INTERFACE) {
            interfaces++;
            if (len < 9u) {
                return offset;
            }
        } else if (type == USB_DT_HID) {
            hid_class++;
            if (len < 9u) {
                return offset;
            }
            uint16_t report_len = (uint16_t)config[offset + 7u]
                                | ((uint16_t)config[offset + 8u] << 8u);
            if (report_len == 0u) {
                return offset;
            }
        } else if (type == USB_DT_ENDPOINT) {
            endpoints++;
            if (len < 7u) {
                return offset;
            }
            if (config[offset + 3u] != USB_EP_ATTR_INTERRUPT) {
                return offset;
            }
        }
        offset += len;
    }
    if (offset != total || interfaces != 3u || hid_class != 3u || endpoints != 3u) {
        return offset;
    }
    return 0u;
}

uint32_t usb_hid_desc_check(void)
{
    return usb_hid_desc_check_buffer(usb_hid_config_descriptor, sizeof(usb_hid_config_descriptor));
}

/* HID 1.11 short-item decoding. Constant input fields occupy wire bits;
 * Report Size and Count are globals and persist across main items. */
uint32_t usb_hid_report_input_size(const uint8_t *desc, uint32_t len)
{
    if (!desc || !len) return 0u;
    uint32_t bits=0, size=0, count=0, offset=0;
    while (offset<len) {
        uint8_t prefix=desc[offset++];
        if (prefix==0xfeu) return 0u;
        uint8_t bytes=prefix & 3u;
        if (bytes==3u) bytes=4u;
        if (bytes>len-offset) return 0u;
        uint32_t value=0;
        for (uint8_t i=0;i<bytes;i++) value|=(uint32_t)desc[offset+i]<<(8u*i);
        switch (prefix & 0xfcu) {
        case 0x74u: size=value; break;
        case 0x94u: count=value; break;
        case 0x84u: return 0u; /* this transport has no report IDs */
        case 0x80u:
            if (!size || !count || size>1024u || count>1024u || bits>65536u-size*count) return 0u;
            bits+=size*count; break;
        default: break;
        }
        offset+=bytes;
    }
    return (bits+7u)/8u;
}
