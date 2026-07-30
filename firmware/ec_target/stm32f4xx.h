#ifndef STM32F4XX_H
#define STM32F4XX_H

#include <stdint.h>

#define __I  volatile const
#define __O  volatile
#define __IO volatile

#define PERIPH_BASE       0x40000000u
#define APB1PERIPH_BASE   PERIPH_BASE
#define APB2PERIPH_BASE   0x40010000u
#define AHB1PERIPH_BASE   0x40020000u
#define AHB2PERIPH_BASE   0x50000000u

typedef struct {
    __IO uint32_t MODER;
    __IO uint32_t OTYPER;
    __IO uint32_t OSPEEDR;
    __IO uint32_t PUPDR;
    __I  uint32_t IDR;
    __IO uint32_t ODR;
    __IO uint32_t BSRR;
    __IO uint32_t LCKR;
    __IO uint32_t AFRL;
    __IO uint32_t AFRH;
} GPIO_TypeDef;

#define GPIOA               ((GPIO_TypeDef *) 0x40020000u)
#define GPIOB               ((GPIO_TypeDef *) 0x40020400u)
#define GPIOC               ((GPIO_TypeDef *) 0x40020800u)
#define GPIOD               ((GPIO_TypeDef *) 0x40020C00u)
#define GPIOE               ((GPIO_TypeDef *) 0x40021000u)

#define GPIO_MODER_INPUT   0u
#define GPIO_MODER_OUTPUT  1u
#define GPIO_MODER_AF      2u
#define GPIO_MODER_ANALOG  3u

#define GPIO_OTYPER_PP     0u
#define GPIO_OTYPER_OD     1u

#define GPIO_OSPEEDR_LOW   0u
#define GPIO_OSPEEDR_MED   1u
#define GPIO_OSPEEDR_FAST  2u
#define GPIO_OSPEEDR_HIGH  3u

#define GPIO_PUPDR_NONE    0u
#define GPIO_PUPDR_PU      1u
#define GPIO_PUPDR_PD      2u

#define GPIO_AF0  0u
#define GPIO_AF1  1u
#define GPIO_AF2  2u
#define GPIO_AF3  3u
#define GPIO_AF4  4u
#define GPIO_AF5  5u
#define GPIO_AF6  6u
#define GPIO_AF7  7u
#define GPIO_AF8  8u
#define GPIO_AF9  9u
#define GPIO_AF10 10u
#define GPIO_AF11 11u
#define GPIO_AF12 12u
#define GPIO_AF13 13u
#define GPIO_AF14 14u
#define GPIO_AF15 15u

typedef struct {
    __IO uint32_t CR1;
    __IO uint32_t CR2;
    __IO uint32_t OAR1;
    __IO uint32_t OAR2;
    __IO uint32_t DR;
    __I  uint32_t SR1;
    __I  uint32_t SR2;
    __IO uint32_t CCR;
    __IO uint32_t TRISE;
    __IO uint32_t FLTR;
} I2C_TypeDef;

#define I2C1                ((I2C_TypeDef *) 0x40005400u)
#define I2C2                ((I2C_TypeDef *) 0x40005800u)

#define I2C_CR1_PE          (1u << 0)
#define I2C_CR1_SMBUS       (1u << 1)
#define I2C_CR1_START       (1u << 8)
#define I2C_CR1_STOP        (1u << 9)
#define I2C_CR1_ACK         (1u << 10)
#define I2C_CR1_POS         (1u << 11)
#define I2C_CR1_NOSTRETCH   (1u << 7)

#define I2C_CR2_FREQ_Msk    (0x3Fu << 0)
#define I2C_CR2_ITBUFEN     (1u << 10)
#define I2C_CR2_ITEVTEN     (1u << 9)
#define I2C_CR2_ITERREN     (1u << 8)

#define I2C_SR1_SB          (1u << 0)
#define I2C_SR1_ADDR        (1u << 1)
#define I2C_SR1_BTF         (1u << 2)
#define I2C_SR1_ADD10       (1u << 3)
#define I2C_SR1_STOPF       (1u << 4)
#define I2C_SR1_RXNE        (1u << 6)
#define I2C_SR1_TXE         (1u << 7)
#define I2C_SR1_BERR        (1u << 8)
#define I2C_SR1_ARLO        (1u << 9)
#define I2C_SR1_AF          (1u << 10)
#define I2C_SR1_OVR         (1u << 11)
#define I2C_SR1_TIMEOUT     (1u << 14)

