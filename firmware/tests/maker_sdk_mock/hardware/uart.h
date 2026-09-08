#include "pico/stdlib.h"
typedef struct {volatile uint32_t dr,fr;} uart_hw_t;
typedef struct {uart_hw_t hw;} uart_inst_t;
extern uart_inst_t mock_uart;
#define uart0 (&mock_uart)
#define UART_PARITY_NONE 0
uint32_t uart_init(uart_inst_t *uart,uint32_t baud);
void uart_deinit(uart_inst_t *uart);
void uart_set_format(uart_inst_t *uart,unsigned bits,unsigned stop,unsigned parity);
void uart_set_hw_flow(uart_inst_t *uart,bool cts,bool rts);
bool uart_is_writable(uart_inst_t *uart);
bool uart_is_readable(uart_inst_t *uart);
uart_hw_t *uart_get_hw(uart_inst_t *uart);
