#ifndef DUCKTOP2_STM32F4XX_H
#define DUCKTOP2_STM32F4XX_H

/* Register layouts and bit definitions come from ST's pinned device header. */
#include "stm32f407xx.h"

uint32_t GetTick(void);
void DelayMs(uint32_t ms);

#define GPIO_MODER_INPUT 0u
#define GPIO_MODER_OUTPUT 1u
#define GPIO_MODER_AF 2u
#define GPIO_MODER_ANALOG 3u
#define GPIO_OTYPER_PP 0u
#define GPIO_OTYPER_OD 1u
#define GPIO_OSPEEDR_HIGH 3u
#define GPIO_PUPDR_NONE 0u
#define GPIO_PUPDR_PU 1u
#define GPIO_PUPDR_PD 2u
#define GPIO_AF0 0u
#define GPIO_AF1 1u
#define GPIO_AF4 4u
#define GPIO_AF7 7u
#define GPIO_AF8 8u
#define GPIO_AF10 10u

#define TIM_CCMR1_OC1M_PWM1 (6u << TIM_CCMR1_OC1M_Pos)
#define ADC_CCR_ADCPRE_DIV4 ADC_CCR_ADCPRE_0
#define ADC1_COMMON ADC123_COMMON
#define SysTick_CTRL_ENABLE SysTick_CTRL_ENABLE_Msk
#define SysTick_CTRL_TICKINT SysTick_CTRL_TICKINT_Msk
#define SysTick_CTRL_CLKSOURCE SysTick_CTRL_CLKSOURCE_Msk
#define SCB_CPACR (SCB->CPACR)
#define NVIC_ISER0 (NVIC->ISER[0])
#define NVIC_IPR(irqn) (NVIC->IP[(irqn)])

#define IWDG_KR_KEY_RELOAD 0xAAAAu
#define IWDG_KR_KEY_ENABLE 0xCCCCu
#define IWDG_KR_KEY_ACCESS 0x5555u
#define IWDG_PR_DIV4 0u
#define IWDG_PR_DIV8 1u
#define IWDG_PR_DIV16 2u
#define IWDG_PR_DIV32 3u
#define IWDG_PR_DIV64 4u
#define IWDG_PR_DIV128 5u
#define IWDG_PR_DIV256 6u

#endif
