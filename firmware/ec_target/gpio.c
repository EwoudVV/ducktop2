#include "gpio.h"
#include "stm32f4xx.h"

void gpio_init_all(void)
{
    RCC->AHB1ENR |= RCC_AHB1ENR_GPIOAEN | RCC_AHB1ENR_GPIOBEN
                  | RCC_AHB1ENR_GPIOCEN | RCC_AHB1ENR_GPIODEN
                  | RCC_AHB1ENR_GPIOEEN;

    GPIOA->MODER = 0;
    GPIOB->MODER = 0;
    GPIOC->MODER = 0;
    GPIOD->MODER = 0;
    GPIOE->MODER = 0;

    /* ---- Port A ---- */

    /* PA0: MU_PWRBTN_N - Output, open-drain, high (inactive) */
    GPIOA->MODER   |= GPIO_MODER_OUTPUT << (0 * 2);
    GPIOA->OTYPER  |= GPIO_OTYPER_OD << 0;
    GPIOA->PUPDR   |= GPIO_PUPDR_PU << (0 * 2);
    GPIOA->ODR     |= 1u << 0;

    /* PA1: BQ_ALERT - Input, pull-up */
    GPIOA->PUPDR   |= GPIO_PUPDR_PU << (1 * 2);

    /* PA2: CHG_INT_N - Input, pull-up */
    GPIOA->PUPDR   |= GPIO_PUPDR_PU << (2 * 2);

    /* PA3: PMIC_QON_ASSERT - Output, push-pull, low */
    GPIOA->MODER   |= GPIO_MODER_OUTPUT << (3 * 2);

    /* PA4: CHG_ENABLE - Output, push-pull, low (charger off) */
    GPIOA->MODER   |= GPIO_MODER_OUTPUT << (4 * 2);

    /* PA5: MU_RSTBTN_N - Output, open-drain, high (inactive) */
    GPIOA->MODER   |= GPIO_MODER_OUTPUT << (5 * 2);
    GPIOA->OTYPER  |= GPIO_OTYPER_OD << 5;
    GPIOA->ODR     |= 1u << 5;

    /* PA6: AUX_DC_ADC - Analog */
    GPIOA->MODER   |= GPIO_MODER_ANALOG << (6 * 2);

    /* PA7: THERM_SKIN_ADC - Analog */
    GPIOA->MODER   |= GPIO_MODER_ANALOG << (7 * 2);

    /* PA8: WIFI_W_DISABLE1_N_EC - Output, push-pull, high (disabled) */
    GPIOA->MODER   |= GPIO_MODER_OUTPUT << (8 * 2);
    GPIOA->ODR     |= 1u << 8;

    /* PA9: GNSS_UART_TX - AF7 (USART1) */
    GPIOA->MODER   |= GPIO_MODER_AF << (9 * 2);
    GPIOA->AFRH     = (GPIOA->AFRH & ~(0xFu << 4)) | (GPIO_AF7 << 4);

    /* PA10: GNSS_UART_RX - AF7 (USART1) */
    GPIOA->MODER   |= GPIO_MODER_AF << (10 * 2);
    GPIOA->AFRH     = (GPIOA->AFRH & ~(0xFu << 8)) | (GPIO_AF7 << 8);

    /* PA11: MCU_USB_DM - AF10 (OTG_FS) */
    GPIOA->MODER   |= GPIO_MODER_AF << (11 * 2);
    GPIOA->AFRH     = (GPIOA->AFRH & ~(0xFu << 12)) | (GPIO_AF10 << 12);

    /* PA12: MCU_USB_DP - AF10 (OTG_FS) */
    GPIOA->MODER   |= GPIO_MODER_AF << (12 * 2);
    GPIOA->AFRH     = (GPIOA->AFRH & ~(0xFu << 16)) | (GPIO_AF10 << 16);

    /* PA13: SWDIO - leave as default (AF0, pull-up) */

    /* PA14: SWCLK - leave as default (AF0, pull-down) */

    /* PA15: WIFI_W_DISABLE2_N_EC - Output, push-pull, high (disabled) */
    GPIOA->MODER   |= GPIO_MODER_OUTPUT << (15 * 2);
    GPIOA->ODR     |= 1u << 15;

    /* ---- Port B ---- */

    /* PB0: THERM_MU_ADC - Analog */
    GPIOB->MODER   |= GPIO_MODER_ANALOG << (0 * 2);

    /* PB1: TRACKPAD_FAULT_N - Input, pull-up */
    GPIOB->PUPDR   |= GPIO_PUPDR_PU << (1 * 2);

    /* PB2: PD2_VALID_N - Input, pull-up */
    GPIOB->PUPDR   |= GPIO_PUPDR_PU << (2 * 2);

    /* PB3: (JTDO/SWO) - leave as default */

    /* PB4: PD2_TCPC_IRQ_N - Input, pull-up */
    GPIOB->PUPDR   |= GPIO_PUPDR_PU << (4 * 2);

    /* PB5: RADIO_DB_PWR_EN - Output, push-pull, low (off) */
    GPIOB->MODER   |= GPIO_MODER_OUTPUT << (5 * 2);

    /* PB6: I2C1_SCL - AF4 */
    GPIOB->MODER   |= GPIO_MODER_AF << (6 * 2);
    GPIOB->OTYPER  |= GPIO_OTYPER_OD << 6;
    GPIOB->PUPDR   |= GPIO_PUPDR_PU << (6 * 2);
    GPIOB->OSPEEDR |= GPIO_OSPEEDR_HIGH << (6 * 2);
    GPIOB->AFRL     = (GPIOB->AFRL & ~(0xFu << 24)) | (GPIO_AF4 << 24);

    /* PB7: I2C1_SDA - AF4 */
    GPIOB->MODER   |= GPIO_MODER_AF << (7 * 2);
    GPIOB->OTYPER  |= GPIO_OTYPER_OD << 7;
    GPIOB->PUPDR   |= GPIO_PUPDR_PU << (7 * 2);
    GPIOB->OSPEEDR |= GPIO_OSPEEDR_HIGH << (7 * 2);
    GPIOB->AFRL     = (GPIOB->AFRL & ~(0xFu << 28)) | (GPIO_AF4 << 28);

    /* PB8: GNSS_EXTINT - Input, pull-down */
    GPIOB->PUPDR   |= GPIO_PUPDR_PD << (8 * 2);

    /* PB9: PD_PROTECT_FAULT_N - Input, pull-up */
    GPIOB->PUPDR   |= GPIO_PUPDR_PU << (9 * 2);

    /* PB10: RADIO_VHF_UART_TX - AF7 (USART3) */
    GPIOB->MODER   |= GPIO_MODER_AF << (10 * 2);
    GPIOB->AFRH     = (GPIOB->AFRH & ~(0xFu << 8)) | (GPIO_AF7 << 8);

    /* PB11: RADIO_VHF_UART_RX - AF7 (USART3) */
    GPIOB->MODER   |= GPIO_MODER_AF << (11 * 2);
    GPIOB->AFRH     = (GPIOB->AFRH & ~(0xFu << 12)) | (GPIO_AF7 << 12);

    /* PB12: SERVICE_MUX_RESET_REQ_N - Output, push-pull, low (reset held) */
    GPIOB->MODER   |= GPIO_MODER_OUTPUT << (12 * 2);

    /* PB13: GNSS_RESET_N - Output, push-pull, low (reset asserted) */
    GPIOB->MODER   |= GPIO_MODER_OUTPUT << (13 * 2);

    /* PB14: GNSS_PPS - Input, pull-down */
    GPIOB->PUPDR   |= GPIO_PUPDR_PD << (14 * 2);

    /* PB15: RADIO_VHF_PTT_N - Output, push-pull, high (inactive) */
    GPIOB->MODER   |= GPIO_MODER_OUTPUT << (15 * 2);
    GPIOB->ODR     |= 1u << 15;

    /* ---- Port C ---- */

    /* PC0: KB_RGB_PWR_EN - Output, push-pull, low (off) */
    GPIOC->MODER   |= GPIO_MODER_OUTPUT << (0 * 2);

    /* PC1: KB_RGB_FAULT_N - Input, pull-up */
    GPIOC->PUPDR   |= GPIO_PUPDR_PU << (1 * 2);

    /* PC2: RADIO_VHF_RF_SEL_3V3 - Output, push-pull, low */
    GPIOC->MODER   |= GPIO_MODER_OUTPUT << (2 * 2);

    /* PC3: RADIO_UHF_RF_SEL_3V3 - Output, push-pull, low */
    GPIOC->MODER   |= GPIO_MODER_OUTPUT << (3 * 2);

    /* PC4: PD1_VALID_N - Input, pull-up */
    GPIOC->PUPDR   |= GPIO_PUPDR_PU << (4 * 2);

    /* PC5: FAN_TACH - Input, pull-down */
    GPIOC->PUPDR   |= GPIO_PUPDR_PD << (5 * 2);

    /* PC6: RADIO_UHF_UART_TX - AF8 (USART6) */
    GPIOC->MODER   |= GPIO_MODER_AF << (6 * 2);
    GPIOC->AFRL     = (GPIOC->AFRL & ~(0xFu << 24)) | (GPIO_AF8 << 24);

    /* PC7: RADIO_UHF_UART_RX - AF8 (USART6) */
    GPIOC->MODER   |= GPIO_MODER_AF << (7 * 2);
    GPIOC->AFRL     = (GPIOC->AFRL & ~(0xFu << 28)) | (GPIO_AF8 << 28);

    /* PC8: RADIO_UHF_PTT_N - Output, push-pull, high (inactive) */
    GPIOC->MODER   |= GPIO_MODER_OUTPUT << (8 * 2);
    GPIOC->ODR     |= 1u << 8;

    /* PC9: RADIO_VHF_PD_N - Output, push-pull, high (inactive) */
    GPIOC->MODER   |= GPIO_MODER_OUTPUT << (9 * 2);
    GPIOC->ODR     |= 1u << 9;

    /* PC10: RADIO_UHF_PD_N - Output, push-pull, high (inactive) */
    GPIOC->MODER   |= GPIO_MODER_OUTPUT << (10 * 2);
    GPIOC->ODR     |= 1u << 10;

    /* PC11: RADIO_VHF_SQL - Input, pull-down */
    GPIOC->PUPDR   |= GPIO_PUPDR_PD << (11 * 2);

    /* PC12: RADIO_UHF_SQL - Input, pull-down */
    GPIOC->PUPDR   |= GPIO_PUPDR_PD << (12 * 2);

    /* PC13: SOURCE_MGR_INT_N - Input, pull-up */
    GPIOC->PUPDR   |= GPIO_PUPDR_PU << (13 * 2);

    /* PC14: LSE_IN - leave as default for LSE */
    /* PC15: LSE_OUT - leave as default for LSE */

    /* ---- Port D - Keyboard Columns ---- */

    for (int i = 0; i <= 15; i++) {
        GPIOD->MODER |= GPIO_MODER_INPUT << (i * 2);
        GPIOD->PUPDR |= GPIO_PUPDR_PD << (i * 2);
    }

    /* ---- Port E ---- */

    /* PE0-PE7: Keyboard rows - Output, push-pull, low */
    for (int i = 0; i <= 7; i++) {
        GPIOE->MODER |= GPIO_MODER_OUTPUT << (i * 2);
    }

    /* PE8: PD1_TCPC_IRQ_N - Input, pull-up */
    GPIOE->PUPDR   |= GPIO_PUPDR_PU << (8 * 2);

    /* PE9: FAN_PWM - AF1 (TIM1_CH1) */
    GPIOE->MODER   |= GPIO_MODER_AF << (9 * 2);
    GPIOE->AFRH     = (GPIOE->AFRH & ~(0xFu << 4)) | (GPIO_AF1 << 4);

    /* PE10: LID_CLOSED_N - Input, pull-up */
    GPIOE->PUPDR   |= GPIO_PUPDR_PU << (10 * 2);

    /* PE11: AUDIO_MIC_EN - Output, push-pull, low (off) */
    GPIOE->MODER   |= GPIO_MODER_OUTPUT << (11 * 2);

    /* PE12: AUDIO_AMP_EC_EN - Output, push-pull, low (off) */
    GPIOE->MODER   |= GPIO_MODER_OUTPUT << (12 * 2);

    /* PE13: MU_12V_ENABLE - Output, push-pull, low (off) */
    GPIOE->MODER   |= GPIO_MODER_OUTPUT << (13 * 2);

    /* PE14: MU_S0_HIGH - Input, pull-down */
    GPIOE->PUPDR   |= GPIO_PUPDR_PD << (14 * 2);

    /* PE15: MU_12V_PG - Input, pull-down */
    GPIOE->PUPDR   |= GPIO_PUPDR_PD << (15 * 2);
}

