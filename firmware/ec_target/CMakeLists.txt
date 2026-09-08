cmake_minimum_required(VERSION 3.20)

set(CMAKE_SYSTEM_NAME Generic)
set(CMAKE_SYSTEM_PROCESSOR arm)
set(CMAKE_TRY_COMPILE_TARGET_TYPE STATIC_LIBRARY)

find_program(ARM_CC arm-none-eabi-gcc)
find_program(ARM_AS arm-none-eabi-as)
find_program(ARM_OBJCOPY arm-none-eabi-objcopy)
find_program(ARM_SIZE arm-none-eabi-size)

if(NOT ARM_CC)
    message(FATAL_ERROR "arm-none-eabi-gcc not found. Install ARM GCC toolchain.")
endif()

set(CMAKE_C_COMPILER ${ARM_CC})
set(CMAKE_ASM_COMPILER ${ARM_CC})

set(COMMON_FLAGS "-mcpu=cortex-m4 -mthumb -mfloat-abi=hard -mfpu=fpv4-sp-d16")
set(FREESTANDING_FLAGS "-ffreestanding -nostdlib -nostdinc")
set(CMAKE_C_FLAGS "${COMMON_FLAGS} ${FREESTANDING_FLAGS} -std=c11 \
    -DSTM32F407xx -DHSE_VALUE=8000000 \
    -ffunction-sections -fdata-sections -fstack-usage -Wall -Wextra -Wpedantic -Werror \
    -Wno-maybe-uninitialized")
set(CMAKE_C_FLAGS_DEBUG "-Og -g3 -DDEBUG")
set(CMAKE_C_FLAGS_RELEASE "-O2 -g0 -DNDEBUG")
set(CMAKE_EXE_LINKER_FLAGS "${COMMON_FLAGS} -Wl,--gc-sections -Wl,-Map=${CMAKE_PROJECT_NAME}.map")
set(CMAKE_ASM_FLAGS "-mcpu=cortex-m4 -mthumb -mfpu=fpv4-sp-d16")
set(CMAKE_ASM_FLAGS_DEBUG "-g")
set(CMAKE_ASM_FLAGS_RELEASE "")

file(STRINGS "${CMAKE_CURRENT_LIST_DIR}/../VERSION" DUCKTOP2_FIRMWARE_VERSION
     LIMIT_COUNT 1)
string(REGEX MATCH "^[0-9]+\\.[0-9]+\\.[0-9]+" DUCKTOP2_PROJECT_VERSION
       "${DUCKTOP2_FIRMWARE_VERSION}")
if(NOT DUCKTOP2_PROJECT_VERSION)
    message(FATAL_ERROR "../VERSION must begin with semantic x.y.z")
endif()

project(ducktop2_firmware_ec VERSION ${DUCKTOP2_PROJECT_VERSION} LANGUAGES C ASM)

set(EC_TARGET_DIR "${CMAKE_CURRENT_LIST_DIR}")
set(EC_SRC_DIR "${EC_TARGET_DIR}/..")

set(TARGET_SOURCES
    main.c
    startup_stm32f407vgtx.s
    system_stm32f4xx.c
    watchdog.c
    gpio.c
    i2c.c
    tca9539.c
    tps25751.c
    bq25798.c
    bq34z100.c
    audio.c
    ssd1306.c
    host_link.c
    usb_power.c
    usb_power_hw.c
    ec_app.c
    ec_app_math.c
    fan_math.c
    matrix_scan.c
    matrix_debounce.c
    usb_hid.c
    usb_hid_desc.c
    libc_stubs.c
)

list(TRANSFORM TARGET_SOURCES PREPEND "${EC_TARGET_DIR}/")

set(POLICY_SOURCES
    "${EC_SRC_DIR}/ec/src/ec_policy.c"
    "${EC_SRC_DIR}/ec/src/ec_commit.c"
    "${EC_SRC_DIR}/ec/src/ec_telemetry.c"
    "${EC_SRC_DIR}/ec/src/ec_fan.c"
    "${EC_SRC_DIR}/ec/src/ec_fan_monitor.c"
    "${EC_SRC_DIR}/ec/src/ec_usb_power.c"
    "${EC_SRC_DIR}/ec/src/ec_keymap.c"
    "${EC_SRC_DIR}/ec/src/ec_battery.c"
    "${EC_SRC_DIR}/ec/src/ec_lid.c"
)

