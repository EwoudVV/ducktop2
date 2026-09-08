#include "usb_power_hw.h"
#include "i2c.h"
#include <stddef.h>
#include <string.h>

static bool initialized;
static uint8_t output0;
static uint32_t flag_cleared_ms, conversion_sequence;
static usb_power_sample_t last_sample;

static bool io_read(uint8_t reg, uint8_t *value)
{
    return tca9548a_select_channel(USB_POWER_MONITOR_CHANNEL) &&
           i2c1_read(USB_POWER_IO_ADDRESS, reg, value, 1);
}
static bool io_write(uint8_t reg, uint8_t value)
{
    return tca9548a_select_channel(USB_POWER_MONITOR_CHANNEL) &&
           i2c1_write(USB_POWER_IO_ADDRESS, reg, value);
}
static bool word_read(uint8_t reg, uint16_t *value)
{
    uint8_t data[2];
    if (!i2c1_read(USB_POWER_MONITOR_ADDRESS,reg,data,2)) return false;
    *value=(uint16_t)(((uint16_t)data[0]<<8)|data[1]);
    return true;
}
static bool word_write(uint8_t reg, uint16_t value)
{
    uint8_t frame[3]={reg,(uint8_t)(value>>8),(uint8_t)value};
    return i2c1_write_raw(USB_POWER_MONITOR_ADDRESS,frame,3);
}
static bool word_set(uint8_t reg, uint16_t value)
{
    uint16_t observed;
    return word_write(reg,value) && word_read(reg,&observed) && observed==value;
}
static bool io_verify(void)
{
    uint8_t o0,o1,c0,c1,p0,p1;
    return io_read(2,&o0) && io_read(3,&o1) && io_read(6,&c0) &&
           io_read(7,&c1) && io_read(0,&p0) && io_read(1,&p1) && (p1&1u) && o0==output0 && o1==1u &&
           c0==0u && c1==0xfeu && p0==output0;
}

uint16_t usb_power_alert_threshold_raw(void)
{
    uint64_t nano_volts=(uint64_t)USB_POWER_TRIP_CURRENT_MA * USB_POWER_SHUNT_MIN_NOHM *
                       (1000000u-USB_POWER_ADC_GAIN_PPM)/1000000000u;
    return (uint16_t)((nano_volts-USB_POWER_ADC_OFFSET_NV)/2500u);
}
uint16_t usb_power_current_upper_ma(int16_t raw)
{
    int64_t measured_nv=(int64_t)raw*2500+USB_POWER_ADC_OFFSET_NV;
    if (measured_nv<=0) return 0u;
    uint64_t numerator=(uint64_t)measured_nv*1000000000u;
    uint64_t denominator=(uint64_t)USB_POWER_SHUNT_MIN_NOHM*(1000000u-USB_POWER_ADC_GAIN_PPM);
    uint64_t result=(numerator+denominator-1u)/denominator;
    return (uint16_t)(result>65535u ? 65535u : result);
}

bool usb_power_hw_write(uint8_t value)
{
    uint8_t actual, pins;
    /* Bit 0 is the global permit. A port permit without it is forbidden. */
    if (!initialized || ((value&0xfeu) && !(value&1u)) || !tca9548a_deselect_all()) return false;
    if (!io_write(2,value) || !io_read(2,&actual) || actual!=value ||
        !io_read(0,&pins) || pins!=value) {
        initialized=false;
        return false; /* Caller must reset NRST; U2400 then releases all permits. */
    }
    if (output0!=value) last_sample.valid=false;
    output0=value;
    bool verified=io_verify() && tca9548a_deselect_all();
    if (!verified) initialized=false;
    return verified;
}

bool usb_power_hw_init(uint32_t now_ms)
{
    uint8_t v;
    uint16_t id, cfg, mask;
    initialized=false;output0=0;flag_cleared_ms=now_ms;conversion_sequence=0;
    memset(&last_sample,0,sizeof(last_sample));
    if (!tca9548a_deselect_all() || !io_write(2,0) || !io_write(3,1) ||
        !io_read(2,&v) || v!=0 || !io_read(3,&v) || v!=1 ||
        !io_write(6,0) || !io_write(7,0xfe) || !io_verify()) return false;
    /* Fault clear remains high; init never erases the independent latch. */
    if (!tca9548a_select_channel(USB_POWER_MONITOR_CHANNEL)) return false;
    bool ok=word_read(0xfe,&id) && id==0x5449u &&
            word_read(0xff,&id) && (id&0xfff0u)==0x2260u &&
            word_set(0,USB_POWER_INA_CONFIG) &&
            word_set(5,USB_POWER_INA_CALIBRATION) &&
            word_set(7,usb_power_alert_threshold_raw()) &&
            word_write(6,0x8001u) && word_read(6,&mask) &&
            (mask&~0x001cu)==0x8001u && word_read(0,&cfg) && cfg==USB_POWER_INA_CONFIG;
    if (!tca9548a_deselect_all()) ok=false;
    initialized=ok;
    return ok;
}

