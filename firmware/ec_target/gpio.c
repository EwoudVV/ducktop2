#include "gpio.h"
#include "fan_math.h"
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

    /* PC5: FAN_TACH - Input, no internal pull (R206 8.2k to MCU_3V3 idles
     * the open-collector FG line high; C209 3.9n filters it) */
    GPIOC->MODER   |= GPIO_MODER_INPUT << (5 * 2);

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

/* ---- ADC1: AUX_DC (PA6), skin NTC (PA7), Mu NTC (PB0) ---- */

/*
 * ADC1 input channels for the monitored signals, per RM0090 Table 8
 * (PA6=IN6, PA7=IN7, PB0=IN8) and verified against the schematic
 * (gen/generate_pin_review_table.py lines 524-527; the EC MCU sheet maps
 * pins 31/32/35 to AUX_DC_ADC/THERM_SKIN_ADC/THERM_MU_ADC on those ports).
 * Note: PA3 (ADC1_IN3) is PMIC_QON_ASSERT, so the previous hardcoded
 * channel 3 for AUX_DC sampled the wrong signal.
 */
#define ADC_CHANNEL_AUX_DC       6u
#define ADC_CHANNEL_THERM_SKIN   7u
#define ADC_CHANNEL_THERM_MU     8u

/* 84-cycle sample time (SMPR2 encoding 0b111) for channels 6/7/8: both NTC
 * dividers carry a 100nF filter cap (C202/C207), so the long sampling
 * window keeps charging error below 1 LSB. */
#define ADC_SMPR_CH6_84CYC      (7u << 18)
#define ADC_SMPR_CH7_84CYC      (7u << 21)
#define ADC_SMPR_CH8_84CYC      (7u << 24)

static volatile bool s_adc_ready;

bool gpio_adc_init(void)
{
    if (s_adc_ready) {
        return true;
    }

    /* Analog mode disconnects the digital pad; idempotent with
     * gpio_init_all() and safe to run before it. */
    RCC->AHB1ENR |= RCC_AHB1ENR_GPIOAEN | RCC_AHB1ENR_GPIOBEN;
    GPIOA->MODER = (GPIOA->MODER & ~(3u << 12)) | (GPIO_MODER_ANALOG << 12);
    GPIOA->MODER = (GPIOA->MODER & ~(3u << 14)) | (GPIO_MODER_ANALOG << 14);
    GPIOB->MODER = (GPIOB->MODER & ~(3u << 0))  | (GPIO_MODER_ANALOG << 0);

    RCC->APB2ENR |= RCC_APB2ENR_ADC1EN;

    /* ADC clock: APB2 = 84 MHz, prescaler /4 -> 21 MHz (RM0090 max 36 MHz).
     * Only ADC1 is used, so a direct write is deterministic. */
    ADC1_COMMON->CCR = ADC_CCR_ADCPRE_DIV4;

    /* Single conversion, right-aligned 12-bit, one channel per sequence. */
    ADC1->CR1 = 0u;
    ADC1->SQR1 = 0u;
    ADC1->SMPR2 = ADC_SMPR_CH6_84CYC | ADC_SMPR_CH7_84CYC | ADC_SMPR_CH8_84CYC;

    ADC1->CR2 = ADC_CR2_ADON;
    {
        /* tSTAB stabilization before calibration (RM0090). */
        volatile uint32_t stab = 1000u;
        while (stab-- != 0u) { }
    }
    ADC1->CR2 |= ADC_CR2_CAL;
    {
        uint32_t timeout = 100000u;
        while ((ADC1->CR2 & ADC_CR2_CAL) && (timeout-- != 0u)) { }
        if (ADC1->CR2 & ADC_CR2_CAL) {
            return false; /* calibration stalled; next read retries */
        }
    }
    s_adc_ready = true;
    return true;
}

