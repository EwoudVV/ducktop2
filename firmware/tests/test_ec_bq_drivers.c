/*
 * Host tests for the target-side BQ25798 charger and BQ34Z100-G1 fuel gauge
 * drivers (firmware/ec_target/bq25798.c, bq34z100.c).
 *
 * Pure C, no hardware: the I2C1 bus is faked by tests/i2c_mock.c, so both
 * the pure encode/decode layer and the full driver transactions (register
 * sequences, readback, fault injection) are exercised on the host.
 */

#include "bq25798.h"
#include "bq34z100.h"
#include "i2c_mock.h"

#include <stdio.h>
#include <string.h>

static int failures;

#define CHECK(expression)                                                      \
  do {                                                                        \
    if (!(expression)) {                                                      \
      fprintf(stderr, "%s:%d: CHECK failed: %s\n", __FILE__, __LINE__,         \
              #expression);                                                   \
      ++failures;                                                             \
    }                                                                         \
  } while (0)

/* ---------------- BQ25798 pure encode/decode ---------------- */

static void test_bq25798_encode_charge_current(void) {
  CHECK(bq25798_encode_charge_current(0) == 5u);     /* clamp 50mA */
  CHECK(bq25798_encode_charge_current(49) == 5u);    /* clamp 50mA */
  CHECK(bq25798_encode_charge_current(50) == 5u);    /* 50mA -> 5 */
  CHECK(bq25798_encode_charge_current(440) == 44u);  /* 10mA/LSB */
  CHECK(bq25798_encode_charge_current(499) == 49u);  /* floor to step */
  CHECK(bq25798_encode_charge_current(5000) == 500u);
  CHECK(bq25798_encode_charge_current(5001) == 500u); /* clamp 5000mA */
}

static void test_bq25798_encode_charge_voltage(void) {
  CHECK(bq25798_encode_charge_voltage(0) == 300u);    /* clamp 3000mV */
  CHECK(bq25798_encode_charge_voltage(2999) == 300u); /* clamp 3000mV */
  CHECK(bq25798_encode_charge_voltage(3000) == 300u); /* 10mV/LSB */
  CHECK(bq25798_encode_charge_voltage(4200) == 420u);
  CHECK(bq25798_encode_charge_voltage(12500) == 1250u);
  CHECK(bq25798_encode_charge_voltage(18800) == 1880u);
  CHECK(bq25798_encode_charge_voltage(18801) == 1880u); /* clamp 18800mV */
}

static void test_bq25798_encode_input_current(void) {
  CHECK(bq25798_encode_input_current(0) == 10u);     /* clamp 100mA */
  CHECK(bq25798_encode_input_current(99) == 10u);    /* clamp 100mA */
  CHECK(bq25798_encode_input_current(100) == 10u);   /* 10mA/LSB */
  CHECK(bq25798_encode_input_current(500) == 50u);
  CHECK(bq25798_encode_input_current(3000) == 300u);
  CHECK(bq25798_encode_input_current(3300) == 330u);
  CHECK(bq25798_encode_input_current(3301) == 330u); /* clamp 3300mA */
}

static void test_bq25798_encode_vsysmin(void) {
  CHECK(bq25798_encode_vsysmin(0) == 0u);      /* clamp 2500mV */
  CHECK(bq25798_encode_vsysmin(2499) == 0u);   /* clamp 2500mV */
  CHECK(bq25798_encode_vsysmin(2500) == 0u);   /* 250mV/LSB, offset 2500 */
  CHECK(bq25798_encode_vsysmin(9000) == 26u);
  CHECK(bq25798_encode_vsysmin(16000) == 54u);
  CHECK(bq25798_encode_vsysmin(16001) == 54u); /* clamp 16000mV */
}

static void test_bq25798_charge_status_decode(void) {
  CHECK(bq25798_charge_status_decode(0x00u) == BQ25798_CHARGE_NONE);
  CHECK(bq25798_charge_status_decode(0x20u) == BQ25798_CHARGE_TRICKLE);
  CHECK(bq25798_charge_status_decode(0x40u) == BQ25798_CHARGE_PRECHARGE);
  CHECK(bq25798_charge_status_decode(0x60u) == BQ25798_CHARGE_FAST);
  CHECK(bq25798_charge_status_decode(0x80u) == BQ25798_CHARGE_TAPER);
  CHECK(bq25798_charge_status_decode(0xA0u) == BQ25798_CHARGE_RESERVED);
  CHECK(bq25798_charge_status_decode(0xC0u) == BQ25798_CHARGE_TOPOFF);
  CHECK(bq25798_charge_status_decode(0xE0u) == BQ25798_CHARGE_TERMINATED);
  /* Lower bits in REG1C must not leak into the 3-bit field. */
  CHECK(bq25798_charge_status_decode(0x65u) == BQ25798_CHARGE_FAST);
}

static void test_bq25798_charge_state_classification(void) {
  CHECK(bq25798_is_charge_in_progress(BQ25798_CHARGE_NONE) == false);
  CHECK(bq25798_is_charge_in_progress(BQ25798_CHARGE_TRICKLE) == true);
  CHECK(bq25798_is_charge_in_progress(BQ25798_CHARGE_PRECHARGE) == true);
  CHECK(bq25798_is_charge_in_progress(BQ25798_CHARGE_FAST) == true);
  CHECK(bq25798_is_charge_in_progress(BQ25798_CHARGE_TAPER) == true);
  CHECK(bq25798_is_charge_in_progress(BQ25798_CHARGE_RESERVED) == false);
  CHECK(bq25798_is_charge_in_progress(BQ25798_CHARGE_TOPOFF) == true);
  CHECK(bq25798_is_charge_in_progress(BQ25798_CHARGE_TERMINATED) == false);
  CHECK(bq25798_charge_done(BQ25798_CHARGE_TERMINATED) == true);
  CHECK(bq25798_charge_done(BQ25798_CHARGE_FAST) == false);
  CHECK(bq25798_charge_done(BQ25798_CHARGE_NONE) == false);
}

/* ---------------- BQ25798 hardware paths (mock I2C) ---------------- */

static void test_bq25798_probe(void) {
  i2c_mock_begin();
  i2c_mock.regfile[BQ25798_REG_PART_INFORMATION] = 0x19u; /* PN=011 rev=001 */
  CHECK(bq25798_probe());
  CHECK(i2c_mock.reads == 1u);
  CHECK(i2c_mock_script_complete());

  i2c_mock_begin();
  i2c_mock.regfile[BQ25798_REG_PART_INFORMATION] = 0x11u; /* PN=010: not 25798 */
  CHECK(!bq25798_probe());

  i2c_mock_begin();
  i2c_mock.nack_all = true;
  CHECK(!bq25798_probe());
}

static void test_bq25798_init_config_bits(void) {
  i2c_mock_begin();
  /* POR defaults: REG18=0x54, REG09=0x05, REG14=0x16, REG10=0x05. */
  i2c_mock.regfile[0x18u] = 0x54u;
  i2c_mock.regfile[0x09u] = 0x05u;
  i2c_mock.regfile[0x14u] = 0x16u;
  i2c_mock.regfile[0x10u] = 0x05u;
  CHECK(bq25798_init());
  CHECK(i2c_mock.regfile[0x18u] == 0x55u); /* TS_IGNORE=1, other bits kept */
  CHECK(i2c_mock.regfile[0x09u] == 0x25u); /* STOP_WD_CHG=1, ITERM kept */
  CHECK(i2c_mock.regfile[0x14u] == 0xB6u); /* SFET_PRESENT + EN_IBAT */
  CHECK(i2c_mock.regfile[0x10u] == 0x0Du); /* WD_RST written, WATCHDOG kept */
  CHECK(i2c_mock.reads == 4u);
  CHECK(i2c_mock.writes == 4u);
  CHECK(i2c_mock_script_complete());

  i2c_mock_begin();
  i2c_mock.nack_all = true;
  CHECK(!bq25798_init());
}

static void test_bq25798_setters(void) {
  i2c_mock_begin();
  CHECK(bq25798_set_charge_current_ma(440u));
  CHECK(i2c_mock.regfile[0x03u] == 0x2Cu); /* 440mA -> 44 = 0x2C */
  CHECK(i2c_mock.regfile[0x04u] == 0x00u);
  CHECK(i2c_mock.write_raws == 1u);

  i2c_mock_begin();
  CHECK(!bq25798_set_charge_current_ma(45u));   /* below 50mA range */
  CHECK(!bq25798_set_charge_current_ma(5001u)); /* above 5000mA range */
  CHECK(i2c_mock.write_raws == 0u);

  i2c_mock_begin();
  CHECK(bq25798_set_charge_voltage_mv(12600u));
  CHECK(i2c_mock.regfile[0x01u] == 0xECu); /* 12600/10=1260=0x04EC, LE */
  CHECK(i2c_mock.regfile[0x02u] == 0x04u);
  CHECK(!bq25798_set_charge_voltage_mv(2999u));
  CHECK(!bq25798_set_charge_voltage_mv(18801u));

  i2c_mock_begin();
  CHECK(bq25798_set_input_current_ma(3000u));
  CHECK(i2c_mock.regfile[0x06u] == 0x2Cu); /* 300=0x12C, LE */
  CHECK(i2c_mock.regfile[0x07u] == 0x01u);
  CHECK(!bq25798_set_input_current_ma(99u));
  CHECK(!bq25798_set_input_current_ma(3301u));

  i2c_mock_begin();
  i2c_mock.regfile[0x06u] = 0x2Cu;
  i2c_mock.regfile[0x07u] = 0x01u;
  uint16_t readback = 0u;
  CHECK(bq25798_read_input_current_limit_ma(&readback));
  CHECK(readback == 3000u);
  CHECK(bq25798_read_input_current_limit_ma(NULL) == false);

  i2c_mock_begin();
  i2c_mock.regfile[0x0Fu] = 0x02u;
  CHECK(bq25798_set_charge_enable(true));
  CHECK(i2c_mock.regfile[0x0Fu] == 0x22u); /* EN_CHG set, EN_TERM kept */
  CHECK(bq25798_set_charge_enable(false));
  CHECK(i2c_mock.regfile[0x0Fu] == 0x02u); /* EN_CHG cleared */
}

static void test_bq25798_status_helpers(void) {
  i2c_mock_begin();
  i2c_mock.regfile[0x1Cu] = 0x60u; /* FAST charge */
  CHECK(bq25798_is_charging());
  i2c_mock.regfile[0x1Cu] = 0xC0u; /* top-off */
  CHECK(bq25798_is_charging());
  i2c_mock.regfile[0x1Cu] = 0xE0u; /* terminated: not charging */
  CHECK(!bq25798_is_charging());
  i2c_mock.regfile[0x1Cu] = 0x00u;
  CHECK(!bq25798_is_charging());

  i2c_mock.regfile[0x1Du] = 0x01u;
  CHECK(bq25798_battery_present());
  i2c_mock.regfile[0x1Du] = 0x00u;
  CHECK(!bq25798_battery_present());

  i2c_mock.regfile[0x1Bu] = 0x09u; /* PG + VBUS present */
  CHECK(bq25798_vbus_present());
  CHECK(bq25798_power_good());
  i2c_mock.regfile[0x1Bu] = 0x00u;
  CHECK(!bq25798_vbus_present());
  CHECK(!bq25798_power_good());
  CHECK(i2c_mock_script_complete());

  i2c_mock_begin();
  i2c_mock.nack_all = true;
  CHECK(!bq25798_is_charging()); /* read failure reads as "not charging" */
  CHECK(!bq25798_battery_present());
  CHECK(!bq25798_vbus_present());
  CHECK(!bq25798_power_good());
}

static void test_bq25798_pet_watchdog(void) {
  i2c_mock_begin();
  i2c_mock.regfile[0x10u] = 0x05u; /* WATCHDOG=40s default */
  CHECK(bq25798_pet_watchdog());
  CHECK(i2c_mock.regfile[0x10u] == 0x0Du); /* WD_RST self-clears in part */

  i2c_mock_begin();
  i2c_mock.nack_all = true;
  CHECK(!bq25798_pet_watchdog());
}

static void test_bq25798_read_telemetry(void) {
  i2c_mock_begin();
  i2c_mock.regfile[0x1Bu] = 0x09u; /* PG_STAT + VBUS_PRESENT */
  i2c_mock.regfile[0x1Cu] = 0x60u; /* FAST charge */
  i2c_mock.regfile[0x1Du] = 0x01u; /* VBAT present */
  i2c_mock.regfile[0x20u] = 0x00u;
  i2c_mock.regfile[0x21u] = 0x00u;
  i2c_mock.regfile[0x31u] = 0x64u; /* IBUS 100mA */
  i2c_mock.regfile[0x32u] = 0x00u;
  i2c_mock.regfile[0x33u] = 0xDCu; /* IBAT +1500mA */
  i2c_mock.regfile[0x34u] = 0x05u;
  i2c_mock.regfile[0x35u] = 0x38u; /* VBUS 19000mV */
  i2c_mock.regfile[0x36u] = 0x4Au;
  i2c_mock.regfile[0x3Bu] = 0xD4u; /* VBAT 12500mV */
  i2c_mock.regfile[0x3Cu] = 0x30u;

  bq25798_telemetry_t t;
  memset(&t, 0, sizeof(t));
  CHECK(bq25798_read_telemetry(&t));
  CHECK(t.vbus_present);
  CHECK(t.power_good);
  CHECK(t.battery_present);
  CHECK(t.charge_status == BQ25798_CHARGE_FAST);
  CHECK(!t.fault);
  CHECK(t.ibus_ma == 100);
  CHECK(t.ibat_ma == 1500);
  CHECK(t.vbus_mv == 19000u);
  CHECK(t.vbat_mv == 12500u);
  /* ADC gated off after the one-shot, one-shot rate kept; WD petted. */
  CHECK(i2c_mock.regfile[0x2Eu] == 0x40u);
  CHECK((i2c_mock.regfile[0x10u] & 0x08u) != 0u);
  CHECK(i2c_mock_script_complete());
}

static void test_bq25798_read_telemetry_signed_and_fault(void) {
  i2c_mock_begin();
  i2c_mock.regfile[0x20u] = 0x20u; /* VBAT_OVP fault status */
  i2c_mock.regfile[0x33u] = 0x20u; /* IBAT -480mA (0xFE20, 2's comp) */
  i2c_mock.regfile[0x34u] = 0xFEu;
  bq25798_telemetry_t t;
  memset(&t, 0, sizeof(t));
  CHECK(bq25798_read_telemetry(&t));
  CHECK(t.fault);
  CHECK(t.ibat_ma == -480);
  CHECK(t.vbat_mv == 0u); /* default regfile zeros */
  CHECK(i2c_mock_script_complete());
}

static void test_bq25798_read_telemetry_error_paths(void) {
  i2c_mock_begin();
  i2c_mock.adc_done_autoset = false; /* conversion never completes */
  i2c_mock.regfile[0x1Eu] = 0x00u;
  bq25798_telemetry_t t;
  memset(&t, 0, sizeof(t));
  t.vbat_mv = 0xBEEFu; /* sentinel: must be untouched on failure */
  CHECK(!bq25798_read_telemetry(&t));
  CHECK(t.vbat_mv == 0xBEEFu);

  i2c_mock_begin();
  i2c_mock.nack_all = true;
  memset(&t, 0, sizeof(t));
  CHECK(!bq25798_read_telemetry(&t));
  CHECK(bq25798_read_telemetry(NULL) == false);
}

/* ---------------- BQ34Z100 pure layer ---------------- */

static void test_bq34z100_checksum(void) {
  uint8_t block[32];
  for (int i = 0; i < 32; i++) {
    block[i] = (uint8_t)i;
  }
  /* SLUSBZ5D 7.3.3.1: checksum = 255 - (8-bit sum of block bytes).
   * 0x00..0x1F sums to 0x1F0, 8-bit truncation 0xF0 -> checksum 0x0F. */
  CHECK(bq34z100_checksum(block, 32) == 0x0Fu);
  CHECK(bq34z100_block_checksum_valid(block, 32, 0x0Fu));
  CHECK(!bq34z100_block_checksum_valid(block, 32, 0x10u));
  CHECK(!bq34z100_block_checksum_valid(block, 31, 0x0Fu)); /* len matters */

  memset(block, 0x00u, sizeof(block));
  CHECK(bq34z100_checksum(block, 32) == 0xFFu);

  memset(block, 0xFFu, sizeof(block));
  /* 255*32 = 8160, 8-bit truncation 0xE0 -> checksum 0x1F. */
  CHECK(bq34z100_checksum(block, 32) == 0x1Fu);

  CHECK(bq34z100_checksum(block, 0) == 0xFFu); /* empty block */
}

static void test_bq34z100_current_decode(void) {
  CHECK(bq34z100_current_ma_decode(0x00u, 0x00u) == 0);
  CHECK(bq34z100_current_ma_decode(0x2Cu, 0x01u) == 300);
  CHECK(bq34z100_current_ma_decode(0xFFu, 0xFFu) == -1);
  CHECK(bq34z100_current_ma_decode(0xD8u, 0xFFu) == -40);
  CHECK(bq34z100_current_ma_decode(0x00u, 0x80u) == -32768);
  CHECK(bq34z100_current_ma_decode(0xFFu, 0x7Fu) == 32767);
}

static void test_bq34z100_temperature_convert(void) {
  CHECK(bq34z100_temperature_deci_c(2932u) == 200);  /* 293.2K -> 20.0C */
  CHECK(bq34z100_temperature_deci_c(3132u) == 400);  /* 40.0C */
  CHECK(bq34z100_temperature_deci_c(2732u) == 0);    /* 273.2K -> 0.0C */
  CHECK(bq34z100_temperature_deci_c(0u) == -2731);   /* absolute zero */
}

static void test_bq34z100_time_and_flags(void) {
  CHECK(bq34z100_time_available(0xFFFFu) == false); /* not discharging/charging */
  CHECK(bq34z100_time_available(0u) == true);
  CHECK(bq34z100_time_available(120u) == true);

  CHECK(bq34z100_flags_charging(BQ34Z100_FLAG_CHG));
  CHECK(!bq34z100_flags_charging(BQ34Z100_FLAG_FC));
  CHECK(bq34z100_flags_discharging(BQ34Z100_FLAG_DSG));
  CHECK(!bq34z100_flags_discharging(BQ34Z100_FLAG_CHG));
  CHECK(bq34z100_flags_full(BQ34Z100_FLAG_FC));
  CHECK(!bq34z100_flags_full(BQ34Z100_FLAG_CHG));
  /* Mixed live flags: charging while discharging report is set etc. */
  uint16_t mixed = (uint16_t)(BQ34Z100_FLAG_CHG | BQ34Z100_FLAG_DSG |
                              BQ34Z100_FLAG_BATLOW | BQ34Z100_FLAG_OCVTAKEN);
  CHECK(bq34z100_flags_charging(mixed));
  CHECK(bq34z100_flags_discharging(mixed));
  CHECK(!bq34z100_flags_full(mixed));
}

/* ---------------- BQ34Z100 hardware paths (mock I2C) ---------------- */

static void test_bq34z100_probe(void) {
  i2c_mock_begin();
  i2c_mock_expect_probe(0x55u, true);
  i2c_mock_expect_write(0x55u, 0x00u, (const uint8_t[]){0x01u, 0x00u}, 2u);
  i2c_mock_expect_read(0x55u, 0x00u, (const uint8_t[]){0x00u, 0x01u}, 2u);
  CHECK(bq34z100_probe()); /* DEVICE_TYPE reads back 0x0100 */
  CHECK(i2c_mock_script_complete());

  i2c_mock_begin();
  i2c_mock_expect_probe(0x55u, true);
  i2c_mock_expect_write(0x55u, 0x00u, (const uint8_t[]){0x01u, 0x00u}, 2u);
  i2c_mock_expect_read(0x55u, 0x00u, (const uint8_t[]){0x01u, 0x00u}, 2u);
  CHECK(!bq34z100_probe()); /* unexpected device type */

  i2c_mock_begin();
  i2c_mock_expect_probe(0x55u, false);
  CHECK(!bq34z100_probe()); /* no ACK: pack absent */

  i2c_mock_begin();
  i2c_mock.present = false;
  CHECK(!bq34z100_probe());
}

static void test_bq34z100_control_read(void) {
  i2c_mock_begin();
  i2c_mock_expect_write(0x55u, 0x00u, (const uint8_t[]){0x02u, 0x00u}, 2u);
  i2c_mock_expect_read(0x55u, 0x00u, (const uint8_t[]){0x30u, 0x01u}, 2u);
  uint16_t fw = 0u;
  CHECK(bq34z100_control_read(BQ34Z100_CONTROL_FW_VERSION, &fw));
  CHECK(fw == 0x0130u);
  CHECK(i2c_mock_script_complete());

  i2c_mock_begin();
  CHECK(bq34z100_control_read(BQ34Z100_CONTROL_CONTROL_STATUS, NULL) == false);

  i2c_mock_begin();
  i2c_mock.nack_all = true;
  uint16_t out = 0u;
  CHECK(!bq34z100_control_read(BQ34Z100_CONTROL_DEVICE_TYPE, &out));
}

static void test_bq34z100_readers(void) {
  i2c_mock_begin();
  i2c_mock_expect_read(0x55u, 0x02u, (const uint8_t[]){42u}, 1u);
  uint8_t soc = 0u;
  CHECK(bq34z100_read_soc_percent(&soc));
  CHECK(soc == 42u);

  i2c_mock_expect_read(0x55u, 0x08u, (const uint8_t[]){0xD4u, 0x30u}, 2u);
  uint16_t mv = 0u;
  CHECK(bq34z100_read_voltage_mv(&mv));
  CHECK(mv == 12500u);

  i2c_mock_expect_read(0x55u, 0x10u, (const uint8_t[]){0xDCu, 0x05u}, 2u);
  int16_t ma = 0;
  CHECK(bq34z100_read_current_ma(&ma));
  CHECK(ma == 1500);

  i2c_mock_expect_read(0x55u, 0x10u, (const uint8_t[]){0xD8u, 0xFFu}, 2u);
  CHECK(bq34z100_read_current_ma(&ma));
  CHECK(ma == -40);

  i2c_mock_expect_read(0x55u, 0x0Au, (const uint8_t[]){0xF4u, 0x01u}, 2u);
  CHECK(bq34z100_read_average_current_ma(&ma));
  CHECK(ma == 500);

  i2c_mock_expect_read(0x55u, 0x0Cu, (const uint8_t[]){0x74u, 0x0Bu}, 2u);
  int16_t deci_c = 0;
  CHECK(bq34z100_read_temperature(&deci_c));
  CHECK(deci_c == 200); /* 293.2K */

  i2c_mock_expect_read(0x55u, 0x0Eu, (const uint8_t[]){0x00u, 0x01u}, 2u);
  uint16_t flags = 0u;
  CHECK(bq34z100_read_flags(&flags));
  CHECK(flags == BQ34Z100_FLAG_CHG);
  CHECK(bq34z100_flags_charging(flags));

  i2c_mock_expect_read(0x55u, 0x04u, (const uint8_t[]){0x00u, 0x02u}, 2u);
  uint16_t mah = 0u;
  CHECK(bq34z100_read_remaining_capacity_mah(&mah));
  CHECK(mah == 512u);

  i2c_mock_expect_read(0x55u, 0x06u, (const uint8_t[]){0x00u, 0x14u}, 2u);
  CHECK(bq34z100_read_full_capacity_mah(&mah));
  CHECK(mah == 5120u);

  i2c_mock_expect_read(0x55u, 0x18u, (const uint8_t[]){0xFFu, 0xFFu}, 2u);
  uint16_t minutes = 0u;
  CHECK(bq34z100_read_time_to_empty(&minutes));
  CHECK(minutes == BQ34Z100_TIME_UNAVAILABLE);
  CHECK(!bq34z100_time_available(minutes));

  i2c_mock_expect_read(0x55u, 0x1Au, (const uint8_t[]){0x78u, 0x00u}, 2u);
  CHECK(bq34z100_read_time_to_full(&minutes));
  CHECK(minutes == 120u);
  CHECK(bq34z100_time_available(minutes));

  i2c_mock_expect_read(0x55u, 0x2Cu, (const uint8_t[]){0x32u, 0x00u}, 2u);
  uint16_t cycles = 0u;
  CHECK(bq34z100_read_cycle_count(&cycles));
  CHECK(cycles == 50u);

  i2c_mock_expect_read(0x55u, 0x2Eu, (const uint8_t[]){64u}, 1u);
  uint8_t health = 0u;
  CHECK(bq34z100_read_health_percent(&health));
  CHECK(health == 64u);

  CHECK(i2c_mock_script_complete());
}

static void test_bq34z100_reader_null_and_nack(void) {
  i2c_mock_begin();
  CHECK(bq34z100_read_soc_percent(NULL) == false);
  CHECK(bq34z100_read_voltage_mv(NULL) == false);
  CHECK(bq34z100_read_current_ma(NULL) == false);
  CHECK(bq34z100_read_average_current_ma(NULL) == false);
  CHECK(bq34z100_read_temperature(NULL) == false);
  CHECK(bq34z100_read_flags(NULL) == false);
  CHECK(bq34z100_read_remaining_capacity_mah(NULL) == false);
  CHECK(bq34z100_read_full_capacity_mah(NULL) == false);
  CHECK(bq34z100_read_time_to_empty(NULL) == false);
  CHECK(bq34z100_read_time_to_full(NULL) == false);
  CHECK(bq34z100_read_cycle_count(NULL) == false);
  CHECK(bq34z100_read_health_percent(NULL) == false);

  i2c_mock_begin();
  i2c_mock.nack_all = true;
  uint8_t b = 0u;
  uint16_t w = 0u;
  int16_t s = 0;
  CHECK(!bq34z100_read_soc_percent(&b));
  CHECK(!bq34z100_read_voltage_mv(&w));
  CHECK(!bq34z100_read_current_ma(&s));
  CHECK(!bq34z100_read_temperature(&s));
  CHECK(!bq34z100_read_flags(&w));
  CHECK(!bq34z100_read_cycle_count(&w));
  CHECK(!bq34z100_read_health_percent(&b));
}

static void test_bq34z100_dataflash_read_block(void) {
  i2c_mock_begin();
  uint8_t pattern[32];
  for (int i = 0; i < 32; i++) {
    pattern[i] = (uint8_t)i;
  }
  for (int i = 0; i < 32; i++) {
    i2c_mock.regfile[0x40u + (uint8_t)i] = pattern[i];
  }
  i2c_mock.regfile[0x60u] = bq34z100_checksum(pattern, 32);

  uint8_t data_out[32];
  uint8_t checksum_out = 0u;
  CHECK(bq34z100_dataflash_read_block(0x40u, 0x00u, data_out, &checksum_out));
  CHECK(memcmp(data_out, pattern, 32) == 0);
  CHECK(checksum_out == bq34z100_checksum(pattern, 32));
  CHECK(bq34z100_block_checksum_valid(data_out, 32, checksum_out));
  /* Protocol setup writes landed in the right command registers. */
  CHECK(i2c_mock.regfile[0x61u] == 0x00u); /* BlockDataControl(0x00) */
  CHECK(i2c_mock.regfile[0x3Eu] == 0x40u); /* DataFlashClass */
  CHECK(i2c_mock.regfile[0x3Fu] == 0x00u); /* DataFlashBlock */
  CHECK(i2c_mock_script_complete());

  i2c_mock_begin();
  CHECK(bq34z100_dataflash_read_block(0x40u, 0x00u, NULL, &checksum_out) ==
        false);
  CHECK(bq34z100_dataflash_read_block(0x40u, 0x00u, data_out, NULL) == false);

  i2c_mock_begin();
  i2c_mock.nack_all = true;
  CHECK(!bq34z100_dataflash_read_block(0x40u, 0x00u, data_out, &checksum_out));
}

int main(void) {
  test_bq25798_encode_charge_current();
  test_bq25798_encode_charge_voltage();
  test_bq25798_encode_input_current();
  test_bq25798_encode_vsysmin();
  test_bq25798_charge_status_decode();
  test_bq25798_charge_state_classification();
  test_bq25798_probe();
  test_bq25798_init_config_bits();
  test_bq25798_setters();
  test_bq25798_status_helpers();
  test_bq25798_pet_watchdog();
  test_bq25798_read_telemetry();
  test_bq25798_read_telemetry_signed_and_fault();
  test_bq25798_read_telemetry_error_paths();

  test_bq34z100_checksum();
  test_bq34z100_current_decode();
  test_bq34z100_temperature_convert();
  test_bq34z100_time_and_flags();
  test_bq34z100_probe();
  test_bq34z100_control_read();
  test_bq34z100_readers();
  test_bq34z100_reader_null_and_nack();
  test_bq34z100_dataflash_read_block();

  if (failures != 0) {
    fprintf(stderr, "bq_driver_tests: %d failure(s)\n", failures);
    return 1;
  }
  puts("bq_driver_tests: PASS");
  return 0;
}
