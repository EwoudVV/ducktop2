#include "bq34z100.h"
#include "i2c.h"

static bool gauge_write_reg2(uint8_t reg, uint16_t value)
{
    uint8_t data[3] = {reg, (uint8_t)(value & 0xFFu), (uint8_t)(value >> 8)};
    return i2c1_write_raw(BQ34Z100_I2C_ADDRESS_7BIT, data, 3);
}

static bool gauge_read_reg2(uint8_t reg, uint16_t *value_out)
{
    uint8_t data[2];
    if (value_out == NULL ||
        !i2c1_read(BQ34Z100_I2C_ADDRESS_7BIT, reg, data, 2)) {
        return false;
    }
    *value_out = (uint16_t)(data[0] | (uint16_t)(data[1] << 8));
    return true;
}

static bool gauge_read_reg1(uint8_t reg, uint8_t *value_out)
{
    if (value_out == NULL) {
        return false;
    }
    return i2c1_read(BQ34Z100_I2C_ADDRESS_7BIT, reg, value_out, 1);
}

uint8_t bq34z100_checksum(const uint8_t *block, uint8_t len)
{
    uint8_t sum = 0u;
    for (uint8_t i = 0; i < len; i++) {
        sum = (uint8_t)(sum + block[i]);
    }
    return (uint8_t)(0xFFu - sum);
}

bool bq34z100_block_checksum_valid(const uint8_t *block, uint8_t len,
                                   uint8_t checksum)
{
    return bq34z100_checksum(block, len) == checksum;
}

int16_t bq34z100_current_ma_decode(uint8_t lo, uint8_t hi)
{
    return (int16_t)(uint16_t)(lo | (uint16_t)(hi << 8));
}

int16_t bq34z100_temperature_deci_c(uint16_t temperature_0_1k)
{
    return (int16_t)(((int32_t)temperature_0_1k * 10 - 27315) / 10);
}

bool bq34z100_time_available(uint16_t gauge_minutes)
{
    return gauge_minutes != BQ34Z100_TIME_UNAVAILABLE;
}

bool bq34z100_flags_charging(uint16_t flags)
{
    return (flags & BQ34Z100_FLAG_CHG) != 0;
}

bool bq34z100_flags_discharging(uint16_t flags)
{
    return (flags & BQ34Z100_FLAG_DSG) != 0;
}

bool bq34z100_flags_full(uint16_t flags)
{
    return (flags & BQ34Z100_FLAG_FC) != 0;
}

bool bq34z100_control_read(uint16_t subcommand, uint16_t *value_out)
{
    if (!gauge_write_reg2(BQ34Z100_REG_CONTROL, subcommand)) {
        return false;
    }
    return gauge_read_reg2(BQ34Z100_REG_CONTROL, value_out);
}

bool bq34z100_probe(void)
{
    uint16_t device_type;
    if (!i2c1_probe(BQ34Z100_I2C_ADDRESS_7BIT)) {
        return false;
    }
    if (!bq34z100_control_read(BQ34Z100_CONTROL_DEVICE_TYPE, &device_type)) {
        return false;
    }
    return device_type == BQ34Z100_DEVICE_TYPE_VALUE;
}

bool bq34z100_read_soc_percent(uint8_t *soc_percent)
{
    return gauge_read_reg1(BQ34Z100_REG_STATE_OF_CHARGE, soc_percent);
}

bool bq34z100_read_voltage_mv(uint16_t *voltage_mv)
{
    return gauge_read_reg2(BQ34Z100_REG_VOLTAGE, voltage_mv);
}

bool bq34z100_read_current_ma(int16_t *current_ma)
{
    uint16_t raw;
    if (current_ma == NULL ||
        !gauge_read_reg2(BQ34Z100_REG_CURRENT, &raw)) {
        return false;
    }
    *current_ma = (int16_t)raw;
    return true;
}

bool bq34z100_read_average_current_ma(int16_t *average_current_ma)
{
    uint16_t raw;
    if (average_current_ma == NULL ||
        !gauge_read_reg2(BQ34Z100_REG_AVERAGE_CURRENT, &raw)) {
        return false;
    }
    *average_current_ma = (int16_t)raw;
    return true;
}

bool bq34z100_read_temperature(int16_t *temperature_deci_c)
{
    uint16_t raw;
    if (temperature_deci_c == NULL ||
        !gauge_read_reg2(BQ34Z100_REG_TEMPERATURE, &raw)) {
        return false;
    }
    *temperature_deci_c = bq34z100_temperature_deci_c(raw);
    return true;
}

bool bq34z100_read_flags(uint16_t *flags)
{
    return gauge_read_reg2(BQ34Z100_REG_FLAGS, flags);
}

bool bq34z100_read_remaining_capacity_mah(uint16_t *capacity_mah)
{
    return gauge_read_reg2(BQ34Z100_REG_REMAINING_CAPACITY, capacity_mah);
}

bool bq34z100_read_full_capacity_mah(uint16_t *capacity_mah)
{
    return gauge_read_reg2(BQ34Z100_REG_FULL_CHARGE_CAPACITY, capacity_mah);
}

bool bq34z100_read_time_to_empty(uint16_t *minutes)
{
    return gauge_read_reg2(BQ34Z100_REG_TIME_TO_EMPTY, minutes);
}

bool bq34z100_read_time_to_full(uint16_t *minutes)
{
    return gauge_read_reg2(BQ34Z100_REG_TIME_TO_FULL, minutes);
}

bool bq34z100_read_cycle_count(uint16_t *cycle_count)
{
    return gauge_read_reg2(BQ34Z100_REG_CYCLE_COUNT, cycle_count);
}

bool bq34z100_read_health_percent(uint8_t *health_percent)
{
    return gauge_read_reg1(BQ34Z100_REG_STATE_OF_HEALTH, health_percent);
}

bool bq34z100_dataflash_read_block(uint8_t df_class, uint8_t df_block,
                                   uint8_t *data_out,
                                   uint8_t *checksum_out)
{
    if (data_out == NULL || checksum_out == NULL) {
        return false;
    }
    if (!i2c1_write(BQ34Z100_I2C_ADDRESS_7BIT, BQ34Z100_REG_BLOCK_DATA_CONTROL,
                    0x00)) {
        return false;
    }
    if (!i2c1_write(BQ34Z100_I2C_ADDRESS_7BIT,
                    BQ34Z100_REG_DATA_FLASH_CLASS, df_class)) {
        return false;
    }
    if (!i2c1_write(BQ34Z100_I2C_ADDRESS_7BIT,
                    BQ34Z100_REG_DATA_FLASH_BLOCK, df_block)) {
        return false;
    }
    if (!i2c1_read(BQ34Z100_I2C_ADDRESS_7BIT, BQ34Z100_REG_BLOCK_DATA,
                   data_out, 32)) {
        return false;
    }
    return i2c1_read(BQ34Z100_I2C_ADDRESS_7BIT,
                     BQ34Z100_REG_BLOCK_DATA_CHECKSUM, checksum_out, 1);
}
