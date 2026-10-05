#ifndef DUCKTOP2_BQ76922_CHARGE_H
#define DUCKTOP2_BQ76922_CHARGE_H
#include "bq76922.h"
typedef struct {
    bool complete, fault_latched, cv_counting, taper_pending, recharge_pending;
    uint32_t cv_dwell_ms, cv_at, taper_at, recharge_at, last_good_at;
    bool had_good;
} bq76922_charge_state_t;
void bq76922_charge_init(bq76922_charge_state_t *);
bool bq76922_charge_step(bq76922_charge_state_t *, const bq76922_t *, uint32_t now_ms,
    bool ready, bool ready_valid, uint32_t ready_at, bool charger_valid,
    uint32_t charger_at, uint16_t charger_target_mv, bool cv_active, bool charge_enabled);
#endif
