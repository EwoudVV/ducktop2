/*
 * Host tests for the EC app pure math (NTC conversion + fan spin-up duty).
 */

#include <assert.h>
#include <stdio.h>
#include <stdlib.h>

#include "ec_app_math.h"

static int s_checks = 0;

#define CHECK(cond)                                                        \
    do {                                                                   \
        s_checks++;                                                        \
        if (!(cond)) {                                                     \
            fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond); \
            exit(1);                                                       \
        }                                                                  \
    } while (0)

static void test_ntc_midscale_25c(void)
{
    /* 25C: R_ntc = R0 -> divider midpoint -> counts ~= 2047. */
    ec_fan_temp_dc_t t = ec_app_ntc_counts_to_temp_dc(2047u);
    CHECK(t > 200 && t < 300);
}

static void test_ntc_endpoints_invalid(void)
{
    CHECK(ec_app_ntc_counts_to_temp_dc(0u) == EC_APP_TEMP_INVALID_DC);
    CHECK(ec_app_ntc_counts_to_temp_dc(4095u) == EC_APP_TEMP_INVALID_DC);
}

static void test_ntc_monotonic(void)
{
    /* Higher temperature -> lower NTC resistance -> lower divider voltage
     * -> fewer counts.  So counts 500 (hot) < counts 3500 (cold). */
    ec_fan_temp_dc_t hot = ec_app_ntc_counts_to_temp_dc(500u);
    ec_fan_temp_dc_t cold = ec_app_ntc_counts_to_temp_dc(3500u);
    CHECK(hot != EC_APP_TEMP_INVALID_DC);
    CHECK(cold != EC_APP_TEMP_INVALID_DC);
    CHECK(hot > cold);
}

static void test_ntc_room_and_body_range(void)
{
    /* Sanity window: 300..500 counts should be well inside 0..100C. */
    ec_fan_temp_dc_t t = ec_app_ntc_counts_to_temp_dc(400u);
    CHECK(t > 0 && t < 1000);
}

static void test_start_duty_off(void)
{
    CHECK(ec_app_fan_start_duty(30u, false, 0u, 500u) == 0u);
}

static void test_start_duty_spin_up_window(void)
{
    /* Policy floor 30% is below the Delta 35% start duty: hold 35% for the
     * first second after start. */
    CHECK(ec_app_fan_start_duty(30u, true, 100u, 500u) == 35u);
    CHECK(ec_app_fan_start_duty(30u, true, 100u, 1099u) == 35u);
}

static void test_start_duty_after_window(void)
{
    CHECK(ec_app_fan_start_duty(30u, true, 100u, 1101u) == 30u);
    CHECK(ec_app_fan_start_duty(30u, true, 100u, 20000u) == 30u);
}

static void test_start_duty_at_or_above_floor(void)
{
    CHECK(ec_app_fan_start_duty(35u, true, 0u, 10u) == 35u);
    CHECK(ec_app_fan_start_duty(100u, true, 0u, 10u) == 100u);
}

static void test_aux_mv_conversion(void)
{
    uint16_t mv = 0u;

    /* Divider 470k/56k: full scale ~31.0 V; mid counts ~15.5 V. */
    CHECK(ec_app_aux_counts_to_mv(2048u, &mv));
    CHECK(mv > 15000u && mv < 16000u);
    CHECK(ec_app_aux_counts_to_mv(1024u, &mv));
    CHECK(mv > 7500u && mv < 8000u);

    /* Endpoints are not measurable inputs. */
    CHECK(!ec_app_aux_counts_to_mv(0u, &mv));
    CHECK(mv == 0u);
    CHECK(ec_app_aux_counts_to_mv(4094u, &mv));
    CHECK(mv > 30500u && mv < 31000u);
    CHECK(!ec_app_aux_counts_to_mv(4095u, &mv));
    CHECK(!ec_app_aux_counts_to_mv(100u, NULL));
}

int main(void)
{
    test_ntc_midscale_25c();
    test_ntc_endpoints_invalid();
    test_ntc_monotonic();
    test_ntc_room_and_body_range();
    test_start_duty_off();
    test_start_duty_spin_up_window();
    test_start_duty_after_window();
    test_start_duty_at_or_above_floor();
    test_aux_mv_conversion();
    printf("ec_app_math_tests: PASS (%d checks)\n", s_checks);
    return 0;
}
