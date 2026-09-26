#include "isl9241.h"
#include "i2c.h"
#include <stddef.h>

enum {
    CHARGE_CURRENT=0x14, MAX_SYSTEM=0x15, CONTROL7=0x38, CONTROL0=0x39,
    INFO1=0x3a, INPUT_LIMIT2=0x3b, CONTROL1=0x3c, CONTROL2=0x3d,
    MIN_SYSTEM=0x3e, INPUT_LIMIT1=0x3f, ACOK_REFERENCE=0x40,
    INTERRUPT_EDGE=0x43, AC_THROTTLE=0x47, DC_THROTTLE=0x48,
    INPUT_VOLTAGE=0x4b, CONTROL3=0x4c, INFO2=0x4d, CONTROL4=0x4e,
    INTERRUPT_MASK=0x4f, ADC_BAT=0x81, ADC_INPUT_CURRENT=0x83,
    ADC_DISCHARGE=0x84, ADC_CHARGE=0x85, ADC_SYS=0x86, ADC_INPUT=0x87,
    INTERRUPT_STATUS=0x90, LIVE_STATUS=0x91, MANUFACTURER=0xfe, DEVICE=0xff
};
enum { CLEAR_THROTTLE=2u, ADAPTER_ALARM=32u, FATAL_STATUS=0x1644u };
/* 3S strap, 724 kHz, PSYS/ADC active on battery, 64 mA precharge,
 * JEITA profile 2, 7 us current alarm, 4.95 s watchdog, no OTG or bypass.
 * ACOK falling reloads the hardware-strapped 200 mA input limit. Every
 * source enable also checks that limit, including warm source changes. */
static const struct { uint8_t reg; uint16_t value; } fixed_config[]={
    {CONTROL0,0x0000},{CONTROL1,0x028b},{CONTROL2,0x2028},
    {CONTROL3,0x1801},{CONTROL7,0x0000},
    {DC_THROTTLE,ISL9241_DC_THROTTLE_MA},{INPUT_VOLTAGE,0x0b40},
    {INTERRUPT_MASK,FATAL_STATUS},{INTERRUPT_EDGE,0x1fff}
};
static uint16_t voltage_mv=ISL9241_CHARGE_VOLTAGE_MAX_MV, current_ma;
static uint16_t control4=0x4041, acok_reference;
static bool initialized, armed;

