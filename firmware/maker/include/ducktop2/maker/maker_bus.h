#ifndef DUCKTOP2_MAKER_BUS_H
#define DUCKTOP2_MAKER_BUS_H
#include "maker_policy.h"
#include <stdint.h>
#define MAKER_BUS_REPORT_SIZE 64u
#define MAKER_BUS_MAX_BYTES 32u
#define MAKER_BUS_MAX_TIMEOUT_MS 100u
typedef enum { MAKER_BUS_UART=1, MAKER_BUS_I2C=2, MAKER_BUS_SPI=3 } maker_bus_kind_t;
typedef enum { MAKER_BUS_OK=0, MAKER_BUS_BAD_REQUEST, MAKER_BUS_NO_LEASE,
               MAKER_BUS_PIN_CONFLICT, MAKER_BUS_TIMEOUT, MAKER_BUS_IO,
               MAKER_BUS_REPLAY, MAKER_BUS_BUSY } maker_bus_result_t;
typedef struct {
    uint32_t sequence,rate;
    uint16_t timeout_ms;
    uint8_t kind,flags,tx_size,rx_size,address;
    uint8_t tx[MAKER_BUS_MAX_BYTES];
} maker_bus_request_t;
/* Parse and validate without touching hardware. Data is copied, never retained
 * through an untrusted USB buffer pointer. Only passive pins can be borrowed. */
maker_bus_result_t maker_bus_parse(const uint8_t *packet,uint16_t size,
    uint32_t last_sequence,bool authorized,uint32_t lease_left_ms,
    const maker_outputs_t *pins,maker_bus_request_t *request);
void maker_bus_response(uint8_t packet[64],const maker_bus_request_t *request,
    maker_bus_result_t result,const uint8_t *rx,uint8_t size,uint32_t actual_rate,
    uint16_t elapsed_ms);
#endif