void gpio_set_pd_path_enable_a(bool enable)
{
    (void)enable;
    /* PD1_PATH_EN is driven through TCA9539 (source manager), not a direct GPIO.
     * Actual control via i2c.c tca9539_write_register(). */
}

void gpio_set_pd_path_enable_b(bool enable)
{
    (void)enable;
    /* PD2_PATH_EN is driven through TCA9539. */
}

bool gpio_get_pd1_valid_n(void)
{
    return (GPIOC->IDR & (1u << 4)) ? true : false;
}

bool gpio_get_pd2_valid_n(void)
{
    return (GPIOB->IDR & (1u << 2)) ? true : false;
}

bool gpio_get_pd1_tcpc_irq_n(void)
{
    return (GPIOE->IDR & (1u << 8)) ? true : false;
}

bool gpio_get_pd2_tcpc_irq_n(void)
{
    return (GPIOB->IDR & (1u << 4)) ? true : false;
}

bool gpio_get_pd_protect_fault_n(void)
{
    return (GPIOB->IDR & (1u << 9)) ? true : false;
}

void gpio_set_charger_enable(bool enable)
{
    if (enable) {
        GPIOA->BSRR = (1u << 4);
    } else {
        GPIOA->BSRR = (1u << (4 + 16));
    }
}

