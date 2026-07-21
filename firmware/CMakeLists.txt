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

add_library(ducktop2_maker_policy STATIC maker/src/maker_policy.c)
target_include_directories(ducktop2_maker_policy PUBLIC maker/include)
ducktop2_target_defaults(ducktop2_maker_policy)

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

add_executable(maker_policy_tests tests/test_maker_policy.c)
target_link_libraries(maker_policy_tests PRIVATE ducktop2_maker_policy)
ducktop2_target_defaults(maker_policy_tests)
add_test(NAME maker_policy_tests COMMAND maker_policy_tests)

find_package(Python3 COMPONENTS Interpreter QUIET)
if(Python3_Interpreter_FOUND)
    add_test(NAME release_contract_tests
             COMMAND ${Python3_EXECUTABLE}
                     ${CMAKE_CURRENT_LIST_DIR}/tools/verify_release_contract.py)
endif()
