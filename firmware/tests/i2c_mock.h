#ifndef DUCKTOP2_TEST_I2C_MOCK_H
#define DUCKTOP2_TEST_I2C_MOCK_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

/*
 * Host-side fake for the target I2C1 root bus, used by the BQ25798/BQ34Z100
 * driver tests.  Implements the i2c1_* entry points declared in i2c.h with
 * a scriptable register file so the drivers can be exercised without
 * hardware: reads fall back to a 256-byte register file, scripted read
 * steps return canned responses, and nack_all/present inject bus faults.
 *
 * The mock never silently fails: a transaction that does not match the next
 * scripted step (or an unscripted write that would corrupt the test) sets
 * script_error, which the test harness asserts against.
 */

#define I2C_MOCK_SCRIPT_MAX 32u
#define I2C_MOCK_BLOCK_MAX 32u

typedef struct {
  uint8_t dev_addr;
  uint8_t reg;              /* probe: unused (len == 0) */
  uint8_t data[I2C_MOCK_BLOCK_MAX]; /* read response / expected write payload */
  uint8_t len;              /* 0 = probe step */
  bool ack;
  bool used;
} i2c_mock_step_t;

typedef struct {
  uint8_t regfile[256];
  bool present;             /* i2c1_probe() result when no probe step scripted */
  bool nack_all;            /* force NACK on every transaction */
  bool adc_done_autoset;    /* REG1E ADC_DONE set when BQ25798 ADC_EN written */
  bool script_error;
  i2c_mock_step_t script[I2C_MOCK_SCRIPT_MAX];
  size_t script_count;
  size_t writes;
  size_t write_raws;
  size_t reads;
  size_t probes;
} i2c_mock_t;

extern i2c_mock_t i2c_mock;

void i2c_mock_begin(void);

void i2c_mock_expect_probe(uint8_t dev_addr, bool ack);
void i2c_mock_expect_read(uint8_t dev_addr, uint8_t reg, const uint8_t *data,
                          uint8_t len);
void i2c_mock_expect_write(uint8_t dev_addr, uint8_t reg, const uint8_t *data,
                           uint8_t len);

/* True when every scripted step has been consumed and no transaction
 * mismatched the script. */
bool i2c_mock_script_complete(void);

#endif /* DUCKTOP2_TEST_I2C_MOCK_H */
