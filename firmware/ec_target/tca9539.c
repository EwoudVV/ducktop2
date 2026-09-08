#include "i2c.h"

#include <stddef.h>

static uint8_t s_output0;
static bool s_initialized;
static uint8_t s_output1;

bool tca9539_init_safe(void)
{
    uint8_t output0, output1;
    uint8_t config0;
    uint8_t config1;

    s_output0 = 0u;
    s_output1 = 0u;
    s_initialized = false;

    /* Latches must be low before P0.0/P0.1 become outputs. */
    if (!tca9539_write_register(TCA9539_REG_OUTPUT0, 0u) ||
        !tca9539_write_register(TCA9539_REG_OUTPUT1, 0u) ||
        !tca9539_read_register(TCA9539_REG_OUTPUT0, &output0) ||
        !tca9539_read_register(TCA9539_REG_OUTPUT1, &output1) ||
        output0 != 0u || output1 != 0u ||
        !tca9539_write_register(TCA9539_REG_CONFIG0, 0xFCu) ||
        !tca9539_write_register(TCA9539_REG_CONFIG1, 0xFEu) ||
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
    /* Two asserted selectors are forbidden even if the caller is wrong. */
    if ((next & 3u) == 3u) return false;
    uint8_t readback;
    if (!tca9539_write_register(TCA9539_REG_OUTPUT0, next) ||
        !tca9539_read_register(TCA9539_REG_OUTPUT0, &readback) || readback != next) {
        s_initialized = false;
        return false;
    }
    s_output0 = next;
    return true;
}

bool tca9539_read_inputs(uint8_t *port0, uint8_t *port1)
{
    if (port0 == NULL || port1 == NULL) return false;
    *port0 = 0u;
    *port1 = 0u;
    return tca9539_verify_state() &&
           tca9539_read_register(TCA9539_REG_INPUT0, port0) &&
           tca9539_read_register(TCA9539_REG_INPUT1, port1);
}

bool tca9539_verify_state(void)
{
    uint8_t out0, out1, cfg0, cfg1;
    bool ok = s_initialized &&
        tca9539_read_register(TCA9539_REG_OUTPUT0, &out0) &&
        tca9539_read_register(TCA9539_REG_OUTPUT1, &out1) &&
        tca9539_read_register(TCA9539_REG_CONFIG0, &cfg0) &&
        tca9539_read_register(TCA9539_REG_CONFIG1, &cfg1) &&
        out0 == s_output0 && out1 == s_output1 && cfg0 == 0xfcu && cfg1 == 0xfeu;
    if (!ok) s_initialized = false;
    return ok;
}

bool tca9539_set_bms_retry(bool asserted)
{
    uint8_t readback, next = asserted ? 1u : 0u;
    if (!s_initialized || !tca9539_write_register(TCA9539_REG_OUTPUT1, next) ||
        !tca9539_read_register(TCA9539_REG_OUTPUT1, &readback) || readback != next) {
        s_initialized = false;
        return false;
    }
    s_output1 = next;
    return true;
}

bool tca9539_ready(void)
{
    return s_initialized;
}

uint8_t tca9539_output0(void)
{
    return s_output0;
}
