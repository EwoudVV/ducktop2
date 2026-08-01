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

const uint8_t usb_hid_config_descriptor[59] = {
    /* Configuration descriptor */
    9u, USB_DT_CONFIG,
    59u, 0x00u,             /* wTotalLength */
    0x02u,                  /* bNumInterfaces */
    0x01u,                  /* bConfigurationValue */
    0x00u,                  /* iConfiguration */
    0x80u,                  /* bmAttributes: bus-powered */
    50u,                    /* bMaxPower (100 mA) */

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

uint32_t usb_hid_desc_check(void)
{
    const uint8_t *config = usb_hid_config_descriptor;
    if (config[0] != 9u || config[1] != USB_DT_CONFIG) {
        return 0u;
    }
    uint32_t total = (uint32_t)config[2] | ((uint32_t)config[3] << 8u);
    if (total != USB_HID_CONFIG_TOTAL_LENGTH || total > sizeof(usb_hid_config_descriptor)) {
        return 2u;
    }
    uint32_t offset = 9u;   /* skip configuration header */
    uint32_t interfaces = 0u;
    uint32_t hid_class = 0u;
    uint32_t endpoints = 0u;
    while (offset < total) {
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
    if (offset != total || interfaces != 2u || hid_class != 2u || endpoints != 2u) {
        return offset;
    }
    return 0u;
}

/* Item payload sizes as written by every shipped HID descriptor (the size
 * nibble of Usage/Input/etc. items does not match the real byte layout).
 * Only the items used by the two report descriptors are needed. */
static uint8_t hid_item_size(uint8_t b)
{
    switch (b) {
    case 0x05u: case 0x09u: case 0x19u: case 0x29u:
    case 0x15u: case 0x25u: case 0x75u: case 0x95u:
    case 0x81u: case 0x91u: case 0xA1u:
        return 1u;
    case 0x26u: case 0x2Au:
        return 2u;
    case 0xC0u:
        return 0u;
    default:
        return 0u;
    }
}

uint32_t usb_hid_report_input_size(const uint8_t *desc, uint32_t len)
{
    uint32_t input_bits = 0u;
    uint32_t report_size = 0u;
    uint32_t report_count = 0u;
    uint32_t offset = 0u;
    while (offset < len) {
        uint8_t b = desc[offset];
        uint8_t size = hid_item_size(b);
        uint32_t value = 0u;
        uint32_t i;
        for (i = 0u; i < size && offset + 1u + i < len; i++) {
            value |= (uint32_t)desc[offset + 1u + i] << (8u * i);
        }
        if (b == 0x75u) {                   /* Report Size */
            report_size = value;
        } else if (b == 0x95u) {            /* Report Count */
            report_count = value;
        } else if (b == 0x81u) {            /* Input main item */
            if ((value & 0x01u) == 0u) {    /* Data (not Const) */
                input_bits += report_size * report_count;
            }
            report_size = 0u;
            report_count = 0u;
        } else if (b == 0x91u) {            /* Output main item */
            report_size = 0u;
            report_count = 0u;
        } else if (b == 0xA1u || b == 0xC0u) {
            report_size = 0u;
            report_count = 0u;
        }
        offset += 1u + size;
    }
    return (input_bits + 7u) / 8u;
}
