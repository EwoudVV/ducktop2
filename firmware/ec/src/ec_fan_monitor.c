#include "ducktop2/ec/ec_fan_monitor.h"
#include <string.h>
void ec_fan_monitor_init(ec_fan_monitor_t *state) { memset(state, 0, sizeof(*state)); }
bool ec_fan_monitor_step(ec_fan_monitor_t *state, bool powered, uint8_t duty,
                         uint16_t fresh_rpm, uint32_t now_ms)
{
    if (state->failed) return false;
    bool required = powered && duty >= 30u;
    if (!required) { state->required=false; return true; }
    if (!state->required) {
        state->required=true; state->started_ms=now_ms; state->last_good_ms=now_ms;
    }
    if (fresh_rpm >= 300u) state->last_good_ms=now_ms;
    if (now_ms-state->started_ms >= 2000u && now_ms-state->last_good_ms >= 1000u)
        state->failed=true;
    return !state->failed;
}
