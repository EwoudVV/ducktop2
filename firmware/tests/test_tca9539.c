#include "i2c.h"
#include "i2c_mock.h"

#include <stdio.h>

static int failures;

#define CHECK(expression)                                                      \
  do {                                                                         \
    if (!(expression)) {                                                       \
      fprintf(stderr, "%s:%d: CHECK failed: %s\n", __FILE__, __LINE__,       \
              #expression);                                                    \
      ++failures;                                                              \
    }                                                                          \
  } while (0)

static void expect_safe_initialization(void)
{
  static const uint8_t zero[] = {0x00u};
  static const uint8_t config0[] = {0xFCu};
  static const uint8_t config1[] = {0xFEu};

  i2c_mock_expect_write(I2C_TCA9539_ADDR, TCA9539_REG_OUTPUT0, zero, 1u);
  i2c_mock_expect_write(I2C_TCA9539_ADDR, TCA9539_REG_OUTPUT1, zero, 1u);
  i2c_mock_expect_write(I2C_TCA9539_ADDR, TCA9539_REG_CONFIG0, config0, 1u);
  i2c_mock_expect_write(I2C_TCA9539_ADDR, TCA9539_REG_CONFIG1, config1, 1u);
  i2c_mock_expect_read(I2C_TCA9539_ADDR, TCA9539_REG_OUTPUT0, zero, 1u);
  i2c_mock_expect_read(I2C_TCA9539_ADDR, TCA9539_REG_CONFIG0, config0, 1u);
  i2c_mock_expect_read(I2C_TCA9539_ADDR, TCA9539_REG_CONFIG1, config1, 1u);
}

static void test_safe_initialization_order(void)
{
  i2c_mock_begin();
  expect_safe_initialization();
  CHECK(tca9539_init_safe());
  CHECK(i2c_mock_script_complete());
}

static void test_path_control_uses_output_latch(void)
{
  static const uint8_t pd1_on[] = {0x01u};
  static const uint8_t both_on[] = {0x03u};
  static const uint8_t pd2_on[] = {0x02u};

  i2c_mock_begin();
  expect_safe_initialization();
  CHECK(tca9539_init_safe());
  i2c_mock_expect_write(I2C_TCA9539_ADDR, TCA9539_REG_OUTPUT0, pd1_on, 1u);
  i2c_mock_expect_write(I2C_TCA9539_ADDR, TCA9539_REG_OUTPUT0, both_on, 1u);
  i2c_mock_expect_write(I2C_TCA9539_ADDR, TCA9539_REG_OUTPUT0, pd2_on, 1u);
  CHECK(tca9539_set_pd_path_enable(0u, true));
  CHECK(tca9539_set_pd_path_enable(1u, true));
  CHECK(tca9539_set_pd_path_enable(0u, false));
  CHECK(i2c_mock_script_complete());
}

static void test_failure_stays_uninitialized(void)
{
  i2c_mock_begin();
  i2c_mock.nack_all = true;
  CHECK(!tca9539_init_safe());
  CHECK(!tca9539_set_pd_path_enable(0u, true));
  CHECK(!tca9539_set_pd_path_enable(2u, true));
}

int main(void)
{
  test_safe_initialization_order();
  test_path_control_uses_output_latch();
  test_failure_stays_uninitialized();
  if (failures != 0) {
    fprintf(stderr, "tca9539_tests: %d failure(s)\n", failures);
    return 1;
  }
  puts("tca9539_tests: PASS");
  return 0;
}
