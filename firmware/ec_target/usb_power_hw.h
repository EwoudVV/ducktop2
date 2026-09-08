#ifndef DUCKTOP2_USB_POWER_HW_H
#define DUCKTOP2_USB_POWER_HW_H
#include <stdbool.h>
#include <stdint.h>
#define USB_POWER_IO_ADDRESS 0x76u
#define USB_POWER_MONITOR_ADDRESS 0x40u
#define USB_POWER_MONITOR_CHANNEL 2u
#define USB_POWER_IN_FAULT_N (1u << 1)
#define USB_POWER_IN_ALERT_N (1u << 2)
#define USB_POWER_IN_PG      (1u << 3)
#define USB_POWER_IN_PD1_PG  (1u << 4)
#define USB_POWER_IN_PD2_PG  (1u << 5)

typedef enum {
    USB_POWER_HW_OK = 0, USB_POWER_HW_NOT_READY, USB_POWER_HW_BUS,
    USB_POWER_HW_CONFIG, USB_POWER_HW_OVERCURRENT, USB_POWER_HW_RANGE
} usb_power_hw_result_t;

typedef struct {
    bool valid;
    uint16_t voltage_mv;
    int16_t nominal_current_ma;
    uint16_t upper_current_ma;
    uint32_t sample_ms, conversion_sequence;
    uint8_t input0, input1;
} usb_power_sample_t;

/* Component, -40..125 C, life, and specified Kelvin-layout envelope. */
#define USB_POWER_SHUNT_NOMINAL_NOHM 5000000u
#define USB_POWER_SHUNT_MIN_NOHM 4757261u
#define USB_POWER_SHUNT_MAX_NOHM 5243261u
#define USB_POWER_ADC_GAIN_PPM 6000u
#define USB_POWER_ADC_OFFSET_NV 25000u
#define USB_POWER_TRIP_CURRENT_MA 6500u
#define USB_POWER_INA_CONFIG 0x4607u /* 64 averages, 140 us bus/shunt, continuous */
#define USB_POWER_INA_CALIBRATION 2048u /* 0.5 mA/LSB, 16.3835 A positive range */

uint16_t usb_power_alert_threshold_raw(void);
uint16_t usb_power_current_upper_ma(int16_t shunt_raw);
bool usb_power_hw_init(uint32_t now_ms);
bool usb_power_hw_write(uint8_t output0);
bool usb_power_hw_clear_fault(uint32_t now_ms);
usb_power_hw_result_t usb_power_hw_sample(uint32_t now_ms, usb_power_sample_t *sample);
uint8_t usb_power_hw_applied(void);
#endif
