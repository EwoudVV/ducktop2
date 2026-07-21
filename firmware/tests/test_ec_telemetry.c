#include "ducktop2/ec/ec_telemetry.h"

#include <stdio.h>

static int failures;

#define CHECK(expression)                                                      \
  do {                                                                         \
    if (!(expression)) {                                                       \
      fprintf(stderr, "%s:%d: CHECK failed: %s\n", __FILE__, __LINE__,         \
              #expression);                                                    \
      ++failures;                                                              \
    }                                                                          \
  } while (0)

static void test_invalid_fields_are_not_exposed(void) {
  ec_telemetry_inputs_t inputs;
  ec_telemetry_snapshot_t snapshot;

  ec_telemetry_inputs_init(&inputs);
  inputs.soc_percent = 80u;
  inputs.pack_voltage_mv = 11750u;
  inputs.pack_current_ma = 1250;
  inputs.active_source = EC_SOURCE_PD1;
  ec_telemetry_build_snapshot(&snapshot, &inputs);

  CHECK(snapshot.valid_flags == 0u);
  CHECK(snapshot.soc_percent == 0u);
  CHECK(snapshot.pack_voltage_mv == 0u);
  CHECK(snapshot.pack_current_ma == 0);
  CHECK(snapshot.charge_power_mw == 0u);
  CHECK(snapshot.discharge_power_mw == 0u);
  CHECK(snapshot.active_input == EC_TELEMETRY_INPUT_NONE);
}

static void test_tcpc_addresses_are_7_bit(void) {
  CHECK(EC_PD1_TCPC_I2C_ADDRESS_7BIT == 0x20u);
  CHECK(EC_PD2_TCPC_I2C_ADDRESS_7BIT == 0x21u);
  CHECK(EC_SOURCE_MANAGER_I2C_ADDRESS_7BIT == 0x74u);
  CHECK(EC_PD1_TCPC_I2C_ADDRESS_7BIT < 0x80u);
  CHECK(EC_PD2_TCPC_I2C_ADDRESS_7BIT < 0x80u);
  CHECK(EC_PD1_SERVICE_MUX_CHANNEL == 2u);
  CHECK(EC_PD2_SERVICE_MUX_CHANNEL == 3u);
  CHECK(EC_TPS25751_ACTIVE_PDO_REGISTER == 0x31u);
  CHECK(EC_TPS25751_ACTIVE_RDO_REGISTER == 0x32u);
  CHECK(EC_TPS25751_PD_STATUS_REGISTER == 0x35u);
}

static void test_bq34z100_time_conversion(void) {
  uint32_t seconds = 123u;

  CHECK(ec_telemetry_bq34z100_minutes_to_seconds(0u, &seconds));
  CHECK(seconds == 0u);
  CHECK(ec_telemetry_bq34z100_minutes_to_seconds(1u, &seconds));
  CHECK(seconds == 60u);
  CHECK(ec_telemetry_bq34z100_minutes_to_seconds(65534u, &seconds));
  CHECK(seconds == 3932040u);
  seconds = 123u;
  CHECK(!ec_telemetry_bq34z100_minutes_to_seconds(
      EC_BQ34Z100_TIME_UNAVAILABLE, &seconds));
  CHECK(seconds == 123u);
  CHECK(!ec_telemetry_bq34z100_minutes_to_seconds(1u, NULL));
}

static void test_discharge_snapshot(void) {
  ec_telemetry_inputs_t inputs;
  ec_telemetry_snapshot_t snapshot;

  ec_telemetry_inputs_init(&inputs);
  inputs.valid_flags = EC_TELEMETRY_VALID_SOC |
                       EC_TELEMETRY_VALID_PACK_VOLTAGE |
                       EC_TELEMETRY_VALID_PACK_CURRENT |
                       EC_TELEMETRY_VALID_TIME_TO_EMPTY |
                       EC_TELEMETRY_VALID_REMAINING_CAPACITY |
                       EC_TELEMETRY_VALID_FULL_CAPACITY |
                       EC_TELEMETRY_VALID_CYCLE_COUNT |
                       EC_TELEMETRY_VALID_HEALTH |
                       EC_TELEMETRY_VALID_ACTIVE_INPUT;
  inputs.soc_percent = 73u;
  inputs.health_percent = 94u;
  inputs.pack_voltage_mv = 11400u;
  inputs.pack_current_ma = -1500;
  inputs.time_to_empty_s = 7200u;
  inputs.remaining_capacity_mah = 7300u;
  inputs.full_capacity_mah = 9800u;
  inputs.cycle_count = 42u;
  inputs.active_source = EC_SOURCE_PACK;
  inputs.pd[0] = (ec_pd_contract_telemetry_t){
      .valid = true,
      .voltage_mv = 15000u,
      .current_ma = 3000u,
  };
  ec_telemetry_build_snapshot(&snapshot, &inputs);

  CHECK((snapshot.valid_flags & EC_TELEMETRY_VALID_PACK_POWER) != 0u);
  CHECK(snapshot.soc_percent == 73u);
  CHECK(snapshot.health_percent == 94u);
  CHECK(snapshot.discharge_power_mw == 17100u);
  CHECK(snapshot.charge_power_mw == 0u);
  CHECK(snapshot.active_input == EC_TELEMETRY_INPUT_PACK);
  CHECK(snapshot.pd[0].valid);
  CHECK(snapshot.pd[0].voltage_mv == 15000u);
  CHECK(snapshot.pd[0].current_ma == 3000u);
  CHECK(!snapshot.pd[1].valid);
}

static void test_charge_snapshot_and_clamping(void) {
  ec_telemetry_inputs_t inputs;
  ec_telemetry_snapshot_t snapshot;

  ec_telemetry_inputs_init(&inputs);
  inputs.valid_flags = EC_TELEMETRY_VALID_SOC |
                       EC_TELEMETRY_VALID_HEALTH |
                       EC_TELEMETRY_VALID_PACK_VOLTAGE |
                       EC_TELEMETRY_VALID_PACK_CURRENT |
                       EC_TELEMETRY_VALID_TIME_TO_FULL |
                       EC_TELEMETRY_VALID_ACTIVE_INPUT;
  inputs.soc_percent = 140u;
  inputs.health_percent = 120u;
  inputs.pack_voltage_mv = 12100u;
  inputs.pack_current_ma = 2000;
  inputs.time_to_full_s = 3600u;
  inputs.active_source = EC_SOURCE_PD2;
  inputs.pd[1] = (ec_pd_contract_telemetry_t){
      .valid = true,
      .voltage_mv = 15000u,
      .current_ma = 2000u,
  };
  ec_telemetry_build_snapshot(&snapshot, &inputs);

  CHECK(snapshot.soc_percent == 100u);
  CHECK(snapshot.health_percent == 100u);
  CHECK(snapshot.charge_power_mw == 24200u);
  CHECK(snapshot.discharge_power_mw == 0u);
  CHECK(snapshot.time_to_full_s == 3600u);
  CHECK(snapshot.active_input == EC_TELEMETRY_INPUT_PD2);
  CHECK(snapshot.pd[1].valid);
}

static void test_invalid_active_source_clears_validity(void) {
  ec_telemetry_inputs_t inputs;
  ec_telemetry_snapshot_t snapshot;

  ec_telemetry_inputs_init(&inputs);
  inputs.valid_flags = EC_TELEMETRY_VALID_ACTIVE_INPUT;
  inputs.active_source = EC_SOURCE_NONE;
  ec_telemetry_build_snapshot(&snapshot, &inputs);

  CHECK((snapshot.valid_flags & EC_TELEMETRY_VALID_ACTIVE_INPUT) == 0u);
  CHECK(snapshot.active_input == EC_TELEMETRY_INPUT_NONE);
}

int main(void) {
  test_tcpc_addresses_are_7_bit();
  test_bq34z100_time_conversion();
  test_invalid_fields_are_not_exposed();
  test_discharge_snapshot();
  test_charge_snapshot_and_clamping();
  test_invalid_active_source_clears_validity();

  if (failures != 0) {
    fprintf(stderr, "ec_telemetry_tests: %d failure(s)\n", failures);
    return 1;
  }
  puts("ec_telemetry_tests: PASS");
  return 0;
}
