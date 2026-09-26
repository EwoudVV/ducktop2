#include "i2c_mock.h"
#include "i2c.h"

#include <string.h>

i2c_mock_t i2c_mock;

void i2c_mock_begin(void)
{
    memset(&i2c_mock, 0, sizeof(i2c_mock));
    i2c_mock.present = true;
    i2c_mock.tca37[1]=i2c_mock.tca37[3]=0xff;
    i2c_mock.adc_done_autoset = true;
}

static i2c_mock_step_t *i2c_mock_next_step(void)
{
    for (size_t i = 0; i < i2c_mock.script_count; i++) {
        if (!i2c_mock.script[i].used) {
            return &i2c_mock.script[i];
        }
    }
    return NULL;
}

void i2c_mock_expect_probe(uint8_t dev_addr, bool ack)
{
    if (i2c_mock.script_count >= I2C_MOCK_SCRIPT_MAX) {
        i2c_mock.script_error = true;
        return;
    }
    i2c_mock_step_t *step = &i2c_mock.script[i2c_mock.script_count++];
    step->dev_addr = dev_addr;
    step->len = 0;
    step->ack = ack;
}

void i2c_mock_expect_read(uint8_t dev_addr, uint8_t reg, const uint8_t *data,
                          uint8_t len)
{
    if (i2c_mock.script_count >= I2C_MOCK_SCRIPT_MAX || len > I2C_MOCK_BLOCK_MAX) {
        i2c_mock.script_error = true;
        return;
    }
    i2c_mock_step_t *step = &i2c_mock.script[i2c_mock.script_count++];
    step->dev_addr = dev_addr;
    step->reg = reg;
    step->len = len;
    step->ack = true;
    memcpy(step->data, data, len);
}

void i2c_mock_expect_write(uint8_t dev_addr, uint8_t reg, const uint8_t *data,
                           uint8_t len)
{
    if (i2c_mock.script_count >= I2C_MOCK_SCRIPT_MAX || len > I2C_MOCK_BLOCK_MAX) {
        i2c_mock.script_error = true;
        return;
    }
    i2c_mock_step_t *step = &i2c_mock.script[i2c_mock.script_count++];
    step->dev_addr = dev_addr;
    step->reg = reg;
    step->len = (uint8_t)(len | 0x80u); /* write flag */
    step->ack = true;
    memcpy(step->data, data, len);
}

bool i2c_mock_script_complete(void)
{
    for (size_t i = 0; i < i2c_mock.script_count; i++) {
        if (!i2c_mock.script[i].used) {
            return false;
        }
    }
    return !i2c_mock.script_error;
}

bool i2c1_write(uint8_t dev_addr, uint8_t reg, uint8_t data)
{
    i2c_mock_step_t *step = i2c_mock_next_step();
    i2c_mock.writes++;
    if (i2c_mock.nack_all || (i2c_mock.nack_address && i2c_mock.nack_address==dev_addr)) {
        return false;
    }
    if (step != NULL && step->len == 0x80u + 1u && step->dev_addr == dev_addr &&
        step->reg == reg) {
        if (step->data[0] != data) {
            i2c_mock.script_error = true;
        }
        step->used = true;
        return step->ack;
    }
    if (step != NULL) { i2c_mock.script_error = true; return false; }
    if(i2c_mock.ignore_writes) return true;
    if(dev_addr==0x49u) {
        if(reg>=4 || reg==0) return false;
        i2c_mock.tca37[reg]=data;return true;
    }
    i2c_mock.regfile[reg] = data;
    if (i2c_mock.adc_done_autoset && dev_addr == 0x6Bu && reg == 0x2Eu &&
        (data & 0x80u) != 0) {
        i2c_mock.regfile[0x1Eu] |= 0x20u;
    }
    return true;
}

