#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
BUILD_DIR=${TMPDIR:-/tmp}/ducktop2-firmware-host-tests
CC_BIN=${CC:-cc}

rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

COMMON_FLAGS="-std=c11 -Wall -Wextra -Wpedantic -Werror"

"$CC_BIN" $COMMON_FLAGS \
    -I"$ROOT/ec/include" \
    "$ROOT/ec/src/ec_policy.c" \
    "$ROOT/tests/test_ec_policy.c" \
    -o "$BUILD_DIR/ec_policy_tests"

"$CC_BIN" $COMMON_FLAGS \
    -I"$ROOT/ec/include" \
    "$ROOT/ec/src/ec_commit.c" \
    "$ROOT/tests/test_ec_commit.c" \
    -o "$BUILD_DIR/ec_commit_tests"

"$CC_BIN" $COMMON_FLAGS \
    -I"$ROOT/ec/include" \
    "$ROOT/ec/src/ec_telemetry.c" \
    "$ROOT/tests/test_ec_telemetry.c" \
    -o "$BUILD_DIR/ec_telemetry_tests"

"$CC_BIN" $COMMON_FLAGS \
    -I"$ROOT/ec/include" \
    "$ROOT/ec/src/ec_keymap.c" \
    "$ROOT/tests/test_ec_keymap.c" \
    -o "$BUILD_DIR/ec_keymap_tests"

"$CC_BIN" $COMMON_FLAGS \
    -I"$ROOT/ec/include" \
    "$ROOT/ec/src/ec_fan.c" \
    "$ROOT/tests/test_ec_fan.c" \
    -o "$BUILD_DIR/ec_fan_tests"

"$CC_BIN" $COMMON_FLAGS \
    -I"$ROOT/ec/include" \
    "$ROOT/ec/src/ec_oled.c" \
    "$ROOT/tests/test_ec_oled.c" \
    -o "$BUILD_DIR/ec_oled_tests"

"$CC_BIN" $COMMON_FLAGS \
    -I"$ROOT/ec/include" \
    "$ROOT/ec/src/ec_lid.c" \
    "$ROOT/tests/test_ec_lid.c" \
    -o "$BUILD_DIR/ec_lid_tests"

"$CC_BIN" $COMMON_FLAGS \
    -I"$ROOT/ec/include" \
    "$ROOT/ec/src/ec_telemetry.c" \
    "$ROOT/ec/src/ec_battery.c" \
    "$ROOT/tests/test_ec_battery.c" \
    -o "$BUILD_DIR/ec_battery_tests"

"$CC_BIN" $COMMON_FLAGS \
    -I"$ROOT/ec_target" \
    "$ROOT/ec_target/bq25798.c" \
    "$ROOT/ec_target/bq34z100.c" \
    "$ROOT/tests/i2c_mock.c" \
    "$ROOT/tests/test_ec_bq_drivers.c" \
    -o "$BUILD_DIR/bq_driver_tests"

"$CC_BIN" $COMMON_FLAGS \
    -I"$ROOT/ec_target" \
    -I"$ROOT/tests" \
    "$ROOT/ec_target/tca9539.c" \
    "$ROOT/tests/i2c_mock.c" \
    "$ROOT/tests/test_tca9539.c" \
    -o "$BUILD_DIR/tca9539_tests"

"$CC_BIN" $COMMON_FLAGS \
    -I"$ROOT/ec_target" \
    "$ROOT/ec_target/fan_math.c" \
    "$ROOT/tests/test_fan_math.c" \
    -o "$BUILD_DIR/fan_math_tests"

"$CC_BIN" $COMMON_FLAGS \
    -I"$ROOT/ec_target" \
    -I"$ROOT/ec/include" \
    "$ROOT/ec_target/ec_app_math.c" \
    "$ROOT/tests/test_ec_app_math.c" \
    -o "$BUILD_DIR/ec_app_math_tests"

"$CC_BIN" $COMMON_FLAGS \
    -I"$ROOT/ec_target" \
    "$ROOT/ec_target/usb_hid_desc.c" \
    "$ROOT/tests/test_usb_hid_desc.c" \
    -o "$BUILD_DIR/usb_hid_desc_tests"

"$CC_BIN" $COMMON_FLAGS \
    -I"$ROOT/maker/include" \
    "$ROOT/maker/src/maker_policy.c" \
    "$ROOT/tests/test_maker_policy.c" \
    -o "$BUILD_DIR/maker_policy_tests"

"$CC_BIN" $COMMON_FLAGS \
    -I"$ROOT/ec_target" \
    -I"$ROOT/ec/include" \
    "$ROOT/ec_target/matrix_debounce.c" \
    "$ROOT/tests/test_matrix_debounce.c" \
    -o "$BUILD_DIR/matrix_debounce_tests"

"$BUILD_DIR/ec_policy_tests"
"$BUILD_DIR/ec_commit_tests"
"$BUILD_DIR/ec_telemetry_tests"
"$BUILD_DIR/ec_keymap_tests"
"$BUILD_DIR/ec_fan_tests"
"$BUILD_DIR/ec_oled_tests"
"$BUILD_DIR/ec_lid_tests"
"$BUILD_DIR/ec_battery_tests"
"$BUILD_DIR/bq_driver_tests"
"$BUILD_DIR/tca9539_tests"
"$BUILD_DIR/fan_math_tests"
"$BUILD_DIR/ec_app_math_tests"
"$BUILD_DIR/usb_hid_desc_tests"
"$BUILD_DIR/maker_policy_tests"
"$BUILD_DIR/matrix_debounce_tests"
"$CC_BIN" $COMMON_FLAGS -DDUCKTOP2_PD_ALLOW_20V=0 -I"$ROOT/ec_target" -I"$ROOT/ec/include" -I"$ROOT/tests" \
    "$ROOT/ec_target/tps25751.c" "$ROOT/tests/i2c_mock.c" "$ROOT/tests/test_tps25751.c" -o "$BUILD_DIR/tps25751_tests"
