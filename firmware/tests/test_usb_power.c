#include "usb_power.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static uint8_t outputs, channel;
static uint32_t conversion_sequence;
static bool fail_write, clear_ok, malformed_pd;
static usb_power_sample_t observation;
static usb_power_hw_result_t result;
static tps25751_port_state_t ports[2];
bool usb_power_hw_init(uint32_t now) {(void)now;outputs=0;return true;}
bool usb_power_hw_write(uint8_t value) {if(fail_write)return false;outputs=value;return true;}
bool usb_power_hw_clear_fault(uint32_t now) {(void)now;assert(outputs==0);return clear_ok;}
usb_power_hw_result_t usb_power_hw_sample(uint32_t now,usb_power_sample_t *sample)
{(void)now;*sample=observation;return result;}
bool tca9548a_select_channel(uint8_t c) {assert(c==2 || c==3);channel=c;return true;}
bool tca9548a_deselect_all(void) {channel=0;return true;}
bool tps25751_read_port_state(uint8_t address,tps25751_port_state_t *state)
{assert(address==channel+0x1e);*state=ports[address-0x20];return !malformed_pd;}
static usb_power_config_t config(void)
{
    usb_power_config_t c={.budget={true,5500,2200,5239,85},.startup_ceiling_ma=5700,
        .pd_inrush_ma=1500,.branch_inrush_ma=1600,.rail_min_mv=5000,.rail_max_mv=5250,
        .startup_timeout_ms=500,.gate_timeout_ms=200,.sample_max_age_ms=100};return c;
}
static void fixture(usb_power_state_t *s)
{
    conversion_sequence=0;fail_write=false;clear_ok=false;malformed_pd=false;result=USB_POWER_HW_OK;
    memset(&observation,0,sizeof(observation));memset(ports,0,sizeof(ports));
    for(unsigned n=0;n<2;n++){ports[n].valid=true;ports[n].source_profile_valid=true;ports[n].typec_mode=2;}
    usb_power_config_t c=config();assert(usb_power_init(s,&c,0));
}
static void sample(usb_power_state_t *s,uint32_t now,uint16_t mv,uint16_t ma,bool pg)
{
    observation=(usb_power_sample_t){.valid=true,.sample_ms=now,.conversion_sequence=++conversion_sequence,.voltage_mv=mv,
        .upper_current_ma=ma,.input1=(uint8_t)(6u|(pg?0x38u:0u))};
    assert(usb_power_poll(s,now));
}
static usb_power_request_t request(void)
{
    usb_power_request_t r={.host_lease_valid=true,.system_safe=true,.requested_mask=127,
        .active_source=2,.available_input_power_mw=100000};return r;
}
int main(void)
{
    usb_power_state_t s;fixture(&s);usb_power_request_t r=request();
    sample(&s,0,0,0,false);assert(usb_power_step(&s,&r,0));
    assert(outputs==0 && s.phase==USB_POWER_PENDING && s.plan.allowed_mask==0x67);
    assert(s.plan.reserved_current_ma==5030 && usb_power_reservation_mw(&s)>30000);
    r.committed_reservation_mw=usb_power_reservation_mw(&s);
    assert(usb_power_step(&s,&r,0));assert(outputs==1 && s.phase==USB_POWER_STARTING);
    sample(&s,20,4800,0,false);assert(usb_power_step(&s,&r,20));assert(outputs==1);
    sample(&s,40,5160,25,true);assert(usb_power_step(&s,&r,40));
    assert(s.phase==USB_POWER_READY && s.applied_mask==0x40); /* largest extra inrush first */
    assert(usb_power_step(&s,&r,40));assert(s.applied_mask==0x40); /* same conversion cannot advance */
    uint8_t expected[]={0x60,0x64,0x65,0x67};
    for(unsigned n=0;n<4;n++) {
        sample(&s,60+n*20,5160,25,true);assert(usb_power_step(&s,&r,60+n*20));
        assert(s.applied_mask==expected[n] && outputs==(uint8_t)(1u|(expected[n]<<1)));
    }
    ports[0].connected=true;ports[0].source=false;ports[0].vconn_enabled=true;
    ports[1].connected=true;ports[1].source=true;ports[1].pp5v_enabled=true;
    sample(&s,140,5160,5000,true);assert(usb_power_step(&s,&r,140));
    assert(s.plan.reserved_current_ma==5030); /* sink VCONN did not release Source reserve */
    assert(usb_power_status(&s,140).pd_roles==0x7b);
    r.transfer_active=true;assert(usb_power_step(&s,&r,140));assert(outputs==0);
    r.transfer_active=false;r.active_source=3;assert(usb_power_step(&s,&r,140));assert(outputs==0);
    assert(usb_power_step(&s,&r,140));assert(outputs==1);
    r.host_lease_valid=false;assert(usb_power_step(&s,&r,140));assert(outputs==0);
    fixture(&s);r=request();sample(&s,0,0,0,false);assert(usb_power_step(&s,&r,0));
    r.committed_reservation_mw=s.plan.reserved_input_power_mw;assert(usb_power_step(&s,&r,0));
    sample(&s,501,0,0,false);assert(usb_power_step(&s,&r,501));
    assert(s.phase==USB_POWER_FAULT && s.fault==USB_POWER_GATE_TIMEOUT && outputs==0);
    r.clear_fault=true;clear_ok=true;assert(usb_power_step(&s,&r,501));assert(s.phase!=USB_POWER_FAULT);
    /* A clear request with a stale or non-quiet sample cannot clear the latch. */
    result=USB_POWER_HW_OVERCURRENT;sample(&s,520,5160,6000,true);
    assert(s.phase==USB_POWER_FAULT);assert(usb_power_step(&s,&r,520));assert(s.phase==USB_POWER_FAULT);
    result=USB_POWER_HW_OK;sample(&s,540,0,0,false);r.clear_fault=false;
    assert(usb_power_step(&s,&r,540));assert(s.phase==USB_POWER_FAULT);
    r.clear_fault=true;assert(usb_power_step(&s,&r,641));assert(s.phase==USB_POWER_FAULT);
    sample(&s,660,0,0,false);assert(usb_power_step(&s,&r,660));assert(s.phase!=USB_POWER_FAULT);
    fail_write=true;r.host_lease_valid=false;assert(!usb_power_step(&s,&r,660)); /* main resets */
    fixture(&s);r=request();malformed_pd=true;sample(&s,0,0,0,false);
    assert(usb_power_step(&s,&r,0));assert((s.plan.allowed_mask&3)==0 && (s.plan.denied_mask&3)==3);
    usb_power_config_t bad=config();bad.budget.admission_current_ma=5800;
    assert(!usb_power_init(&s,&bad,0));bad=config();bad.pd_inrush_ma=0;assert(!usb_power_init(&s,&bad,0));
    puts("USB power target: PASS (reserve-before-enable, measured startup, staggered gates, sink/VCONN costs, source/lease loss, fault clear and reset)");
}
