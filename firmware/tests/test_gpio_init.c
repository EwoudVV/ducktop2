/* Run the actual GPIO setup against RAM registers using the pinned ST types. */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "stm32f4xx.h"

static GPIO_TypeDef ports[5];
static RCC_TypeDef clock_regs;
static ADC_TypeDef adc_regs;
static ADC_Common_TypeDef adc_common_regs;
static TIM_TypeDef timer_regs[2];
static SYSCFG_TypeDef syscfg_regs;
static EXTI_TypeDef exti_regs;
static NVIC_Type nvic_regs;

#undef GPIOA
#undef GPIOB
#undef GPIOC
#undef GPIOD
#undef GPIOE
#undef RCC
#undef ADC1
#undef ADC1_COMMON
#undef TIM1
#undef TIM2
#undef SYSCFG
#undef EXTI
#undef NVIC
#define GPIOA (&ports[0])
#define GPIOB (&ports[1])
#define GPIOC (&ports[2])
#define GPIOD (&ports[3])
#define GPIOE (&ports[4])
#define RCC (&clock_regs)
#define ADC1 (&adc_regs)
#define ADC1_COMMON (&adc_common_regs)
#define TIM1 (&timer_regs[0])
#define TIM2 (&timer_regs[1])
#define SYSCFG (&syscfg_regs)
#define EXTI (&exti_regs)
#define NVIC (&nvic_regs)

#include "../ec_target/gpio.c"

uint32_t GetTick(void) { return 0u; }
void DelayMs(uint32_t ms) { (void)ms; }

static void check_startup(void)
{
    gpio_init_all();
    /* Status inputs must not load their external bias networks. */
    assert(((GPIOE->PUPDR >> 28) & 15u) == 0u);
    assert(((GPIOE->MODER >> 28) & 15u) == 0u);
    assert(((GPIOE->MODER >> 26) & 3u) == GPIO_MODER_OUTPUT);
    assert((GPIOE->ODR & (1u << 13)) == 0u);
    assert((GPIOA->ODR & ((1u << 3) | (1u << 4))) == 0u);
    assert(((GPIOA->MODER >> 26) & 15u) == 10u); /* SWD survives. */
}

int main(void)
{
    memset(ports, 0, sizeof ports);
    check_startup();
    /* Also clear pulls left by a bootloader or an earlier initialization. */
    GPIOE->PUPDR |= (GPIO_PUPDR_PD << 30) | (GPIO_PUPDR_PU << 28);
    check_startup();
    GPIOE->PUPDR |= (GPIO_PUPDR_PU << 30) | (GPIO_PUPDR_PD << 28);
    check_startup();
    puts("GPIO startup: status inputs, power defaults and repeat initialization pass");
    return 0;
}
