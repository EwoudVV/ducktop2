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
set(CMAKE_ASM_COMPILER ${ARM_AS})

set(COMMON_FLAGS "-mcpu=cortex-m4 -mthumb -mfloat-abi=hard -mfpu=fpv4-sp-d16")
set(FREESTANDING_FLAGS "-ffreestanding -nostdlib -nostdinc")
set(CMAKE_C_FLAGS "${COMMON_FLAGS} ${FREESTANDING_FLAGS} -std=c11 \
    -DSTM32F407xx -DHSE_VALUE=8000000 \
    -DDUCKTOP2_FIRMWARE_VERSION='\"${DUCKTOP2_FIRMWARE_VERSION}\"' \
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
    gpio.c
    i2c.c
    bq25798.c
    bq34z100.c
    ec_app.c
    ec_app_math.c
    fan_math.c
    libc_stubs.c
)

list(TRANSFORM TARGET_SOURCES PREPEND "${EC_TARGET_DIR}/")

set(POLICY_SOURCES
    "${EC_SRC_DIR}/ec/src/ec_policy.c"
    "${EC_SRC_DIR}/ec/src/ec_commit.c"
    "${EC_SRC_DIR}/ec/src/ec_telemetry.c"
    "${EC_SRC_DIR}/ec/src/ec_fan.c"
)

add_executable(ducktop2_ec ${TARGET_SOURCES} ${POLICY_SOURCES})
target_include_directories(ducktop2_ec PRIVATE ${EC_TARGET_DIR})
target_include_directories(ducktop2_ec PRIVATE ${EC_TARGET_DIR}/include)
target_include_directories(ducktop2_ec PUBLIC ${EC_SRC_DIR}/ec/include)
target_link_options(ducktop2_ec PRIVATE
    -T${EC_TARGET_DIR}/STM32F407VGTx_FLASH.ld
    -nostdlib)

add_custom_command(TARGET ducktop2_ec POST_BUILD
    COMMAND ${ARM_OBJCOPY} -O binary ducktop2_ec ducktop2_ec.bin
    COMMAND ${ARM_SIZE} ducktop2_ec
    COMMENT "Generating ducktop2_ec.bin"
    BYPRODUCTS ducktop2_ec.bin
    WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
)