static uint16_t adc_read_channel(uint32_t channel)
{
    if (!gpio_adc_init()) {
        return 0u;
    }
    ADC1->SQR3 = channel;
    ADC1->CR2 |= ADC_CR2_SWSTART;
    /* Bounded EOC wait so a dead ADC cannot hang the policy loop. */
    uint32_t timeout = 100000u;
    while (!(ADC1->SR & ADC_SR_EOC) && (timeout-- != 0u)) { }
    if (!(ADC1->SR & ADC_SR_EOC)) {
        return 0u;
    }
    return (uint16_t)ADC1->DR; /* reading DR clears EOC */
}

uint16_t gpio_read_adc_aux_dc(void)
{
    return adc_read_channel(ADC_CHANNEL_AUX_DC);
}

uint16_t gpio_read_adc_thermal_skin(void)
{
    return adc_read_channel(ADC_CHANNEL_THERM_SKIN);
}

uint16_t gpio_read_adc_thermal_mu(void)
{
    return adc_read_channel(ADC_CHANNEL_THERM_MU);
}

/* ---- TIM1_CH1 fan PWM (PE9, AF1) ---- */

/*
 * Signal chain (schematic, gen/generate_internal_services_sheet.py): FAN_PWM
 * (PE9) -> R207 100R -> Q200 (2N7002KT1G) gate; Q200 drains J52 pin 4
 * (FAN_PWM_CONN).  Fan contract (J52 EndpointElectricalContract): 25 kHz
 * open-drain PWM, floating input = full speed, 0% duty = stopped.  Q200
 * inverts, so the MCU pin high-time is the complement of the commanded fan
 * speed; fan_pwm_ccr_from_duty() encodes that.  The unpowered/reset EC is
 * fail-safe by R208 (100k gate pull-down -> FET off -> full speed).
 *
 * PE9 is TIM1_CH1 (AF1, RM0090); there is no complementary-output pin in
 * this design, so CC1NE is not set.  Frequency: 168 MHz / 6720 = 25.0 kHz.
 */
#define FAN_PWM_TIM_HZ          168000000u
#define FAN_PWM_FREQ_HZ         25000u
#define FAN_PWM_PERIOD_TICKS    (FAN_PWM_TIM_HZ / FAN_PWM_FREQ_HZ)

static volatile bool s_fan_pwm_ready;

static void gpio_fan_pwm_init(void)
{
    if (s_fan_pwm_ready) {
        return;
    }

    /* PE9 = TIM1_CH1 (AF1); high speed for 25 kHz gate drive into Q200. */
    RCC->AHB1ENR |= RCC_AHB1ENR_GPIOEEN;
    GPIOE->MODER = (GPIOE->MODER & ~(3u << 18)) | (GPIO_MODER_AF << 18);
    GPIOE->AFRH = (GPIOE->AFRH & ~(0xFu << 4)) | (GPIO_AF1 << 4);
    GPIOE->OSPEEDR = (GPIOE->OSPEEDR & ~(3u << 18)) | (GPIO_OSPEEDR_HIGH << 18);
    GPIOE->OTYPER &= ~(1u << 9); /* push-pull, not open-drain */

    RCC->APB2ENR |= RCC_APB2ENR_TIM1EN;
    TIM1->PSC = 0u;                          /* 168 MHz timer tick */
    TIM1->ARR = FAN_PWM_PERIOD_TICKS - 1u;   /* 25 kHz PWM */
    TIM1->CCMR1 = TIM_CCMR1_OC1PE | TIM_CCMR1_OC1M_PWM1;
    TIM1->CCER = TIM_CCER_CC1E;              /* CH1 only; no CH1N in design */
    TIM1->BDTR = TIM_BDTR_MOE;               /* main output enable */
    TIM1->EGR |= TIM_EGR_UG;                 /* latch PSC/ARR */
    TIM1->CR1 = TIM_CR1_ARPE | TIM_CR1_CEN;
    s_fan_pwm_ready = true;
}

void gpio_set_fan_pwm_duty(uint16_t duty_percent)
{
    gpio_fan_pwm_init();
    TIM1->CCR1 = fan_pwm_ccr_from_duty(duty_percent, FAN_PWM_PERIOD_TICKS);
}

/* ---- Fan tachometer: PC5 (EXTI5) + TIM2 free-running microseconds ---- */

