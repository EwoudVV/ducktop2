#ifndef DUCKTOP2_EC_FAN_MONITOR_H
#define DUCKTOP2_EC_FAN_MONITOR_H
#include <stdbool.h>
#include <stdint.h>
typedef struct { bool required, failed; uint32_t started_ms, last_good_ms; } ec_fan_monitor_t;
void ec_fan_monitor_init(ec_fan_monitor_t *state);
bool ec_fan_monitor_step(ec_fan_monitor_t *state, bool powered, uint8_t duty,
                         uint16_t fresh_rpm, uint32_t now_ms);
#endif