void gpio_set_pmic_qon_assert(bool assert)
{
    if (assert) {
        GPIOA->BSRR = (1u << 3);
    } else {
        GPIOA->BSRR = (1u << (3 + 16));
    }
}

bool gpio_get_charger_int_n(void)
{
    return (GPIOA->IDR & (1u << 2)) ? true : false;
}

bool gpio_get_bq_alert(void)
{
    return (GPIOA->IDR & (1u << 1)) ? true : false;
}

void gpio_set_mu_12v_enable(bool enable)
{
    if (enable) {
        GPIOE->BSRR = (1u << 13);
    } else {
        GPIOE->BSRR = (1u << (13 + 16));
    }
}

bool gpio_get_mu_12v_pg(void)
{
    return (GPIOE->IDR & (1u << 15)) ? true : false;
}

bool gpio_get_mu_s0_high(void)
{
    return (GPIOE->IDR & (1u << 14)) ? true : false;
}

void gpio_set_mu_pwrbtn_n(bool active)
{
    if (active) {
        GPIOA->BSRR = (1u << (0 + 16));
    } else {
        GPIOA->BSRR = (1u << 0);
    }
}

void gpio_set_mu_rstbtn_n(bool active)
{
    if (active) {
        GPIOA->BSRR = (1u << (5 + 16));
    } else {
        GPIOA->BSRR = (1u << 5);
    }
}