#define I2C_SR2_MSL         (1u << 0)
#define I2C_SR2_BUSY        (1u << 1)
#define I2C_SR2_TRA         (1u << 2)

#define I2C_CCR_FS          (1u << 15)
#define I2C_CCR_DUTY        (1u << 14)

typedef struct {
    __IO uint32_t CR1;
    __IO uint32_t CR2;
    __IO uint32_t SMCR;
    __IO uint32_t DIER;
    __IO uint32_t SR;
    __IO uint32_t EGR;
    __IO uint32_t CCMR1;
    __IO uint32_t CCMR2;
    __IO uint32_t CCER;
    __IO uint32_t CNT;
    __IO uint32_t PSC;
    __IO uint32_t ARR;
    uint32_t  RESERVED0;
    __IO uint32_t CCR1;
    __IO uint32_t CCR2;
    __IO uint32_t CCR3;
    __IO uint32_t CCR4;
    uint32_t  RESERVED1;
    __IO uint32_t BDTR;
    __IO uint32_t DCR;
    __IO uint32_t DMAR;
} TIM_TypeDef;

#define TIM1                ((TIM_TypeDef *) 0x40010000u)
#define TIM2                ((TIM_TypeDef *) 0x40000000u)
#define TIM3                ((TIM_TypeDef *) 0x40000400u)

#define TIM_CR1_CEN         (1u << 0)
#define TIM_CR1_OPM         (1u << 3)
#define TIM_CR1_ARPE        (1u << 7)
#define TIM_CCER_CC1E       (1u << 0)
#define TIM_CCER_CC1P       (1u << 1)
#define TIM_CCER_CC1NE      (1u << 2)
#define TIM_CCER_CC1NP      (1u << 3)
#define TIM_BDTR_MOE        (1u << 15)
#define TIM_BDTR_AOE        (1u << 14)
#define TIM_EGR_UG          (1u << 0)

#define TIM_CCMR1_OC1M_PWM1 (6u << 4)
#define TIM_CCMR1_OC1M_PWM2 (7u << 4)
#define TIM_CCMR1_OC1PE     (1u << 3)

typedef struct {
    __IO uint32_t SR;
    __IO uint32_t CR1;
    __IO uint32_t CR2;
    __IO uint32_t SMPR1;
    __IO uint32_t SMPR2;
    __IO uint32_t JOFR1;
    __IO uint32_t JOFR2;
    __IO uint32_t JOFR3;
    __IO uint32_t JOFR4;
    __IO uint32_t HTR;
    __IO uint32_t LTR;
    __IO uint32_t SQR1;
    __IO uint32_t SQR2;
    __IO uint32_t SQR3;
    __IO uint32_t JSQR;
    __IO uint32_t JDR1;
    __IO uint32_t JDR2;
    __IO uint32_t JDR3;
    __IO uint32_t JDR4;
    __IO uint32_t DR;
} ADC_TypeDef;

typedef struct {
    uint32_t RESERVED0[4];
    __IO uint32_t CCR;
} ADC_Common_TypeDef;

#define ADC1                ((ADC_TypeDef *) 0x40012000u)
#define ADC1_COMMON         ((ADC_Common_TypeDef *) ADC1)

#define ADC_CR1_RES_12BIT   (0u << 24)
#define ADC_CR2_CONT        (1u << 1)
#define ADC_CR2_ADON        (1u << 0)
#define ADC_CR2_SWSTART     (1u << 30)
#define ADC_SR_EOC          (1u << 1)

typedef struct {
    __IO uint32_t ACR;
    __IO uint32_t KEYR;
    __IO uint32_t OPTKEYR;
    __IO uint32_t SR;
    __IO uint32_t CR;
    __IO uint32_t OPTCR;
} FLASH_TypeDef;

#define FLASH               ((FLASH_TypeDef *) 0x40023C00u)
#define FLASH_ACR_LATENCY_0WS  (0u << 0)
#define FLASH_ACR_LATENCY_1WS  (1u << 0)
#define FLASH_ACR_LATENCY_2WS  (2u << 0)
#define FLASH_ACR_LATENCY_3WS  (3u << 0)
#define FLASH_ACR_LATENCY_4WS  (4u << 0)
#define FLASH_ACR_LATENCY_5WS  (5u << 0)
#define FLASH_ACR_ICEN         (1u << 1)
#define FLASH_ACR_DCEN         (1u << 2)
#define FLASH_ACR_PRFTEN       (1u << 8)

