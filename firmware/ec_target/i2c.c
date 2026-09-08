#include "i2c.h"
#include "stm32f4xx.h"
#include <stddef.h>

#define I2C_TIMEOUT_CYCLES 100000u
#define I2C_ERROR_FLAGS (I2C_SR1_AF | I2C_SR1_BERR | I2C_SR1_ARLO | I2C_SR1_OVR)

void i2c1_init(void)
{
    RCC->APB1ENR |= RCC_APB1ENR_I2C1EN;
    (void)RCC->APB1ENR;
    I2C1->CR1 = I2C_CR1_SWRST;
    I2C1->CR1 = 0u;
    /* APB1 = 42 MHz; standard mode gives the muxed service bus margin. */
    I2C1->CR2 = 42u;
    I2C1->CCR = 210u;
    I2C1->TRISE = 43u;
    I2C1->OAR1 = 1u << 14;
    I2C1->CR1 = I2C_CR1_PE;
}

static bool wait_flag(volatile uint32_t *reg, uint32_t mask, bool set)
{
    for (uint32_t count = 0; count < I2C_TIMEOUT_CYCLES; ++count) {
        if (I2C1->SR1 & I2C_ERROR_FLAGS) return false;
        if (((*reg & mask) != 0u) == set) return true;
    }
    return false;
}

static bool abort_transfer(void)
{
    /* ARLO means another master owns the bus: do not issue a STOP then. */
    if ((I2C1->SR1 & I2C_SR1_ARLO) == 0u) I2C1->CR1 |= I2C_CR1_STOP;
    I2C1->SR1 &= ~I2C_ERROR_FLAGS;
    I2C1->CR1 &= ~(I2C_CR1_ACK | I2C_CR1_POS);
    (void)wait_flag(&I2C1->SR2, I2C_SR2_BUSY, false);
    i2c1_init();
    return false;
}

static void clear_addr(void)
{
    (void)I2C1->SR1;
    (void)I2C1->SR2;
}

static bool start_address(uint8_t address, bool read)
{
    I2C1->CR1 |= I2C_CR1_START;
    if (!wait_flag(&I2C1->SR1, I2C_SR1_SB, true)) return false;
    I2C1->DR = (uint8_t)((address << 1) | (read ? 1u : 0u));
    return wait_flag(&I2C1->SR1, I2C_SR1_ADDR, true);
}

static bool begin(uint8_t address)
{
    if (address > 0x7fu) return false;
    I2C1->CR1 &= ~(I2C_CR1_ACK | I2C_CR1_POS);
    I2C1->SR1 &= ~I2C_ERROR_FLAGS;
    return wait_flag(&I2C1->SR2, I2C_SR2_BUSY, false);
}

static bool complete(void)
{
    I2C1->CR1 &= ~(I2C_CR1_ACK | I2C_CR1_POS);
    if (!wait_flag(&I2C1->SR2, I2C_SR2_BUSY, false)) return abort_transfer();
    return true;
}

bool i2c1_write(uint8_t address, uint8_t reg, uint8_t value)
{
    uint8_t bytes[2] = {reg, value};
    return i2c1_write_raw(address, bytes, 2);
}

bool i2c1_write_raw(uint8_t address, uint8_t *data, uint16_t size)
{
    if (!data || !size) return false;
    if (!begin(address) || !start_address(address, false)) return abort_transfer();
    clear_addr();
    for (uint16_t index = 0; index < size; ++index) {
        if (!wait_flag(&I2C1->SR1, I2C_SR1_TXE, true)) return abort_transfer();
        I2C1->DR = data[index];
    }
    if (!wait_flag(&I2C1->SR1, I2C_SR1_BTF, true)) return abort_transfer();
    I2C1->CR1 |= I2C_CR1_STOP;
    return complete();
}

