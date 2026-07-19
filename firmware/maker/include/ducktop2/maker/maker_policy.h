#ifndef DUCKTOP2_MAKER_POLICY_H
#define DUCKTOP2_MAKER_POLICY_H

#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

#define MAKER_USER_IO_COUNT 26u

typedef enum {
  MAKER_IO_HIGH_IMPEDANCE = 0,
  MAKER_IO_INPUT,
  MAKER_IO_ANALOG_INPUT,
  MAKER_IO_OUTPUT_LOW,
  MAKER_IO_OUTPUT_HIGH,
  MAKER_IO_ALTERNATE_FUNCTION
} maker_io_mode_t;

typedef enum {
  MAKER_FAULT_NONE = 0,
  MAKER_FAULT_WATCHDOG,
  MAKER_FAULT_USER_POWER,
  MAKER_FAULT_INTERLOCK,
  MAKER_FAULT_IO_AUTHORIZATION
} maker_fault_t;

typedef struct {
  bool reset_asserted;
  bool watchdog_healthy;
  bool user_power_fault_n;
  bool hardware_interlock_ready;
  bool user_power_authorized;
  bool user_io_authorized;
} maker_inputs_t;

typedef struct {
  bool user_rails_enable;
  maker_io_mode_t io_mode[MAKER_USER_IO_COUNT];
} maker_outputs_t;

typedef struct {
  bool user_rails_requested;
  maker_io_mode_t requested_io_mode[MAKER_USER_IO_COUNT];
  maker_fault_t fault;
  maker_outputs_t outputs;
} maker_controller_t;

void maker_inputs_init(maker_inputs_t *inputs);
void maker_controller_init(maker_controller_t *controller);
void maker_controller_request_user_rails(maker_controller_t *controller,
                                         bool enable);
bool maker_controller_request_io_mode(maker_controller_t *controller,
                                      size_t index, maker_io_mode_t mode);
void maker_controller_step(maker_controller_t *controller,
                           const maker_inputs_t *inputs);
void maker_controller_watchdog_trip(maker_controller_t *controller);
bool maker_controller_clear_fault(maker_controller_t *controller,
                                  bool root_cause_removed);
const maker_outputs_t *
maker_controller_outputs(const maker_controller_t *controller);

#ifdef __cplusplus
}
#endif

#endif
