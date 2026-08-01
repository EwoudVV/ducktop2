#ifndef DUCKTOP2_BQ25798_H
#define DUCKTOP2_BQ25798_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/*
 * Ducktop2 EC driver for the TI BQ25798 buck-boost charger / NVDC power path
 * (U2, sheet 01, BQ25798RQMR VQFN-29).
 *
 * The charger sits on the EC I2C1 root bus (SCL/SDA wired to pins 14/15 on the
 * schematic; R30/R31 4.7k pull-ups to MCU_3V3) and is the EC's only regulator
 * path: it charges the 3S protected pack, and in NVDC mode its SYS pin powers
 * VSYS while an input source is present.
 *
 * Register map source: BQ25798 datasheet SLUSDV2C (MAY 2020 - REVISED JUNE
 * 2026), section 7.5 "Register Map", fetched from ti.com/lit/ds/symlink/
 * bq25798.pdf on 2026-08-01.  All offsets, field positions, bit steps and
 * range limits below were verified against that document; there are no
 * unverified registers in this header.
 *
 * I2C address: the BQ25798 has NO address strap pin (the VQFN-29 pin list on
 * the schematic has no ADDR pin), so the fixed datasheet address applies.
 * SLUSDV2C 7.5: "The BQ25798 7-bit address is defined as 1101 011 (0x6B)".
 *
 * Multi-byte registers are little-endian (low byte at offset, high byte at
 * offset+1), matching the TI charger register convention; the part supports
 * multi-byte reads and writes of all registers.
 *
 * Design notes specific to this board (from generate_power_sheet.py):
 *  - TS is fixed at 58.9% REGN by R16/R705; the driver sets TS_IGNORE=1.
 *  - /CE is the fail-off hardware path (Q700 + R14); CHG_ENABLE is a separate
 *    GPIO (main.c), so register EN_CHG is a secondary gate only.
 *  - Q25 (CSD17575Q3) ship FET is on SDRV; driver sets SFET_PRESENT=1 so the
 *    SDRV_CTRL features are unlocked (POR IDLE keeps the FET fully on).
 *  - STOP_WD_CHG=1 makes I2C watchdog expiry set EN_CHG=0 (charger stops if
 *    the EC dies); the EC pets the watchdog from bq25798_read_telemetry().
 */

#define BQ25798_I2C_ADDRESS_7BIT 0x6Bu

/* Register offsets (SLUSDV2C Table 7-12). */
#define BQ25798_REG_MINIMUM_SYSTEM_VOLTAGE  0x00u /* VSYSMIN 5:0, 250mV, off 2500mV */
#define BQ25798_REG_CHARGE_VOLTAGE_LIMIT    0x01u /* VREG 10:0, 10mV, 16-bit      */
#define BQ25798_REG_CHARGE_CURRENT_LIMIT    0x03u /* ICHG 8:0, 10mA, 16-bit       */
#define BQ25798_REG_INPUT_VOLTAGE_LIMIT     0x05u /* VINDPM 7:0, 100mV            */
#define BQ25798_REG_INPUT_CURRENT_LIMIT     0x06u /* IINDPM 8:0, 10mA, 16-bit     */
#define BQ25798_REG_TERMINATION_CONTROL     0x09u
#define BQ25798_REG_CHARGER_CONTROL_0       0x0Fu
#define BQ25798_REG_CHARGER_CONTROL_1       0x10u
#define BQ25798_REG_CHARGER_CONTROL_2       0x11u
#define BQ25798_REG_CHARGER_CONTROL_5       0x14u
#define BQ25798_REG_NTC_CONTROL_1           0x18u
#define BQ25798_REG_CHARGER_STATUS_0        0x1Bu
#define BQ25798_REG_CHARGER_STATUS_1        0x1Cu
#define BQ25798_REG_CHARGER_STATUS_2        0x1Du
#define BQ25798_REG_CHARGER_STATUS_3        0x1Eu
#define BQ25798_REG_FAULT_STATUS_0          0x20u
#define BQ25798_REG_FAULT_STATUS_1          0x21u
#define BQ25798_REG_ADC_CONTROL             0x2Eu
#define BQ25798_REG_ADC_FUNCTION_DISABLE_0  0x2Fu
#define BQ25798_REG_IBUS_ADC                0x31u /* 16-bit, 1mA/LSB, 2's comp   */
#define BQ25798_REG_IBAT_ADC                0x33u /* 16-bit, 1mA/LSB, 2's comp   */
#define BQ25798_REG_VBUS_ADC                0x35u /* 16-bit, 1mV/LSB             */
#define BQ25798_REG_VBAT_ADC                0x3Bu /* 16-bit, 1mV/LSB (BATP sense)*/
#define BQ25798_REG_PART_INFORMATION        0x48u

