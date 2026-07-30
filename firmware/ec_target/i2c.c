#include "i2c.h"
#include "stm32f4xx.h"

#define I2C_TIMEOUT_CYCLES 50000

static void i2c1_enable_clock(void)
{
    RCC->APB1ENR |= RCC_APB1ENR_I2C1EN;
}

static void i2c1_disable(void)
{
    I2C1->CR1 &= ~I2C_CR1_PE;
}

static void i2c1_enable(void)
{
    I2C1->CR1 |= I2C_CR1_PE;
}

void i2c1_init(void)
{
    i2c1_disable();
    i2c1_enable_clock();

    uint32_t pclk1 = 42000000;

    I2C1->CR2 = (pclk1 / 1000000) & I2C_CR2_FREQ_Msk;

    I2C1->CCR = I2C_CCR_FS | (pclk1 / (3 * 400000));
    I2C1->TRISE = ((pclk1 / 1000000) * 300 / 1000) + 1;

    I2C1->CR1 |= I2C_CR1_PE;
}

static bool wait_for_flag(__I uint32_t *reg, uint32_t mask, bool set)
{
    uint32_t timeout = I2C_TIMEOUT_CYCLES;
    while (timeout--) {
        bool flag = (*reg & mask) ? true : false;
        if (flag == set) return true;
    }
    return false;
}

static void clear_addr(void)
{
    (void)I2C1->SR2;
}

static bool send_start(void)
{
    I2C1->CR1 |= I2C_CR1_START;
    return wait_for_flag(&I2C1->SR1, I2C_SR1_SB, true);
}

static bool send_stop(void)
{
    I2C1->CR1 |= I2C_CR1_STOP;
    return true;
}

static bool send_address(uint8_t addr, bool is_read)
{
    uint8_t addr_byte = (addr << 1) | (is_read ? 1 : 0);
    I2C1->DR = addr_byte;
    return wait_for_flag(&I2C1->SR1, I2C_SR1_ADDR, true);
}

static bool wait_txe(void)
{
    return wait_for_flag(&I2C1->SR1, I2C_SR1_TXE, true);
}

static bool wait_rxne(void)
{
    return wait_for_flag(&I2C1->SR1, I2C_SR1_RXNE, true);
}

static bool wait_btf(void)
{
    return wait_for_flag(&I2C1->SR1, I2C_SR1_BTF, true);
}

bool i2c1_write(uint8_t dev_addr, uint8_t reg, uint8_t data)
{
    uint8_t buf[2] = {reg, data};
    return i2c1_write_raw(dev_addr, buf, 2);
}

bool i2c1_write_raw(uint8_t dev_addr, uint8_t *data, uint16_t len)
{
    if (!send_start()) return false;
    if (!send_address(dev_addr, false)) {
        send_stop();
        i2c1_enable();
        return false;
    }
    clear_addr();
    for (uint16_t i = 0; i < len; i++) {
        if (!wait_txe()) {
            send_stop();
            return false;
        }
        I2C1->DR = data[i];
    }
    if (!wait_btf()) {
        send_stop();
        return false;
    }
    send_stop();
    return true;
}

bool i2c1_read(uint8_t dev_addr, uint8_t reg, uint8_t *data, uint16_t len)
{
    if (!send_start()) return false;
    if (!send_address(dev_addr, false)) {
        send_stop();
        i2c1_enable();
        return false;
    }
    clear_addr();
    if (!wait_txe()) {
        send_stop();
        return false;
    }
    I2C1->DR = reg;
    if (!wait_btf()) {
        send_stop();
        return false;
    }

    if (!send_start()) return false;
    if (!send_address(dev_addr, true)) {
        send_stop();
        i2c1_enable();
        return false;
    }
    clear_addr();

    if (len == 1) {
        I2C1->CR1 &= ~I2C_CR1_ACK;
        send_stop();
        if (!wait_rxne()) return false;
        data[0] = (uint8_t)I2C1->DR;
    } else {
        I2C1->CR1 |= I2C_CR1_ACK;
        for (uint16_t i = 0; i < len; i++) {
            if (i == len - 1) {
                I2C1->CR1 &= ~I2C_CR1_ACK;
                send_stop();
            }
            if (!wait_rxne()) return false;
            data[i] = (uint8_t)I2C1->DR;
        }
    }
    return true;
}

bool i2c1_read_raw(uint8_t dev_addr, uint8_t *data, uint16_t len)
{
    if (!send_start()) return false;
    if (!send_address(dev_addr, true)) {
        send_stop();
        i2c1_enable();
        return false;
    }
    clear_addr();

    if (len == 1) {
        I2C1->CR1 &= ~I2C_CR1_ACK;
        send_stop();
        if (!wait_rxne()) return false;
        data[0] = (uint8_t)I2C1->DR;
    } else {
        I2C1->CR1 |= I2C_CR1_ACK;
        for (uint16_t i = 0; i < len; i++) {
            if (i == len - 1) {
                I2C1->CR1 &= ~I2C_CR1_ACK;
                send_stop();
            }
            if (!wait_rxne()) return false;
            data[i] = (uint8_t)I2C1->DR;
        }
    }
    return true;
}

bool i2c1_probe(uint8_t dev_addr)
{
    if (!send_start()) return false;
    if (!send_address(dev_addr, false)) {
        send_stop();
        i2c1_enable();
        return false;
    }
    clear_addr();
    send_stop();
    return true;
}

bool tca9548a_select_channel(uint8_t channel)
{
    if (channel > 7) return false;
    uint8_t control_byte = (uint8_t)(1u << channel);
    return i2c1_write_raw(I2C_TCA9548A_ADDR, &control_byte, 1);
}

bool tca9548a_select_all(void)
{
    uint8_t control_byte = 0xFF;
    return i2c1_write_raw(I2C_TCA9548A_ADDR, &control_byte, 1);
}

void tca9548a_deselect_all(void)
{
    uint8_t control_byte = 0x00;
    i2c1_write_raw(I2C_TCA9548A_ADDR, &control_byte, 1);
}

bool tca9539_write_register(uint8_t reg, uint8_t value)
{
    return i2c1_write(I2C_TCA9539_ADDR, reg, value);
}

bool tca9539_read_register(uint8_t reg, uint8_t *value)
{
    return i2c1_read(I2C_TCA9539_ADDR, reg, value, 1);
}
