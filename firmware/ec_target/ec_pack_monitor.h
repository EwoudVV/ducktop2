#ifndef DUCKTOP2_EC_PACK_MONITOR_H
#define DUCKTOP2_EC_PACK_MONITOR_H
#include "bq76922.h"
void ec_pack_monitor_init(void);
void ec_pack_monitor_set_ready(bool valid, bool ready, uint32_t now_ms);
void ec_pack_monitor_poll(uint32_t now_ms);
bool ec_pack_monitor_discharge_allowed(uint32_t now_ms, uint16_t total_request_ma);
bool ec_pack_monitor_charge_allowed(uint32_t now_ms, uint16_t request_ma);
bool ec_pack_monitor_charge_step(uint32_t now_ms, bool charger_valid, uint32_t charger_at,
                                 bool cv_active, bool charge_enabled);
bool ec_pack_monitor_charge_complete(void);
bool ec_pack_monitor_current(uint32_t now_ms, int32_t *current_ma);
const bq76922_sample_t *ec_pack_monitor_sample(void);
#endif
