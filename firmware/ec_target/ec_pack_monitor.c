#include "ec_pack_monitor.h"
#include "bq76922_profile.h"
#include "bq76922_charge.h"
#include "board_profile.h"
#include "i2c.h"
#include <string.h>

static bq76922_t monitor;
static bq76922_charge_state_t charge_state;
static bool ready_valid, monitor_ready;
static uint32_t ready_at, sample_at, verify_at;

static bool read_wire(void *context, uint8_t address, uint8_t reg,
                      uint8_t *data, uint16_t length)
{
    (void)context;
    return i2c1_read(address, reg, data, length);
}
static bool write_wire(void *context, uint8_t address, uint8_t reg,
                       const uint8_t *data, uint16_t length)
{
    (void)context;
    uint8_t frame[65];
    if (length > 64u) return false;
    frame[0] = reg; memcpy(&frame[1], data, length);
    return i2c1_write_raw(address, frame, length + 1u);
}

void ec_pack_monitor_init(void)
{
    const bq76922_transport_t io = {.read=read_wire, .write=write_wire};
    bq76922_init(&monitor, &io, &ducktop2_bq76922_profile);
    bq76922_charge_init(&charge_state);
    ready_valid = monitor_ready = false;
    ready_at = sample_at = verify_at = 0;
}
void ec_pack_monitor_set_ready(bool valid, bool ready, uint32_t now_ms)
{
    ready_valid = valid; monitor_ready = valid && ready; ready_at = now_ms;
    /* REG1/interface loss revokes the old readback as well as admission. */
    if (!valid || !ready) bq76922_transport_lost(&monitor);
}
void ec_pack_monitor_poll(uint32_t now_ms)
{
    if ((int32_t)(now_ms - sample_at) >= 0) {
        sample_at = now_ms + 100u;
        (void)bq76922_read_sample(&monitor, now_ms);
    }
    if (monitor.verifying) (void)bq76922_verify_step(&monitor, now_ms);
    else if ((int32_t)(now_ms - verify_at) >= 0) {
        verify_at = now_ms + 1000u;
        (void)bq76922_begin_verify(&monitor, now_ms);
    }
}
static bool qualified(void)
{
    return DUCKTOP2_PACK_MONITOR_QUALIFIED && DUCKTOP2_PACK_OTP_QUALIFIED &&
        DUCKTOP2_PACK_DISCHARGE_SENSE_QUALIFIED && DUCKTOP2_PACK_THERMAL_QUALIFIED &&
        DUCKTOP2_PACK_CELL_VOLTAGE_QUALIFIED;
}
bool ec_pack_monitor_discharge_allowed(uint32_t now_ms, uint16_t total_request_ma)
{
    return qualified() && bq76922_discharge_admitted(&monitor, now_ms,
        monitor_ready, ready_valid, ready_at, total_request_ma);
}
bool ec_pack_monitor_charge_allowed(uint32_t now_ms, uint16_t request_ma)
{
    return qualified() && DUCKTOP2_PACK_CELL_VOLTAGE_QUALIFIED &&
        DUCKTOP2_PACK_CHARGE_VOLTAGE_QUALIFIED && DUCKTOP2_PACK_CHARGE_TERMINATION_QUALIFIED &&
        DUCKTOP2_PACK_CHARGE_MAX_RISE_MV == monitor.profile->charge_max_rise_mv &&
        DUCKTOP2_PACK_CHARGE_VOLTAGE_MV == monitor.profile->charge_voltage_mv &&
        !charge_state.complete && !charge_state.fault_latched &&
        bq76922_charge_admitted(&monitor, now_ms,
        monitor_ready, ready_valid, ready_at, request_ma);
}
bool ec_pack_monitor_charge_step(uint32_t now, bool charger_valid, uint32_t charger_at,
                                 bool cv_active, bool charge_enabled)
{
    return bq76922_charge_step(&charge_state, &monitor, now, monitor_ready, ready_valid, ready_at,
        charger_valid && qualified() && DUCKTOP2_PACK_CELL_VOLTAGE_QUALIFIED &&
        DUCKTOP2_PACK_CHARGE_VOLTAGE_QUALIFIED && DUCKTOP2_PACK_CHARGE_TERMINATION_QUALIFIED &&
        DUCKTOP2_PACK_CHARGE_MAX_RISE_MV == monitor.profile->charge_max_rise_mv,
        charger_at, DUCKTOP2_PACK_CHARGE_VOLTAGE_MV, cv_active, charge_enabled);
}
bool ec_pack_monitor_charge_complete(void) {return charge_state.complete;}
bool ec_pack_monitor_current(uint32_t now_ms, int32_t *current_ma)
{
    if (!current_ma || !qualified() || !monitor.config_valid || !monitor.sample.valid ||
        !monitor.profile->qualified || now_ms - monitor.sample.at_ms > monitor.profile->sample_max_age_ms ||
        now_ms - monitor.config_at_ms > monitor.profile->config_max_age_ms) return false;
    /* Preserve charge direction. Discharge uses the measured transfer bound. */
    *current_ma = monitor.sample.current_ma > 0 ? monitor.sample.current_ma :
        -monitor.sample.discharge_upper_ma;
    return true;
}
const bq76922_sample_t *ec_pack_monitor_sample(void) { return &monitor.sample; }