bool usb_power_hw_clear_fault(uint32_t now_ms)
{
    uint8_t value, pins;
    if (!initialized || output0!=0u || !last_sample.valid ||
        now_ms-last_sample.sample_ms>100u || last_sample.upper_current_ma>100u ||
        last_sample.nominal_current_ma < -5 || !tca9548a_deselect_all() || !io_verify() ||
        !io_read(1,&pins) || !(pins&USB_POWER_IN_ALERT_N)) return false;
    /* Clear only after the caller has verified fresh near-zero current.
     * Each I2C transfer exceeds the latch's minimum asynchronous pulse. */
    if (!io_write(3,0) || !io_read(3,&value) || value!=0 ||
        !io_write(3,1) || !io_read(3,&value) || value!=1 || !io_read(1,&pins) ||
        (pins&(USB_POWER_IN_FAULT_N|USB_POWER_IN_ALERT_N))!=
               (USB_POWER_IN_FAULT_N|USB_POWER_IN_ALERT_N)) {
        initialized=false;
        return false;
    }
    bool verified=io_verify() && tca9548a_deselect_all();
    if (!verified) initialized=false;
    return verified;
}

usb_power_hw_result_t usb_power_hw_sample(uint32_t now_ms, usb_power_sample_t *sample)
{
    uint16_t cfg, calibration, limit, flags, shunt, bus, after;
    if (!sample) return USB_POWER_HW_RANGE;
    memset(sample,0,sizeof(*sample));
    if (!initialized || !tca9548a_deselect_all() || !io_verify() ||
        !io_read(0,&sample->input0) || !io_read(1,&sample->input1)) return USB_POWER_HW_BUS;
    bool fault=(sample->input1&(USB_POWER_IN_FAULT_N|USB_POWER_IN_ALERT_N))!=
               (USB_POWER_IN_FAULT_N|USB_POWER_IN_ALERT_N);
    /* Do not clear an INA latch while old permits remain high. The external
     * flip-flop independently keeps the converter off during this ordering. */
    if (fault && output0 && !usb_power_hw_write(0)) return USB_POWER_HW_BUS;
    if (!tca9548a_select_channel(USB_POWER_MONITOR_CHANNEL)) return USB_POWER_HW_BUS;
    usb_power_hw_result_t result=USB_POWER_HW_OK;
    uint32_t lower_sample_time=flag_cleared_ms;
    if (!word_read(0,&cfg) || !word_read(5,&calibration) || !word_read(7,&limit) ||
        !word_read(6,&flags)) result=USB_POWER_HW_BUS;
    else if (cfg!=USB_POWER_INA_CONFIG || calibration!=USB_POWER_INA_CALIBRATION ||
             limit!=usb_power_alert_threshold_raw() || (flags&~0x001cu)!=0x8001u)
        result=USB_POWER_HW_CONFIG;
    else {
        flag_cleared_ms=now_ms;
        fault=fault || (flags&0x10u);
        if (flags&4u) result=USB_POWER_HW_RANGE;
        else if (!(flags&8u)) result=USB_POWER_HW_NOT_READY;
        else if (!word_read(1,&shunt) || !word_read(2,&bus) || !word_read(6,&after))
            result=USB_POWER_HW_BUS;
        else {
            fault=fault || (after&0x10u);
            /* A conversion during the read makes the pair non-atomic. Retry
             * on the next bounded poll; never manufacture a fresh timestamp. */
            if (after&8u) result=USB_POWER_HW_NOT_READY;
            else if ((after&~0x001cu)!=0x8001u || (after&4u) || bus>0x7fffu)
                result=USB_POWER_HW_RANGE;
            else {
                int16_t raw=(int16_t)shunt;
                sample->nominal_current_ma=(int16_t)(raw/2);
                sample->upper_current_ma=usb_power_current_upper_ma(raw);
                sample->voltage_mv=(uint16_t)(((uint32_t)bus*5u)/4u);
                sample->sample_ms=lower_sample_time;
                if (raw < -100 || sample->voltage_mv>5500u) result=USB_POWER_HW_RANGE;
                else {sample->valid=true;sample->conversion_sequence=++conversion_sequence;}
            }
        }
    }
    if (!tca9548a_deselect_all()) { result=USB_POWER_HW_BUS;sample->valid=false; }
    if (sample->valid) last_sample=*sample;
    if (fault) {
        if (output0 && !usb_power_hw_write(0)) return USB_POWER_HW_BUS;
        return USB_POWER_HW_OVERCURRENT;
    }
    if (result!=USB_POWER_HW_OK && result!=USB_POWER_HW_NOT_READY) {
        last_sample.valid=false;
        if (output0 && !usb_power_hw_write(0)) return USB_POWER_HW_BUS;
        initialized=false;
    }
    return result;
}
uint8_t usb_power_hw_applied(void) { return output0; }
