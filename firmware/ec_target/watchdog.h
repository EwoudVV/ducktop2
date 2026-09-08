#ifndef DUCKTOP2_WATCHDOG_H
#define DUCKTOP2_WATCHDOG_H
#include <stdint.h>

#define EC_WATCHDOG_PRESCALER_BITS 2u
#define EC_WATCHDOG_DIVIDER 16u
#define EC_WATCHDOG_RELOAD 624u

/* 312.5 ms at nominal 32 kHz LSI. */
static inline uint32_t ec_watchdog_timeout_ms(uint32_t lsi_hz)
{
    return lsi_hz ? ((EC_WATCHDOG_RELOAD + 1u) * EC_WATCHDOG_DIVIDER * 1000u
                     + lsi_hz - 1u) / lsi_hz : 0u;
}
void ec_watchdog_start(void);
void ec_watchdog_pet(void);
#endif
