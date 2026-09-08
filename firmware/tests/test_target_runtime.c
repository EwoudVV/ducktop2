#include "host_link.h"
#include "ducktop2/ec/ec_fan_monitor.h"
#include "ducktop2/ec/ec_policy.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static void u32(uint8_t *p,uint32_t v) { for(unsigned i=0;i<4;i++) p[i]=(uint8_t)(v>>(i*8)); }
static uint32_t get32(const uint8_t *p) { return p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24); }
int main(void)
{
    ec_host_init(); assert(!ec_host_state(0).valid);
    assert(ec_host_request_budget(30000));
    ec_telemetry_snapshot_t telemetry={0}; ec_battery_report_t battery={0};
    ec_host_publish(&telemetry,&battery,0,0,0,0);
    uint8_t p[64]={0}; memcpy(p,"DT2\1",4); u32(p+4,get32(ec_host_report()+4));
    u32(p+8,30000); u32(p+12,25000); u32(p+16,5000); u32(p+24,1000);
    ec_host_receive(p,63,0); assert(!ec_host_state(0).valid);
    ec_host_receive(p,64,0); assert(ec_host_state(999).valid);
    assert(!ec_host_state(1000).valid);
    u32(p+8,30001); ec_host_receive(p,64,1100); assert(!ec_host_state(1100).valid);
    u32(p+8,30000); ec_host_receive(p,64,1100); assert(ec_host_state(1100).valid);
    assert(ec_host_request_budget(29000)); assert(!ec_host_state(1100).valid);
    ec_host_receive(p,64,1100); assert(!ec_host_state(1100).valid);
    ec_host_publish(&telemetry,&battery,0,0,0,1100);
    u32(p+4,get32(ec_host_report()+4));u32(p+8,28000);u32(p+12,27000);
    u32(p+20,128);p[28]=0x45;
    ec_host_receive(p,64,1100);assert(ec_host_state(1100).usb_requested_mask==0x45);
    assert(ec_host_take_usb_clear(1100));assert(!ec_host_take_usb_clear(1100));
    ec_host_receive(p,64,1101);assert(!ec_host_take_usb_clear(1101));
    uint32_t old_generation=get32(p+4);
    assert(ec_host_request_budget(31000) && ec_host_state(1101).valid);
    ec_host_publish(&telemetry,&battery,0,0,0,1101);
    assert(get32(ec_host_report()+4)!=old_generation && get32(ec_host_report()+40)==old_generation);
    /* Old-generation replies cannot extend the retained lease. */
    ec_host_receive(p,64,1900);assert(!ec_host_state(2101).valid);
    u32(p+4,get32(ec_host_report()+4));p[28]=128;ec_host_receive(p,64,2200);assert(!ec_host_state(2200).valid);
    p[28]=127;p[29]=1;ec_host_receive(p,64,2200);assert(!ec_host_state(2200).valid);
    p[29]=0;ec_host_receive(p,64,2200);assert(ec_host_state(2200).valid);
    ec_host_usb_status_t usb={0x21,0x40,3,0xb7,5200,5160,32000};ec_host_publish_usb(&usb);
    ec_host_publish(&telemetry,&battery,0,0,0,2200);
    assert(ec_host_report()[52]==0x21 && ec_host_report()[55]==0xb7 && get32(ec_host_report()+60)==32000);
    ec_fan_monitor_t fan; ec_fan_monitor_init(&fan);
    assert(ec_fan_monitor_step(&fan,false,100,0,0));
    assert(ec_fan_monitor_step(&fan,true,100,0,1));
    assert(ec_fan_monitor_step(&fan,true,100,0,2000));
    assert(!ec_fan_monitor_step(&fan,true,100,0,2001));
    assert(!ec_fan_monitor_step(&fan,true,100,6000,2500));
    ec_fan_monitor_init(&fan);
    assert(ec_fan_monitor_step(&fan,true,30,6000,0));
    assert(ec_fan_monitor_step(&fan,true,30,6000,1900));
    assert(ec_fan_monitor_step(&fan,true,30,0,2800));
    assert(!ec_fan_monitor_step(&fan,true,30,0,2900));
    puts("target runtime: PASS (host lease/generation/range, fan start/stall/latch)");
}
