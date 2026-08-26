#include "i2c.h"

#include <stddef.h>

static uint8_t s_output0;
static bool s_initialized;

bool tca9539_init_safe(void)
{
    uint8_t output0;
    uint8_t config0;
    uint8_t config1;

    s_output0 = 0u;
    s_initialized = false;

    /* Latches must be low before P0.0/P0.1 become outputs. */
    if (!tca9539_write_register(TCA9539_REG_OUTPUT0, 0u) ||
        !tca9539_write_register(TCA9539_REG_OUTPUT1, 0u) ||
        !tca9539_write_register(TCA9539_REG_CONFIG0, 0xFCu) ||
        !tca9539_write_register(TCA9539_REG_CONFIG1, 0xFEu) ||
        !tca9539_read_register(TCA9539_REG_OUTPUT0, &output0) ||
        !tca9539_read_register(TCA9539_REG_CONFIG0, &config0) ||
        !tca9539_read_register(TCA9539_REG_CONFIG1, &config1)) {
        return false;
    }
    if (output0 != 0u || config0 != 0xFCu || config1 != 0xFEu) {
        return false;
    }

    s_initialized = true;
    return true;
}

bool tca9539_set_pd_path_enable(uint8_t path, bool enable)
{
    uint8_t mask;
    uint8_t next;

    if (!s_initialized || path > 1u) {
        return false;
    }

    mask = (uint8_t)(1u << path);
    next = enable ? (uint8_t)(s_output0 | mask)
                  : (uint8_t)(s_output0 & (uint8_t)~mask);
    if (!tca9539_write_register(TCA9539_REG_OUTPUT0, next)) {
        return false;
    }
    s_output0 = next;
    return true;
}

bool tca9539_read_inputs(uint8_t *port0, uint8_t *port1)
{
    return port0 != NULL && port1 != NULL &&
           tca9539_read_register(TCA9539_REG_INPUT0, port0) &&
           tca9539_read_register(TCA9539_REG_INPUT1, port1);
}