typedef struct {
    __IO uint32_t CR;
    __IO uint32_t PLLCFGR;
    __IO uint32_t CFGR;
    __IO uint32_t CIR;
    __IO uint32_t AHB1RSTR;
    __IO uint32_t AHB2RSTR;
    uint32_t  RESERVED0[2];
    __IO uint32_t APB1RSTR;
    __IO uint32_t APB2RSTR;
    uint32_t  RESERVED1[2];
    __IO uint32_t AHB1ENR;
    __IO uint32_t AHB2ENR;
    uint32_t  RESERVED2[2];
    __IO uint32_t APB1ENR;
    __IO uint32_t APB2ENR;
    uint32_t  RESERVED3[2];
    __IO uint32_t AHB1LPENR;
    __IO uint32_t AHB2LPENR;
    uint32_t  RESERVED4[2];
    __IO uint32_t APB1LPENR;
    __IO uint32_t APB2LPENR;
    uint32_t  RESERVED5[2];
    __IO uint32_t BDCR;
    __IO uint32_t CSR;
    uint32_t  RESERVED6[2];
    __IO uint32_t SSCGR;
    __IO uint32_t PLLI2SCFGR;
    __IO uint32_t PLLSAICFGR;
    __IO uint32_t DCKCFGR;
} RCC_TypeDef;

#define RCC                 ((RCC_TypeDef *) 0x40023800u)

#define RCC_CR_HSEON        (1u << 16)
#define RCC_CR_HSERDY       (1u << 17)
#define RCC_CR_PLLON        (1u << 24)
#define RCC_CR_PLLRDY       (1u << 25)

#define RCC_PLLCFGR_PLLSRC_HSE  (1u << 22)
#define RCC_PLLCFGR_PLLM        (0x3Fu << 0)
#define RCC_PLLCFGR_PLLM_Pos    0u
#define RCC_PLLCFGR_PLLM_Msk    (0x3Fu << 0)
#define RCC_PLLCFGR_PLLN        (0x1FFu << 6)
#define RCC_PLLCFGR_PLLN_Pos    6u
#define RCC_PLLCFGR_PLLN_Msk    (0x1FFu << 6)
#define RCC_PLLCFGR_PLLP        (3u << 16)
#define RCC_PLLCFGR_PLLP_Pos    16u
#define RCC_PLLCFGR_PLLP_Msk    (3u << 16)
#define RCC_PLLCFGR_PLLQ        (0xFu << 24)
#define RCC_PLLCFGR_PLLQ_Pos    24u
#define RCC_PLLCFGR_PLLQ_Msk    (0xFu << 24)

#define RCC_CFGR_HPRE_Pos       4u
#define RCC_CFGR_PPRE1_Pos      10u
#define RCC_CFGR_PPRE2_Pos      13u

#define RCC_CFGR_SW            (3u << 0)
#define RCC_CFGR_SW_HSE        (1u << 0)
#define RCC_CFGR_SW_PLL        (2u << 0)
#define RCC_CFGR_SWS           (3u << 2)
#define RCC_CFGR_SWS_HSE       (1u << 2)
#define RCC_CFGR_SWS_PLL       (2u << 2)
#define RCC_CFGR_HPRE          (0xFu << 4)
#define RCC_CFGR_HPRE_1        (0u << 4)
#define RCC_CFGR_HPRE_DIV2     (8u << 4)
#define RCC_CFGR_PPRE1         (7u << 10)
#define RCC_CFGR_PPRE1_1       (0u << 10)
#define RCC_CFGR_PPRE1_2       (4u << 10)
#define RCC_CFGR_PPRE1_4       (5u << 10)
#define RCC_CFGR_PPRE1_8       (6u << 10)
#define RCC_CFGR_PPRE1_16      (7u << 10)
#define RCC_CFGR_PPRE2         (7u << 13)
#define RCC_CFGR_PPRE2_1       (0u << 13)
#define RCC_CFGR_PPRE2_2       (4u << 13)
#define RCC_CFGR_PPRE2_4       (5u << 13)
#define RCC_CFGR_PPRE2_8       (6u << 13)
#define RCC_CFGR_PPRE2_16      (7u << 13)

#define RCC_AHB1ENR_GPIOAEN   (1u << 0)
#define RCC_AHB1ENR_GPIOBEN   (1u << 1)
#define RCC_AHB1ENR_GPIOCEN   (1u << 2)
#define RCC_AHB1ENR_GPIODEN   (1u << 3)
#define RCC_AHB1ENR_GPIOEEN   (1u << 4)
#define RCC_AHB1ENR_DMA1EN    (1u << 21)
#define RCC_AHB1ENR_DMA2EN    (1u << 22)

