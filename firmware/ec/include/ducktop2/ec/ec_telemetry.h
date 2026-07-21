#ifndef DUCKTOP2_EC_TELEMETRY_H
#define DUCKTOP2_EC_TELEMETRY_H

#include "ducktop2/ec/ec_policy.h"

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define EC_PD1_TCPC_I2C_ADDRESS_7BIT 0x20u
#define EC_PD2_TCPC_I2C_ADDRESS_7BIT 0x21u
#define EC_SOURCE_MANAGER_I2C_ADDRESS_7BIT 0x74u
#define EC_PD1_SERVICE_MUX_CHANNEL 2u
#define EC_PD2_SERVICE_MUX_CHANNEL 3u
#define EC_TPS25751_ACTIVE_PDO_REGISTER 0x31u
#define EC_TPS25751_ACTIVE_RDO_REGISTER 0x32u
#define EC_TPS25751_PD_STATUS_REGISTER 0x35u
#define EC_BQ34Z100_TIME_UNAVAILABLE 0xffffu

typedef enum {
  EC_TELEMETRY_VALID_SOC = 1u << 0,
  EC_TELEMETRY_VALID_PACK_VOLTAGE = 1u << 1,
  EC_TELEMETRY_VALID_PACK_CURRENT = 1u << 2,
  EC_TELEMETRY_VALID_PACK_POWER = 1u << 3,
  EC_TELEMETRY_VALID_TIME_TO_EMPTY = 1u << 4,
  EC_TELEMETRY_VALID_TIME_TO_FULL = 1u << 5,
  EC_TELEMETRY_VALID_REMAINING_CAPACITY = 1u << 6,
  EC_TELEMETRY_VALID_FULL_CAPACITY = 1u << 7,
  EC_TELEMETRY_VALID_CYCLE_COUNT = 1u << 8,
  EC_TELEMETRY_VALID_HEALTH = 1u << 9,
  EC_TELEMETRY_VALID_ACTIVE_INPUT = 1u << 10
} ec_telemetry_valid_flag_t;

typedef enum {
  EC_TELEMETRY_INPUT_NONE = 0,
  EC_TELEMETRY_INPUT_PACK,
  EC_TELEMETRY_INPUT_AUX,
  EC_TELEMETRY_INPUT_PD1,
  EC_TELEMETRY_INPUT_PD2
} ec_telemetry_input_t;

typedef struct {
  bool valid;
  uint16_t voltage_mv;
  uint16_t current_ma;
} ec_pd_contract_telemetry_t;

typedef struct {
  uint16_t valid_flags;
  uint8_t soc_percent;
  uint8_t health_percent;
  uint16_t pack_voltage_mv;
  int32_t pack_current_ma;
  uint32_t time_to_empty_s;
  uint32_t time_to_full_s;
  uint32_t remaining_capacity_mah;
  uint32_t full_capacity_mah;
  uint16_t cycle_count;
  ec_source_id_t active_source;
  ec_pd_contract_telemetry_t pd[EC_PD_PORT_COUNT];
} ec_telemetry_inputs_t;

typedef struct {
  uint16_t valid_flags;
  uint8_t soc_percent;
  uint8_t health_percent;
  uint16_t pack_voltage_mv;
  int32_t pack_current_ma;
  uint32_t charge_power_mw;
  uint32_t discharge_power_mw;
  uint32_t time_to_empty_s;
  uint32_t time_to_full_s;
  uint32_t remaining_capacity_mah;
  uint32_t full_capacity_mah;
  uint16_t cycle_count;
  ec_telemetry_input_t active_input;
  ec_pd_contract_telemetry_t pd[EC_PD_PORT_COUNT];
} ec_telemetry_snapshot_t;

void ec_telemetry_inputs_init(ec_telemetry_inputs_t *inputs);
bool ec_telemetry_bq34z100_minutes_to_seconds(uint16_t gauge_minutes,
                                              uint32_t *seconds_out);
void ec_telemetry_build_snapshot(ec_telemetry_snapshot_t *snapshot,
                                 const ec_telemetry_inputs_t *inputs);

#ifdef __cplusplus
}
#endif

#endif
