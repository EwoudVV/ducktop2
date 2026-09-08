#include "bq25798.h"
#include "i2c.h"

#define BQ25798_ADC_POLL_ATTEMPTS 100u

static bool bq25798_rmw8(uint8_t reg, uint8_t set_bits, uint8_t clear_bits)
{
    uint8_t value;
    if (!i2c1_read(BQ25798_I2C_ADDRESS_7BIT, reg, &value, 1)) {
        return false;
    }
    value = (uint8_t)((value & (uint8_t)~clear_bits) | set_bits);
    if (!i2c1_write(BQ25798_I2C_ADDRESS_7BIT, reg, value)) return false;
    uint8_t readback;
    if (!i2c1_read(BQ25798_I2C_ADDRESS_7BIT, reg, &readback, 1)) return false;
    /* WD_RST is a command bit that self-clears. */
    uint8_t mask = reg == BQ25798_REG_CHARGER_CONTROL_1 ?
                   (uint8_t)~BQ25798_REG10_WD_RST : 0xffu;
    return (value & mask) == (readback & mask);
}

uint16_t bq25798_encode_charge_current(uint16_t ma)
{
    if (ma < BQ25798_CHARGE_CURRENT_MIN_MA) ma = BQ25798_CHARGE_CURRENT_MIN_MA;
    if (ma > BQ25798_CHARGE_CURRENT_MAX_MA) ma = BQ25798_CHARGE_CURRENT_MAX_MA;
    return (uint16_t)(ma / 10u); /* ICHG, 10mA/LSB */
}

uint16_t bq25798_encode_charge_voltage(uint16_t mv)
{
    if (mv < BQ25798_CHARGE_VOLTAGE_MIN_MV) mv = BQ25798_CHARGE_VOLTAGE_MIN_MV;
    if (mv > BQ25798_CHARGE_VOLTAGE_MAX_MV) mv = BQ25798_CHARGE_VOLTAGE_MAX_MV;
    return (uint16_t)(mv / 10u); /* VREG, 10mV/LSB */
}

uint16_t bq25798_encode_input_current(uint16_t ma)
{
    if (ma < BQ25798_INPUT_CURRENT_MIN_MA) ma = BQ25798_INPUT_CURRENT_MIN_MA;
    if (ma > BQ25798_INPUT_CURRENT_MAX_MA) ma = BQ25798_INPUT_CURRENT_MAX_MA;
    return (uint16_t)(ma / 10u); /* IINDPM, 10mA/LSB */
}

uint8_t bq25798_encode_vsysmin(uint16_t mv)
{
    if (mv < BQ25798_VSYSMIN_MIN_MV) mv = BQ25798_VSYSMIN_MIN_MV;
    if (mv > BQ25798_VSYSMIN_MAX_MV) mv = BQ25798_VSYSMIN_MAX_MV;
    return (uint8_t)((mv - BQ25798_VSYSMIN_MIN_MV) / 250u); /* 250mV/LSB */
}

bq25798_charge_status_t bq25798_charge_status_decode(uint8_t reg1c)
{
    return (bq25798_charge_status_t)((reg1c & BQ25798_REG1C_CHG_STAT_MASK) >> 5);
}

bool bq25798_is_charge_in_progress(bq25798_charge_status_t status)
{
    switch (status) {
    case BQ25798_CHARGE_TRICKLE:
    case BQ25798_CHARGE_PRECHARGE:
    case BQ25798_CHARGE_FAST:
    case BQ25798_CHARGE_TAPER:
    case BQ25798_CHARGE_TOPOFF:
        return true;
    case BQ25798_CHARGE_NONE:
    case BQ25798_CHARGE_RESERVED:
    case BQ25798_CHARGE_TERMINATED:
    default:
        return false;
    }
}

bool bq25798_charge_done(bq25798_charge_status_t status)
{
    return status == BQ25798_CHARGE_TERMINATED;
}

