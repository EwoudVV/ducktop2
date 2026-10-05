#ifndef DUCKTOP2_BQ76922_H
#define DUCKTOP2_BQ76922_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include "bq76922_charge_limits.h"

#define BQ76922_I2C_ADDRESS 0x08u
#define BQ76922_CELL_MASK 0x0013u
#define BQ76922_CHG_FET 0x01u
#define BQ76922_DSG_FET 0x04u
#define BQ76922_PDSG_FET 0x08u
#define BQ76922_CUV 0x04u
#define BQ76922_COV 0x08u

/* The transport returns wire bytes, including one CRC after each data byte.
 * Reads must use the repeated-start form in SLUUCG7 section 9.2. */
typedef struct {
    void *context;
    bool (*read)(void *, uint8_t, uint8_t, uint8_t *, uint16_t);
    bool (*write)(void *, uint8_t, uint8_t, const uint8_t *, uint16_t);
} bq76922_transport_t;

typedef struct {
    uint16_t address;
    uint8_t length;
    uint8_t value[4];
} bq76922_config_row_t;

typedef struct {
    const bq76922_config_row_t *rows;
    size_t row_count;
    bool complete;
    bool qualified;
    bool cell_voltage_qualified, charge_voltage_qualified, termination_qualified;
    uint16_t charge_voltage_mv, charge_cell_max_mv, charge_spread_max_mv;
    uint16_t cell_voltage_error_mv, charge_max_rise_mv;
    uint16_t discharge_cell_min_mv;
    uint16_t normal_charge_cell_min_mv;
    uint16_t cell_max_mv;
    uint16_t pack_min_mv;
    uint16_t current_gain_min_permille;
    uint16_t current_offset_ma;
    uint16_t current_lsb_ma;
    uint16_t discharge_limit_ma;
    uint16_t charge_limit_ma;
    uint16_t dynamic_reserve_ma;
    uint16_t sample_max_age_ms;
    uint16_t config_max_age_ms;
} bq76922_profile_t;

typedef struct {
    bool valid;
    uint16_t cell_mv[3];
    uint16_t stack_mv;
    int16_t current_ma; /* Positive charge; negative discharge. */
    int32_t discharge_upper_ma;
    int32_t charge_upper_ma;
    uint8_t safety_a, safety_b, safety_c;
    uint8_t safety_alert_a, safety_alert_b, safety_alert_c;
    uint8_t pf_a, pf_b, pf_c, pf_d;
    uint8_t pf_alert_a, pf_alert_b, pf_alert_c, pf_alert_d;
    uint16_t battery_status, alarm_raw;
    uint8_t fet_status;
    uint32_t at_ms;
} bq76922_sample_t;

typedef struct {
    bq76922_transport_t io;
    const bq76922_profile_t *profile;
    bq76922_sample_t sample;
    bool config_valid;
    bool verifying;
    bool waiting;
    size_t row;
    uint16_t pending_address;
    uint32_t pending_at_ms, config_at_ms;
} bq76922_t;

uint8_t bq76922_crc8(const uint8_t *data, size_t length);
void bq76922_init(bq76922_t *, const bq76922_transport_t *, const bq76922_profile_t *);
bool bq76922_begin_verify(bq76922_t *, uint32_t now_ms);
bool bq76922_verify_step(bq76922_t *, uint32_t now_ms);
bool bq76922_read_sample(bq76922_t *, uint32_t now_ms);
void bq76922_transport_lost(bq76922_t *);
bool bq76922_discharge_admitted(const bq76922_t *, uint32_t now_ms,
                               bool monitor_ready, bool ready_valid,
                               uint32_t ready_at_ms, uint16_t total_request_ma);
bool bq76922_charge_admitted(const bq76922_t *, uint32_t now_ms,
                            bool monitor_ready, bool ready_valid,
                            uint32_t ready_at_ms, uint16_t request_ma);
bool bq76922_charge_profile_ready(const bq76922_profile_t *);
#endif
