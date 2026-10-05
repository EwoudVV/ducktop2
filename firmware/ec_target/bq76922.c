#include "bq76922.h"
#include <string.h>

uint8_t bq76922_crc8(const uint8_t *data, size_t length)
{
    uint8_t crc = 0;
    for (size_t i = 0; i < length; ++i) {
        crc ^= data[i];
        for (unsigned bit = 0; bit < 8; ++bit)
            crc = (uint8_t)((crc << 1) ^ ((crc & 0x80u) ? 0x07u : 0u));
    }
    return crc;
}

static uint16_t word(const uint8_t *b)
{ return (uint16_t)b[0] | ((uint16_t)b[1] << 8); }

static bool read_crc(bq76922_t *d, uint8_t reg, uint8_t *data, uint8_t length)
{
    uint8_t wire[64];
    if (!d || !data || !length || length > 32u || !d->io.read ||
        !d->io.read(d->io.context, BQ76922_I2C_ADDRESS, reg, wire, 2u * length))
        return false;
    for (uint8_t i = 0; i < length; ++i) {
        const uint8_t first[] = {0x10u, reg, 0x11u, wire[2u * i]};
        uint8_t crc = i ? bq76922_crc8(&wire[2u * i], 1) : bq76922_crc8(first, 4);
        if (wire[2u * i + 1u] != crc) return false;
        data[i] = wire[2u * i];
    }
    return true;
}

/* The awake pin has no alarm mask. Runtime writes only select readback
 * addresses; no alarm/FET/recovery/configuration/OTP writes are emitted. */
static bool request_readback(bq76922_t *d, uint16_t address)
{
    uint8_t wire[4], bytes[] = {(uint8_t)address, (uint8_t)(address >> 8)};
    uint8_t first[] = {0x10u, 0x3eu, bytes[0]};
    wire[0] = bytes[0]; wire[1] = bq76922_crc8(first, 3);
    wire[2] = bytes[1]; wire[3] = bq76922_crc8(&bytes[1], 1);
    return d->io.write && d->io.write(d->io.context, BQ76922_I2C_ADDRESS, 0x3eu, wire, 4);
}

void bq76922_transport_lost(bq76922_t *d)
{
    if (!d) return;
    memset(&d->sample, 0, sizeof(d->sample));
    d->config_valid = d->verifying = d->waiting = false;
}

void bq76922_init(bq76922_t *d, const bq76922_transport_t *io,
                 const bq76922_profile_t *profile)
{
    if (!d) return;
    memset(d, 0, sizeof(*d));
    if (io) d->io = *io;
    d->profile = profile;
}

static bool profile_ready(const bq76922_profile_t *p)
{
    if (!p || !p->rows || !p->row_count) return false;
    for (size_t i = 0; i < p->row_count; ++i)
        if (p->rows[i].address < 0x9000u || !p->rows[i].length || p->rows[i].length > 4u)
            return false;
    return p && p->complete && p->rows && p->row_count && p->current_lsb_ma == 1u &&
        p->discharge_cell_min_mv && p->normal_charge_cell_min_mv >= p->discharge_cell_min_mv &&
        p->cell_max_mv > p->normal_charge_cell_min_mv && p->pack_min_mv && p->sample_max_age_ms &&
        p->config_max_age_ms &&
        p->current_gain_min_permille <= 1000u && p->discharge_limit_ma <= 8000u &&
        p->charge_limit_ma <= 3000u && p->dynamic_reserve_ma < p->discharge_limit_ma;
}

bool bq76922_begin_verify(bq76922_t *d, uint32_t now_ms)
{
    uint8_t bytes[2];
    if (!d || !profile_ready(d->profile) || !read_crc(d, 0x12u, bytes, 2) ||
        /* UNSEALED, initialized, awake, no CONFIG_UPDATE/DEEPSLEEP. */
        (word(bytes) & 0x0303u) != 0x0200u) {
        bq76922_transport_lost(d); return false;
    }
    d->row = 0; d->verifying = true; d->waiting = false;
    d->pending_at_ms = now_ms;
    return true;
}