/* REG09 Termination Control fields (7.5.1.7). */
#define BQ25798_REG09_STOP_WD_CHG           (1u << 5) /* WD expiry sets EN_CHG=0 */

/* REG0F Charger Control 0 fields (7.5.1.12). */
#define BQ25798_REG0F_EN_CHG                (1u << 5)
#define BQ25798_REG0F_EN_TERM               (1u << 1)

/* REG10 Charger Control 1 fields (7.5.1.13). */
#define BQ25798_REG10_WD_RST                (1u << 3) /* self-clears after reset */
#define BQ25798_REG10_WATCHDOG_MASK         0x07u
#define BQ25798_WATCHDOG_DISABLE            0x00u
#define BQ25798_WATCHDOG_40_S               0x05u /* POR default */

/* REG11 Charger Control 2 fields (7.5.1.14). */
#define BQ25798_REG11_SDRV_CTRL_MASK        (3u << 1)
#define BQ25798_SDRV_IDLE                   0x00u /* POR: ship FET fully on */

/* REG14 Charger Control 5 fields (7.5.1.17). */
#define BQ25798_REG14_SFET_PRESENT          (1u << 7) /* Q25 populated -> set 1 */
#define BQ25798_REG14_EN_IBAT               (1u << 5) /* IBAT sense in HiZ/bat-only */

/* REG18 NTC Control 1 fields (7.5.1.21). */
#define BQ25798_REG18_TS_IGNORE             (1u << 0)

/* REG1B Charger Status 0 fields (7.5.1.23). */
#define BQ25798_REG1B_PG_STAT               (1u << 3)
#define BQ25798_REG1B_VBUS_PRESENT_STAT     (1u << 0)

/* REG1C Charger Status 1 fields (7.5.1.24). */
#define BQ25798_REG1C_CHG_STAT_MASK         (7u << 5)

/* REG1D Charger Status 2 fields (7.5.1.25). */
#define BQ25798_REG1D_VBAT_PRESENT_STAT     (1u << 0) /* VBAT > VBAT_UVLOZ */

/* REG1E Charger Status 3 fields (7.5.1.26). */
#define BQ25798_REG1E_ADC_DONE_STAT         (1u << 5) /* one-shot mode only */

/* REG2E ADC Control fields (7.5.1.42). */
#define BQ25798_REG2E_ADC_EN                (1u << 7)
#define BQ25798_REG2E_ADC_RATE              (1u << 6) /* 0=continuous 1=one-shot */
#define BQ25798_REG2E_ADC_SAMPLE_MASK       (3u << 4)
#define BQ25798_ADC_SAMPLE_13_BIT           (2u << 4)

/* REG48 Part Information fields (7.5.1.57). */
#define BQ25798_REG48_PN_MASK               (7u << 3)
#define BQ25798_REG48_PN_BQ25798            (3u << 3) /* 011b = BQ25798 */

/* Datasheet range limits (clamped-low behaviour; writes outside range are
 * ignored by the charger, so the driver clamps before writing). */
#define BQ25798_CHARGE_CURRENT_MIN_MA       50u
#define BQ25798_CHARGE_CURRENT_MAX_MA       5000u
#define BQ25798_CHARGE_VOLTAGE_MIN_MV       3000u
#define BQ25798_CHARGE_VOLTAGE_MAX_MV       18800u
#define BQ25798_INPUT_CURRENT_MIN_MA        100u
#define BQ25798_INPUT_CURRENT_MAX_MA        3300u
#define BQ25798_VSYSMIN_MIN_MV              2500u
#define BQ25798_VSYSMIN_MAX_MV              16000u

