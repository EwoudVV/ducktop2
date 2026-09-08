#include "watchdog.h"
#include "stm32f4xx.h"

_Static_assert(EC_WATCHDOG_DIVIDER == (4u << EC_WATCHDOG_PRESCALER_BITS),
               "watchdog divider must match the hardware encoding");
_Static_assert(EC_WATCHDOG_RELOAD <= 4095u, "watchdog reload is 12 bits");

void ec_watchdog_start(void)
{
    IWDG->KR = IWDG_KR_KEY_ENABLE;
    IWDG->KR = IWDG_KR_KEY_ACCESS;
    IWDG->PR = EC_WATCHDOG_PRESCALER_BITS;
    IWDG->RLR = EC_WATCHDOG_RELOAD;
    for (uint32_t attempts = 0; attempts < 100000u; ++attempts) {
        if (IWDG->SR == 0) {
            ec_watchdog_pet();
            return;
        }
    }
    /* The watchdog is already running if its configuration never settles. */
    for (;;) __WFI();
}

void ec_watchdog_pet(void)
{
    IWDG->KR = IWDG_KR_KEY_RELOAD;
}