bool bq76922_verify_step(bq76922_t *d, uint32_t now_ms)
{
    uint8_t echo[2], length, buffer[32], checksum;
    if (!d || !d->verifying || !profile_ready(d->profile)) return false;
    /* The final request verifies active autonomous FET mode, not only RAM. */
    uint16_t address = d->row < d->profile->row_count ?
        d->profile->rows[d->row].address : 0x0057u;
    if (!d->waiting) {
        if (!request_readback(d, address)) goto lost;
        d->pending_address = address; d->pending_at_ms = now_ms; d->waiting = true;
        return true;
    }
    if (now_ms - d->pending_at_ms < 2u) return true;
    if (now_ms - d->pending_at_ms > 250u || !read_crc(d, 0x3eu, echo, 2)) goto lost;
    if (word(echo) == 0xffffu) return true;
    if (word(echo) != d->pending_address || !read_crc(d, 0x61u, &length, 1) ||
        length < 5u || length > 36u || !read_crc(d, 0x40u, buffer, (uint8_t)(length - 4u)) ||
        !read_crc(d, 0x60u, &checksum, 1)) goto lost;
    uint8_t sum = (uint8_t)(echo[0] + echo[1]);
    for (uint8_t i = 0; i < length - 4u; ++i) sum = (uint8_t)(sum + buffer[i]);
    if (checksum != (uint8_t)~sum) goto lost;
    if (d->row < d->profile->row_count) {
        const bq76922_config_row_t *r = &d->profile->rows[d->row];
        if (!r->length || r->length > 4u || r->length > length - 4u ||
            memcmp(buffer, r->value, r->length)) goto lost;
        ++d->row;
        uint16_t next_address = d->row < d->profile->row_count ?
            d->profile->rows[d->row].address : 0x0057u;
        if (!request_readback(d, next_address)) goto lost;
        d->pending_address = next_address; d->pending_at_ms = now_ms;
        d->waiting = true;
    } else {
        /* FET_EN set; all manufacturing FET test bits and OTPW_EN clear. */
        if (length < 6u || (word(buffer) & 0x00f7u) != 0x0050u) goto lost;
        d->config_valid = true; d->config_at_ms = now_ms;
        d->verifying = d->waiting = false;
    }
    return true;
lost:
    bq76922_transport_lost(d); return false;
}

bool bq76922_read_sample(bq76922_t *d, uint32_t now_ms)
{
    uint8_t status[30], current[2], fet, alarm[2], stack[2];
    if (!d || !read_crc(d, 0x00u, status, 30) || !read_crc(d, 0x3au, current, 2) ||
        !read_crc(d, 0x7fu, &fet, 1) || !read_crc(d, 0x64u, alarm, 2) ||
        !read_crc(d, 0x34u, stack, 2) || word(stack) > 6553u) {
        bq76922_transport_lost(d); return false;
    }
    bq76922_sample_t next;
    memset(&next, 0, sizeof(next));
    next.battery_status = word(&status[0x12]);
    if ((next.battery_status & 0x0303u) != 0x0200u) {
        bq76922_transport_lost(d); return false;
    }
    next.cell_mv[0] = word(&status[0x14]);
    next.cell_mv[1] = word(&status[0x16]);
    next.cell_mv[2] = word(&status[0x1c]);
    next.stack_mv = (uint16_t)(word(stack) * 10u);
    next.current_ma = (int16_t)word(current);
    next.safety_a = status[0x03]; next.safety_b = status[0x05]; next.safety_c = status[0x07];
    next.safety_alert_a = status[0x02]; next.safety_alert_b = status[0x04]; next.safety_alert_c = status[0x06];
    next.pf_a = status[0x0b]; next.pf_b = status[0x0d];
    next.pf_c = status[0x0f]; next.pf_d = status[0x11];
    next.pf_alert_a = status[0x0a]; next.pf_alert_b = status[0x0c];
    next.pf_alert_c = status[0x0e]; next.pf_alert_d = status[0x10];
    next.fet_status = fet; next.alarm_raw = word(alarm); next.at_ms = now_ms;
    if (profile_ready(d->profile) && d->profile->current_gain_min_permille) {
        uint32_t magnitude = next.current_ma < 0 ? (uint32_t)(-(int32_t)next.current_ma) : 0u;
        uint32_t upper = (magnitude + d->profile->current_offset_ma + d->profile->current_lsb_ma) * 1000u;
        next.discharge_upper_ma = (int32_t)((upper + d->profile->current_gain_min_permille - 1u) /
                                           d->profile->current_gain_min_permille);
        magnitude = next.current_ma > 0 ? (uint32_t)next.current_ma : 0u;
        upper = (magnitude + d->profile->current_offset_ma + d->profile->current_lsb_ma) * 1000u;
        next.charge_upper_ma = (int32_t)((upper + d->profile->current_gain_min_permille - 1u) /
                                        d->profile->current_gain_min_permille);
    }
    next.valid = true; d->sample = next;
    return true;
}

