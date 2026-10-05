#include "bq76922_charge.h"
#include <string.h>

void bq76922_charge_init(bq76922_charge_state_t *s)
{ if (s) memset(s, 0, sizeof(*s)); }

bool bq76922_charge_step(bq76922_charge_state_t *s, const bq76922_t *d, uint32_t now,
    bool ready, bool ready_valid, uint32_t ready_at, bool charger_valid,
    uint32_t charger_at, uint16_t charger_target_mv, bool cv_active, bool charge_enabled)
{
    if (!s || !d || !d->profile) return false;
    bool valid = !s->fault_latched && charger_valid &&
        charger_target_mv == d->profile->charge_voltage_mv &&
        now - charger_at <= BQ76922_CHARGER_SAMPLE_MAX_AGE_MS &&
        bq76922_charge_admitted(d, now, ready, ready_valid, ready_at, d->profile->charge_limit_ma);
    /* count only intervals bounded by fresh, qualified, enabled CV samples.
     * pauses preserve the budget; only a completed/recharged cycle resets it. */
    bool cv_now = valid && !s->complete && charge_enabled && cv_active;
    if (cv_now && s->cv_counting) {
        uint32_t elapsed = now - s->cv_at;
        if (elapsed <= d->profile->sample_max_age_ms) {
            uint32_t remaining = BQ76922_CV_DWELL_MAX_MS - s->cv_dwell_ms;
            s->cv_dwell_ms += elapsed < remaining ? elapsed : remaining;
        }
    }
    s->cv_counting = cv_now; s->cv_at = now;
    if (s->cv_dwell_ms >= BQ76922_CV_DWELL_MAX_MS && !s->complete) {
        s->fault_latched = true; valid = false;
    }
    if (!valid) {
        s->taper_pending = s->recharge_pending = s->had_good = s->cv_counting = false;
        return false;
    }
    if (s->had_good && now - s->last_good_at > d->profile->sample_max_age_ms)
        s->taper_pending = s->recharge_pending = false;
    s->had_good = true; s->last_good_at = now;
    uint16_t low = UINT16_MAX, high = 0; uint32_t sum = 0;
    for (unsigned i=0; i<3; ++i) {
        uint16_t mv=d->sample.cell_mv[i]; sum+=mv;
        if (mv<low) low=mv;
        if (mv>high) high=mv;
    }
    if (s->complete) {
        if (high > BQ76922_RECHARGE_CELL_MAX_MV) s->recharge_pending=false;
        else if (!s->recharge_pending) {s->recharge_pending=true; s->recharge_at=now;}
        else if (now-s->recharge_at >= BQ76922_RECHARGE_HOLD_MS) {
            s->complete=s->recharge_pending=s->cv_counting=false;
            s->cv_dwell_ms=0;
        }
        return !s->complete;
    }
    bool taper = charge_enabled && cv_active && low >= BQ76922_TAPER_CELL_MIN_MV &&
        sum >= BQ76922_TAPER_CELL_SUM_MIN_MV && d->sample.current_ma >= 0 &&
        d->sample.charge_upper_ma >= 0 && d->sample.charge_upper_ma <= (int32_t)BQ76922_TAPER_UPPER_MA;
    if (!taper) s->taper_pending=false;
    else if (!s->taper_pending) {s->taper_pending=true; s->taper_at=now;}
    else if (now-s->taper_at >= BQ76922_TAPER_HOLD_MS) {
        s->complete=true; s->taper_pending=false;
    }
    return !s->complete;
}
