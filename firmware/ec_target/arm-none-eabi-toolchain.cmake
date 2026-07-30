set(CMAKE_SYSTEM_NAME Generic)
set(CMAKE_SYSTEM_PROCESSOR arm)
set(CMAKE_TRY_COMPILE_TARGET_TYPE STATIC_LIBRARY)

find_program(CMAKE_C_COMPILER arm-none-eabi-gcc)
find_program(CMAKE_ASM_COMPILER arm-none-eabi-as)

if(NOT CMAKE_C_COMPILER)
    message(FATAL_ERROR "arm-none-eabi-gcc not found")
endif()

set(CMAKE_C_FLAGS "-mcpu=cortex-m4 -mthumb -mfloat-abi=hard -mfpu=fpv4-sp-d16 \
    -ffunction-sections -fdata-sections -fstack-usage -Wall -Wextra -Wpedantic \
    -Werror -Wno-unused-parameter" CACHE STRING "ARM GCC C flags")
set(CMAKE_C_FLAGS_DEBUG "-Og -g3 -DDEBUG" CACHE STRING "Debug flags")
set(CMAKE_C_FLAGS_RELEASE "-O2 -g0 -DNDEBUG" CACHE STRING "Release flags")
set(CMAKE_EXE_LINKER_FLAGS "-Wl,--gc-sections -Wl,-Map=ducktop2_ec.map" CACHE STRING "Linker flags")
set(CMAKE_ASM_FLAGS "-mcpu=cortex-m4 -mthumb -x assembler-with-cpp" CACHE STRING "ASM flags")

set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)
