#include "bus_target.h"
#include "pico/stdlib.h"
#include "hardware/uart.h"
#include "hardware/i2c.h"
#include "hardware/spi.h"
#include "hardware/regs/uart.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
uart_inst_t mock_uart;spi_inst_t mock_spi;i2c_inst_t mock_i2c;
static uint32_t elapsed,abort_at;static bool stuck,rx_error;
static unsigned functions[30],directions[30],writes,reads;
static absolute_time_t write_deadline,read_deadline;
absolute_time_t get_absolute_time(void){elapsed+=1000;return elapsed;}
absolute_time_t make_timeout_time_ms(uint32_t ms){return elapsed+ms*1000;}
int64_t absolute_time_diff_us(absolute_time_t a,absolute_time_t b){return b-a;}
void gpio_set_dir(unsigned p,bool out){directions[p]=out;}
void gpio_set_function(unsigned p,unsigned fn){functions[p]=fn;}
void gpio_disable_pulls(unsigned p){(void)p;}
void gpio_put(unsigned p,bool value){(void)p;(void)value;}
uint32_t uart_init(uart_inst_t *u,uint32_t rate){memset(u,0,sizeof(*u));return rate;}
void uart_deinit(uart_inst_t *u){(void)u;}
void uart_set_format(uart_inst_t *u,unsigned bits,unsigned stop,unsigned parity){(void)u;assert(bits==8 && stop==1 && parity==0);}
void uart_set_hw_flow(uart_inst_t *u,bool cts,bool rts){(void)u;assert(!cts && !rts);}
bool uart_is_writable(uart_inst_t *u){(void)u;return !stuck;}
bool uart_is_readable(uart_inst_t *u){u->hw.dr=rx_error?0x85a:0x5a;return !stuck;}
uart_hw_t *uart_get_hw(uart_inst_t *u){return &u->hw;}
uint32_t spi_init(spi_inst_t *s,uint32_t rate){memset(s,0,sizeof(*s));return rate;}
void spi_deinit(spi_inst_t *s){(void)s;}
void spi_set_format(spi_inst_t *s,unsigned bits,unsigned pol,unsigned phase,unsigned order){(void)s;assert(bits==8 && pol<=1 && phase<=1 && order==0);}
bool spi_is_writable(spi_inst_t *s){(void)s;return !stuck;}
bool spi_is_readable(spi_inst_t *s){(void)s;return !stuck;}
bool spi_is_busy(spi_inst_t *s){(void)s;return stuck;}
spi_hw_t *spi_get_hw(spi_inst_t *s){return &s->hw;}
uint32_t i2c_init(i2c_inst_t *i,uint32_t rate){i->active=true;return rate;}
void i2c_deinit(i2c_inst_t *i){i->active=false;}
int i2c_write_blocking_until(i2c_inst_t *i,uint8_t address,const uint8_t *data,size_t n,bool nostop,absolute_time_t deadline)
{
    assert(i->active && address==0x55 && data[0]==0xa1 && nostop);writes++;write_deadline=deadline;
    if(stuck){elapsed=(uint32_t)deadline;return PICO_ERROR_TIMEOUT;}elapsed+=10000;return (int)n;
}
int i2c_read_blocking_until(i2c_inst_t *i,uint8_t address,uint8_t *data,size_t n,bool nostop,absolute_time_t deadline)
{
    assert(i->active && address==0x55 && !nostop);reads++;read_deadline=deadline;memset(data,0x3c,n);return (int)n;
}
static bool guard(void){return !abort_at || elapsed<abort_at;}
static void reset(void){elapsed=abort_at=writes=reads=0;stuck=rx_error=false;for(unsigned i=0;i<30;i++){functions[i]=GPIO_FUNC_SIO;directions[i]=0;}directions[10]=1;}
static void cleaned(unsigned first,unsigned count){for(unsigned i=first;i<first+count;i++)assert(functions[i]==GPIO_FUNC_SIO && !directions[i]);assert(directions[10]);}
int main(void)
{
    maker_bus_request_t r={.kind=MAKER_BUS_UART,.rate=9600,.timeout_ms=50,.tx_size=1,.rx_size=1,.tx={0xa1}};
    uint8_t rx[32],received;uint32_t rate;
    reset();assert(maker_bus_target_execute(&r,guard,rx,&received,&rate)==MAKER_BUS_OK);assert(received==1 && rx[0]==0x5a);cleaned(0,2);
    reset();stuck=true;assert(maker_bus_target_execute(&r,guard,rx,&received,&rate)==MAKER_BUS_TIMEOUT);assert(elapsed<=51000);cleaned(0,2);
    reset();rx_error=true;assert(maker_bus_target_execute(&r,guard,rx,&received,&rate)==MAKER_BUS_IO);cleaned(0,2);
    r.kind=MAKER_BUS_I2C;r.rate=100000;r.address=0x55;
    reset();assert(maker_bus_target_execute(&r,guard,rx,&received,&rate)==MAKER_BUS_OK);assert(rx[0]==0x3c && writes==1 && reads==1 && write_deadline==read_deadline);cleaned(2,2);
    reset();stuck=true;assert(maker_bus_target_execute(&r,guard,rx,&received,&rate)==MAKER_BUS_TIMEOUT);assert(reads==0 && !mock_i2c.active);cleaned(2,2);
    r.kind=MAKER_BUS_SPI;r.rate=1000000;r.address=0;r.tx_size=r.rx_size=3;r.tx[1]=0xb2;r.tx[2]=0xc3;
    reset();assert(maker_bus_target_execute(&r,guard,rx,&received,&rate)==MAKER_BUS_OK);assert(received==3 && !memcmp(rx,r.tx,3));cleaned(16,4);
    reset();stuck=true;assert(maker_bus_target_execute(&r,guard,rx,&received,&rate)==MAKER_BUS_TIMEOUT);assert(elapsed<=51000);cleaned(16,4);
    reset();stuck=true;abort_at=5000;assert(maker_bus_target_execute(&r,guard,rx,&received,&rate)==MAKER_BUS_TIMEOUT);assert(elapsed<=6000);cleaned(16,4);
    puts("maker target buses: PASS (UART/SPI stuck loops, I2C shared deadline, lease loss, pin cleanup)");
}
