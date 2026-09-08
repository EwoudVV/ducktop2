#include "ducktop2/maker/maker_bus.h"
#include <string.h>
static uint32_t u32(const uint8_t *p){return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
static void put32(uint8_t *p,uint32_t value){for(unsigned i=0;i<4;i++)p[i]=(uint8_t)(value>>(i*8));}
maker_bus_result_t maker_bus_parse(const uint8_t *p,uint16_t size,uint32_t last,
    bool authorized,uint32_t lease_left,const maker_outputs_t *pins,maker_bus_request_t *r)
{
    if(!r)return MAKER_BUS_BAD_REQUEST;
    memset(r,0,sizeof(*r));
    if(!p || size!=64 || !pins || memcmp(p,"MB2\1",4))return MAKER_BUS_BAD_REQUEST;
    r->sequence=u32(p+4);r->kind=p[8];r->flags=p[9];r->tx_size=p[10];r->rx_size=p[11];
    r->rate=u32(p+12);r->timeout_ms=(uint16_t)(p[16]|((uint16_t)p[17]<<8));r->address=p[18];
    if(!r->sequence || (int32_t)(r->sequence-last)<=0)return MAKER_BUS_REPLAY;
    if(!r->timeout_ms || r->timeout_ms>100 || r->tx_size>32 || r->rx_size>32 ||
       (!r->tx_size && !r->rx_size))return MAKER_BUS_BAD_REQUEST;
    for(unsigned i=19;i<32;i++)if(p[i])return MAKER_BUS_BAD_REQUEST;
    for(unsigned i=32+r->tx_size;i<64;i++)if(p[i])return MAKER_BUS_BAD_REQUEST;
    unsigned first,count;
    switch(r->kind){
    case MAKER_BUS_UART:
        first=0;count=2;
        if(r->flags || r->address || r->rate<300 || r->rate>115200)return MAKER_BUS_BAD_REQUEST;
        break;
    case MAKER_BUS_I2C:
        first=2;count=2;
        if(r->flags || r->address<8 || r->address>0x77 || r->rate<10000 || r->rate>100000)
            return MAKER_BUS_BAD_REQUEST;
        break;
    case MAKER_BUS_SPI:
        first=16;count=4;
        if(r->flags>3 || r->address || r->rate<10000 || r->rate>1000000 ||
           (r->tx_size && r->rx_size && r->tx_size!=r->rx_size))return MAKER_BUS_BAD_REQUEST;
        break;
    default:return MAKER_BUS_BAD_REQUEST;
    }
    if(!authorized || lease_left<r->timeout_ms+10u)return MAKER_BUS_NO_LEASE;
    for(unsigned i=first;i<first+count;i++)if(pins->io_mode[i]!=MAKER_IO_HIGH_IMPEDANCE)
        return MAKER_BUS_PIN_CONFLICT;
    memcpy(r->tx,p+32,r->tx_size);
    return MAKER_BUS_OK;
}
void maker_bus_response(uint8_t p[64],const maker_bus_request_t *r,maker_bus_result_t result,
    const uint8_t *rx,uint8_t size,uint32_t actual_rate,uint16_t elapsed_ms)
{
    memset(p,0,64);memcpy(p,"MR2\1",4);
    if(r){put32(p+4,r->sequence);p[9]=r->kind;}
    p[8]=(uint8_t)result;
    if(size>32 || !rx)size=0;
    p[10]=size;put32(p+12,actual_rate);p[16]=(uint8_t)elapsed_ms;p[17]=(uint8_t)(elapsed_ms>>8);
    if(size)memcpy(p+32,rx,size);
}
