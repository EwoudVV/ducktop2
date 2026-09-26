#include "tca9537.h"
#include "i2c.h"

/* TI SCPS279, tables 8-1 through 8-6. Each address is a byte register. */
static bool initialized, aux_enabled;
static bool write_checked(uint8_t reg, uint8_t value, uint8_t mask)
{
    uint8_t actual;
    return i2c1_write(TCA9537_ADDRESS,reg,value) &&
        i2c1_read(TCA9537_ADDRESS,reg,&actual,1) &&
        (actual & mask)==(value & mask);
}
bool tca9537_init_safe(void)
{
    initialized=aux_enabled=false;
    /* Set the latch before changing its pin from input to output. */
    initialized=write_checked(1,0xfe,0x0f) && write_checked(2,0,0x0f) &&
                write_checked(3,0xfe,0x0f);
    return initialized;
}
bool tca9537_read_inputs(uint8_t *inputs)
{
    uint8_t config,polarity,output,value;
    if(!initialized || !inputs ||
       !i2c1_read(TCA9537_ADDRESS,3,&config,1) || (config & 15u)!=14u ||
       !i2c1_read(TCA9537_ADDRESS,2,&polarity,1) || (polarity & 15u)!=0u ||
       !i2c1_read(TCA9537_ADDRESS,1,&output,1) || (output & 1u)!=(unsigned)aux_enabled ||
       !i2c1_read(TCA9537_ADDRESS,0,&value,1) || (value & 1u)!=(unsigned)aux_enabled) {
        initialized=false;
        return false;
    }
    *inputs=value;
    return true;
}
bool tca9537_set_aux_enable(bool enable)
{
    uint8_t inputs;
    if(!tca9537_read_inputs(&inputs)) return false;
    if(!write_checked(1,enable ? 0xff : 0xfe,15u)) { initialized=false; return false; }
    aux_enabled=enable;
    return tca9537_read_inputs(&inputs);
}
bool tca9537_aux_enabled(void) { return initialized && aux_enabled; }
