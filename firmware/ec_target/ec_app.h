/*
 * Ducktop2 EC target glue: binds the BQ25798/BQ34Z100 drivers, thermal ADC,
 * and fan PWM/tach hardware to the host-tested policy contracts
 * (ec_inputs_t / ec_telemetry_inputs_t / ec_fan_*).
 *
 * Design rules followed here:
 *  - Every hardware probe result is latched; a dead device makes the
 *    corresponding input invalid (never stale data).
 *  - Thermal data that cannot be converted forces the fan fail-safe
 *    (ec_fan handles invalid temps with 100% duty) and clears thermal_ok.
 *  - The fan PWM is driven with the Delta BFB04512HHA-CZ0T contract:
 *    open-drain node, complement encoding in gpio.c, 25 kHz, and a minimum
 *    35% start duty for spin-up (policy floor is 30%).
 *  - Pure math (NTC conversion, spin-up duty) is host-tested.
 */

#ifndef DUCKTOP2_EC_APP_H
#define DUCKTOP2_EC_APP_H

#include <stdbool.h>
#include <stdint.h>

#include "ducktop2/ec/ec_policy.h"
#include "ducktop2/ec/ec_telemetry.h"
#include "ducktop2/ec/ec_fan.h"
#include "ec_app_math.h"

#ifdef __cplusplus
extern "C" {
#endif

/*
 * Hardware init: probes the charger and gauge once; latches configuration
 * validity.  Call once after I2C init.  Never blocks longer than the I2C
 * driver timeouts.
 */
void ec_app_init(void);
bool ec_app_charger_configured(void);
bool ec_app_gauge_present(void);
/* Fresh result of the last charger telemetry read (REG1D VBAT present). */
bool ec_app_battery_present(void);

/*
 * Fill the power/battery/thermal inputs the policy consumes.  PD contract
 * reads stay in main.c (they touch the TCA9548A mux); this fills the
 * charger, pack, VSYS, and thermal fields of both structs.
 */
void ec_app_read_power_inputs(ec_inputs_t *inputs,
                              ec_telemetry_inputs_t *telemetry);

/* Commit-side: apply the policy IINDPM command to the charger.  Returns
 * true when the charger accepted the write and the applied value is
 * latched for read_inputs. */
bool ec_app_apply_charger_iindpm_ma(uint16_t ma);
uint16_t ec_app_applied_charger_iindpm_ma(void);
bool ec_app_charger_iindpm_applied(void);

/*
 * Fan loop: read both NTCs, convert, run the fan policy, and return the
 * duty to write (spin-up override applied).  Updates the tach window as a
 * side effect; rpm_out may be NULL.
 */
uint8_t ec_app_fan_step(const ec_fan_config_t *config, ec_fan_state_t *state,
                        uint32_t now_ms, uint16_t *rpm_out);

#ifdef __cplusplus
}
#endif

#endif /* DUCKTOP2_EC_APP_H */
