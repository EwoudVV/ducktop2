#include "pico/stdlib.h"
typedef struct {bool active;} i2c_inst_t;
extern i2c_inst_t mock_i2c;
#define i2c1 (&mock_i2c)
uint32_t i2c_init(i2c_inst_t *i2c,uint32_t rate);
void i2c_deinit(i2c_inst_t *i2c);
int i2c_write_blocking_until(i2c_inst_t *i2c,uint8_t address,const uint8_t *data,size_t length,bool nostop,absolute_time_t deadline);
int i2c_read_blocking_until(i2c_inst_t *i2c,uint8_t address,uint8_t *data,size_t length,bool nostop,absolute_time_t deadline);
