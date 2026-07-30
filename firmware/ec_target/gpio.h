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

uint16_t gpio_read_adc_aux_dc(void);
uint16_t gpio_read_adc_thermal_skin(void);
uint16_t gpio_read_adc_thermal_mu(void);

void gpio_set_fan_pwm_duty(uint16_t duty_percent);
uint16_t gpio_read_fan_tach(void);

#endif
