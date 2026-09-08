#include "bus_target.h"
#include "pico/stdlib.h"
#include "hardware/uart.h"
#include "hardware/i2c.h"
#include "hardware/spi.h"
#include "hardware/regs/uart.h"

static void input(unsigned pin){gpio_set_dir(pin,GPIO_IN);gpio_set_function(pin,GPIO_FUNC_SIO);gpio_disable_pulls(pin);}
void maker_bus_target_abort(void)
{
    /* Pin isolation first makes a stalled peripheral unable to drive the header. */
    input(0);input(1);input(2);input(3);
    for(unsigned pin=16;pin<20;pin++)input(pin);
    uart_deinit(uart0);i2c_deinit(i2c1);spi_deinit(spi0);
}
static bool within(absolute_time_t deadline,bool (*guard)(void))
{return guard && guard() && absolute_time_diff_us(get_absolute_time(),deadline)>0;}
maker_bus_result_t maker_bus_target_execute(const maker_bus_request_t *r,bool (*guard)(void),
    uint8_t *rx,uint8_t *received,uint32_t *actual_rate)
{
    absolute_time_t deadline=make_timeout_time_ms(r->timeout_ms);
    maker_bus_result_t result=MAKER_BUS_OK;*received=0;*actual_rate=0;
    if(!within(deadline,guard))return MAKER_BUS_NO_LEASE;
    if(r->kind==MAKER_BUS_UART){
        *actual_rate=uart_init(uart0,r->rate);uart_set_format(uart0,8,1,UART_PARITY_NONE);
        uart_set_hw_flow(uart0,false,false);gpio_set_function(0,GPIO_FUNC_UART);gpio_set_function(1,GPIO_FUNC_UART);
        for(unsigned n=0;n<r->tx_size;n++){
            while(!uart_is_writable(uart0))if(!within(deadline,guard)){result=MAKER_BUS_TIMEOUT;goto done;}
            if(!within(deadline,guard)){result=MAKER_BUS_TIMEOUT;goto done;}
            uart_get_hw(uart0)->dr=r->tx[n];
        }
        while(uart_get_hw(uart0)->fr & UART_UARTFR_BUSY_BITS)
            if(!within(deadline,guard)){result=MAKER_BUS_TIMEOUT;goto done;}
        while(*received<r->rx_size){
            if(!within(deadline,guard)){result=MAKER_BUS_TIMEOUT;goto done;}
            if(uart_is_readable(uart0)){
                uint32_t data=uart_get_hw(uart0)->dr;
                if(data&0xf00u){result=MAKER_BUS_IO;goto done;}
                rx[(*received)++]=(uint8_t)data;
            }
        }
    }else if(r->kind==MAKER_BUS_I2C){
        *actual_rate=i2c_init(i2c1,r->rate);
        gpio_set_function(2,GPIO_FUNC_I2C);gpio_set_function(3,GPIO_FUNC_I2C);
        int count;
        if(r->tx_size){
            count=i2c_write_blocking_until(i2c1,r->address,r->tx,r->tx_size,r->rx_size!=0,deadline);
            if(count!=(int)r->tx_size){result=count==PICO_ERROR_TIMEOUT?MAKER_BUS_TIMEOUT:MAKER_BUS_IO;goto done;}
        }
        if(!within(deadline,guard)){result=MAKER_BUS_TIMEOUT;goto done;}
        if(r->rx_size){
            count=i2c_read_blocking_until(i2c1,r->address,rx,r->rx_size,false,deadline);
            if(count!=(int)r->rx_size){result=count==PICO_ERROR_TIMEOUT?MAKER_BUS_TIMEOUT:MAKER_BUS_IO;goto done;}
            *received=(uint8_t)count;
        }
    }else if(r->kind==MAKER_BUS_SPI){
        *actual_rate=spi_init(spi0,r->rate);spi_set_format(spi0,8,(r->flags&2)?SPI_CPOL_1:SPI_CPOL_0,
                                                       (r->flags&1)?SPI_CPHA_1:SPI_CPHA_0,SPI_MSB_FIRST);
        gpio_set_function(16,GPIO_FUNC_SPI);gpio_set_function(18,GPIO_FUNC_SPI);gpio_set_function(19,GPIO_FUNC_SPI);
        gpio_put(17,1);gpio_set_function(17,GPIO_FUNC_SIO);gpio_set_dir(17,GPIO_OUT);gpio_put(17,0);
        unsigned length=r->tx_size?r->tx_size:r->rx_size,tx=0,read=0;
        while(read<length){
            if(!within(deadline,guard)){result=MAKER_BUS_TIMEOUT;goto done;}
            if(tx<length && spi_is_writable(spi0)) {
                spi_get_hw(spi0)->dr=r->tx_size?r->tx[tx]:0xffu;tx++;
            }
            if(spi_is_readable(spi0)){uint8_t data=(uint8_t)spi_get_hw(spi0)->dr;if(read<r->rx_size)rx[read]=data;read++;}
        }
        while(spi_is_busy(spi0))if(!within(deadline,guard)){result=MAKER_BUS_TIMEOUT;goto done;}
        gpio_put(17,1);*received=r->rx_size;
    }else result=MAKER_BUS_BAD_REQUEST;
    if(!within(deadline,guard))result=MAKER_BUS_TIMEOUT;
 done:
    /* Only borrowed pins are changed here. Global passive handling on errors
     * is owned by the main loop and clears user authorization as well. */
    if(r->kind==MAKER_BUS_UART){input(0);input(1);uart_deinit(uart0);}
    if(r->kind==MAKER_BUS_I2C){input(2);input(3);i2c_deinit(i2c1);}
    if(r->kind==MAKER_BUS_SPI){gpio_put(17,1);for(unsigned pin=16;pin<20;pin++)input(pin);spi_deinit(spi0);}
    return result;
}