bool i2c1_write_raw(uint8_t dev_addr, uint8_t *data, uint16_t len)
{
    i2c_mock_step_t *step = i2c_mock_next_step();
    i2c_mock.write_raws++;
    if (i2c_mock.nack_all || (i2c_mock.nack_address && i2c_mock.nack_address==dev_addr)) {
        return false;
    }
    if (len == 0 || data == NULL) {
        return false;
    }
    if (step != NULL && step->len == (uint8_t)(0x80u + (len - 1u)) &&
        step->dev_addr == dev_addr && step->reg == data[0]) {
        if (memcmp(step->data, &data[1], len - 1u) != 0) {
            i2c_mock.script_error = true;
        }
        step->used = true;
        return step->ack;
    }
    if (step != NULL) { i2c_mock.script_error = true; return false; }
    if(i2c_mock.ignore_writes) return true;
    if(dev_addr==0x09u) {
        if(len!=3) {i2c_mock.script_error=true;return false;}
        i2c_mock.isl_words[data[0]]=(uint16_t)data[1] | ((uint16_t)data[2]<<8);
        if(data[0]==0x4eu) i2c_mock.isl_words[0x4e]&=(uint16_t)~2u;
        return true;
    }
    if(dev_addr==0x55u && i2c_mock.gauge_emulated) {
        if(len==3 && data[0]==0 && data[1]==1 && data[2]==0) {
            i2c_mock.gauge[0]=0;i2c_mock.gauge[1]=1;return true;
        }
        for(uint16_t i=1;i<len;i++)i2c_mock.gauge[(uint8_t)(data[0]+i-1)]=data[i];
        return true;
    }
    for (uint16_t i = 1; i < len; i++) {
        i2c_mock.regfile[data[0] + (uint8_t)(i - 1u)] = data[i];
    }
    return true;
}

bool i2c1_read(uint8_t dev_addr, uint8_t reg, uint8_t *data, uint16_t len)
{
    i2c_mock_step_t *step = i2c_mock_next_step();
    i2c_mock.reads++;
    if (i2c_mock.nack_all || (i2c_mock.nack_address && i2c_mock.nack_address==dev_addr)) {
        return false;
    }
    if (step != NULL && step->len == len && step->dev_addr == dev_addr &&
        step->reg == reg && (step->len & 0x80u) == 0) {
        memcpy(data, step->data, len);
        step->used = true;
        return step->ack;
    }
    if (step != NULL) { i2c_mock.script_error = true; return false; }
    if(dev_addr==0x09u) {
        if(len!=2) {i2c_mock.script_error=true;return false;}
        data[0]=(uint8_t)i2c_mock.isl_words[reg];data[1]=(uint8_t)(i2c_mock.isl_words[reg]>>8);
        return true;
    }
    if(dev_addr==0x49u) {
        if(len!=1 || reg>=4) return false;
        uint8_t cfg=i2c_mock.tca37[3];
        data[0]=reg ? i2c_mock.tca37[reg] :
            (uint8_t)(((i2c_mock.tca37[0]&cfg) | (i2c_mock.tca37[1] & ~cfg)) ^ i2c_mock.tca37[2]);
        return true;
    }
    if(dev_addr==0x55u && i2c_mock.gauge_emulated) {
        for(uint16_t i=0;i<len;i++)data[i]=i2c_mock.gauge[(uint8_t)(reg+i)];
        return true;
    }
    if(dev_addr==0x74u && i2c_mock.expander_pins_emulated && reg<=1 && len==1) {
        uint8_t cfg=i2c_mock.regfile[6+reg];
        data[0]=(uint8_t)((i2c_mock.regfile[reg]&cfg) | (i2c_mock.regfile[2+reg]&~cfg));
        return true;
    }
    for (uint16_t i = 0; i < len; i++) {
        data[i] = i2c_mock.regfile[reg + (uint8_t)i];
    }
    return true;
}

bool i2c1_probe(uint8_t dev_addr)
{
    i2c_mock_step_t *step = i2c_mock_next_step();
    i2c_mock.probes++;
    if(i2c_mock.nack_all || (i2c_mock.nack_address && i2c_mock.nack_address==dev_addr)) return false;
    if (step != NULL && step->len == 0 && step->dev_addr == dev_addr) {
        step->used = true;
        return step->ack;
    }
    if (step != NULL) { i2c_mock.script_error = true; return false; }
    return i2c_mock.present;
}

bool tca9539_write_register(uint8_t reg, uint8_t value)
{
    return i2c1_write(0x74u, reg, value);
}

bool tca9539_read_register(uint8_t reg, uint8_t *value)
{
    return i2c1_read(0x74u, reg, value, 1u);
}
