#ifndef DUCKTOP2_SOURCE_PATHS_H
#define DUCKTOP2_SOURCE_PATHS_H
#include "ducktop2/ec/ec_policy.h"
#include <stdbool.h>
#include <stdint.h>

typedef struct {
    uint8_t port0, port1, control;
    bool valid, all_off, pd_good[2], aux_good;
} source_paths_state_t;

bool source_paths_init(void);
bool source_paths_read(source_paths_state_t *state, uint32_t now_ms);
bool source_paths_set(ec_source_id_t source, bool enable, uint16_t voltage_mv,
                      uint32_t now_ms);
#endif
