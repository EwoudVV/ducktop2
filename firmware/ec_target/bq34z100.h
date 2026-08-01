#ifndef DUCKTOP2_BQ34Z100_H
#define DUCKTOP2_BQ34Z100_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/*
 * Ducktop2 EC driver for the TI BQ34Z100-G1 wide-range Impedance Track fuel
 * gauge (U10, sheet 01, BQ34Z100PWR-G1 TSSOP-14) on the protected external
 * 3S pack.
 *
 * The gauge is powered from MCU_3V3 (REGIN/VCC, schematic pin 6) and senses
 * the pack through FG_BAT_SENSE (divider R180/R181/R182) and the 5 mOhm
 * Kelvin shunt (FG_SRP/FG_SRN).  Because it sits on the pack, "gauge
 * responded" is the EC's pack-present proxy: ec_battery.h treats a failed
 * probe as EC_BATTERY_NOT_PRESENT.
 *
 * Register map source: BQ34Z100-G1 datasheet SLUSBZ5D (JANUARY 2015 -
 * REVISED APRIL 2021), section 7.3 "Data Commands", fetched from
 * ti.com/lit/ds/symlink/bq34z100-g1.pdf on 2026-08-01.  All offsets below
 * were verified against that document; there are no unverified registers in
 * this header.
 *
 * I2C address: fixed at 0x55.  SLUSBZ5D 7.3.15.5: "The 7-bit device address
 * (ADDR) ... is fixed as 1010101.  The 8-bit device address is therefore
 * 0xAA or 0xAB for write or read."  The TSSOP-14 pin list on the schematic
 * has no ADDR pin, so the fixed address applies.
 *
 * Byte order: standard SBS word commands (Voltage(), Current(), ...) are
 * little-endian, low byte at the command offset.  The data-flash block
 * space stores 16-bit fields MSB-first (SLUSBZ5D 7.3.3.1 example: Pack
 * Configuration MSB at 0x40).  Control subcommands are written low byte
 * first, e.g. Control(0x0414) is (wr 0x00 0x14 0x04).
 *
 * The gauge clock-stretches up to 6-8 ms when waking from FULLSLEEP
 * (SLUSBZ5D 7.3.1.2.12); the shared i2c1 polling driver bounds each wait at
 * ~50000 cycles, so do not enable FULLSLEEP while the EC polls it.
 */

#define BQ34Z100_I2C_ADDRESS_7BIT 0x55u

/* Standard commands (SLUSBZ5D Table 7-1). */
#define BQ34Z100_REG_CONTROL                 0x00u /* 2-byte subcommand        */
#define BQ34Z100_REG_STATE_OF_CHARGE         0x02u /* single byte, %           */
#define BQ34Z100_REG_MAX_ERROR               0x03u /* single byte, %           */
#define BQ34Z100_REG_REMAINING_CAPACITY      0x04u /* mAh                      */
#define BQ34Z100_REG_FULL_CHARGE_CAPACITY    0x06u /* mAh                      */
#define BQ34Z100_REG_VOLTAGE                 0x08u /* mV                       */
#define BQ34Z100_REG_AVERAGE_CURRENT         0x0Au /* signed mA                */
#define BQ34Z100_REG_TEMPERATURE             0x0Cu /* 0.1 K                    */
#define BQ34Z100_REG_FLAGS                   0x0Eu
#define BQ34Z100_REG_CURRENT                 0x10u /* signed mA, 1 s update    */
#define BQ34Z100_REG_FLAGS_B                 0x12u
#define BQ34Z100_REG_TIME_TO_EMPTY           0x18u /* minutes, 0xFFFF = n/a    */
#define BQ34Z100_REG_TIME_TO_FULL            0x1Au /* minutes, 0xFFFF = n/a    */
#define BQ34Z100_REG_CYCLE_COUNT             0x2Cu /* counts                   */
#define BQ34Z100_REG_STATE_OF_HEALTH         0x2Eu /* %, 0..100                */
#define BQ34Z100_REG_DESIGN_CAPACITY         0x3Cu /* mAh                      */

/* Data flash block protocol (SLUSBZ5D 7.3.3.1).  Data flash access via
 * 0x3E/0x3F requires UNSEALED mode; the runtime commands above work in
 * SEALED mode, which is how a configured pack ships. */
#define BQ34Z100_REG_DATA_FLASH_CLASS        0x3Eu
#define BQ34Z100_REG_DATA_FLASH_BLOCK        0x3Fu
#define BQ34Z100_REG_BLOCK_DATA              0x40u /* 32-byte block, 0x40..0x5F */
#define BQ34Z100_REG_BLOCK_DATA_CHECKSUM     0x60u
#define BQ34Z100_REG_BLOCK_DATA_CONTROL      0x61u /* write 0x00 for DF access */

