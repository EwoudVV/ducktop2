#include "pico/stdlib.h"
#include "hardware/adc.h"
#include "hardware/watchdog.h"
#include "tusb.h"
#include "bus_target.h"
#include "ducktop2/maker/maker_policy.h"
#include <string.h>

static const uint8_t pins[MAKER_USER_IO_COUNT]={0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,26,27,28};
static maker_controller_t controller;
static uint32_t request_at, generation;
static bool authorized, rails_requested;
static uint8_t status[64];
static maker_io_mode_t applied_modes[MAKER_USER_IO_COUNT];
static uint8_t pending_bus[64],bus_response[64];
static bool bus_pending,bus_response_dirty,header_guard_ready;
static uint32_t bus_sequence;
static volatile bool hardware_fault;
static bool bus_guard(void)
{
    return authorized && to_ms_since_boot(get_absolute_time())-request_at<1000u &&
           header_guard_ready && !hardware_fault && gpio_get(25) && !gpio_get(24) && tud_mounted();
}

static void high_z(unsigned pin)
{
    gpio_init(pin); gpio_set_dir(pin,GPIO_IN); gpio_disable_pulls(pin);
}
static void passive(void)
{
    gpio_put(29,0);
    for(unsigned i=0;i<MAKER_USER_IO_COUNT;i++) {high_z(pins[i]);applied_modes[i]=MAKER_IO_HIGH_IMPEDANCE;}
}
static void power_fault_irq(uint gpio,uint32_t events)
{
    (void)gpio;(void)events;hardware_fault=true;
    passive();
}
static void bus_fail(void)
{
    authorized=false;rails_requested=false;bus_pending=false;
    passive();maker_bus_target_abort();maker_controller_transaction_trip(&controller);
}
static void apply(const maker_outputs_t *out)
{
    if(hardware_fault){passive();return;}
    /* Stop rails before changing IO into its passive state. */
    if(!out->user_rails_enable) gpio_put(29,0);
    for(unsigned i=0;i<MAKER_USER_IO_COUNT;i++) {
        unsigned pin=pins[i]; maker_io_mode_t mode=out->io_mode[i];
        if(applied_modes[i]==mode) continue;
        applied_modes[i]=mode;
        if(mode==MAKER_IO_ANALOG_INPUT && pin>=26) adc_gpio_init(pin);
        else {
            gpio_set_dir(pin,GPIO_IN); gpio_set_function(pin,GPIO_FUNC_SIO); gpio_disable_pulls(pin);
            if(mode==MAKER_IO_OUTPUT_LOW || mode==MAKER_IO_OUTPUT_HIGH) {
                gpio_put(pin,mode==MAKER_IO_OUTPUT_HIGH); gpio_set_dir(pin,GPIO_OUT);
            }
        }
    }
    if(out->user_rails_enable) gpio_put(29,1);
    if(hardware_fault)passive();
}
uint16_t tud_hid_get_report_cb(uint8_t instance,uint8_t id,hid_report_type_t type,uint8_t *data,uint16_t length)
{
    (void)instance;(void)type;
    if(id) return 0;
    if(length>64) length=64;
    memcpy(data,bus_response_dirty?bus_response:status,length);return length;
}
void tud_hid_set_report_cb(uint8_t instance,uint8_t id,hid_report_type_t type,const uint8_t *data,uint16_t length)
{
    (void)instance;
    if(id || type!=HID_REPORT_TYPE_FEATURE || length!=64) return;
    if(!memcmp(data,"MB2\1",4)) {
        if(bus_pending){
            maker_bus_request_t request;
            (void)maker_bus_parse(data,length,bus_sequence,false,0,maker_controller_outputs(&controller),&request);
            if(request.sequence && (int32_t)(request.sequence-bus_sequence)>0)bus_sequence=request.sequence;
            maker_bus_response(bus_response,&request,MAKER_BUS_BUSY,NULL,0,0,0);
            bus_response_dirty=true;bus_fail();return;
        }
        memcpy(pending_bus,data,64);bus_pending=true;return;
    }
    if(memcmp(data,"MK2\1",4))return;
    uint32_t next=(uint32_t)data[4]|((uint32_t)data[5]<<8)|((uint32_t)data[6]<<16)|((uint32_t)data[7]<<24);
    if(!next || (int32_t)(next-generation)<=0 || data[8]>1 || data[9]>1) return;
    for(unsigned i=10+MAKER_USER_IO_COUNT;i<64;i++) if(data[i]) return;
    for(unsigned i=0;i<MAKER_USER_IO_COUNT;i++) {
        if(data[10+i]>MAKER_IO_OUTPUT_HIGH || (data[10+i]==MAKER_IO_ANALOG_INPUT && pins[i]<26)) return;
    }
    /* A fresh explicit packet is the only authorization. Alternate functions
     * need a separate peripheral configuration and are not accepted as GPIO. */
    generation=next; request_at=to_ms_since_boot(get_absolute_time());
    authorized=data[9]!=0; rails_requested=data[8]!=0;
    if(!authorized) passive();
    if(!rails_requested && !authorized && gpio_get(25)) {
        hardware_fault=false;
        if(controller.fault!=MAKER_FAULT_NONE)(void)maker_controller_clear_fault(&controller,true);
    }
    maker_controller_request_user_rails(&controller,rails_requested);
    for(unsigned i=0;i<MAKER_USER_IO_COUNT;i++)
        (void)maker_controller_request_io_mode(&controller,i,(maker_io_mode_t)data[10+i]);
}
int main(void)
{
    /* The SDK clock bootstrap precedes main. BOOTSEL/RUN and SWD remain the
     * recovery path if startup cannot reach this watchdog. */
    gpio_init(29);gpio_put(29,0);gpio_set_dir(29,GPIO_OUT);passive();
    gpio_init(24);gpio_set_dir(24,GPIO_IN);gpio_pull_up(24);
    gpio_init(25);gpio_set_dir(25,GPIO_IN);gpio_pull_up(25);
    gpio_set_irq_enabled_with_callback(25,GPIO_IRQ_EDGE_FALL,true,power_fault_irq);
    gpio_init(23);gpio_put(23,1);gpio_set_dir(23,GPIO_OUT);
    adc_init();maker_controller_init(&controller);watchdog_enable(500,true);
    tusb_init();
    uint32_t boot=to_ms_since_boot(get_absolute_time()),last_sent=0;
    for(;;) {
        tud_task();uint32_t now=to_ms_since_boot(get_absolute_time());
        bool live=authorized && now-request_at<1000u && tud_mounted() && !gpio_get(24);
        maker_inputs_t input;maker_inputs_init(&input);
        input.watchdog_healthy=true;input.user_power_fault_n=gpio_get(25) && !hardware_fault;
        /* U922 opens the bus switches after its 200 ms core-rail delay. There
         * is no readable OE pin. This delay is a guard, not OE readback. */
        input.hardware_interlock_ready=now-boot>=250u && !gpio_get(24) && tud_mounted();
        header_guard_ready=input.hardware_interlock_ready;
        input.user_power_authorized=live;input.user_io_authorized=live;
        if(!live) {rails_requested=false;maker_controller_request_user_rails(&controller,false);
            for(unsigned i=0;i<MAKER_USER_IO_COUNT;i++) (void)maker_controller_request_io_mode(&controller,i,MAKER_IO_HIGH_IMPEDANCE);}
        maker_controller_step(&controller,&input);apply(maker_controller_outputs(&controller));
        if(bus_pending) {
            maker_bus_request_t request;uint32_t age=now-request_at;
            maker_bus_result_t result=maker_bus_parse(pending_bus,64,bus_sequence,
                bus_guard() && controller.fault==MAKER_FAULT_NONE,age<1000u?1000u-age:0u,
                maker_controller_outputs(&controller),&request);
            bus_pending=false;uint8_t received=0,rx[32];uint32_t actual_rate=0;
            if(request.sequence && (int32_t)(request.sequence-bus_sequence)>0)bus_sequence=request.sequence;
            if(result==MAKER_BUS_OK) {
                result=maker_bus_target_execute(&request,bus_guard,rx,&received,&actual_rate);
            }
            maker_bus_response(bus_response,&request,result,rx,received,actual_rate,
                (uint16_t)(to_ms_since_boot(get_absolute_time())-now));
            bus_response_dirty=true;
            if(result!=MAKER_BUS_OK)bus_fail();
        }
        memset(status,0,sizeof(status));memcpy(status,"MK2\1",4);
        for(unsigned i=0;i<4;i++) status[4+i]=(uint8_t)(generation>>(8*i));
        status[8]=(uint8_t)controller.fault;status[9]=gpio_get(29);
        status[10]=live && header_guard_ready && controller.fault==MAKER_FAULT_NONE;
        status[47]=header_guard_ready && gpio_get(25);
        for(unsigned i=0;i<MAKER_USER_IO_COUNT;i++) status[11+i]=(uint8_t)gpio_get(pins[i]);
        for(unsigned i=0;i<3;i++) {
            if(applied_modes[23+i]==MAKER_IO_ANALOG_INPUT) {
                adc_select_input(i);uint16_t value=adc_read();
                status[40+i*2]=(uint8_t)value;status[41+i*2]=(uint8_t)(value>>8);
            }
        }
        for(unsigned i=0;i<4;i++)status[48+i]=(uint8_t)(bus_sequence>>(i*8));
        if(bus_response_dirty && tud_hid_ready()) {
            if(tud_hid_report(0,bus_response,64))bus_response_dirty=false;
        }
        if(now-last_sent>=100 && tud_hid_ready()) {tud_hid_report(0,status,64);last_sent=now;}
        watchdog_update();sleep_ms(5);
    }
}
