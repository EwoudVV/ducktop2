#ifndef DUCKTOP2_EC_COMMIT_H
#define DUCKTOP2_EC_COMMIT_H

#include "ducktop2/ec/ec_policy.h"

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
  EC_COMMIT_PD1_PATH_ENABLE = 0,
  EC_COMMIT_PD2_PATH_ENABLE,
  EC_COMMIT_PD3_PATH_ENABLE,
  EC_COMMIT_CHARGER_IINDPM_MA,
  EC_COMMIT_CHARGE_BUDGET_MW,
  EC_COMMIT_MU_EDP_BUDGET_MW,
  EC_COMMIT_CHARGER_ENABLE,
  EC_COMMIT_MU_12V_ENABLE,
  EC_COMMIT_KEYBOARD_RGB_ENABLE,
  EC_COMMIT_RADIO_VHF_ENABLE,
  EC_COMMIT_RADIO_UHF_ENABLE,
  EC_COMMIT_AUDIO_AMP_ENABLE,
  EC_COMMIT_AUDIO_MIC_ENABLE,
  EC_COMMIT_COMMAND_COUNT
} ec_commit_command_t;

typedef bool (*ec_commit_write_fn)(void *context, ec_commit_command_t command,
                                   uint32_t value);

typedef struct {
  void *context;
  ec_commit_write_fn write;
} ec_commit_driver_t;

typedef enum {
  EC_COMMIT_OK = 0,
  EC_COMMIT_INVALID_ARGUMENT,
  EC_COMMIT_INVALID_DESIRED_STATE,
  EC_COMMIT_IO_ERROR,
  EC_COMMIT_SAFE_STATE_IO_ERROR
} ec_commit_result_t;

typedef struct {
  ec_outputs_t applied;
  bool initialized;
} ec_commit_state_t;

void ec_commit_state_init(ec_commit_state_t *state);
ec_commit_result_t ec_commit_force_safe(ec_commit_state_t *state,
                                        const ec_commit_driver_t *driver);
ec_commit_result_t ec_commit_apply(ec_commit_state_t *state,
                                   const ec_commit_driver_t *driver,
                                   const ec_outputs_t *desired);

#ifdef __cplusplus
}
#endif

#endif
