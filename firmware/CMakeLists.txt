cmake_minimum_required(VERSION 3.20)

file(STRINGS "${CMAKE_CURRENT_LIST_DIR}/VERSION" DUCKTOP2_FIRMWARE_VERSION
     LIMIT_COUNT 1)
string(REGEX MATCH "^[0-9]+\\.[0-9]+\\.[0-9]+" DUCKTOP2_PROJECT_VERSION
       "${DUCKTOP2_FIRMWARE_VERSION}")
if(NOT DUCKTOP2_PROJECT_VERSION)
    message(FATAL_ERROR "firmware/VERSION must begin with semantic x.y.z")
endif()

project(ducktop2_firmware VERSION ${DUCKTOP2_PROJECT_VERSION} LANGUAGES C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS OFF)

option(DUCKTOP2_STRICT_WARNINGS "Treat host-build warnings as errors" ON)

function(ducktop2_target_defaults target)
    if(MSVC)
        target_compile_options(${target} PRIVATE /W4)
        if(DUCKTOP2_STRICT_WARNINGS)
            target_compile_options(${target} PRIVATE /WX)
        endif()
    else()
        target_compile_options(${target} PRIVATE -Wall -Wextra -Wpedantic)
        if(DUCKTOP2_STRICT_WARNINGS)
            target_compile_options(${target} PRIVATE -Werror)
        endif()
    endif()
    target_compile_definitions(${target} PUBLIC
        DUCKTOP2_FIRMWARE_VERSION="${DUCKTOP2_FIRMWARE_VERSION}")
endfunction()

enable_testing()

add_library(ducktop2_ec_policy STATIC ec/src/ec_policy.c)
target_include_directories(ducktop2_ec_policy PUBLIC ec/include)
ducktop2_target_defaults(ducktop2_ec_policy)

add_library(ducktop2_ec_commit STATIC ec/src/ec_commit.c)
target_include_directories(ducktop2_ec_commit PUBLIC ec/include)
ducktop2_target_defaults(ducktop2_ec_commit)

add_library(ducktop2_ec_telemetry STATIC ec/src/ec_telemetry.c)
target_include_directories(ducktop2_ec_telemetry PUBLIC ec/include)
ducktop2_target_defaults(ducktop2_ec_telemetry)

add_library(ducktop2_ec_keymap STATIC ec/src/ec_keymap.c)
target_include_directories(ducktop2_ec_keymap PUBLIC ec/include)
ducktop2_target_defaults(ducktop2_ec_keymap)

add_library(ducktop2_ec_fan STATIC ec/src/ec_fan.c)
target_include_directories(ducktop2_ec_fan PUBLIC ec/include)
ducktop2_target_defaults(ducktop2_ec_fan)

add_library(ducktop2_ec_oled STATIC ec/src/ec_oled.c)
target_include_directories(ducktop2_ec_oled PUBLIC ec/include)
ducktop2_target_defaults(ducktop2_ec_oled)

add_library(ducktop2_ec_lid STATIC ec/src/ec_lid.c)
target_include_directories(ducktop2_ec_lid PUBLIC ec/include)
ducktop2_target_defaults(ducktop2_ec_lid)

add_library(ducktop2_ec_battery STATIC ec/src/ec_battery.c)
target_include_directories(ducktop2_ec_battery PUBLIC ec/include)
ducktop2_target_defaults(ducktop2_ec_battery)

add_library(ducktop2_bq STATIC
    ec_target/bq25798.c
    ec_target/bq34z100.c)
target_include_directories(ducktop2_bq PUBLIC ec_target)
ducktop2_target_defaults(ducktop2_bq)

add_library(ducktop2_maker_policy STATIC maker/src/maker_policy.c)
target_include_directories(ducktop2_maker_policy PUBLIC maker/include)
ducktop2_target_defaults(ducktop2_maker_policy)

add_library(ducktop2_matrix_debounce STATIC ec_target/matrix_debounce.c)
target_include_directories(ducktop2_matrix_debounce PUBLIC ec_target ec/include)
ducktop2_target_defaults(ducktop2_matrix_debounce)

add_executable(ec_policy_tests tests/test_ec_policy.c)
target_link_libraries(ec_policy_tests PRIVATE ducktop2_ec_policy)
ducktop2_target_defaults(ec_policy_tests)
add_test(NAME ec_policy_tests COMMAND ec_policy_tests)

add_executable(ec_commit_tests tests/test_ec_commit.c)
target_link_libraries(ec_commit_tests PRIVATE ducktop2_ec_commit)
ducktop2_target_defaults(ec_commit_tests)
add_test(NAME ec_commit_tests COMMAND ec_commit_tests)