static uint8_t safety_a(const bq76922_sample_t *s)
{ return (uint8_t)(s->safety_a | s->safety_alert_a); }
static uint8_t safety_b(const bq76922_sample_t *s)
{ return (uint8_t)(s->safety_b | s->safety_alert_b); }
static uint8_t safety_c(const bq76922_sample_t *s)
{
    /* Alert C bit3 is precharge-timeout suspension; Status C bit2 is PTO.
     * Neither permits normal charge. Other known alert bits match status. */
    return (uint8_t)(s->safety_c | (s->safety_alert_c & 0xf0u) |
                     ((s->safety_alert_c & 0x08u) ? 0x04u : 0u));
}

static bool fresh_and_known(const bq76922_t *d, uint32_t now_ms,
                            bool monitor_ready, bool ready_valid, uint32_t ready_at_ms)
{
    if (!d || !profile_ready(d->profile) || !d->profile->qualified || !d->profile->cell_voltage_qualified ||
        !d->profile->current_gain_min_permille || !d->profile->dynamic_reserve_ma || !d->config_valid ||
        !d->sample.valid || !ready_valid || !monitor_ready ||
        now_ms - ready_at_ms > d->profile->sample_max_age_ms ||
        now_ms - d->sample.at_ms > d->profile->sample_max_age_ms ||
        now_ms - d->config_at_ms > d->profile->config_max_age_ms) return false;
    const bq76922_sample_t *s = &d->sample;
    if (s->stack_mv < d->profile->pack_min_mv) return false;
    /* All PF alerts/statuses fail both directions. Reserved/unknown safety
     * or FET bits and unexplained summary flags are not recovery grants. */
    if (s->pf_a || s->pf_b || s->pf_c || s->pf_d || s->pf_alert_a || s->pf_alert_b ||
        s->pf_alert_c || s->pf_alert_d || (s->battery_status & 0x1000u) ||
        (s->alarm_raw & 0x2918u) || (s->fet_status & 0xb0u) ||
        (safety_a(s) & 0x03u) || (safety_b(s) & 0x08u) ||
        (s->safety_c & 0x09u) || (s->safety_alert_c & 0x07u)) return false;
    if ((s->battery_status & 0x0800u) && !(safety_a(s) || safety_b(s) || safety_c(s))) return false;
    if ((s->alarm_raw & 0x4000u) && !safety_a(s)) return false;
    if ((s->alarm_raw & 0x8000u) && !(safety_b(s) || safety_c(s))) return false;
    if ((s->alarm_raw & 0x1000u) && !(safety_a(s) || safety_b(s) || safety_c(s))) return false;
    for (unsigned cell = 0; cell < 3; ++cell)
        if (!s->cell_mv[cell] || s->cell_mv[cell] > d->profile->cell_max_mv) return false;
    return true;
}