bool bq25798_probe(void)
{
    uint8_t part_info;
    if (!i2c1_read(BQ25798_I2C_ADDRESS_7BIT, BQ25798_REG_PART_INFORMATION,
                   &part_info, 1)) {
        return false;
    }
    return (part_info & BQ25798_REG48_PN_MASK) == BQ25798_REG48_PN_BQ25798;
}

bool bq25798_init(void)
{
    /* Both charge gates start off. Real thermistors must gate charging. */
    if (!bq25798_set_charge_enable(false) ||
        !bq25798_rmw8(BQ25798_REG_NTC_CONTROL_1, 0, BQ25798_REG18_TS_IGNORE)) {
        return false;
    }
    /* Fail-safe: I2C watchdog expiry must stop charging (EC is the charge
     * manager; if it dies the charger must not continue unattended). */
    if (!bq25798_rmw8(BQ25798_REG_TERMINATION_CONTROL,
                      BQ25798_REG09_STOP_WD_CHG, 0)) {
        return false;
    }
    /* Q25 ship FET is populated and IBAT sense is wanted in battery-only
     * mode (ship FET on SDRV, EN_IBAT enables IBAT ADC discharging sense). */
    if (!bq25798_rmw8(BQ25798_REG_CHARGER_CONTROL_5,
                      BQ25798_REG14_SFET_PRESENT | BQ25798_REG14_EN_IBAT, 0)) {
        return false;
    }
    return bq25798_rmw8(BQ25798_REG_CHARGER_CONTROL_1,
        BQ25798_WATCHDOG_40_S | BQ25798_REG10_WD_RST, BQ25798_REG10_WATCHDOG_MASK);
}

bool bq25798_set_charge_current_ma(uint16_t ma)
{
    if (ma < BQ25798_CHARGE_CURRENT_MIN_MA ||
        ma > BQ25798_CHARGE_CURRENT_MAX_MA) {
        return false;
    }
    uint16_t reg = bq25798_encode_charge_current(ma);
    uint8_t data[3] = {BQ25798_REG_CHARGE_CURRENT_LIMIT,
                       (uint8_t)(reg >> 8), (uint8_t)(reg & 0xFFu)};
    return i2c1_write_raw(BQ25798_I2C_ADDRESS_7BIT, data, 3);
}

bool bq25798_set_charge_voltage_mv(uint16_t mv)
{
    if (mv < BQ25798_CHARGE_VOLTAGE_MIN_MV ||
        mv > BQ25798_CHARGE_VOLTAGE_MAX_MV) {
        return false;
    }
    uint16_t reg = bq25798_encode_charge_voltage(mv);
    uint8_t data[3] = {BQ25798_REG_CHARGE_VOLTAGE_LIMIT,
                       (uint8_t)(reg >> 8), (uint8_t)(reg & 0xFFu)};
    return i2c1_write_raw(BQ25798_I2C_ADDRESS_7BIT, data, 3);
}

bool bq25798_set_input_current_ma(uint16_t ma)
{
    if (ma < BQ25798_INPUT_CURRENT_MIN_MA ||
        ma > BQ25798_INPUT_CURRENT_MAX_MA) {
        return false;
    }
    uint16_t reg = bq25798_encode_input_current(ma);
    uint8_t data[3] = {BQ25798_REG_INPUT_CURRENT_LIMIT,
                       (uint8_t)(reg >> 8), (uint8_t)(reg & 0xFFu)};
    return i2c1_write_raw(BQ25798_I2C_ADDRESS_7BIT, data, 3);
}

bool bq25798_read_input_current_limit_ma(uint16_t *ma_out)
{
    uint8_t data[2];
    if (ma_out == NULL ||
        !i2c1_read(BQ25798_I2C_ADDRESS_7BIT, BQ25798_REG_INPUT_CURRENT_LIMIT,
                   data, 2)) {
        return false;
    }
    *ma_out = (uint16_t)(((uint16_t)(data[0] & 0x01u) << 8 | data[1]) * 10u);
    return true;
}