#define RCC_APB1ENR_I2C1EN   (1u << 21)
#define RCC_APB1ENR_USART2EN (1u << 17)
#define RCC_APB1ENR_USART3EN (1u << 18)

#define RCC_APB2ENR_TIM1EN   (1u << 0)
#define RCC_APB2ENR_USART1EN (1u << 4)
#define RCC_APB2ENR_USART6EN (1u << 5)
#define RCC_APB2ENR_ADC1EN   (1u << 8)
#define RCC_APB2ENR_SYSCFGEN (1u << 14)

typedef struct {
    __IO uint32_t IMR;
    __IO uint32_t EMR;
    __IO uint32_t RTSR;
    __IO uint32_t FTSR;
    __IO uint32_t SWIER;
    __IO uint32_t PR;
} EXTI_TypeDef;

typedef struct {
    __IO uint32_t MEMRMP;
    __IO uint32_t PMC;
    __IO uint32_t EXTICR[4];
    uint32_t  RESERVED0[2];
    __IO uint32_t CMPCR;
} SYSCFG_TypeDef;

#define SYSCFG              ((SYSCFG_TypeDef *) 0x40013800u)
#define EXTI                ((EXTI_TypeDef *) 0x40013C00u)

typedef struct {
    __IO uint32_t CTRL;
    __IO uint32_t LOAD;
    __IO uint32_t VAL;
    __I  uint32_t CALIB;
} SysTick_Type;

#define SysTick             ((SysTick_Type *) 0xE000E010u)

#define SysTick_CTRL_ENABLE     (1u << 0)
#define SysTick_CTRL_TICKINT    (1u << 1)
#define SysTick_CTRL_CLKSOURCE  (1u << 2)
#define SysTick_CTRL_COUNTFLAG  (1u << 16)

typedef struct {
    __I  uint32_t CPUID;
    __IO uint32_t ICSR;
    __IO uint32_t VTOR;
    __IO uint32_t AIRCR;
    __IO uint32_t SCR;
    __IO uint32_t CCR;
    __I  uint32_t SHP[3];
    __IO uint32_t SHCSR;
    __IO uint32_t CFSR;
    __IO uint32_t HFSR;
    __IO uint32_t DFSR;
    __IO uint32_t MMFAR;
    __IO uint32_t BFAR;
    __IO uint32_t AFSR;
} SCB_Type;

#define SCB                 ((SCB_Type *) 0xE000ED00u)

#define SCB_CPACR            (*((__IO uint32_t *)0xE000ED88u))

#define SCB_AIRCR_VECTKEY   (0x5FAu << 16)
#define SCB_AIRCR_SYSRESETREQ (1u << 2)

#define NVIC_ISER0          (*((__IO uint32_t *)0xE000E100u))
#define NVIC_ISER1          (*((__IO uint32_t *)0xE000E104u))
#define NVIC_ISER2          (*((__IO uint32_t *)0xE000E108u))
#define NVIC_ISER3          (*((__IO uint32_t *)0xE000E10Cu))
#define NVIC_ICER0          (*((__IO uint32_t *)0xE000E180u))
#define NVIC_ICER1          (*((__IO uint32_t *)0xE000E184u))
#define NVIC_ICER2          (*((__IO uint32_t *)0xE000E188u))
#define NVIC_ICER3          (*((__IO uint32_t *)0xE000E18Cu))
#define NVIC_IPR_BASE       0xE000E400u

typedef struct {
    __IO uint32_t KR;
    __IO uint32_t PR;
    __IO uint32_t RLR;
    __IO uint32_t SR;
} IWDG_TypeDef;

#define IWDG                ((IWDG_TypeDef *) 0x40003000u)

#define IWDG_KR_KEY_RELOAD  0xAAAAu
#define IWDG_KR_KEY_ENABLE  0xCCCCu
#define IWDG_KR_KEY_ACCESS  0x5555u
#define IWDG_PR_DIV4        0u
#define IWDG_PR_DIV8        1u
#define IWDG_PR_DIV16       2u
#define IWDG_PR_DIV32       3u
#define IWDG_PR_DIV64       4u
#define IWDG_PR_DIV128      5u
#define IWDG_PR_DIV256      6u

void SystemInit(void);
void SystemCoreClockUpdate(void);
uint32_t GetTick(void);
void DelayMs(uint32_t ms);

extern uint32_t _estack;
extern uint32_t _sdata;
extern uint32_t _edata;
extern uint32_t _sbss;
extern uint32_t _ebss;

#endif
