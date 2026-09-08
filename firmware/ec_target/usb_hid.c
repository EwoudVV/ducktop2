#include "usb_hid.h"
#include "usb_hid_desc.h"
#include "host_link.h"
#include "stm32f4xx.h"
#include "tusb.h"
#include <string.h>

extern uint32_t GetTick(void);

static ec_hid_keyboard_report_t keyboard_pending;
static ec_hid_consumer_report_t consumer_pending;
static bool keyboard_dirty;
static bool consumer_dirty;
static bool initialized;
static uint8_t keyboard_leds;
static uint16_t idle_ms[2];
static uint32_t last_sent_ms[2];

uint32_t tusb_time_millis_api(void)
{
    return GetTick();
}

void OTG_FS_IRQHandler(void)
{
    tud_int_handler(0);
}

void usb_hid_init(void)
{
    RCC->AHB1ENR |= RCC_AHB1ENR_GPIOAEN;
    (void)RCC->AHB1ENR;
    GPIOA->MODER = (GPIOA->MODER & ~((3u << 22) | (3u << 24)))
                  | (2u << 22) | (2u << 24);
    GPIOA->AFR[1] = (GPIOA->AFR[1] & ~(0xFFu << 12)) | (0xAAu << 12);
    GPIOA->OTYPER &= ~((1u << 11) | (1u << 12));
    GPIOA->PUPDR &= ~((3u << 22) | (3u << 24));
    GPIOA->OSPEEDR |= (3u << 22) | (3u << 24);
    RCC->AHB2ENR |= RCC_AHB2ENR_OTGFSEN;
    (void)RCC->AHB2ENR;
    NVIC_SetPriority(OTG_FS_IRQn, 5);
    const tusb_rhport_init_t port = {.role = TUSB_ROLE_DEVICE, .speed = TUSB_SPEED_FULL};
    initialized = tusb_init(0, &port);
    keyboard_dirty = true;
    consumer_dirty = true;
}

bool usb_hid_configured(void)
{
    return initialized && tud_mounted();
}

void usb_hid_send_keyboard(const ec_hid_keyboard_report_t *report)
{
    if (report && memcmp(report, &keyboard_pending, sizeof(*report)) != 0) {
        keyboard_pending = *report;
        keyboard_dirty = true;
    }
}

void usb_hid_send_consumer(const ec_hid_consumer_report_t *report)
{
    if (report && memcmp(report, &consumer_pending, sizeof(*report)) != 0) {
        consumer_pending = *report;
        consumer_dirty = true;
    }
}

void usb_hid_poll(void)
{
    if (!initialized) return;
    tud_task();
    uint32_t now = GetTick();
    static uint32_t status_sent;
    if (now - status_sent >= 100u && tud_hid_n_ready(2) &&
        tud_hid_n_report(2, 0, ec_host_report(), EC_HOST_REPORT_BYTES))
        status_sent = now;
    if (idle_ms[0] && now - last_sent_ms[0] >= idle_ms[0]) keyboard_dirty = true;
    if (idle_ms[1] && now - last_sent_ms[1] >= idle_ms[1]) consumer_dirty = true;
    if (keyboard_dirty && tud_hid_n_ready(0) &&
        tud_hid_n_report(0, 0, &keyboard_pending, sizeof(keyboard_pending))) {
        keyboard_dirty = false;
        last_sent_ms[0] = now;
    }
    if (consumer_dirty && tud_hid_n_ready(1) &&
        tud_hid_n_report(1, 0, &consumer_pending, sizeof(consumer_pending))) {
        consumer_dirty = false;
        last_sent_ms[1] = now;
    }
}

bool tud_hid_set_idle_cb(uint8_t instance, uint8_t rate)
{
    if (instance == 2) return true;
    if (instance > 2) return false;
    idle_ms[instance] = (uint16_t)rate * 4u;
    return true;
}

void tud_mount_cb(void)
{
    keyboard_dirty = true;
    consumer_dirty = true;
}

uint8_t const *tud_descriptor_device_cb(void)
{
    return usb_hid_device_descriptor;
}

uint8_t const *tud_descriptor_configuration_cb(uint8_t index)
{
    return index == 0 ? usb_hid_config_descriptor : NULL;
}

uint8_t const *tud_hid_descriptor_report_cb(uint8_t instance)
{
    if (instance == 0) return usb_hid_keyboard_report_descriptor;
    if (instance == 1) return usb_hid_consumer_report_descriptor;
    if (instance == 2) return usb_hid_status_report_descriptor;
    return NULL;
}

uint16_t const *tud_descriptor_string_cb(uint8_t index, uint16_t langid)
{
    (void)langid;
    static uint16_t descriptor[32];
    const uint8_t *source;
    switch (index) {
    case 0: source = usb_hid_string_langid; break;
    case USB_STR_MANUFACTURER: source = usb_hid_string_manufacturer; break;
    case USB_STR_PRODUCT: source = usb_hid_string_product; break;
    case USB_STR_SERIAL: source = usb_hid_string_serial; break;
    default: return NULL;
    }
    if (source[0] > sizeof(descriptor)) return NULL;
    memcpy(descriptor, source, source[0]);
    return descriptor;
}

uint16_t tud_hid_get_report_cb(uint8_t instance, uint8_t report_id,
                              hid_report_type_t type, uint8_t *buffer, uint16_t length)
{
    if (report_id != 0) return 0;
    const void *source = NULL;
    uint16_t size = 0;
    if (type == HID_REPORT_TYPE_INPUT) {
        if (instance == 0) { source = &keyboard_pending; size = sizeof(keyboard_pending); }
        if (instance == 1) { source = &consumer_pending; size = sizeof(consumer_pending); }
    } else if (instance == 0 && type == HID_REPORT_TYPE_OUTPUT) {
        source = &keyboard_leds;
        size = 1;
    }
    if (instance == 2 && (type == HID_REPORT_TYPE_INPUT || type == HID_REPORT_TYPE_FEATURE)) {
        source = ec_host_report(); size = EC_HOST_REPORT_BYTES;
    }
    if (source == NULL) return 0;
    if (size > length) size = length;
    memcpy(buffer, source, size);
    return size;
}

void tud_hid_set_report_cb(uint8_t instance, uint8_t report_id,
                          hid_report_type_t type, uint8_t const *buffer, uint16_t size)
{
    if (instance == 0 && report_id == 0 && type == HID_REPORT_TYPE_OUTPUT && size == 1)
        keyboard_leds = buffer[0] & 0x1Fu;
    if (instance == 2 && report_id == 0 && type == HID_REPORT_TYPE_FEATURE)
        ec_host_receive(buffer, size, GetTick());
}