/*
 * J52 pin 3 (FAN_TACH): open-collector FG from the Delta blower, 2 pulses
 * per revolution, pulled up by R206 (8.2k to MCU_3V3) and filtered by C209
 * (3.9n).  The line idles high and pulses low.  EXTI5 falling edges are
 * timestamped against the 32-bit TIM2 counter free-running at 1 MHz; the
 * period between two consecutive edges is one FG pulse = half a
 * revolution.  The 1 us resolution keeps RPM error below 0.1% even at the
 * fan's 6100 RPM maximum (4.9 ms pulse period), far beyond the 1 ms
 * SysTick granularity.
 */
#define FAN_TACH_PULSES_PER_REV   2u
#define FAN_TACH_FRESH_WINDOW_MS  250u

static volatile bool s_tach_ready;
static volatile bool s_tach_first_edge;
static volatile uint32_t s_tach_last_edge_us;
static volatile uint32_t s_tach_period_us;
static volatile uint32_t s_tach_last_edge_ms;
static volatile uint16_t s_tach_rpm;

void EXTI9_5_IRQHandler(void)
{
    if (EXTI->PR & (1u << 5)) {
        EXTI->PR = (1u << 5); /* write-1-to-clear */
        uint32_t now_us = TIM2->CNT;
        if (s_tach_first_edge) {
            /* Unsigned difference is wrap-safe over the 71-minute counter
             * rollover: pulse periods are orders of magnitude shorter. */
            s_tach_period_us = now_us - s_tach_last_edge_us;
        } else {
            s_tach_first_edge = true; /* first edge: no period yet */
        }
        s_tach_last_edge_us = now_us;
        s_tach_last_edge_ms = GetTick();
    }
}

static void gpio_fan_tach_init(void)
{
    if (s_tach_ready) {
        return;
    }

    /* PC5 input, no internal pull (R206 defines the idle-high level). */
    RCC->AHB1ENR |= RCC_AHB1ENR_GPIOCEN;
    GPIOC->MODER = (GPIOC->MODER & ~(3u << 10)) | (GPIO_MODER_INPUT << 10);
    GPIOC->PUPDR &= ~(3u << 10);

    /* APB1 is /4, so TIM2 receives 2 * PCLK1 = 84 MHz. */
    RCC->APB1ENR |= RCC_APB1ENR_TIM2EN;
    TIM2->PSC = 84u - 1u;
    TIM2->ARR = 0xFFFFFFFFu;
    TIM2->CR1 = TIM_CR1_CEN;

    /* Falling-edge EXTI on PC5 (EXTI5 -> EXTI9_5, NVIC IRQ 23).  The
     * interrupt is armed last so no edge is timestamped before the
     * hardware is fully configured. */
    RCC->APB2ENR |= RCC_APB2ENR_SYSCFGEN;
    SYSCFG->EXTICR[1] = (SYSCFG->EXTICR[1] & ~(0xFu << 4)) | (2u << 4);
    EXTI->IMR |= (1u << 5);
    EXTI->FTSR |= (1u << 5);
    EXTI->PR = (1u << 5);
    NVIC_ISER0 = (1u << 23);
    NVIC_IPR(23) = 0u;

    s_tach_first_edge = false;
    s_tach_period_us = 0u;
    s_tach_last_edge_us = 0u;
    s_tach_last_edge_ms = 0u;
    s_tach_rpm = 0u;
    s_tach_ready = true;
}

void gpio_fan_tach_update(void)
{
    if (!s_tach_ready) {
        gpio_fan_tach_init();
    }
    if (fan_tach_is_fresh(s_tach_last_edge_ms, GetTick(),
                          FAN_TACH_FRESH_WINDOW_MS)) {
        s_tach_rpm = fan_rpm_from_period_us(s_tach_period_us,
                                            FAN_TACH_PULSES_PER_REV);
    } else {
        s_tach_rpm = 0u; /* no edge within the window: stalled or off */
    }
}

uint16_t gpio_fan_tach_rpm(void)
{
    return s_tach_rpm;
}

uint16_t gpio_read_fan_tach(void)
{
    return (GPIOC->IDR & (1u << 5)) ? 1u : 0u;
}