/* CHG_STAT_2:0 decoding, REG1C bits 7:5 (7.5.1.24). */
typedef enum {
  BQ25798_CHARGE_NONE = 0,        /* not charging */
  BQ25798_CHARGE_TRICKLE,         /* trickle charge */
  BQ25798_CHARGE_PRECHARGE,       /* pre-charge */
  BQ25798_CHARGE_FAST,            /* fast charge, CC mode */
  BQ25798_CHARGE_TAPER,           /* taper charge, CV mode */
  BQ25798_CHARGE_RESERVED,        /* reserved code 5 */
  BQ25798_CHARGE_TOPOFF,          /* top-off timer active */
  BQ25798_CHARGE_TERMINATED       /* charge termination done */
} bq25798_charge_status_t;

/* One-shot ADC + status readback.  IBAT is positive while charging and
 * negative while discharging (REG33, 7.5.1.46). */
typedef struct {
  bool vbus_present;
  bool power_good;
  bool battery_present;           /* VBAT > VBAT_UVLOZ, REG1D bit 0 */
  bq25798_charge_status_t charge_status;
  bool fault;                     /* any REG20/REG21 fault status bit */
  int16_t ibat_ma;                /* battery current, +charge/-discharge */
  int16_t ibus_ma;                /* input current, +in/-out */
  uint16_t vbat_mv;               /* pack voltage at BATP sense */
  uint16_t vbus_mv;               /* VBUS voltage */
} bq25798_telemetry_t;

/* ---- Pure, host-testable encode/decode layer (no I2C, no hardware) ---- */

/* Register-value encoders.  Inputs are clamped to the datasheet range and
 * rounded down to the register step. */
uint16_t bq25798_encode_charge_current(uint16_t ma);
uint16_t bq25798_encode_charge_voltage(uint16_t mv);
uint16_t bq25798_encode_input_current(uint16_t ma);
uint8_t bq25798_encode_vsysmin(uint16_t mv);

bq25798_charge_status_t bq25798_charge_status_decode(uint8_t reg1c);
bool bq25798_is_charge_in_progress(bq25798_charge_status_t status);
bool bq25798_charge_done(bq25798_charge_status_t status);

/* ---- Hardware layer (I2C1 root bus) ---- */

/* Read REG48 and verify the part number field reads 011b (BQ25798).
 * Returns false if the charger is absent or unreachable. */
bool bq25798_probe(void);

/* Board-configuration write sequence: TS_IGNORE=1 (REG18), STOP_WD_CHG=1
 * (REG09), SFET_PRESENT=1 + EN_IBAT=1 (REG14), then pet the watchdog.
 * Safe to retry: each step is idempotent. */
bool bq25798_init(void);

bool bq25798_set_charge_current_ma(uint16_t ma);
bool bq25798_set_charge_voltage_mv(uint16_t mv);
bool bq25798_set_input_current_ma(uint16_t ma);
bool bq25798_read_input_current_limit_ma(uint16_t *ma_out); /* readback */

bool bq25798_set_charge_enable(bool enable); /* REG0F EN_CHG gate */

bool bq25798_is_charging(void);
bool bq25798_battery_present(void);
bool bq25798_vbus_present(void);
bool bq25798_power_good(void);

/* Write WD_RST (REG10 bit 3) to reset the I2C watchdog timer.  With the
 * watchdog at its 40 s default the EC must pet it regularly; expiry sets
 * EN_CHG=0 because STOP_WD_CHG=1. */
bool bq25798_pet_watchdog(void);

/* Trigger a one-shot ADC conversion (IBUS/IBAT/VBUS/VBAT), wait for
 * ADC_DONE, read the results and pet the watchdog.  On any failure returns
 * false and leaves *telemetry untouched; the caller keeps the last valid
 * sample.  Blocking: one-shot conversion takes a few ms at 13-bit. */
bool bq25798_read_telemetry(bq25798_telemetry_t *telemetry);

#ifdef __cplusplus
}
#endif

#endif /* DUCKTOP2_BQ25798_H */