void gpio_set_service_mux_reset(bool released)
{
    if (released) {
        GPIOB->BSRR = (1u << 12);
    } else {
        GPIOB->BSRR = (1u << (12 + 16));
    }
}

void gpio_set_keyboard_rgb_enable(bool enable)
{
    if (enable) {
        GPIOC->BSRR = (1u << 0);
    } else {
        GPIOC->BSRR = (1u << (0 + 16));
    }
}

bool gpio_get_trackpad_fault_n(void)
{
    return (GPIOB->IDR & (1u << 1)) ? true : false;
}

void gpio_set_gnss_reset_n(bool active)
{
    if (active) {
        GPIOB->BSRR = (1u << 13);
    } else {
        GPIOB->BSRR = (1u << (13 + 16));
    }
}

void gpio_set_radio_db_power_enable(bool enable)
{
    if (enable) {
        GPIOB->BSRR = (1u << 5);
    } else {
        GPIOB->BSRR = (1u << (5 + 16));
    }
}

void gpio_set_audio_amp_enable(bool enable)
{
    if (enable) {
        GPIOE->BSRR = (1u << 12);
    } else {
        GPIOE->BSRR = (1u << (12 + 16));
    }
}

void gpio_set_audio_mic_enable(bool enable)
{
    if (enable) {
        GPIOE->BSRR = (1u << 11);
    } else {
        GPIOE->BSRR = (1u << (11 + 16));
    }
}

