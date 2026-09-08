#ifndef DUCKTOP2_MAKER_BUS_TARGET_H
#define DUCKTOP2_MAKER_BUS_TARGET_H
#include "ducktop2/maker/maker_bus.h"
/* guard must remain true throughout the operation; all borrowed pins return
 * to inputs with no pulls before this function returns, including errors. */
maker_bus_result_t maker_bus_target_execute(const maker_bus_request_t *request,
    bool (*guard)(void),uint8_t *rx,uint8_t *received,uint32_t *actual_rate);
void maker_bus_target_abort(void);
#endif