add_executable(ec_telemetry_tests tests/test_ec_telemetry.c)
target_link_libraries(ec_telemetry_tests PRIVATE ducktop2_ec_telemetry)
ducktop2_target_defaults(ec_telemetry_tests)
add_test(NAME ec_telemetry_tests COMMAND ec_telemetry_tests)

add_executable(ec_keymap_tests tests/test_ec_keymap.c)
target_link_libraries(ec_keymap_tests PRIVATE ducktop2_ec_keymap)
ducktop2_target_defaults(ec_keymap_tests)
add_test(NAME ec_keymap_tests COMMAND ec_keymap_tests)

add_executable(ec_fan_tests tests/test_ec_fan.c)
target_link_libraries(ec_fan_tests PRIVATE ducktop2_ec_fan)
ducktop2_target_defaults(ec_fan_tests)
add_test(NAME ec_fan_tests COMMAND ec_fan_tests)

add_executable(ec_oled_tests tests/test_ec_oled.c)
target_link_libraries(ec_oled_tests PRIVATE ducktop2_ec_oled)
ducktop2_target_defaults(ec_oled_tests)
add_test(NAME ec_oled_tests COMMAND ec_oled_tests)

add_executable(ec_lid_tests tests/test_ec_lid.c)
target_link_libraries(ec_lid_tests PRIVATE ducktop2_ec_lid)
ducktop2_target_defaults(ec_lid_tests)
add_test(NAME ec_lid_tests COMMAND ec_lid_tests)

add_executable(ec_battery_tests tests/test_ec_battery.c)
target_link_libraries(ec_battery_tests PRIVATE ducktop2_ec_battery ducktop2_ec_telemetry)
ducktop2_target_defaults(ec_battery_tests)
add_test(NAME ec_battery_tests COMMAND ec_battery_tests)

add_executable(bq_driver_tests tests/i2c_mock.c tests/test_ec_bq_drivers.c)
target_link_libraries(bq_driver_tests PRIVATE ducktop2_bq)
ducktop2_target_defaults(bq_driver_tests)
add_test(NAME bq_driver_tests COMMAND bq_driver_tests)

add_executable(tca9539_tests
    tests/i2c_mock.c
    tests/test_tca9539.c
    ec_target/tca9539.c)
target_include_directories(tca9539_tests PRIVATE ec_target tests)
ducktop2_target_defaults(tca9539_tests)
add_test(NAME tca9539_tests COMMAND tca9539_tests)

add_executable(fan_math_tests tests/test_fan_math.c ec_target/fan_math.c)
target_include_directories(fan_math_tests PRIVATE ec_target)
ducktop2_target_defaults(fan_math_tests)
add_test(NAME fan_math_tests COMMAND fan_math_tests)

add_executable(ec_app_math_tests tests/test_ec_app_math.c ec_target/ec_app_math.c)
target_include_directories(ec_app_math_tests PRIVATE ec_target ec/include)
ducktop2_target_defaults(ec_app_math_tests)
add_test(NAME ec_app_math_tests COMMAND ec_app_math_tests)

add_executable(usb_hid_desc_tests tests/test_usb_hid_desc.c ec_target/usb_hid_desc.c)
target_include_directories(usb_hid_desc_tests PRIVATE ec_target)
ducktop2_target_defaults(usb_hid_desc_tests)
add_test(NAME usb_hid_desc_tests COMMAND usb_hid_desc_tests)

add_executable(maker_policy_tests tests/test_maker_policy.c)
target_link_libraries(maker_policy_tests PRIVATE ducktop2_maker_policy)
ducktop2_target_defaults(maker_policy_tests)
add_test(NAME maker_policy_tests COMMAND maker_policy_tests)

add_executable(matrix_debounce_tests tests/test_matrix_debounce.c)
target_link_libraries(matrix_debounce_tests PRIVATE ducktop2_matrix_debounce)
ducktop2_target_defaults(matrix_debounce_tests)
add_test(NAME matrix_debounce_tests COMMAND matrix_debounce_tests)

find_package(Python3 COMPONENTS Interpreter QUIET)
if(Python3_Interpreter_FOUND)
    add_test(NAME release_contract_tests
             COMMAND ${Python3_EXECUTABLE}
                     ${CMAKE_CURRENT_LIST_DIR}/tools/verify_release_contract.py)
endif()

