#include "ducktop2/ec/ec_telemetry.h"

#include <limits.h>
#include <string.h>

static uint32_t saturate_u64(uint64_t value) {
  return value > UINT32_MAX ? UINT32_MAX : (uint32_t)value;
}

static ec_telemetry_input_t map_active_input(ec_source_id_t source) {
  switch (source) {
    case EC_SOURCE_PACK:
      return EC_TELEMETRY_INPUT_PACK;
    case EC_SOURCE_AUX:
      return EC_TELEMETRY_INPUT_AUX;
    case EC_SOURCE_PD1:
      return EC_TELEMETRY_INPUT_PD1;
    case EC_SOURCE_PD2:
      return EC_TELEMETRY_INPUT_PD2;
    default:
      return EC_TELEMETRY_INPUT_NONE;
  }
}

void ec_telemetry_inputs_init(ec_telemetry_inputs_t *inputs) {
  if (inputs == NULL) {
    return;
  }
  memset(inputs, 0, sizeof(*inputs));
  inputs->active_source = EC_SOURCE_NONE;
}

bool ec_telemetry_bq34z100_minutes_to_seconds(uint16_t gauge_minutes,
                                              uint32_t *seconds_out) {
  if (seconds_out == NULL || gauge_minutes == EC_BQ34Z100_TIME_UNAVAILABLE) {
    return false;
  }
  *seconds_out = (uint32_t)gauge_minutes * 60u;
  return true;
}

void ec_telemetry_build_snapshot(ec_telemetry_snapshot_t *snapshot,
                                 const ec_telemetry_inputs_t *inputs) {
  uint64_t power_mw;
  uint64_t current_magnitude_ma;
  size_t index;

  if (snapshot == NULL) {
    return;
  }
  memset(snapshot, 0, sizeof(*snapshot));
  snapshot->active_input = EC_TELEMETRY_INPUT_NONE;
  if (inputs == NULL) {
    return;
  }

  snapshot->valid_flags = inputs->valid_flags;
  if ((inputs->valid_flags & EC_TELEMETRY_VALID_SOC) != 0u) {
    snapshot->soc_percent = inputs->soc_percent <= 100u
                                ? inputs->soc_percent
                                : 100u;
  }
  if ((inputs->valid_flags & EC_TELEMETRY_VALID_HEALTH) != 0u) {
    snapshot->health_percent = inputs->health_percent <= 100u
                                   ? inputs->health_percent
                                   : 100u;
  }
  if ((inputs->valid_flags & EC_TELEMETRY_VALID_PACK_VOLTAGE) != 0u) {
    snapshot->pack_voltage_mv = inputs->pack_voltage_mv;
  }
  if ((inputs->valid_flags & EC_TELEMETRY_VALID_PACK_CURRENT) != 0u) {
    snapshot->pack_current_ma = inputs->pack_current_ma;
  }
  if ((inputs->valid_flags & EC_TELEMETRY_VALID_TIME_TO_EMPTY) != 0u) {
    snapshot->time_to_empty_s = inputs->time_to_empty_s;
  }
  if ((inputs->valid_flags & EC_TELEMETRY_VALID_TIME_TO_FULL) != 0u) {
    snapshot->time_to_full_s = inputs->time_to_full_s;
  }
  if ((inputs->valid_flags & EC_TELEMETRY_VALID_REMAINING_CAPACITY) != 0u) {
    snapshot->remaining_capacity_mah = inputs->remaining_capacity_mah;
  }
  if ((inputs->valid_flags & EC_TELEMETRY_VALID_FULL_CAPACITY) != 0u) {
    snapshot->full_capacity_mah = inputs->full_capacity_mah;
  }
  if ((inputs->valid_flags & EC_TELEMETRY_VALID_CYCLE_COUNT) != 0u) {
    snapshot->cycle_count = inputs->cycle_count;
  }
  if ((inputs->valid_flags & EC_TELEMETRY_VALID_ACTIVE_INPUT) != 0u) {
    snapshot->active_input = map_active_input(inputs->active_source);
    if (snapshot->active_input == EC_TELEMETRY_INPUT_NONE) {
      snapshot->valid_flags &=
          (uint16_t)~EC_TELEMETRY_VALID_ACTIVE_INPUT;
    }
  }

  if ((inputs->valid_flags & EC_TELEMETRY_VALID_PACK_VOLTAGE) != 0u &&
      (inputs->valid_flags & EC_TELEMETRY_VALID_PACK_CURRENT) != 0u) {
    current_magnitude_ma = inputs->pack_current_ma < 0
                               ? (uint64_t)(-(int64_t)inputs->pack_current_ma)
                               : (uint64_t)inputs->pack_current_ma;
    power_mw = ((uint64_t)inputs->pack_voltage_mv * current_magnitude_ma) /
               1000u;
    snapshot->valid_flags |= EC_TELEMETRY_VALID_PACK_POWER;
    /* BQ34Z100 Current() is positive while charging and negative while discharging. */
    if (inputs->pack_current_ma > 0) {
      snapshot->charge_power_mw = saturate_u64(power_mw);
    } else {
      snapshot->discharge_power_mw = saturate_u64(power_mw);
    }
  } else {
    snapshot->valid_flags &= (uint16_t)~EC_TELEMETRY_VALID_PACK_POWER;
  }

  for (index = 0; index < EC_PD_PORT_COUNT; ++index) {
    if (inputs->pd[index].valid) {
      snapshot->pd[index] = inputs->pd[index];
    }
  }
}
