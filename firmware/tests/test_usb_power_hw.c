#include "usb_power_hw.h"
#include "i2c.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static uint8_t io[8], mux;
static uint16_t ina[256];
static bool latch, fail_write, expect_off_before_flags, drop_sys5_during_clear;
static unsigned log_count;
static struct {uint8_t addr, bytes[3], count;} log_items[128];
static void log_write(uint8_t addr,const uint8_t *bytes,unsigned n)
{
    assert(log_count<128 && n<=3);
    log_items[log_count].addr=addr;log_items[log_count].count=(uint8_t)n;
    memcpy(log_items[log_count++].bytes,bytes,n);
}
static void pins(void)
{
    if (!(io[1]&0x40u) || (ina[6]&0x10u)) latch=true;
    io[0]=io[2];
    io[1]=(uint8_t)((io[1]&0xf8u)|(io[3]&1u)|(latch?0:2u)|((ina[6]&0x10u)?0:4u));
}
bool tca9548a_deselect_all(void) {mux=0;return true;}
bool tca9548a_select_channel(uint8_t c) {assert(c==2);mux=4;return true;}
bool i2c1_write(uint8_t address,uint8_t reg,uint8_t value)
{
    assert(address==0x76 && mux==4 && reg<8);
    uint8_t data[]={reg,value};log_write(address,data,2);
    if (fail_write) return false;
    io[reg]=value;
    if (reg==3 && !(value&1u)) {
        if (drop_sys5_during_clear) io[1]&=(uint8_t)~0x40u;
        if (!(ina[6]&0x10u) && (io[1]&0x40u)) latch=false;
    }
    pins();return true;
}
bool i2c1_write_raw(uint8_t address,uint8_t *data,uint16_t size)
{
    assert(address==0x40 && mux==4 && size==3);
    log_write(address,data,3);
    if (fail_write) return false;
    ina[data[0]]=(uint16_t)(((uint16_t)data[1]<<8)|data[2]);return true;
}
bool i2c1_read(uint8_t address,uint8_t reg,uint8_t *data,uint16_t size)
{
    if (address==0x76) {assert(mux==4 && size==1 && reg<8);pins();data[0]=io[reg];return true;}
    assert(address==0x40 && mux==4 && size==2);
    if (reg==6 && expect_off_before_flags) assert(io[2]==0);
    data[0]=(uint8_t)(ina[reg]>>8);data[1]=(uint8_t)ina[reg];
    if (reg==6) ina[reg]&=(uint16_t)~0x18u; /* flags clear on read, external latch stays */
    return true;
}
static void fixture(void)
{
    memset(io,0,sizeof(io));memset(ina,0,sizeof(ina));
    io[1]=0x40;drop_sys5_during_clear=false;
    ina[0xfe]=0x5449;ina[0xff]=0x2260;ina[2]=4000;
    latch=false;fail_write=false;expect_off_before_flags=false;log_count=0;
}
static void fresh(uint16_t raw) {ina[1]=raw;ina[6]|=8;}
int main(void)
{
    usb_power_sample_t sample;
    fixture();assert(usb_power_hw_init(0));
    assert(usb_power_alert_threshold_raw()==12122u);
    /* Independent physical corners in volts/ohms, including one full code.
     * These literals reject stale shunt bounds and a missing quantization guard. */
    double earliest=(12122.0*0.0000025-0.000025)/(0.00530583*1.006);
    double latest=(12123.0*0.0000025+0.000025)/(0.00469483*0.994);
    assert(earliest>5.6 && latest<6.5);
    assert(usb_power_current_upper_ma(10000)==5363u);
    /* Literal on-wire calibration, threshold and direction expectations. */
    assert(log_items[0].addr==0x76 && log_items[0].bytes[0]==2 && log_items[0].bytes[1]==0);
    assert(log_items[1].addr==0x76 && log_items[1].bytes[0]==3 && log_items[1].bytes[1]==1);
    assert(log_items[2].bytes[0]==6 && log_items[2].bytes[1]==0);
    assert(log_items[3].bytes[0]==7 && log_items[3].bytes[1]==0xfe);
    assert(log_items[4].addr==0x40 && log_items[4].bytes[0]==0 && log_items[4].bytes[1]==0x46 && log_items[4].bytes[2]==7);
    assert(log_items[5].bytes[0]==5 && log_items[5].bytes[1]==8 && log_items[5].bytes[2]==0);
    assert(log_items[6].bytes[0]==7 && log_items[6].bytes[1]==0x2f && log_items[6].bytes[2]==0x5a);
    assert(log_items[7].bytes[0]==6 && log_items[7].bytes[1]==0x80 && log_items[7].bytes[2]==1);
    assert(!usb_power_hw_write(2)); /* no global permit */
    assert(usb_power_hw_write(3));
    fresh(10000);assert(usb_power_hw_sample(20,&sample)==USB_POWER_HW_OK);
    assert(sample.valid && sample.voltage_mv==5000 && sample.nominal_current_ma==5000);
    assert(sample.upper_current_ma>5000 && sample.upper_current_ma<5400);
    assert(sample.sample_ms==0 && sample.conversion_sequence==1);
    assert(usb_power_hw_sample(40,&sample)==USB_POWER_HW_NOT_READY && !sample.valid);
    ina[5]=0;fresh(0);assert(usb_power_hw_sample(60,&sample)==USB_POWER_HW_CONFIG);
    fixture();assert(usb_power_hw_init(100));assert(usb_power_hw_write(3));
    latch=true;ina[6]|=0x18;ina[1]=13000;expect_off_before_flags=true;
    assert(usb_power_hw_sample(120,&sample)==USB_POWER_HW_OVERCURRENT);
    assert(usb_power_hw_applied()==0 && latch); /* reading INA did not clear external latch */
    assert(!usb_power_hw_clear_fault(120)); /* current still high */
    fresh(0);assert(usb_power_hw_sample(140,&sample)==USB_POWER_HW_OVERCURRENT);
    assert(sample.valid && sample.upper_current_ma<10);
    assert(usb_power_hw_clear_fault(140) && !latch && io[3]==1);
    assert(!usb_power_hw_clear_fault(300)); /* stale quiet sample */
    fresh((uint16_t)-200);assert(usb_power_hw_sample(160,&sample)==USB_POWER_HW_RANGE);
    fixture();ina[0xfe]=0xffff;assert(!usb_power_hw_init(0));
    fixture();assert(usb_power_hw_init(0));fail_write=true;assert(!usb_power_hw_write(1));
    assert(!usb_power_hw_write(0)); /* caller must use NRST after an unverifiable safe write */
    /* SYS5 is off at cold start: its hardware preset cannot be cleared. */
    fixture();io[1]=0;assert(usb_power_hw_init(0));fresh(0);
    assert(usb_power_hw_sample(20,&sample)==USB_POWER_HW_OVERCURRENT && latch);
    assert(!usb_power_hw_clear_fault(20) && io[2]==0);
    io[1]|=0x40;fresh(0);assert(usb_power_hw_sample(40,&sample)==USB_POWER_HW_OVERCURRENT);
    assert(latch); /* Recovery alone cannot clear the independent latch. */
    assert(usb_power_hw_clear_fault(40) && !latch);
    latch=true;fresh(0);assert(usb_power_hw_sample(60,&sample)==USB_POWER_HW_OVERCURRENT);
    drop_sys5_during_clear=true;
    assert(!usb_power_hw_clear_fault(60) && latch && io[2]==0);
    assert(!usb_power_hw_write(1)); /* failed clear verification requires reset */
    puts("USB power hardware: PASS (literal wire words, reset-safe directions, real conversion flags, retained fault latch, failed writes)");
}
