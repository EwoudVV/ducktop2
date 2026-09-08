#ifndef DUCKTOP2_TPS25751_H
#define DUCKTOP2_TPS25751_H
#include <stdbool.h>
#include <stdint.h>

typedef struct {
    bool connected;
    bool sink;
    bool dfp;
    bool valid;
    uint16_t voltage_mv;
    uint16_t current_ma;
} tps25751_contract_t;

/* SPMU379A tables 5-11, 5-21, 5-22, 5-25. The caller owns mux selection. */
bool tps25751_read_contract(uint8_t address, tps25751_contract_t *contract);
bool tps25751_decode_contract(const uint8_t status[5], const uint8_t pdo[6],
                              const uint8_t rdo[16], const uint8_t pd_status[4],
                              tps25751_contract_t *contract);

/* Runtime output-side observation is separate from sink qualification. */
typedef struct {
    bool valid, connected, source, dfp, pp5v_enabled, vconn_enabled;
    bool pphv_input_enabled, power_path_fault, source_profile_valid;
    uint8_t typec_mode, vconn_switch;
} tps25751_port_state_t;
bool tps25751_read_port_state(uint8_t address, tps25751_port_state_t *state);
/* 0 = Sink-only, 2 = DRP. A changed value disconnects/reconnects the port.
 * This acknowledges configuration readback, not a live power transition. */
bool tps25751_set_typec_mode(uint8_t address, uint8_t mode);

#endif
