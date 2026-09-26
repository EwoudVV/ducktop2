#ifndef DUCKTOP2_TCA9537_H
#define DUCKTOP2_TCA9537_H
#include <stdbool.h>
#include <stdint.h>

#define TCA9537_ADDRESS 0x49u
#define TCA9537_AUX_ENABLE (1u << 0)
#define TCA9537_CHARGER_BIAS_GOOD (1u << 1)
#define TCA9537_PACK_CHARGE_PERMIT (1u << 2)
#define TCA9537_PROCHOT_N (1u << 3)

/* P0 is the only output. RESET follows the EC reset line, so its external
 * pull-down disables AUX even when the processor cannot reach the bus. */
bool tca9537_init_safe(void);
bool tca9537_read_inputs(uint8_t *inputs);
bool tca9537_set_aux_enable(bool enable);
bool tca9537_aux_enabled(void);
#endif