add_executable(tps25751_tests tests/test_tps25751.c tests/i2c_mock.c ec_target/tps25751.c)
target_include_directories(tps25751_tests PRIVATE ec_target ec/include tests)
target_compile_definitions(tps25751_tests PRIVATE DUCKTOP2_PD_ALLOW_20V=0)
ducktop2_target_defaults(tps25751_tests)
add_test(NAME tps25751_tests COMMAND tps25751_tests)
add_executable(target_runtime_tests tests/test_target_runtime.c ec_target/host_link.c ec/src/ec_fan_monitor.c)
target_include_directories(target_runtime_tests PRIVATE ec_target ec/include)
ducktop2_target_defaults(target_runtime_tests)
add_test(NAME target_runtime_tests COMMAND target_runtime_tests)
add_executable(ec_app_tests tests/test_ec_app.c tests/i2c_mock.c ec_target/ec_app.c ec_target/ec_app_math.c)
target_include_directories(ec_app_tests PRIVATE ec_target ec/include tests)
target_link_libraries(ec_app_tests PRIVATE ducktop2_bq ducktop2_ec_telemetry ducktop2_ec_fan ducktop2_ec_policy)
ducktop2_target_defaults(ec_app_tests)
add_test(NAME ec_app_tests COMMAND ec_app_tests)
add_executable(services_tests tests/test_services.c tests/i2c_mock.c ec_target/audio.c ec_target/ssd1306.c)
target_include_directories(services_tests PRIVATE ec_target ec/include tests)
ducktop2_target_defaults(services_tests)
add_test(NAME services_tests COMMAND services_tests)

add_executable(tps25751_20v_tests tests/test_tps25751.c tests/i2c_mock.c ec_target/tps25751.c)
target_include_directories(tps25751_20v_tests PRIVATE ec_target ec/include tests)
target_compile_definitions(tps25751_20v_tests PRIVATE DUCKTOP2_PD_ALLOW_20V=1)
ducktop2_target_defaults(tps25751_20v_tests)
add_test(NAME tps25751_20v_tests COMMAND tps25751_20v_tests)

add_executable(ec_charge_profile_tests tests/test_ec_app.c tests/i2c_mock.c ec_target/ec_app.c ec_target/ec_app_math.c)
target_include_directories(ec_charge_profile_tests PRIVATE ec_target ec/include tests)
target_compile_definitions(ec_charge_profile_tests PRIVATE DUCKTOP2_PACK_QUALIFIED=1 DUCKTOP2_CHARGING_QUALIFIED=1 DUCKTOP2_PACK_CHARGE_CURRENT_MA=500 DUCKTOP2_PACK_CHARGE_VOLTAGE_MV=12600)
target_link_libraries(ec_charge_profile_tests PRIVATE ducktop2_bq ducktop2_ec_telemetry ducktop2_ec_fan ducktop2_ec_policy)
ducktop2_target_defaults(ec_charge_profile_tests)
add_test(NAME ec_charge_profile_tests COMMAND ec_charge_profile_tests)

add_executable(ec_transfer_tests tests/test_ec_transfer.c)
target_link_libraries(ec_transfer_tests PRIVATE ducktop2_ec_policy ducktop2_ec_commit)
ducktop2_target_defaults(ec_transfer_tests)
add_test(NAME ec_transfer_tests COMMAND ec_transfer_tests)
add_executable(maker_bus_tests tests/test_maker_bus.c maker/src/maker_bus.c)
target_include_directories(maker_bus_tests PRIVATE maker/include)
ducktop2_target_defaults(maker_bus_tests)
add_test(NAME maker_bus_tests COMMAND maker_bus_tests)
add_executable(maker_bus_target_tests tests/test_maker_bus_target.c maker_target/bus_target.c)
target_include_directories(maker_bus_target_tests PRIVATE tests/maker_sdk_mock maker_target maker/include)
ducktop2_target_defaults(maker_bus_target_tests)
add_test(NAME maker_bus_target_tests COMMAND maker_bus_target_tests)

add_executable(ec_usb_power_tests ec/src/ec_usb_power.c tests/test_ec_usb_power.c)
target_include_directories(ec_usb_power_tests PRIVATE ec/include)
ducktop2_target_defaults(ec_usb_power_tests)
add_test(NAME ec_usb_power_tests COMMAND ec_usb_power_tests)

add_executable(usb_power_hw_tests ec_target/usb_power_hw.c tests/test_usb_power_hw.c)
target_include_directories(usb_power_hw_tests PRIVATE ec_target)
ducktop2_target_defaults(usb_power_hw_tests)
add_test(NAME usb_power_hw_tests COMMAND usb_power_hw_tests)
add_executable(usb_power_tests ec_target/usb_power.c ec/src/ec_usb_power.c tests/test_usb_power.c)
target_include_directories(usb_power_tests PRIVATE ec_target ec/include)
ducktop2_target_defaults(usb_power_tests)
add_test(NAME usb_power_tests COMMAND usb_power_tests)

find_package(Python3 COMPONENTS Interpreter REQUIRED)
add_test(NAME tps25751_config_tests COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/tests/test_tps25751_config.py)
