#include "stm32f4xx.h"

#define PLL_M 8
#define PLL_N 336
#define PLL_P 2
#define PLL_Q 7

static uint32_t SystemCoreClock = 16000000;

void SystemCoreClockUpdate(void)
{
    uint32_t pllm, plln, pllp, hse;
    uint32_t sysclk;

    if ((RCC->CFGR & RCC_CFGR_SWS) == RCC_CFGR_SWS_PLL) {
        hse = HSE_VALUE;
        pllm = ((RCC->PLLCFGR & RCC_PLLCFGR_PLLM) >> RCC_PLLCFGR_PLLM_Pos) + 1;
        plln = (RCC->PLLCFGR & RCC_PLLCFGR_PLLN) >> RCC_PLLCFGR_PLLN_Pos;
        pllp = (((RCC->PLLCFGR & RCC_PLLCFGR_PLLP) >> RCC_PLLCFGR_PLLP_Pos) * 2) + 2;
        sysclk = (hse / pllm * plln) / pllp;
    } else if ((RCC->CFGR & RCC_CFGR_SWS) == RCC_CFGR_SWS_HSE) {
        sysclk = HSE_VALUE;
    } else {
        sysclk = 16000000;
    }
    SystemCoreClock = sysclk;

    uint32_t hpre = (RCC->CFGR & RCC_CFGR_HPRE) >> RCC_CFGR_HPRE_Pos;
    uint32_t ahb_prescaler = 1;
    if (hpre >= 8 && hpre < 10) ahb_prescaler = 2;
    else if (hpre >= 10 && hpre < 12) ahb_prescaler = 4;
    else if (hpre >= 12 && hpre < 14) ahb_prescaler = 8;
    else if (hpre >= 14 && hpre < 15) ahb_prescaler = 16;
    else if (hpre >= 15) ahb_prescaler = 64;
    SystemCoreClock /= ahb_prescaler;
}

static void systick_config(uint32_t reload)
{
    SysTick->LOAD = reload - 1;
    SysTick->VAL = 0;
    SysTick->CTRL = SysTick_CTRL_ENABLE | SysTick_CTRL_TICKINT | SysTick_CTRL_CLKSOURCE;
}

void SystemInit(void)
{
    SCB_CPACR |= ((3u << 10*2) | (3u << 11*2));

    RCC->CR |= RCC_CR_HSEON;
    while (!(RCC->CR & RCC_CR_HSERDY));

    RCC->PLLCFGR = (PLL_M - 1) << RCC_PLLCFGR_PLLM_Pos
                 | PLL_N << RCC_PLLCFGR_PLLN_Pos
                 | ((PLL_P / 2 - 1) & 3u) << RCC_PLLCFGR_PLLP_Pos
                 | PLL_Q << RCC_PLLCFGR_PLLQ_Pos
                 | RCC_PLLCFGR_PLLSRC_HSE;

    FLASH->ACR = FLASH_ACR_LATENCY_5WS
               | FLASH_ACR_ICEN
               | FLASH_ACR_DCEN
               | FLASH_ACR_PRFTEN;

    RCC->CFGR = RCC_CFGR_HPRE_1
              | RCC_CFGR_PPRE1_2
              | RCC_CFGR_PPRE2_1;

    RCC->CR |= RCC_CR_PLLON;
    while (!(RCC->CR & RCC_CR_PLLRDY));

    RCC->CFGR = (RCC->CFGR & ~RCC_CFGR_SW) | RCC_CFGR_SW_PLL;
    while ((RCC->CFGR & RCC_CFGR_SWS) != RCC_CFGR_SWS_PLL);

    SystemCoreClockUpdate();

    systick_config(SystemCoreClock / 1000);
}