bool bq25798_set_charge_enable(bool enable)
{
    return bq25798_rmw8(BQ25798_REG_CHARGER_CONTROL_0,
                        enable ? BQ25798_REG0F_EN_CHG : 0,
                        enable ? 0 : BQ25798_REG0F_EN_CHG);
}

bool bq25798_is_charging(void)
{
    uint8_t reg1c;
    if (!i2c1_read(BQ25798_I2C_ADDRESS_7BIT, BQ25798_REG_CHARGER_STATUS_1,
                   &reg1c, 1)) {
        return false;
    }
    return bq25798_is_charge_in_progress(bq25798_charge_status_decode(reg1c));
}

bool bq25798_battery_present(void)
{
    uint8_t reg1d;
    if (!i2c1_read(BQ25798_I2C_ADDRESS_7BIT, BQ25798_REG_CHARGER_STATUS_2,
                   &reg1d, 1)) {
        return false;
    }
    return (reg1d & BQ25798_REG1D_VBAT_PRESENT_STAT) != 0;
}

bool bq25798_vbus_present(void)
{
    uint8_t reg1b;
    if (!i2c1_read(BQ25798_I2C_ADDRESS_7BIT, BQ25798_REG_CHARGER_STATUS_0,
                   &reg1b, 1)) {
        return false;
    }
    return (reg1b & BQ25798_REG1B_VBUS_PRESENT_STAT) != 0;
}

bool bq25798_power_good(void)
{
    uint8_t reg1b;
    if (!i2c1_read(BQ25798_I2C_ADDRESS_7BIT, BQ25798_REG_CHARGER_STATUS_0,
                   &reg1b, 1)) {
        return false;
    }
    return (reg1b & BQ25798_REG1B_PG_STAT) != 0;
}

bool bq25798_pet_watchdog(void)
{
    return bq25798_rmw8(BQ25798_REG_CHARGER_CONTROL_1, BQ25798_REG10_WD_RST,
                        0);
}

static bool bq25798_read_adc_u16(uint8_t reg, uint16_t *value_out)
{
    uint8_t data[2];
    if (!i2c1_read(BQ25798_I2C_ADDRESS_7BIT, reg, data, 2)) {
        return false;
    }
    *value_out = (uint16_t)((uint16_t)data[0] << 8 | data[1]);
    return true;
}

bool bq25798_start_sample(void)
{
    return i2c1_write(BQ25798_I2C_ADDRESS_7BIT, BQ25798_REG_ADC_CONTROL,
                      BQ25798_REG2E_ADC_EN | BQ25798_REG2E_ADC_RATE |
                      BQ25798_ADC_SAMPLE_13_BIT);
}

static bool read_adc(uint16_t *ibus_ma, int16_t *ibat_ma, uint16_t *vbus_mv,
                      uint16_t *vbat_mv, uint16_t *vsys_mv)
{
    uint16_t ibus;
    uint16_t ibat;
    uint16_t vbus;
    uint16_t vbat;
    if (!bq25798_read_adc_u16(BQ25798_REG_IBUS_ADC, &ibus) ||
        !bq25798_read_adc_u16(BQ25798_REG_IBAT_ADC, &ibat) ||
        !bq25798_read_adc_u16(BQ25798_REG_VBUS_ADC, &vbus) ||
        !bq25798_read_adc_u16(BQ25798_REG_VBAT_ADC, &vbat) ||
        !bq25798_read_adc_u16(BQ25798_REG_VSYS_ADC, vsys_mv)) {
        return false;
    }

    /* Gate the ADC off until the next trigger; keep one-shot rate selected. */
    (void)i2c1_write(BQ25798_I2C_ADDRESS_7BIT, BQ25798_REG_ADC_CONTROL,
                     BQ25798_REG2E_ADC_RATE);

    *ibus_ma = ibus;
    *ibat_ma = (int16_t)ibat;
    *vbus_mv = vbus;
    *vbat_mv = vbat;
    return true;
}