"$CC_BIN" $COMMON_FLAGS -I"$ROOT/ec_target" -I"$ROOT/ec/include" \
    "$ROOT/ec_target/host_link.c" "$ROOT/ec/src/ec_fan_monitor.c" "$ROOT/tests/test_target_runtime.c" -o "$BUILD_DIR/target_runtime_tests"
"$CC_BIN" $COMMON_FLAGS -I"$ROOT/ec_target" -I"$ROOT/ec/include" -I"$ROOT/tests" \
    "$ROOT/ec_target/ec_app.c" "$ROOT/ec_target/ec_app_math.c" "$ROOT/ec_target/bq25798.c" \
    "$ROOT/ec_target/bq34z100.c" "$ROOT/ec/src/ec_telemetry.c" "$ROOT/ec/src/ec_fan.c" "$ROOT/ec/src/ec_policy.c" \
    "$ROOT/tests/i2c_mock.c" "$ROOT/tests/test_ec_app.c" -o "$BUILD_DIR/ec_app_tests"
"$CC_BIN" $COMMON_FLAGS -I"$ROOT/ec_target" -I"$ROOT/ec/include" -I"$ROOT/tests" \
    "$ROOT/ec_target/audio.c" "$ROOT/ec_target/ssd1306.c" "$ROOT/tests/i2c_mock.c" "$ROOT/tests/test_services.c" -o "$BUILD_DIR/services_tests"
"$BUILD_DIR/tps25751_tests"
"$CC_BIN" $COMMON_FLAGS -DDUCKTOP2_PD_ALLOW_20V=1 -I"$ROOT/ec_target" -I"$ROOT/ec/include" -I"$ROOT/tests" \
    "$ROOT/ec_target/tps25751.c" "$ROOT/tests/i2c_mock.c" "$ROOT/tests/test_tps25751.c" -o "$BUILD_DIR/tps25751_20v_tests"
"$BUILD_DIR/tps25751_20v_tests"
"$BUILD_DIR/target_runtime_tests"
"$BUILD_DIR/ec_app_tests"
"$CC_BIN" $COMMON_FLAGS -DDUCKTOP2_PACK_QUALIFIED=1 -DDUCKTOP2_CHARGING_QUALIFIED=1 \
    -DDUCKTOP2_PACK_CHARGE_CURRENT_MA=500 -DDUCKTOP2_PACK_CHARGE_VOLTAGE_MV=12600 \
    -I"$ROOT/ec_target" -I"$ROOT/ec/include" -I"$ROOT/tests" \
    "$ROOT/ec_target/ec_app.c" "$ROOT/ec_target/ec_app_math.c" "$ROOT/ec_target/bq25798.c" \
    "$ROOT/ec_target/bq34z100.c" "$ROOT/ec/src/ec_telemetry.c" "$ROOT/ec/src/ec_fan.c" "$ROOT/ec/src/ec_policy.c" \
    "$ROOT/tests/i2c_mock.c" "$ROOT/tests/test_ec_app.c" -o "$BUILD_DIR/ec_charge_profile_tests"
"$BUILD_DIR/ec_charge_profile_tests"
"$BUILD_DIR/services_tests"
"$CC_BIN" $COMMON_FLAGS -I"$ROOT/ec/include" "$ROOT/ec/src/ec_policy.c" "$ROOT/ec/src/ec_commit.c" \
    "$ROOT/tests/test_ec_transfer.c" -o "$BUILD_DIR/ec_transfer_tests"
"$CC_BIN" $COMMON_FLAGS -I"$ROOT/maker/include" "$ROOT/maker/src/maker_bus.c" \
    "$ROOT/tests/test_maker_bus.c" -o "$BUILD_DIR/maker_bus_tests"
"$CC_BIN" $COMMON_FLAGS -I"$ROOT/tests/maker_sdk_mock" -I"$ROOT/maker_target" -I"$ROOT/maker/include" \
    "$ROOT/maker_target/bus_target.c" "$ROOT/tests/test_maker_bus_target.c" -o "$BUILD_DIR/maker_bus_target_tests"
"$BUILD_DIR/ec_transfer_tests"
"$BUILD_DIR/maker_bus_tests"
"$BUILD_DIR/maker_bus_target_tests"
"$CC_BIN" $COMMON_FLAGS -I"$ROOT/ec/include" "$ROOT/ec/src/ec_usb_power.c" \
    "$ROOT/tests/test_ec_usb_power.c" -o "$BUILD_DIR/ec_usb_power_tests"
"$BUILD_DIR/ec_usb_power_tests"
"$CC_BIN" $COMMON_FLAGS -I"$ROOT/ec_target" "$ROOT/ec_target/usb_power_hw.c" \
    "$ROOT/tests/test_usb_power_hw.c" -o "$BUILD_DIR/usb_power_hw_tests"
"$CC_BIN" $COMMON_FLAGS -I"$ROOT/ec_target" -I"$ROOT/ec/include" \
    "$ROOT/ec_target/usb_power.c" "$ROOT/ec/src/ec_usb_power.c" \
    "$ROOT/tests/test_usb_power.c" -o "$BUILD_DIR/usb_power_tests"
"$BUILD_DIR/usb_power_hw_tests"
"$BUILD_DIR/usb_power_tests"
python3 "$ROOT/tools/verify_release_contract.py"

printf '%s\n' "host tests: PASS ($CC_BIN)"