static bool receive(uint8_t address, uint8_t *data, uint16_t size)
{
    I2C1->CR1 |= I2C_CR1_ACK;
    if (!start_address(address, true)) return abort_transfer();
    /* RM0090 EV6/EV7 end sequences, cross-checked against ST HAL v1.8.5.
     * Protect ADDR/ACK/STOP ordering from USB and keyboard interrupts. */
    uint32_t primask = __get_PRIMASK();
    __disable_irq();
    if (size == 1u) {
        I2C1->CR1 &= ~I2C_CR1_ACK;
        clear_addr();
        I2C1->CR1 |= I2C_CR1_STOP;
    } else if (size == 2u) {
        I2C1->CR1 |= I2C_CR1_POS;
        I2C1->CR1 &= ~I2C_CR1_ACK;
        clear_addr();
    } else {
        clear_addr();
    }
    __set_PRIMASK(primask);
    while (size > 3u) {
        if (!wait_flag(&I2C1->SR1, I2C_SR1_RXNE, true)) return abort_transfer();
        *data++ = (uint8_t)I2C1->DR;
        --size;
    }
    if (size == 3u) {
        if (!wait_flag(&I2C1->SR1, I2C_SR1_BTF, true)) return abort_transfer();
        primask = __get_PRIMASK();
        __disable_irq();
        I2C1->CR1 &= ~I2C_CR1_ACK;
        *data++ = (uint8_t)I2C1->DR;
        __set_PRIMASK(primask);
        size = 2u;
    }
    if (size == 2u) {
        if (!wait_flag(&I2C1->SR1, I2C_SR1_BTF, true)) return abort_transfer();
        primask = __get_PRIMASK();
        __disable_irq();
        I2C1->CR1 |= I2C_CR1_STOP;
        *data++ = (uint8_t)I2C1->DR;
        *data = (uint8_t)I2C1->DR;
        __set_PRIMASK(primask);
    } else {
        if (!wait_flag(&I2C1->SR1, I2C_SR1_RXNE, true)) return abort_transfer();
        *data = (uint8_t)I2C1->DR;
    }
    return complete();
}

bool i2c1_read(uint8_t address, uint8_t reg, uint8_t *data, uint16_t size)
{
    if (!data || !size) return false;
    if (!begin(address) || !start_address(address, false)) return abort_transfer();
    clear_addr();
    if (!wait_flag(&I2C1->SR1, I2C_SR1_TXE, true)) return abort_transfer();
    I2C1->DR = reg;
    if (!wait_flag(&I2C1->SR1, I2C_SR1_BTF, true)) return abort_transfer();
    return receive(address, data, size);
}

bool i2c1_read_raw(uint8_t address, uint8_t *data, uint16_t size)
{
    if (!data || !size) return false;
    if (!begin(address)) return abort_transfer();
    return receive(address, data, size);
}

bool i2c1_probe(uint8_t address)
{
    if (!begin(address) || !start_address(address, false)) return abort_transfer();
    clear_addr();
    I2C1->CR1 |= I2C_CR1_STOP;
    return complete();
}

bool tca9548a_select_channel(uint8_t channel)
{
    if (channel > 7) return false;
    uint8_t control_byte = (uint8_t)(1u << channel);
    uint8_t actual;
    return i2c1_write_raw(I2C_TCA9548A_ADDR, &control_byte, 1) &&
           i2c1_read_raw(I2C_TCA9548A_ADDR, &actual, 1) && actual == control_byte;
}

bool tca9548a_select_all(void)
{
    uint8_t control_byte = 0xFF;
    return i2c1_write_raw(I2C_TCA9548A_ADDR, &control_byte, 1);
}

bool tca9548a_deselect_all(void)
{
    uint8_t control_byte = 0x00, actual;
    return i2c1_write_raw(I2C_TCA9548A_ADDR, &control_byte, 1) &&
           i2c1_read_raw(I2C_TCA9548A_ADDR, &actual, 1) && actual == 0;
}

bool tca9539_write_register(uint8_t reg, uint8_t value)
{
    return i2c1_write(I2C_TCA9539_ADDR, reg, value);
}

bool tca9539_read_register(uint8_t reg, uint8_t *value)
{
    return i2c1_read(I2C_TCA9539_ADDR, reg, value, 1);
}
