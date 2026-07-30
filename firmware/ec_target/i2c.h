#ifndef DUCKTOP2_I2C_H
#define DUCKTOP2_I2C_H

#include <stdbool.h>
#include <stdint.h>

#define I2C_TCA9548A_ADDR      0x70u
#define I2C_TCA9539_ADDR       0x74u

#define I2C_PD1_TCPC_ADDR      0x20u
#define I2C_PD2_TCPC_ADDR      0x21u

void i2c1_init(void);

bool i2c1_write(uint8_t dev_addr, uint8_t reg, uint8_t data);
bool i2c1_write_raw(uint8_t dev_addr, uint8_t *data, uint16_t len);
bool i2c1_read(uint8_t dev_addr, uint8_t reg, uint8_t *data, uint16_t len);
bool i2c1_read_raw(uint8_t dev_addr, uint8_t *data, uint16_t len);

bool i2c1_probe(uint8_t dev_addr);

bool tca9548a_select_channel(uint8_t channel);
bool tca9548a_select_all(void);
void tca9548a_deselect_all(void);

bool tca9539_write_register(uint8_t reg, uint8_t value);
bool tca9539_read_register(uint8_t reg, uint8_t *value);

#endif
