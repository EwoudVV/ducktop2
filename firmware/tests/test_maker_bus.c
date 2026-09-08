#include "ducktop2/maker/maker_bus.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static void put32(uint8_t *p,uint32_t n){for(unsigned i=0;i<4;i++)p[i]=(uint8_t)(n>>(8*i));}
int main(void)
{
    uint8_t packet[64]={0},reply[64];memcpy(packet,"MB2\1",4);put32(packet+4,7);
    packet[8]=1;packet[10]=2;packet[11]=1;put32(packet+12,9600);packet[16]=50;
    packet[32]=0x41;packet[33]=0x42;
    maker_outputs_t pins={0};maker_bus_request_t request;
    assert(maker_bus_parse(packet,64,6,true,1000,&pins,&request)==MAKER_BUS_OK);
    assert(request.sequence==7 && request.rate==9600 && request.tx[0]==0x41 && request.rx_size==1);
    assert(maker_bus_parse(packet,63,6,true,1000,&pins,&request)==MAKER_BUS_BAD_REQUEST);
    assert(maker_bus_parse(packet,64,7,true,1000,&pins,&request)==MAKER_BUS_REPLAY);
    assert(maker_bus_parse(packet,64,6,false,1000,&pins,&request)==MAKER_BUS_NO_LEASE);
    assert(maker_bus_parse(packet,64,6,true,59,&pins,&request)==MAKER_BUS_NO_LEASE);
    pins.io_mode[0]=MAKER_IO_OUTPUT_HIGH;
    assert(maker_bus_parse(packet,64,6,true,1000,&pins,&request)==MAKER_BUS_PIN_CONFLICT);
    pins.io_mode[0]=MAKER_IO_HIGH_IMPEDANCE;
    packet[8]=2;put32(packet+12,100000);packet[18]=0x55;
    assert(maker_bus_parse(packet,64,6,true,1000,&pins,&request)==MAKER_BUS_OK);
    packet[18]=0x78;assert(maker_bus_parse(packet,64,6,true,1000,&pins,&request)==MAKER_BUS_BAD_REQUEST);
    packet[18]=0x55;pins.io_mode[3]=MAKER_IO_INPUT;
    assert(maker_bus_parse(packet,64,6,true,1000,&pins,&request)==MAKER_BUS_PIN_CONFLICT);
    pins.io_mode[3]=0;packet[8]=3;packet[18]=0;packet[9]=3;packet[11]=2;put32(packet+12,1000000);
    assert(maker_bus_parse(packet,64,6,true,1000,&pins,&request)==MAKER_BUS_OK);
    pins.io_mode[17]=MAKER_IO_OUTPUT_LOW;
    assert(maker_bus_parse(packet,64,6,true,1000,&pins,&request)==MAKER_BUS_PIN_CONFLICT);
    pins.io_mode[17]=0;packet[63]=1;
    assert(maker_bus_parse(packet,64,6,true,1000,&pins,&request)==MAKER_BUS_BAD_REQUEST);
    packet[63]=0;packet[16]=101;
    assert(maker_bus_parse(packet,64,6,true,1000,&pins,&request)==MAKER_BUS_BAD_REQUEST);
    packet[16]=50;assert(maker_bus_parse(packet,64,6,true,1000,&pins,&request)==MAKER_BUS_OK);
    const uint8_t rx[]={0x12,0x34};maker_bus_response(reply,&request,MAKER_BUS_TIMEOUT,rx,2,999000,50);
    assert(!memcmp(reply,"MR2\1",4) && reply[4]==7 && reply[8]==4 && reply[10]==2);
    assert(reply[32]==0x12 && reply[33]==0x34 && reply[34]==0);
    puts("maker bus: PASS (literal protocol, lease/deadline limits, all pin groups, malformed requests)");
}
