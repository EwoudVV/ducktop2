#ifndef DUCKTOP2_GPIO_H
#define DUCKTOP2_GPIO_H

#include <stdbool.h>
#include <stdint.h>

void gpio_init_all(void);

void gpio_set_pd_path_enable_a(bool enable);
void gpio_set_pd_path_enable_b(bool enable);
bool gpio_get_pd1_valid_n(void);
bool gpio_get_pd2_valid_n(void);
bool gpio_get_pd1_tcpc_irq_n(void);
bool gpio_get_pd2_tcpc_irq_n(void);
bool gpio_get_pd_protect_fault_n(void);

void gpio_set_charger_enable(bool enable);
void gpio_set_pmic_qon_assert(bool assert);
bool gpio_get_charger_int_n(void);
bool gpio_get_bq_alert(void);

void gpio_set_mu_12v_enable(bool enable);
bool gpio_get_mu_12v_pg(void);
bool gpio_get_mu_s0_high(void);
void gpio_set_mu_pwrbtn_n(bool active);
void gpio_set_mu_rstbtn_n(bool active);

void gpio_set_service_mux_reset(bool released);
void gpio_set_keyboard_rgb_enable(bool enable);
bool gpio_get_trackpad_fault_n(void);

void gpio_set_gnss_reset_n(bool active);
void gpio_set_radio_db_power_enable(bool enable);
void gpio_set_audio_amp_enable(bool enable);
void gpio_set_audio_mic_enable(bool enable);

/*
 * One-time ADC1 setup: analog-mode pins, ADC clock, sample times, and
 * stabilization.  Self-guarding: the first ADC read calls it lazily and later
 * calls are no-ops.
 */
bool gpio_adc_init(void);

/*
 * Single-shot 12-bit conversions: AUX_DC (PA6/ADC1_IN6), skin NTC
 * (PA7/ADC1_IN7), Mu NTC (PB0/ADC1_IN8).  Return 0 on init failure or a
 * conversion timeout (the caller's thermal policy treats invalid data
 * fail-safe).
 */
uint16_t gpio_read_adc_aux_dc(void);
uint16_t gpio_read_adc_thermal_skin(void);
uint16_t gpio_read_adc_thermal_mu(void);

/*
 * Command fan speed 0..100 percent on PE9/TIM1_CH1 (25 kHz).  The duty is
 * the commanded fan speed, not the raw MCU pin duty: the open-drain sink
 * stage (Q200) inverts, so 0 = fan stopped and 100 = full speed.  Clamped
 * internally to 0..100.
 */
void gpio_set_fan_pwm_duty(uint16_t duty_percent);

/*
 * Fan tachometer: PC5 (EXTI5) falling edges are timestamped against a
 * free-running 1 MHz counter in the ISR; the period between two edges is
 * one FG pulse = half a revolution.
 *
 * gpio_fan_tach_update() must be polled (any rate; it lazily initializes
 * the tach hardware and re-derives the RPM each call, returning 0 once the
 * last edge ages past the 250 ms freshness window, i.e. a stalled fan).
 * gpio_fan_tach_rpm() returns the last value computed by update().
 */
void gpio_fan_tach_update(void);
uint16_t gpio_fan_tach_rpm(void);

/* Raw level of the fan FG line (1 = idle high); debug/introspection only. */
uint16_t gpio_read_fan_tach(void);

#endif
