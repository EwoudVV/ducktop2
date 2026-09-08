#ifndef MOCK_PICO_STDLIB_H
#define MOCK_PICO_STDLIB_H
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
typedef unsigned uint;
typedef int64_t absolute_time_t;
#define GPIO_IN false
#define GPIO_OUT true
#define GPIO_FUNC_SIO 5u
#define GPIO_FUNC_UART 2u
#define GPIO_FUNC_I2C 3u
#define GPIO_FUNC_SPI 1u
#define PICO_ERROR_TIMEOUT (-1)
absolute_time_t get_absolute_time(void);
absolute_time_t make_timeout_time_ms(uint32_t ms);
int64_t absolute_time_diff_us(absolute_time_t from,absolute_time_t to);
void gpio_set_dir(unsigned pin,bool output);
void gpio_set_function(unsigned pin,unsigned function);
void gpio_disable_pulls(unsigned pin);
void gpio_put(unsigned pin,bool value);
#endif