bool bq25798_read_sample(bq25798_telemetry_t *telemetry, bool *complete)
{
    if (telemetry == NULL || complete == NULL) return false;
    *complete = false;
    uint8_t done;
    if (!i2c1_read(BQ25798_I2C_ADDRESS_7BIT, BQ25798_REG_CHARGER_STATUS_3,
                   &done, 1)) return false;
    if ((done & BQ25798_REG1E_ADC_DONE_STAT) == 0u) return true;

    uint8_t reg1b;
    uint8_t reg1c;
    uint8_t reg1d;
    uint8_t reg20;
    uint8_t reg21;
    if (!i2c1_read(BQ25798_I2C_ADDRESS_7BIT, BQ25798_REG_CHARGER_STATUS_0,
                   &reg1b, 1) ||
        !i2c1_read(BQ25798_I2C_ADDRESS_7BIT, BQ25798_REG_CHARGER_STATUS_1,
                   &reg1c, 1) ||
        !i2c1_read(BQ25798_I2C_ADDRESS_7BIT, BQ25798_REG_CHARGER_STATUS_2,
                   &reg1d, 1) ||
        !i2c1_read(BQ25798_I2C_ADDRESS_7BIT, BQ25798_REG_FAULT_STATUS_0,
                   &reg20, 1) ||
        !i2c1_read(BQ25798_I2C_ADDRESS_7BIT, BQ25798_REG_FAULT_STATUS_1,
                   &reg21, 1)) {
        return false;
    }

    uint16_t ibus_ma;
    int16_t ibat_ma;
    uint16_t vbus_mv;
    uint16_t vbat_mv;
    if (!read_adc(&ibus_ma, &ibat_ma, &vbus_mv, &vbat_mv, &telemetry->vsys_mv)) {
        return false;
    }

    telemetry->vbus_present =
        (reg1b & BQ25798_REG1B_VBUS_PRESENT_STAT) != 0;
    telemetry->power_good = (reg1b & BQ25798_REG1B_PG_STAT) != 0;
    telemetry->battery_present =
        (reg1d & BQ25798_REG1D_VBAT_PRESENT_STAT) != 0;
    telemetry->charge_status =
        bq25798_charge_status_decode(reg1c);
    telemetry->fault = (reg20 | reg21) != 0;
    telemetry->ibus_ma = (int16_t)ibus_ma;
    telemetry->ibat_ma = ibat_ma;
    telemetry->vbus_mv = vbus_mv;
    telemetry->vbat_mv = vbat_mv;

    *complete = true;
    return bq25798_pet_watchdog();
}

/* Synchronous diagnostic API. The target uses start_sample/read_sample so
 * ADC conversion never stalls USB or watchdog service. */
bool bq25798_read_telemetry(bq25798_telemetry_t *telemetry)
{
    if (!telemetry || !bq25798_start_sample()) return false;
    for (unsigned i = 0; i < BQ25798_ADC_POLL_ATTEMPTS; ++i) {
        bool complete;
        if (!bq25798_read_sample(telemetry, &complete)) return false;
        if (complete) return true;
    }
    return false;
}

bool bq25798_read_charge_limits(uint16_t *voltage_mv, uint16_t *current_ma)
{
    uint16_t v, i;
    if (!voltage_mv || !current_ma ||
        !bq25798_read_adc_u16(BQ25798_REG_CHARGE_VOLTAGE_LIMIT, &v) ||
        !bq25798_read_adc_u16(BQ25798_REG_CHARGE_CURRENT_LIMIT, &i)) return false;
    *voltage_mv = (v & 0x7ffu) * 10u;
    *current_ma = (i & 0x1ffu) * 10u;
    return true;
}
