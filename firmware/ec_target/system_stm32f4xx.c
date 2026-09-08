#include "stm32f4xx.h"
#include "watchdog.h"
#include <stdbool.h>

#define PLL_M 8u
#define PLL_N 336u
#define PLL_P 2u
#define PLL_Q 7u
#define SYSCLK_HZ ((HSE_VALUE / PLL_M) * PLL_N / PLL_P)
#define USBCLK_HZ ((HSE_VALUE / PLL_M) * PLL_N / PLL_Q)

_Static_assert(SYSCLK_HZ == 168000000u, "SYSCLK must be 168 MHz");
_Static_assert(USBCLK_HZ == 48000000u, "USB clock must be 48 MHz");

uint32_t SystemCoreClock = 16000000u;
const uint8_t AHBPrescTable[16] = {0, 0, 0, 0, 0, 0, 0, 0, 1, 2, 3, 4, 6, 7, 8, 9};
const uint8_t APBPrescTable[8] = {0, 0, 0, 0, 1, 2, 3, 4};

void SystemCoreClockUpdate(void)
{
    uint32_t source = RCC->CFGR & RCC_CFGR_SWS;
    uint32_t clock = 16000000u;
    if (source == RCC_CFGR_SWS_PLL) {
        uint32_t input = (RCC->PLLCFGR & RCC_PLLCFGR_PLLSRC_HSE) ? HSE_VALUE : 16000000u;
        uint32_t m = (RCC->PLLCFGR & RCC_PLLCFGR_PLLM) >> RCC_PLLCFGR_PLLM_Pos;
        uint32_t n = (RCC->PLLCFGR & RCC_PLLCFGR_PLLN) >> RCC_PLLCFGR_PLLN_Pos;
        uint32_t p = 2u * (1u + ((RCC->PLLCFGR & RCC_PLLCFGR_PLLP) >> RCC_PLLCFGR_PLLP_Pos));
        if (m == 0) { SystemCoreClock = 0; return; }
        clock = (input / m * n) / p;
    } else if (source == RCC_CFGR_SWS_HSE) {
        clock = HSE_VALUE;
    }
    uint32_t divider = (RCC->CFGR & RCC_CFGR_HPRE) >> RCC_CFGR_HPRE_Pos;
    SystemCoreClock = clock >> AHBPrescTable[divider];
}

static bool clock_wait(volatile uint32_t *reg, uint32_t mask, uint32_t value)
{
    for (uint32_t attempts = 0; attempts < 100000u; ++attempts)
        if ((*reg & mask) == value) return true;
    return false;
}

static void clock_failed(void)
{
    /* Leave the hardware in its reset state and let the watchdog recover. */
    for (;;) __WFI();
}

void SystemInit(void)
{
    ec_watchdog_start();
    SCB->CPACR |= (0xFu << 20);
    __DSB();
    __ISB();
    RCC->CR |= RCC_CR_HSEON;
    if (!clock_wait(&RCC->CR, RCC_CR_HSERDY, RCC_CR_HSERDY)) clock_failed();
    RCC->APB1ENR |= RCC_APB1ENR_PWREN;
    (void)RCC->APB1ENR;
    PWR->CR |= PWR_CR_VOS;
    RCC->PLLCFGR = PLL_M << RCC_PLLCFGR_PLLM_Pos
                  | PLL_N << RCC_PLLCFGR_PLLN_Pos
                  | ((PLL_P / 2u - 1u) << RCC_PLLCFGR_PLLP_Pos)
                  | PLL_Q << RCC_PLLCFGR_PLLQ_Pos | RCC_PLLCFGR_PLLSRC_HSE;
    FLASH->ACR = FLASH_ACR_LATENCY_5WS | FLASH_ACR_ICEN | FLASH_ACR_DCEN | FLASH_ACR_PRFTEN;
    if (!clock_wait(&FLASH->ACR, FLASH_ACR_LATENCY, FLASH_ACR_LATENCY_5WS)) clock_failed();
    RCC->CFGR = RCC_CFGR_HPRE_DIV1 | RCC_CFGR_PPRE1_DIV4 | RCC_CFGR_PPRE2_DIV2;
    RCC->CR |= RCC_CR_PLLON;
    if (!clock_wait(&RCC->CR, RCC_CR_PLLRDY, RCC_CR_PLLRDY)) clock_failed();
    RCC->CFGR = (RCC->CFGR & ~RCC_CFGR_SW) | RCC_CFGR_SW_PLL;
    if (!clock_wait(&RCC->CFGR, RCC_CFGR_SWS, RCC_CFGR_SWS_PLL)) clock_failed();
    SystemCoreClockUpdate();
    if (SystemCoreClock != SYSCLK_HZ) clock_failed();
    SysTick->LOAD = SystemCoreClock / 1000u - 1u;
    SysTick->VAL = 0;
    SysTick->CTRL = SysTick_CTRL_ENABLE_Msk | SysTick_CTRL_TICKINT_Msk | SysTick_CTRL_CLKSOURCE_Msk;
    ec_watchdog_pet();
}