/* Control() subcommands (SLUSBZ5D Table 7-2). */
#define BQ34Z100_CONTROL_CONTROL_STATUS      0x0000u
#define BQ34Z100_CONTROL_DEVICE_TYPE         0x0001u /* returns 0x0100          */
#define BQ34Z100_CONTROL_FW_VERSION          0x0002u
#define BQ34Z100_CONTROL_HW_VERSION          0x0003u
#define BQ34Z100_CONTROL_SEALED              0x0020u
#define BQ34Z100_CONTROL_RESET               0x0041u

#define BQ34Z100_DEVICE_TYPE_VALUE           0x0100u

/* Flags() bits, register 0x0E/0x0F (SLUSBZ5D 7.3.1.10). */
#define BQ34Z100_FLAG_DSG       (1u << 0) /* discharging detected       */
#define BQ34Z100_FLAG_SOCF      (1u << 1) /* SOC threshold final reached */
#define BQ34Z100_FLAG_SOC1      (1u << 2) /* SOC threshold 1 reached    */
#define BQ34Z100_FLAG_CF        (1u << 3) /* condition flag             */
#define BQ34Z100_FLAG_OCVTAKEN  (1u << 7) /* OCV measured in RELAX      */
#define BQ34Z100_FLAG_CHG       (1u << 8) /* (fast) charging allowed    */
#define BQ34Z100_FLAG_FC        (1u << 9) /* full charge detected       */
#define BQ34Z100_FLAG_XCHG      (1u << 10)/* charging not allowed       */
#define BQ34Z100_FLAG_BATLOW    (1u << 11)/* low battery voltage        */
#define BQ34Z100_FLAG_BATHI     (1u << 12)/* high battery voltage       */
#define BQ34Z100_FLAG_OTD       (1u << 14)/* overtemp in discharge      */
#define BQ34Z100_FLAG_OTC       (1u << 15)/* overtemp in charge         */

/* Time values: 0xFFFF means the quantity is not being computed. */
#define BQ34Z100_TIME_UNAVAILABLE 0xFFFFu

/* ---- Pure, host-testable layer (no I2C, no hardware) ---- */

/* Data flash block checksum (SLUSBZ5D 7.3.3.1): checksum = 255 - (8-bit sum
 * of the block bytes).  len is the block length in bytes (32 for a full
 * data flash block). */
uint8_t bq34z100_checksum(const uint8_t *block, uint8_t len);
bool bq34z100_block_checksum_valid(const uint8_t *block, uint8_t len,
                                   uint8_t checksum);

/* SBS word assembly: low byte first (little-endian). */
int16_t bq34z100_current_ma_decode(uint8_t lo, uint8_t hi);

/* Temperature() reports 0.1 K units; convert to decidegrees Celsius. */
int16_t bq34z100_temperature_deci_c(uint16_t temperature_0_1k);

bool bq34z100_time_available(uint16_t gauge_minutes);
bool bq34z100_flags_charging(uint16_t flags);
bool bq34z100_flags_discharging(uint16_t flags);
bool bq34z100_flags_full(uint16_t flags);

/* ---- Hardware layer (I2C1 root bus) ---- */

/* Write a Control() subcommand to 0x00 and read the 2-byte response from
 * 0x00/0x01 (low byte first). */
bool bq34z100_control_read(uint16_t subcommand, uint16_t *value_out);

/* Pack-present probe: I2C ACK + DEVICE_TYPE reads back 0x0100.  False
 * means the pack/gauge is absent or unpowered; ec_battery maps that to
 * EC_BATTERY_NOT_PRESENT. */
bool bq34z100_probe(void);

bool bq34z100_read_soc_percent(uint8_t *soc_percent);
bool bq34z100_read_voltage_mv(uint16_t *voltage_mv);
bool bq34z100_read_current_ma(int16_t *current_ma);
bool bq34z100_read_average_current_ma(int16_t *average_current_ma);
bool bq34z100_read_temperature(int16_t *temperature_deci_c);
bool bq34z100_read_flags(uint16_t *flags);
bool bq34z100_read_remaining_capacity_mah(uint16_t *capacity_mah);
bool bq34z100_read_full_capacity_mah(uint16_t *capacity_mah);
bool bq34z100_read_time_to_empty(uint16_t *minutes);
bool bq34z100_read_time_to_full(uint16_t *minutes);
bool bq34z100_read_cycle_count(uint16_t *cycle_count);
bool bq34z100_read_health_percent(uint8_t *health_percent);

/* UNSEALED-only data flash block read: BlockDataControl(0x00),
 * DataFlashClass(class), DataFlashBlock(block), then read the 32 bytes at
 * 0x40 and the block checksum at 0x60.  data_out must hold 32 bytes. */
bool bq34z100_dataflash_read_block(uint8_t df_class, uint8_t df_block,
                                   uint8_t *data_out,
                                   uint8_t *checksum_out);

#ifdef __cplusplus
}
#endif

#endif /* DUCKTOP2_BQ34Z100_H */
