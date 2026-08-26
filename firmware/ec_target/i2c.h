#ifndef DUCKTOP2_I2C_H
#define DUCKTOP2_I2C_H

#include <stdbool.h>
#include <stdint.h>

#define I2C_TCA9548A_ADDR      0x70u
#define I2C_TCA9539_ADDR       0x74u

#define I2C_PD1_TCPC_ADDR      0x20u
#define I2C_PD2_TCPC_ADDR      0x21u

#define TCA9539_REG_INPUT0     0x00u
#define TCA9539_REG_INPUT1     0x01u
#define TCA9539_REG_OUTPUT0    0x02u
#define TCA9539_REG_OUTPUT1    0x03u
#define TCA9539_REG_CONFIG0    0x06u
#define TCA9539_REG_CONFIG1    0x07u

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
bool tca9539_init_safe(void);
bool tca9539_set_pd_path_enable(uint8_t path, bool enable);
bool tca9539_read_inputs(uint8_t *port0, uint8_t *port1);
bool tca9539_ready(void);
uint8_t tca9539_output0(void);

#endif