uint16_t gpio_read_adc_aux_dc(void)
{
    RCC->APB2ENR |= RCC_APB2ENR_ADC1EN;
    ADC1->CR2 = ADC_CR2_ADON;
    for (volatile int i = 0; i < 10; i++);
    ADC1->SQR3 = 3;
    ADC1->CR2 |= ADC_CR2_SWSTART;
    while (!(ADC1->SR & ADC_SR_EOC));
    return (uint16_t)ADC1->DR;
}

uint16_t gpio_read_adc_thermal_skin(void)
{
    RCC->APB2ENR |= RCC_APB2ENR_ADC1EN;
    ADC1->CR2 = ADC_CR2_ADON;
    for (volatile int i = 0; i < 10; i++);
    ADC1->SQR3 = 7;
    ADC1->CR2 |= ADC_CR2_SWSTART;
    while (!(ADC1->SR & ADC_SR_EOC));
    return (uint16_t)ADC1->DR;
}

uint16_t gpio_read_adc_thermal_mu(void)
{
    RCC->APB2ENR |= RCC_APB2ENR_ADC1EN;
    ADC1->CR2 = ADC_CR2_ADON;
    for (volatile int i = 0; i < 10; i++);
    ADC1->SQR3 = 8;
    ADC1->CR2 |= ADC_CR2_SWSTART;
    while (!(ADC1->SR & ADC_SR_EOC));
    return (uint16_t)ADC1->DR;
}

void gpio_set_fan_pwm_duty(uint16_t duty_percent)
{
    if (duty_percent > 100) duty_percent = 100;
    RCC->APB2ENR |= RCC_APB2ENR_TIM1EN;
    TIM1->PSC = 84 - 1;
    TIM1->ARR = 1000 - 1;
    TIM1->CCR1 = (uint32_t)duty_percent * 10u;
    TIM1->CCMR1 = TIM_CCMR1_OC1M_PWM1 | TIM_CCMR1_OC1PE;
    TIM1->CCER = TIM_CCER_CC1E | TIM_CCER_CC1NE;
    TIM1->BDTR = TIM_BDTR_MOE | TIM_BDTR_AOE;
    TIM1->EGR |= TIM_EGR_UG;
    TIM1->CR1 |= TIM_CR1_ARPE | TIM_CR1_CEN;
}

uint16_t gpio_read_fan_tach(void)
{
    return (GPIOC->IDR & (1u << 5)) ? 1 : 0;
}
