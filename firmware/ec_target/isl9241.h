#ifndef DUCKTOP2_ISL9241_H
#define DUCKTOP2_ISL9241_H
#include <stdbool.h>
#include <stdint.h>
#include "board_profile.h"

/* FN8945 Rev.6.00. SMBus words are sent low byte first. Hardware uses
 * 20 mOhm input and 10 mOhm battery shunts, with the default 1x gain. */
#define ISL9241_I2C_ADDRESS 0x09u
#define ISL9241_BOOT_INPUT_MA 200u
#define ISL9241_INPUT_CURRENT_MAX_MA 4400u
#define ISL9241_CHARGE_CURRENT_MIN_MA 64u
#define ISL9241_CHARGE_CURRENT_MAX_MA 3000u
#define ISL9241_CHARGE_VOLTAGE_MIN_MV 10200u
/* 12.528 V plus the 0.5% regulation high corner remains below 12.6 V. */
#define ISL9241_CHARGE_VOLTAGE_MAX_MV 12528u
#define ISL9241_MIN_SYSTEM_MV 10112u
#define ISL9241_SAMPLE_WAIT_MS 120u
/* Specified 1.77..2.39 A trip range at 2.048 A, plus external shunt
 * tolerance. PSYS stays enabled so battery mode uses this comparator. */
#define ISL9241_DC_THROTTLE_MA DUCKTOP2_ISL_DC_PROCHOT_MA

typedef enum {
    ISL9241_CHARGE_NONE, ISL9241_CHARGE_TRICKLE,
    ISL9241_CHARGE_FAST, ISL9241_CHARGE_TAPER
} isl9241_charge_status_t;
typedef struct {
    bool vbus_present, power_good, battery_present, fault, throttled;
    isl9241_charge_status_t charge_status;
    int16_t ibat_ma, ibus_ma;
    uint16_t vbat_mv, vbus_mv, vsys_mv;
} isl9241_telemetry_t;

bool isl9241_probe(void);
bool isl9241_init(void);
bool isl9241_configuration_ok(void);
bool isl9241_set_input_current_ma(uint16_t ma);
bool isl9241_read_input_current_limit_ma(uint16_t *ma);
bool isl9241_program_charge_limits(uint16_t mv, uint16_t ma);
bool isl9241_read_charge_limits(uint16_t *mv, uint16_t *ma);
bool isl9241_set_charge_enable(bool enable);
bool isl9241_pet_watchdog(void);
/* Zero selects battery operation. Nonzero enables the input-loss alarm
 * above the minimum system voltage where the adapter voltage permits it. */
bool isl9241_set_adapter_alarm(uint16_t nominal_mv);
bool isl9241_clear_throttle(void);
/* The ADC runs continuously. Wait SAMPLE_WAIT_MS before accepting a new
 * sample, covering the 100 ms battery-voltage conversion interval. */
bool isl9241_read_sample(isl9241_telemetry_t *sample);
bool isl9241_is_charge_in_progress(isl9241_charge_status_t status);
#endif
