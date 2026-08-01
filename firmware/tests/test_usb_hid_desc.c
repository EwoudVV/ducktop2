/*
 * Host tests for the EC USB HID descriptor tables.
 */

#include <stdio.h>
#include <stdlib.h>

#include "usb_hid_desc.h"

static int s_checks = 0;

#define CHECK(cond)                                                        \
    do {                                                                   \
        s_checks++;                                                        \
        if (!(cond)) {                                                     \
            fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond); \
            exit(1);                                                       \
        }                                                                  \
    } while (0)

static void test_device_descriptor(void)
{
    const uint8_t *d = usb_hid_device_descriptor;
    CHECK(d[0] == 18u);
    CHECK(d[1] == USB_DT_DEVICE);
    CHECK(d[4] == 0u);   /* class per interface */
    CHECK(d[7] == 64u);  /* EP0 max packet */
    CHECK(((uint16_t)d[8] | ((uint16_t)d[9] << 8u)) == USB_VID_DUCKTOP2);
    CHECK(((uint16_t)d[10] | ((uint16_t)d[11] << 8u)) == USB_PID_EC_KEYBOARD);
    CHECK(d[17] == 1u);  /* one configuration */
}

static void test_config_descriptor_walk(void)
{
    uint32_t result = usb_hid_desc_check();
    CHECK(result == 0u);
}

static void test_endpoints(void)
{
    const uint8_t *c = usb_hid_config_descriptor;
    CHECK(((uint16_t)c[2] | ((uint16_t)c[3] << 8u)) == USB_HID_CONFIG_TOTAL_LENGTH);
    CHECK(c[4] == 2u);   /* two interfaces */

    uint32_t offset = 9u;
    uint32_t hid_count = 0u;
    uint32_t ep_count = 0u;
    while (offset < USB_HID_CONFIG_TOTAL_LENGTH) {
        uint8_t len = c[offset];
        uint8_t type = c[offset + 1u];
        if (type == USB_DT_HID) {
            hid_count++;
            uint16_t report_len = (uint16_t)c[offset + 7u] | ((uint16_t)c[offset + 8u] << 8u);
            if (hid_count == 1u) {
                CHECK(report_len == sizeof(usb_hid_keyboard_report_descriptor));
            } else {
                CHECK(report_len == sizeof(usb_hid_consumer_report_descriptor));
            }
        } else if (type == USB_DT_ENDPOINT) {
            ep_count++;
            CHECK((c[offset + 2u] & 0x80u) != 0u);   /* IN */
            CHECK(c[offset + 3u] == USB_EP_ATTR_INTERRUPT);
            CHECK(c[offset + 6u] == USB_HID_BINTERVAL);
            CHECK((uint16_t)c[offset + 4u] == USB_HID_REPORT_SIZE);
            if (ep_count == 1u) {
                CHECK(c[offset + 2u] == USB_HID_KEYBOARD_EP);
            } else {
                CHECK(c[offset + 2u] == USB_HID_CONSUMER_EP);
            }
        }
        offset += len;
    }
    CHECK(hid_count == 2u);
    CHECK(ep_count == 2u);
}

static void test_report_descriptor_sizes(void)
{
    /* Boot keyboard: modifier (8) + 6 keys (48) = 56 data bits = 7 bytes;
     * the reserved byte is a constant item. */
    CHECK(usb_hid_report_input_size(usb_hid_keyboard_report_descriptor,
                                    sizeof(usb_hid_keyboard_report_descriptor)) == 7u);
    /* Consumer: 4 x 16-bit usages = 64 bits = 8 bytes. */
    CHECK(usb_hid_report_input_size(usb_hid_consumer_report_descriptor,
                                    sizeof(usb_hid_consumer_report_descriptor)) == 8u);
}

static void test_string_descriptors(void)
{
    CHECK(usb_hid_string_langid[0] == 4u);
    CHECK(usb_hid_string_langid[1] == USB_DT_STRING);
    CHECK(usb_hid_string_manufacturer[0] == 22u);
    CHECK(usb_hid_string_product[0] == 24u);
    CHECK(usb_hid_string_serial[0] == 28u);
    CHECK((usb_hid_string_product[0] - 2u) / 2u == 11u);  /* "Ducktop2 EC" chars */
}

int main(void)
{
    test_device_descriptor();
    test_config_descriptor_walk();
    test_endpoints();
    test_report_descriptor_sizes();
    test_string_descriptors();
    printf("usb_hid_desc_tests: PASS (%d checks)\n", s_checks);
    return 0;
}