bool bq76922_discharge_admitted(const bq76922_t *d, uint32_t now_ms,
                               bool monitor_ready, bool ready_valid,
                               uint32_t ready_at_ms, uint16_t total_request_ma)
{
    if (!fresh_and_known(d, now_ms, monitor_ready, ready_valid, ready_at_ms) ||
        (safety_a(&d->sample) & 0xe4u) || (safety_b(&d->sample) & 0xe6u) ||
        (safety_c(&d->sample) & 0xe2u) ||
        !total_request_ma || total_request_ma > d->profile->discharge_limit_ma ||
        !(d->sample.fet_status & BQ76922_DSG_FET) ||
        (d->sample.fet_status & BQ76922_PDSG_FET)) return false;
    for (unsigned cell = 0; cell < 3; ++cell)
        if (d->sample.cell_mv[cell] < d->profile->discharge_cell_min_mv) return false;
    return (uint32_t)d->sample.discharge_upper_ma + d->profile->dynamic_reserve_ma <=
        d->profile->discharge_limit_ma;
}

bool bq76922_charge_profile_ready(const bq76922_profile_t *p)
{
    bool cov=false, override=false;
    if (p && p->rows) for (size_t i=0; i<p->row_count; ++i) {
        const bq76922_config_row_t *r=&p->rows[i];
        if (r->address==0x9278u) cov=r->length==1u && r->value[0]==82u;
        if (r->address==0x91d6u) override=r->length==2u && r->value[0]==0xffu && r->value[1]==0xffu;
    }
    return p && cov && override && p->cell_voltage_qualified && p->charge_voltage_qualified && p->termination_qualified &&
        p->charge_voltage_mv == BQ76922_CHARGE_CV_MV &&
        p->charge_cell_max_mv == BQ76922_CHARGE_CELL_MAX_MV &&
        p->charge_spread_max_mv == BQ76922_CHARGE_SPREAD_MAX_MV &&
        p->cell_voltage_error_mv && p->cell_voltage_error_mv <= BQ76922_CHARGE_CELL_ERROR_MAX_MV &&
        p->charge_max_rise_mv && p->charge_max_rise_mv <= BQ76922_CHARGE_RISE_MAX_MV;
}

bool bq76922_charge_admitted(const bq76922_t *d, uint32_t now_ms,
                            bool monitor_ready, bool ready_valid,
                            uint32_t ready_at_ms, uint16_t request_ma)
{
    if (!fresh_and_known(d, now_ms, monitor_ready, ready_valid, ready_at_ms) ||
        !bq76922_charge_profile_ready(d->profile) ||
        /* CUV charge recovery has no qualified branch in this profile. */
        (safety_a(&d->sample) & 0x9cu) || (safety_b(&d->sample) & 0xd5u) ||
        (safety_c(&d->sample) & 0x56u) ||
        !request_ma || request_ma > d->profile->charge_limit_ma ||
        !(d->sample.fet_status & BQ76922_CHG_FET) ||
        (d->sample.fet_status & 0x02u)) return false;
    /* No precharge/deep-discharge recovery branch exists. Every cell must
     * meet the separately justified normal-charge admission floor. */
    uint16_t low = UINT16_MAX, high = 0;
    for (unsigned cell = 0; cell < 3; ++cell) {
        uint16_t mv = d->sample.cell_mv[cell];
        if (mv < d->profile->normal_charge_cell_min_mv || mv > d->profile->charge_cell_max_mv) return false;
        if (mv < low) low = mv;
        if (mv > high) high = mv;
    }
    if (high - low > d->profile->charge_spread_max_mv) return false;
    return d->sample.current_ma <= (int32_t)d->profile->charge_limit_ma;
}