static bool read_word(uint8_t reg,uint16_t *out)
{
    uint8_t bytes[2];
    if(!out || !i2c1_read(ISL9241_I2C_ADDRESS,reg,bytes,2)) return false;
    *out=(uint16_t)bytes[0] | ((uint16_t)bytes[1]<<8);
    return true;
}
static bool write_word(uint8_t reg,uint16_t value,uint16_t mask)
{
    uint8_t bytes[3]={reg,(uint8_t)value,(uint8_t)(value>>8)};
    uint16_t actual;
    return i2c1_write_raw(ISL9241_I2C_ADDRESS,bytes,3) && read_word(reg,&actual) &&
           (actual & mask)==(value & mask);
}
bool isl9241_probe(void)
{
    uint16_t manufacturer,device,info;
    return read_word(MANUFACTURER,&manufacturer) && manufacturer==0x0049 &&
           read_word(DEVICE,&device) && device==0x000e &&
           read_word(INFO2,&info) && (info & 31u)==12u;
}
bool isl9241_set_charge_enable(bool enable)
{
    if(enable && (!initialized || current_ma<ISL9241_CHARGE_CURRENT_MIN_MA ||
                  !isl9241_configuration_ok())) return false;
    /* The caller holds the external NTC inhibit throughout these writes.
     * Both registers must be zero for a complete software charge inhibit. */
    bool cc=write_word(CHARGE_CURRENT,enable ? current_ma : 0u,0x1ffc);
    bool minimum=write_word(MIN_SYSTEM,enable ? ISL9241_MIN_SYSTEM_MV : 0u,0x3fc0);
    armed=enable && cc && minimum;
    return cc && minimum;
}
bool isl9241_set_input_current_ma(uint16_t ma)
{
    if(ma<ISL9241_BOOT_INPUT_MA || ma>ISL9241_INPUT_CURRENT_MAX_MA || ma%4u) return false;
    /* Keep both limit registers bounded even though the two-level mode is off. */
    uint16_t alert=(uint16_t)(((uint32_t)ma+128u)/128u*128u);
    return write_word(INPUT_LIMIT1,ma,0x1ffc) &&
           write_word(INPUT_LIMIT2,ma,0x1ffc) &&
           write_word(AC_THROTTLE,alert,0x1f80);
}
bool isl9241_read_input_current_limit_ma(uint16_t *ma)
{
    uint16_t first,second;
    if(!ma || !read_word(INPUT_LIMIT1,&first) || !read_word(INPUT_LIMIT2,&second)) return false;
    if((first & 0x1ffcu)!=(second & 0x1ffcu)) {
        /* ACOK reload changes ACLIM1 only. With two-level mode verified off,
         * synchronize the inactive limit down to the safe strap value. */
        if((first & 0x1ffcu)!=ISL9241_BOOT_INPUT_MA || !isl9241_configuration_ok() ||
           !isl9241_set_input_current_ma(ISL9241_BOOT_INPUT_MA)) return false;
    }
    *ma=first & 0x1ffcu;
    return true;
}
bool isl9241_init(void)
{
    initialized=armed=false;
    current_ma=0;voltage_mv=ISL9241_CHARGE_VOLTAGE_MAX_MV;
    control4=0x4041;acok_reference=0;
    if(!isl9241_probe() || !isl9241_set_charge_enable(false) ||
       !isl9241_set_input_current_ma(ISL9241_BOOT_INPUT_MA) ||
       !write_word(MAX_SYSTEM,voltage_mv,0x7ff8)) return false;
    for(size_t i=0;i<sizeof(fixed_config)/sizeof(fixed_config[0]);i++)
        if(!write_word(fixed_config[i].reg,fixed_config[i].value,0xffff)) return false;
    if(!write_word(ACOK_REFERENCE,acok_reference,0x3fc0) ||
       !write_word(CONTROL4,control4,0xfffd)) return false;
    initialized=true;
    return isl9241_configuration_ok();
}
bool isl9241_configuration_ok(void)
{
    uint16_t actual;
    if(!initialized) return false;
    for(size_t i=0;i<sizeof(fixed_config)/sizeof(fixed_config[0]);i++)
        if(!read_word(fixed_config[i].reg,&actual) || actual!=fixed_config[i].value) return false;
    if(!read_word(CONTROL4,&actual) || (actual & 0xfffdu)!=control4 ||
       !read_word(ACOK_REFERENCE,&actual) || (actual & 0x3fc0u)!=acok_reference ||
       !read_word(MAX_SYSTEM,&actual) || (actual & 0x7ff8u)!=voltage_mv) return false;
    return true;
}
bool isl9241_program_charge_limits(uint16_t mv,uint16_t ma)
{
    if(!initialized || mv<ISL9241_CHARGE_VOLTAGE_MIN_MV ||
       mv>ISL9241_CHARGE_VOLTAGE_MAX_MV || mv%8u ||
       ma<ISL9241_CHARGE_CURRENT_MIN_MA || ma>ISL9241_CHARGE_CURRENT_MAX_MA || ma%4u)
        return false;
    if(!isl9241_set_charge_enable(false) || !isl9241_configuration_ok() ||
       !write_word(MAX_SYSTEM,mv,0x7ff8)) return false;
    voltage_mv=mv;current_ma=ma;
    return isl9241_set_charge_enable(true);
}
bool isl9241_read_charge_limits(uint16_t *mv,uint16_t *ma)
{
    uint16_t v,c,minimum;
    if(!mv || !ma || !read_word(MAX_SYSTEM,&v) || !read_word(CHARGE_CURRENT,&c) ||
       !read_word(MIN_SYSTEM,&minimum) ||
       (minimum & 0x3fc0u)!=(armed ? ISL9241_MIN_SYSTEM_MV : 0u)) return false;
    *mv=v & 0x7ff8u;*ma=c & 0x1ffcu;
    return true;
}
bool isl9241_pet_watchdog(void)
{
    return isl9241_configuration_ok() && write_word(MAX_SYSTEM,voltage_mv,0x7ff8);
}
bool isl9241_set_adapter_alarm(uint16_t nominal_mv)
{
    if(!initialized || (nominal_mv && (nominal_mv<5000u || nominal_mv>22000u))) return false;
    uint32_t threshold=nominal_mv==5000u ? 3500u : (uint32_t)nominal_mv*4u/5u;
    if(threshold>16000u) threshold=16000u;
    uint16_t reference=(uint16_t)((threshold/96u)<<6);
    uint16_t flags=nominal_mv ? (uint16_t)(control4 | ADAPTER_ALARM) :
                              (uint16_t)(control4 & ~ADAPTER_ALARM);
    if(!write_word(ACOK_REFERENCE,reference,0x3fc0) || !write_word(CONTROL4,flags,0xfffd)) return false;
    acok_reference=reference;control4=flags;
    return true;
}
bool isl9241_clear_throttle(void)
{
    return isl9241_configuration_ok() && write_word(CONTROL4,control4 | CLEAR_THROTTLE,0xfffd);
}
bool isl9241_read_sample(isl9241_telemetry_t *sample)
{
    uint16_t info1,info2,status,bat,sys,input,ibus,dc,cc,interrupt;
    if(!sample || !isl9241_configuration_ok() ||
       !read_word(INFO1,&info1) || !read_word(INFO2,&info2) ||
       !read_word(LIVE_STATUS,&status) || !read_word(ADC_BAT,&bat) ||
       !read_word(ADC_SYS,&sys) || !read_word(ADC_INPUT,&input) ||
       !read_word(ADC_INPUT_CURRENT,&ibus) || !read_word(ADC_DISCHARGE,&dc) ||
       !read_word(ADC_CHARGE,&cc) || !read_word(INTERRUPT_STATUS,&interrupt)) return false;
    (void)interrupt; /* Reading acknowledges only events that have ended. */
    isl9241_telemetry_t next={0};
    next.vbat_mv=(uint16_t)(((bat>>6)&255u)*64u);
    next.vsys_mv=(uint16_t)(((sys>>6)&255u)*96u);
    next.vbus_mv=(uint16_t)(((input>>6)&255u)*96u);
    next.ibus_ma=(int16_t)((ibus & 255u)*222u/10u);
    /* Do not subtract a possibly older charging conversion from discharge.
     * The gauge supplies the signed pack value for user-visible telemetry. */
    next.ibat_ma=(dc & 255u) ? -(int16_t)(((dc & 255u)*444u+9u)/10u) :
                              (int16_t)((cc & 255u)*222u/10u);
    next.vbus_present=next.power_good=(info2 & 0x4000u)!=0;
    next.battery_present=(info2 & 0x1000u)==0 && next.vbat_mv>=7500u && next.vbat_mv<=13000u;
    unsigned state=(info2>>8)&15u;
    next.fault=(status & FATAL_STATUS)!=0 || state==7u || state==9u;
    next.throttled=(info1 & 0x1c00u)!=0;
    if(state==6u && (cc & 255u))
        next.charge_status=(info1 & 16u) ? ISL9241_CHARGE_TRICKLE :
            ((info1>>13)&3u)==0 ? ISL9241_CHARGE_TAPER : ISL9241_CHARGE_FAST;
    if(!isl9241_pet_watchdog()) return false;
    *sample=next;
    return true;
}
bool isl9241_is_charge_in_progress(isl9241_charge_status_t status)
{
    return status==ISL9241_CHARGE_TRICKLE || status==ISL9241_CHARGE_FAST ||
           status==ISL9241_CHARGE_TAPER;
}
