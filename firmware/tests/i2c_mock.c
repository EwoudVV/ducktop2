#include "i2c_mock.h"
#include "i2c.h"

#include <string.h>

i2c_mock_t i2c_mock;

void i2c_mock_begin(void)
{
    memset(&i2c_mock, 0, sizeof(i2c_mock));
    i2c_mock.present = true;
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
    if (i2c_mock.nack_all) {
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
    if (i2c_mock.nack_all) {
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
    for (uint16_t i = 1; i < len; i++) {
        i2c_mock.regfile[data[0] + (uint8_t)(i - 1u)] = data[i];
    }
    return true;
}

bool i2c1_read(uint8_t dev_addr, uint8_t reg, uint8_t *data, uint16_t len)
{
    i2c_mock_step_t *step = i2c_mock_next_step();
    i2c_mock.reads++;
    if (i2c_mock.nack_all) {
        return false;
    }
    if (step != NULL && step->len == len && step->dev_addr == dev_addr &&
        step->reg == reg && (step->len & 0x80u) == 0) {
        memcpy(data, step->data, len);
        step->used = true;
        return step->ack;
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
    if (step != NULL && step->len == 0 && step->dev_addr == dev_addr) {
        step->used = true;
        return step->ack;
    }
    return i2c_mock.present;
}