add_executable(ducktop2_ec ${TARGET_SOURCES} ${POLICY_SOURCES})
target_compile_definitions(ducktop2_ec PRIVATE
    DUCKTOP2_FIRMWARE_VERSION="${DUCKTOP2_FIRMWARE_VERSION}")
set(DUCKTOP2_PROFILE_FIELDS
    PACK_QUALIFIED GAUGE_QUALIFIED CHARGING_QUALIFIED PACK_BRIDGE_QUALIFIED
    EXTERNAL_BOOT_QUALIFIED EXTERNAL_BOOT_BUDGET_MW
    PACK_BOOT_QUALIFIED PACK_BOOT_BUDGET_MW AUX_QUALIFIED_CURRENT_MA
    PD_ALLOW_20V IINDPM_CAP_MA PD_IINDPM_MARGIN_MA PACK_USABLE_CURRENT_MA
    PACK_CHARGE_CURRENT_MA PACK_CHARGE_VOLTAGE_MV
    AUX_WORST_CASE_MW AUX_LOADS_QUALIFIED USB_POWER_QUALIFIED USB_ADMISSION_MA
    USB_RIGHT_HARNESS_MA USB_EFFICIENCY_PERCENT USB_PD_INRUSH_MA USB_BRANCH_INRUSH_MA)
foreach(field IN LISTS DUCKTOP2_PROFILE_FIELDS)
    set(key "DUCKTOP2_${field}")
    if(DEFINED ${key})
        if(NOT "${${key}}" MATCHES "^[0-9]+$")
            message(FATAL_ERROR "${key} must be an integer, with 0/1 for switches")
        endif()
        target_compile_definitions(ducktop2_ec PRIVATE "${key}=${${key}}")
    endif()
endforeach()
target_include_directories(ducktop2_ec PRIVATE ${EC_TARGET_DIR})
target_include_directories(ducktop2_ec PRIVATE ${EC_TARGET_DIR}/include)
target_include_directories(ducktop2_ec PUBLIC ${EC_SRC_DIR}/ec/include)
set(VENDOR_DIR "${EC_SRC_DIR}/vendor")
set(TINYUSB_DIR "${VENDOR_DIR}/tinyusb/src")
target_include_directories(ducktop2_ec SYSTEM PRIVATE
    "${VENDOR_DIR}/cmsis-device-f4/Include"
    "${VENDOR_DIR}/cmsis-core/CMSIS/Core/Include"
    "${TINYUSB_DIR}")
set(TINYUSB_SOURCES
    "${TINYUSB_DIR}/tusb.c"
    "${TINYUSB_DIR}/common/tusb_fifo.c"
    "${TINYUSB_DIR}/device/usbd.c"
    "${TINYUSB_DIR}/class/hid/hid_device.c"
    "${TINYUSB_DIR}/portable/synopsys/dwc2/dcd_dwc2.c"
    "${TINYUSB_DIR}/portable/synopsys/dwc2/dwc2_common.c")
# Upstream uses unsigned 32-bit flag enums, a supported GCC extension.
set_source_files_properties(${TINYUSB_SOURCES} PROPERTIES COMPILE_OPTIONS "-Wno-pedantic")
target_sources(ducktop2_ec PRIVATE ${TINYUSB_SOURCES})
target_link_options(ducktop2_ec PRIVATE
    -T${EC_TARGET_DIR}/STM32F407VGTx_FLASH.ld
    -nostdlib)
target_link_libraries(ducktop2_ec PRIVATE gcc)

add_custom_command(TARGET ducktop2_ec POST_BUILD
    COMMAND ${ARM_OBJCOPY} -O binary ducktop2_ec ducktop2_ec.bin
    COMMAND ${ARM_SIZE} ducktop2_ec
    COMMENT "Generating ducktop2_ec.bin"
    BYPRODUCTS ducktop2_ec.bin
    WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
)
