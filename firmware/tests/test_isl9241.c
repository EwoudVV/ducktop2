#include "isl9241.h"
#include "i2c_mock.h"
#include <assert.h>
#include <stdio.h>

static void seed(void)
{
    i2c_mock_begin();
    i2c_mock.isl_words[0xfe]=0x49;i2c_mock.isl_words[0xff]=0x0e;
    i2c_mock.isl_words[0x4d]=0x4c0c;
    i2c_mock.isl_words[0x81]=172u<<6; /* 11.008 V */
    i2c_mock.isl_words[0x86]=125u<<6; /* 12 V */
    i2c_mock.isl_words[0x87]=208u<<6; /* 19.968 V */
}
int main(void)
{
    seed();assert(isl9241_probe());
    i2c_mock.isl_words[0xfe]=0x4900;assert(!isl9241_probe());
    seed();i2c_mock.isl_words[0x4d]=0x4c0b;assert(!isl9241_probe());
    seed();assert(isl9241_init());
    assert(i2c_mock.isl_words[0x14]==0 && i2c_mock.isl_words[0x3e]==0);
    assert(i2c_mock.isl_words[0x15]==12528 && i2c_mock.isl_words[0x3f]==200);
    assert(i2c_mock.isl_words[0x3d]==0x2028 && i2c_mock.isl_words[0x4e]==0x4041);
    assert(i2c_mock.isl_words[0x4b]==0x0b40); /* 3.840 V, 85.333 mV per code */
    assert(i2c_mock.isl_words[0x48]==2048 && (i2c_mock.isl_words[0x3c]&8u));
    /* Literal SMBus frames catch byte order independently of the word bank. */
    uint8_t limit[2]={0x28,0x11},alert[2]={0x80,0x11};
    i2c_mock_expect_write(9,0x3f,limit,2);i2c_mock_expect_read(9,0x3f,limit,2);
    i2c_mock_expect_write(9,0x3b,limit,2);i2c_mock_expect_read(9,0x3b,limit,2);
    i2c_mock_expect_write(9,0x47,alert,2);i2c_mock_expect_read(9,0x47,alert,2);
    assert(isl9241_set_input_current_ma(4392));assert(i2c_mock_script_complete());
    assert(!isl9241_set_input_current_ma(4404) && !isl9241_set_input_current_ma(4393));
    assert(!isl9241_program_charge_limits(12600,500));
    assert(!isl9241_program_charge_limits(12528,63));
    assert(isl9241_program_charge_limits(12528,500));
    uint16_t mv,ma;assert(isl9241_read_charge_limits(&mv,&ma) && mv==12528 && ma==500);
    assert(i2c_mock.isl_words[0x3e]==10112);
    assert(isl9241_set_charge_enable(false));
    assert(i2c_mock.isl_words[0x14]==0 && i2c_mock.isl_words[0x3e]==0);
    assert(isl9241_set_adapter_alarm(5000) && i2c_mock.isl_words[0x40]==0x0900);
    assert(isl9241_set_adapter_alarm(20000) && i2c_mock.isl_words[0x40]==0x2980);
    assert(isl9241_set_adapter_alarm(0) && !(i2c_mock.isl_words[0x4e]&32u));
    isl9241_telemetry_t t;
    i2c_mock.isl_words[0x84]=10;i2c_mock.isl_words[0x85]=20;
    assert(isl9241_read_sample(&t) && t.vbat_mv==11008 && t.vsys_mv==12000);
    assert(t.ibat_ma==-444 && t.battery_present && !t.fault);
    i2c_mock.isl_words[0x91]=0x400;
    assert(isl9241_read_sample(&t) && t.fault);
    i2c_mock.isl_words[0x3d]=0; /* brownout lost the NTC safety configuration */
    assert(!isl9241_configuration_ok() && !isl9241_set_charge_enable(true));
    seed();i2c_mock.ignore_writes=true;assert(!isl9241_init());
    seed();i2c_mock.nack_address=9;assert(!isl9241_init());
    puts("ISL9241: PASS (literal word frames, strap, limits, NTC configuration, alarms, reset and failed readback)");
}
