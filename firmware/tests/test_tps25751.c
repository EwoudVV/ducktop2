#include "tps25751.h"
#include "board_profile.h"
#include "i2c_mock.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

/* Independent wire examples: count prefix, then least-significant byte.
 * PDO = fixed 15 V / 3 A (0x0004b12c); RDO #2 / 3 A (0x2004b12c).
 * The 12-byte RDO tail is deliberately different from its active low word. */
static const uint8_t st[] = {5, 0x0d, 0, 0x20, 0, 0};
static const uint8_t pdo[] = {6, 0x2c, 0xb1, 4, 0, 0xaa, 1};
static const uint8_t rdo[] = {16, 0x2c, 0xb1, 4, 0x20, 0, 0, 0, 0, 0, 0, 0, 0, 1, 2, 3, 4};
static const uint8_t pd[] = {4, 0x1c, 0, 0, 0};
static void expect_snapshot(uint8_t address, const uint8_t *status)
{
    i2c_mock_expect_read(address, 0x1a, status, 6);
    i2c_mock_expect_read(address, 0x34, pdo, 7);
    i2c_mock_expect_read(address, 0x35, rdo, 17);
    i2c_mock_expect_read(address, 0x40, pd, 5);
}
static void config_read(uint8_t address,const uint8_t *cfg)
{
    i2c_mock_expect_read(address,0x28,cfg,1);
    i2c_mock_expect_read(address,0x28,cfg,(uint8_t)(cfg[0]+1));
}
static void port_snapshot(const uint8_t status[6],const uint8_t power[6],
                          const uint8_t pdstate[5],const uint8_t *cfg)
{
    i2c_mock_expect_read(0x20,0x1a,status,6);
    i2c_mock_expect_read(0x20,0x26,power,6);
    i2c_mock_expect_read(0x20,0x40,pdstate,5);
    config_read(0x20,cfg);
    static const uint8_t source_profile[]={63,1,168,42,90,144,1,4};
    static const uint8_t control[]={4,0x70,0xc1,0x81,0};
    static const uint8_t global[]={14,1,0x81,2};
    i2c_mock_expect_read(0x20,0x32,source_profile,8);
    i2c_mock_expect_read(0x20,0x29,control,5);
    i2c_mock_expect_read(0x20,0x27,global,4);
}
static void port_tests(void)
{
    uint8_t cfg[19]={17,0xa2,0x48,0x22,0xa5,0x3c,0x81,0x72,0x63,0x54,0x45,0x36,0x27,0x18,0x09,0xfa,0xeb,0xdc,0xcd};
    uint8_t sink[6]={5,0x0d,0,0x20,0,0};
    uint8_t source[6]={5,0x6d,0,0x20,0,0};
    uint8_t sink_vconn[6]={5,0x02,0x30,0,0,0x40}; /* PP_EXT input, CC1 VCONN */
    uint8_t source_vconn[6]={5,0x83,0,0,0,0x40}; /* PP5V output, CC2 VCONN */
    uint8_t sink_pd[5]={4,0x1c,0,0,0},source_pd[5]={4,0x5c,0,0,0};
    tps25751_port_state_t state;
    i2c_mock_begin();port_snapshot(sink,sink_vconn,sink_pd,cfg);port_snapshot(sink,sink_vconn,sink_pd,cfg);
    assert(tps25751_read_port_state(0x20,&state));
    assert(state.valid && state.source_profile_valid && state.connected && !state.source && state.vconn_enabled && state.vconn_switch==2 &&
           state.pphv_input_enabled && !state.pp5v_enabled && state.typec_mode==2 && i2c_mock_script_complete());
    i2c_mock_begin();port_snapshot(source,source_vconn,source_pd,cfg);port_snapshot(source,source_vconn,source_pd,cfg);
    assert(tps25751_read_port_state(0x20,&state) && state.source && state.dfp && state.pp5v_enabled &&
           state.vconn_enabled && state.vconn_switch==3 && i2c_mock_script_complete());
    i2c_mock_begin();port_snapshot(source,source_vconn,sink_pd,cfg);port_snapshot(source,source_vconn,sink_pd,cfg);
    assert(!tps25751_read_port_state(0x20,&state) && !state.valid);
    i2c_mock_begin();port_snapshot(source,source_vconn,source_pd,cfg);port_snapshot(sink,sink_vconn,sink_pd,cfg);
    assert(!tps25751_read_port_state(0x20,&state) && !state.valid);
    i2c_mock_begin();port_snapshot(source,source_vconn,source_pd,cfg);port_snapshot(source,source_vconn,source_pd,cfg);
    /* A live 3 A Source PDO can never satisfy the fixed 900 mA reservation. */
    for(size_t n=0;n<i2c_mock.script_count;n++) if(i2c_mock.script[n].reg==0x32) {
        i2c_mock.script[n].data[4]=0x2c;i2c_mock.script[n].data[5]=0x91;
    }
    assert(tps25751_read_port_state(0x20,&state) && !state.source_profile_valid);
    /* The official export has one reserved tail byte on 0x29. Both wire
     * lengths are supported; unrecognized lengths and UFP swaps fail off. */
    for(uint8_t length=3;length<=6;length++) {
        i2c_mock_begin();port_snapshot(source,source_vconn,source_pd,cfg);port_snapshot(source,source_vconn,source_pd,cfg);
        for(size_t n=0;n<i2c_mock.script_count;n++) if(i2c_mock.script[n].reg==0x29)
            i2c_mock.script[n].data[0]=length;
        assert(tps25751_read_port_state(0x20,&state)==(length==4 || length==5));
        if(length==4 || length==5) assert(state.source_profile_valid && i2c_mock_script_complete());
    }
    i2c_mock_begin();port_snapshot(source,source_vconn,source_pd,cfg);port_snapshot(source,source_vconn,source_pd,cfg);
    for(size_t n=0;n<i2c_mock.script_count;n++) if(i2c_mock.script[n].reg==0x29)
        i2c_mock.script[n].data[2]|=0x10; /* Process Swap to UFP */
    assert(tps25751_read_port_state(0x20,&state) && !state.source_profile_valid);
    cfg[2]=8; /* The right USB2 image cannot qualify the left Gen2 port. */
    i2c_mock_begin();port_snapshot(source,source_vconn,source_pd,cfg);port_snapshot(source,source_vconn,source_pd,cfg);
    assert(tps25751_read_port_state(0x20,&state) && !state.source_profile_valid);
    cfg[2]=0x48;
    uint8_t off[6]={5,0,0,0,0,0x40};
    i2c_mock_begin();port_snapshot(sink,off,sink_pd,cfg);port_snapshot(sink,off,sink_pd,cfg);
    assert(tps25751_read_port_state(0x20,&state) && !state.vconn_enabled && !state.pp5v_enabled);
    for(uint8_t length=17;length<=18;length++) {
        uint8_t changed[19];cfg[0]=length;memcpy(changed,cfg,sizeof(changed));changed[1]=0xa0;
        i2c_mock_begin();config_read(0x21,cfg);
        i2c_mock_expect_write(0x21,0x28,changed,(uint8_t)(length+1));config_read(0x21,changed);
        assert(tps25751_set_typec_mode(0x21,0) && i2c_mock_script_complete());
        assert(i2c_mock.write_raws==1); /* exact length prefix and unrelated-byte preservation */
        i2c_mock_begin();config_read(0x21,changed);
        assert(tps25751_set_typec_mode(0x21,0) && i2c_mock.write_raws==0 && i2c_mock_script_complete());
    }
    assert(!tps25751_set_typec_mode(0x20,1) && !tps25751_set_typec_mode(0x20,3));
    cfg[0]=16;i2c_mock_begin();i2c_mock_expect_read(0x20,0x28,cfg,1);
    assert(!tps25751_set_typec_mode(0x20,2));
}
int main(void)
{
    port_tests();
    tps25751_contract_t c;
    for (uint8_t address=0x20; address<=0x21; ++address) {
        i2c_mock_begin(); expect_snapshot(address, st); expect_snapshot(address, st);
        assert(tps25751_read_contract(address, &c));
        assert(c.valid && c.sink && c.connected && c.voltage_mv == 15000 && c.current_ma == 3000);
        assert(i2c_mock_script_complete());
    }
    const uint8_t pdo20[6]={0x2c,0x41,0x06,0x00,0,0};
    assert(tps25751_decode_contract(st+1,pdo20,rdo+1,pd+1,&c)==(DUCKTOP2_PD_ALLOW_20V != 0));
    if (DUCKTOP2_PD_ALLOW_20V) assert(c.voltage_mv==20000 && c.current_ma==3000);
    uint8_t bad[17];
    memcpy(bad, st, sizeof(st)); bad[0] = 4;
    i2c_mock_begin(); i2c_mock_expect_read(0x20, 0x1a, bad, 6);
    assert(!tps25751_read_contract(0x20, &c) && !c.valid);
    memcpy(bad, st, sizeof(st)); bad[1] |= 0x20;
    i2c_mock_begin(); expect_snapshot(0x20, st); expect_snapshot(0x20, bad);
    assert(!tps25751_read_contract(0x20, &c) && !c.valid);
    assert(!tps25751_decode_contract(bad+1, pdo+1, rdo+1, pd+1, &c));
    memcpy(bad, pd, sizeof(pd)); bad[1] |= 0x40;
    assert(!tps25751_decode_contract(st+1, pdo+1, rdo+1, bad+1, &c));
    memcpy(bad, pdo, sizeof(pdo)); bad[4] = 0xc0;
    assert(!tps25751_decode_contract(st+1, bad+1, rdo+1, pd+1, &c));
    memcpy(bad, rdo, sizeof(rdo)); bad[3] = 8;
    assert(!tps25751_decode_contract(st+1, pdo+1, bad+1, pd+1, &c));
    memcpy(bad, st, sizeof(st)); bad[1] = 7;
    assert(!tps25751_decode_contract(bad+1, pdo+1, rdo+1, pd+1, &c));
    i2c_mock_begin(); i2c_mock.nack_all = true;
    assert(!tps25751_read_contract(0x20, &c) && !c.valid);
    puts("tps25751: PASS (literal frames, both ports, malformed/role/transition/fault cases)");
}
