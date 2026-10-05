#include "bq76922.h"
#include "bq76922_profile.h"
#include "ec_pack_monitor.h"
#include "i2c.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

/* Synthetic limits exercise software only. They are not cell ratings. */
static const bq76922_config_row_t rows[] = {
    {0x9236u, 1, {0x0du}}, {0x9237u, 1, {0x01u}},
    {0x9239u, 1, {0x11u}}, {0x923au, 1, {0x10u}},
    {0x92fau, 1, {0x02u}}, {0x92fbu, 1, {0x02u}},
    {0x92fcu, 1, {0x8au}}, {0x9304u, 2, {0x13u, 0x00u}},
    {0x9278u, 1, {82u}}, {0x91d6u, 2, {0xffu,0xffu}},
    {0x9343u, 2, {0x50u, 0x00u}}
};
static const bq76922_profile_t synthetic = {
    .rows=rows, .row_count=sizeof(rows)/sizeof(rows[0]), .complete=true, .qualified=true,
    .discharge_cell_min_mv=3100, .normal_charge_cell_min_mv=3100, .cell_max_mv=4200, .pack_min_mv=9000,
    .cell_voltage_qualified=true, .charge_voltage_qualified=true, .termination_qualified=true,
    .charge_voltage_mv=12120, .charge_cell_max_mv=4100, .charge_spread_max_mv=30,
    .cell_voltage_error_mv=15, .charge_max_rise_mv=9,
    .current_gain_min_permille=1000, .current_offset_ma=0, .current_lsb_ma=1,
    .discharge_limit_ma=8000, .charge_limit_ma=3000, .dynamic_reserve_ma=100,
    .sample_max_age_ms=200, .config_max_age_ms=2000
};
typedef struct {
    uint8_t registers[128];
    const bq76922_profile_t *expected;
    uint16_t selected, mfg;
    bool lost, crc_bad, checksum_bad, corrupt_row, wrong_echo, busy;
    bool write_violation;
    unsigned writes;
} model_t;

static void put_word(uint8_t *p, uint16_t value)
{ p[0]=(uint8_t)value; p[1]=(uint8_t)(value>>8); }
static uint8_t payload(model_t *m, uint8_t buffer[32])
{
    memset(buffer, 0, 32);
    if (m->selected == 0x0057u) {put_word(buffer, m->mfg); return 2;}
    for (size_t i=0; i<m->expected->row_count; ++i) if (m->expected->rows[i].address==m->selected) {
        const bq76922_config_row_t *r=&m->expected->rows[i];
        memcpy(buffer, r->value, r->length);
        if (m->corrupt_row) buffer[0] ^= 1u;
        return r->length;
    }
    return 0;
}
static bool write_model(void *ctx, uint8_t address, uint8_t reg,
                        const uint8_t *wire, uint16_t length)
{
    model_t *m=ctx;
    ++m->writes;
    if (m->lost) return false;
    uint8_t first[]={0x10u, reg, wire[0]};
    if (address!=0x08u || reg!=0x3eu || length!=4 ||
        wire[1]!=bq76922_crc8(first,3) || wire[3]!=bq76922_crc8(&wire[2],1)) {
        m->write_violation=true; return false;
    }
    m->selected=(uint16_t)wire[0] | ((uint16_t)wire[2]<<8);
    if (m->selected<0x9000u && m->selected!=0x0057u) {
        m->write_violation=true; return false;
    }
    return true;
}
static bool read_model(void *ctx, uint8_t address, uint8_t reg,
                       uint8_t *wire, uint16_t length)
{
    model_t *m=ctx; uint8_t buffer[32], data[32];
    if (m->lost || address!=0x08u || !length || length%2 || length>64) return false;
    uint8_t size=payload(m,buffer), count=(uint8_t)(length/2u);
    memset(data,0,sizeof(data));
    if (reg==0x3e) put_word(data,m->busy ? 0xffffu :
                          (m->wrong_echo ? (uint16_t)(m->selected+1u) : m->selected));
    else if (reg==0x61) data[0]=(uint8_t)(size+4u);
    else if (reg==0x40) memcpy(data,buffer,size);
    else if (reg==0x60) {
        uint8_t sum=(uint8_t)((uint8_t)m->selected+(uint8_t)(m->selected>>8));
        for (uint8_t i=0;i<size;++i) sum=(uint8_t)(sum+buffer[i]);
        data[0]=(uint8_t)~sum;
        if(m->checksum_bad) data[0]^=1u;
    } else {
        for(uint8_t i=0;i<count;++i) data[i]=m->registers[(uint8_t)(reg+i)];
    }
    for(uint8_t i=0;i<count;++i) {
        wire[2u*i]=data[i];
        uint8_t first[]={0x10u,reg,0x11u,data[i]};
        wire[2u*i+1u]=i ? bq76922_crc8(&data[i],1) : bq76922_crc8(first,4);
    }
    if(m->crc_bad) wire[1]^=1u;
    return true;
}
static model_t *adapter_model;
bool i2c1_read(uint8_t address, uint8_t reg, uint8_t *data, uint16_t length)
{ return read_model(adapter_model,address,reg,data,length); }
bool i2c1_write_raw(uint8_t address, uint8_t *data, uint16_t length)
{
    if (!data || length<2u) return false;
    return write_model(adapter_model,address,data[0],&data[1],length-1u);
}

static void model_init(model_t *m)
{
    memset(m,0,sizeof(*m));
    m->expected=&synthetic;
    put_word(&m->registers[0x12],0x0200);
    put_word(&m->registers[0x14],3700);
    put_word(&m->registers[0x16],3700);
    put_word(&m->registers[0x1c],3700);
    put_word(&m->registers[0x3a],(uint16_t)(int16_t)-2000);
    put_word(&m->registers[0x34],1110);
    m->registers[0x7f]=BQ76922_CHG_FET | BQ76922_DSG_FET;
    m->mfg=0x0050;
}
static void driver_init(bq76922_t *d, model_t *m, const bq76922_profile_t *p)
{
    bq76922_transport_t io={.context=m,.read=read_model,.write=write_model};
    bq76922_init(d,&io,p);
}
static bool verify(bq76922_t *d, uint32_t start)
{
    if(!bq76922_begin_verify(d,start)) return false;
    for(uint32_t ms=start;d->verifying && ms<start+500u;ms+=2u)
        if(!bq76922_verify_step(d,ms)) return false;
    return d->config_valid && !d->verifying;
}
static bool discharge(const bq76922_t *d,uint32_t now,uint16_t request)
{ return bq76922_discharge_admitted(d,now,true,true,now,request); }
static bool charge(const bq76922_t *d,uint32_t now,uint16_t request)
{ return bq76922_charge_admitted(d,now,true,true,now,request); }

int main(void)
{
    model_t m; bq76922_t d;
    assert(bq76922_crc8((const uint8_t *)"123456789",9)==0xf4u);
    model_init(&m);driver_init(&d,&m,&synthetic);
    assert(verify(&d,0));assert(bq76922_read_sample(&d,100));
    assert(discharge(&d,100,8000));assert(charge(&d,100,3000));
    assert(!discharge(&d,100,8001));assert(!charge(&d,100,3001));
    assert(!m.write_violation);
    model_init(&m);driver_init(&d,&m,&synthetic);assert(bq76922_begin_verify(&d,0));
    for(uint32_t ms=0;d.verifying && ms<1000u;ms+=40u) assert(bq76922_verify_step(&d,ms));
    assert(d.config_valid && !d.verifying);
    model_init(&m);driver_init(&d,&m,&synthetic);assert(verify(&d,0));
    assert(bq76922_read_sample(&d,100));
    assert(!discharge(&d,301,8000));assert(!charge(&d,301,3000));
    assert(!bq76922_discharge_admitted(&d,100,false,true,100,8000));
    assert(!bq76922_discharge_admitted(&d,100,true,false,100,8000));
    assert(!bq76922_discharge_admitted(&d,301,true,true,100,8000));
    assert(bq76922_read_sample(&d,2200));assert(!discharge(&d,2200,8000));

    model_init(&m);driver_init(&d,&m,&synthetic);assert(verify(&d,0));
    put_word(&m.registers[0x14],2000);put_word(&m.registers[0x16],4000);put_word(&m.registers[0x1c],4000);
    assert(bq76922_read_sample(&d,100));
    assert(!discharge(&d,100,8000));assert(!charge(&d,100,3000));
    model_init(&m);m.registers[0x03]=BQ76922_CUV;
    driver_init(&d,&m,&synthetic);assert(verify(&d,0));assert(bq76922_read_sample(&d,100));
    assert(!discharge(&d,100,8000));assert(!charge(&d,100,3000));

    model_init(&m);driver_init(&d,&m,&synthetic);assert(verify(&d,0));
    /* External charge-temperature window asserted CFETOFF. No software
     * override is sent, and discharge remains independently available. */
    m.registers[0x7f]=BQ76922_DSG_FET;
    assert(bq76922_read_sample(&d,100));assert(discharge(&d,100,8000));assert(!charge(&d,100,3000));
    /* External discharge-temperature window asserted DFETOFF. */
    m.registers[0x7f]=BQ76922_CHG_FET;
    assert(bq76922_read_sample(&d,102));assert(!discharge(&d,102,8000));assert(charge(&d,102,3000));
    m.registers[0x7f]=BQ76922_PDSG_FET | BQ76922_DSG_FET | BQ76922_CHG_FET;
    assert(bq76922_read_sample(&d,104));assert(!discharge(&d,104,8000));

    model_init(&m);driver_init(&d,&m,&synthetic);assert(verify(&d,0));
    put_word(&m.registers[0x3a],3000);
    assert(bq76922_read_sample(&d,100));assert(d.sample.discharge_upper_ma==1);
    assert(discharge(&d,100,8000));assert(charge(&d,100,3000));
    put_word(&m.registers[0x3a],3001);
    assert(bq76922_read_sample(&d,102));assert(!charge(&d,102,3000));
    put_word(&m.registers[0x3a],(uint16_t)(int16_t)-7900);
    assert(bq76922_read_sample(&d,104));assert(!discharge(&d,104,8000));
    put_word(&m.registers[0x3a],(uint16_t)(int16_t)-32768);
    assert(bq76922_read_sample(&d,106));assert(d.sample.discharge_upper_ma==32769);
    assert(!discharge(&d,106,8000));

    model_init(&m);driver_init(&d,&m,&synthetic);assert(verify(&d,0));
    m.lost=true;assert(!bq76922_read_sample(&d,100));assert(!d.sample.valid && !d.config_valid);
    assert(!discharge(&d,100,8000));assert(!charge(&d,100,3000));
    model_init(&m);m.crc_bad=true;driver_init(&d,&m,&synthetic);assert(!verify(&d,0));
    model_init(&m);m.checksum_bad=true;driver_init(&d,&m,&synthetic);assert(!verify(&d,0));
    model_init(&m);m.corrupt_row=true;driver_init(&d,&m,&synthetic);assert(!verify(&d,0));
    model_init(&m);m.wrong_echo=true;driver_init(&d,&m,&synthetic);assert(!verify(&d,0));
    model_init(&m);m.busy=true;driver_init(&d,&m,&synthetic);assert(!verify(&d,0));
    model_init(&m);m.mfg=0x0040;driver_init(&d,&m,&synthetic);assert(!verify(&d,0));
    model_init(&m);put_word(&m.registers[0x12],0x0300);driver_init(&d,&m,&synthetic);assert(!verify(&d,0));
    model_init(&m);driver_init(&d,&m,&synthetic);assert(verify(&d,0));
    m.crc_bad=true;assert(!bq76922_read_sample(&d,100));assert(!d.sample.valid && !d.config_valid);
    model_init(&m);driver_init(&d,&m,&synthetic);assert(verify(&d,0));
    m.registers[0x0f]=1;assert(bq76922_read_sample(&d,100));
    assert(!discharge(&d,100,8000));assert(!charge(&d,100,3000));

    bq76922_profile_t unqualified=synthetic;unqualified.qualified=false;
    model_init(&m);driver_init(&d,&m,&unqualified);assert(verify(&d,0));assert(bq76922_read_sample(&d,100));
    assert(!discharge(&d,100,8000));assert(!charge(&d,100,3000));
    model_init(&m);m.expected=&ducktop2_bq76922_profile;
    driver_init(&d,&m,&ducktop2_bq76922_profile);assert(verify(&d,0));
    assert(bq76922_read_sample(&d,200));
    assert(!discharge(&d,200,8000) && !charge(&d,200,3000));
    assert(ducktop2_bq76922_profile.complete && !ducktop2_bq76922_profile.qualified);
    model_init(&m);driver_init(&d,&m,&synthetic);assert(verify(&d,0));
    put_word(&m.registers[0x34],899);assert(bq76922_read_sample(&d,100));
    assert(!discharge(&d,100,8000) && !charge(&d,100,3000));
    bq76922_profile_t missing_bounds=synthetic;missing_bounds.current_gain_min_permille=0;
    model_init(&m);driver_init(&d,&m,&missing_bounds);assert(verify(&d,0));
    assert(bq76922_read_sample(&d,100));assert(!discharge(&d,100,8000));
    model_init(&m);driver_init(&d,&m,&synthetic);assert(verify(&d,0));
    m.registers[0x05]=0x40u;assert(bq76922_read_sample(&d,100));
    assert(!discharge(&d,100,8000) && !charge(&d,100,3000));
    /* COV is a charge fault. A bounded discharge may reduce it while
     * DSG is on, every ordinary cell/current bound holds and READY is fresh. */
    model_init(&m);driver_init(&d,&m,&synthetic);assert(verify(&d,0));
    m.registers[0x03]=BQ76922_COV;m.registers[0x7f]=BQ76922_DSG_FET;
    put_word(&m.registers[0x1c],4160);put_word(&m.registers[0x34],1156);
    put_word(&m.registers[0x12],0x0a00);put_word(&m.registers[0x64],0x4000);
    assert(bq76922_read_sample(&d,100));assert(discharge(&d,100,8000));assert(!charge(&d,100,3000));
    put_word(&m.registers[0x3a],(uint16_t)(int16_t)-7900);
    assert(bq76922_read_sample(&d,102));assert(!discharge(&d,102,8000));
    put_word(&m.registers[0x3a],(uint16_t)(int16_t)-2000);m.registers[0x03]=0;m.registers[0x02]=BQ76922_COV;
    assert(bq76922_read_sample(&d,104));assert(discharge(&d,104,8000));assert(!charge(&d,104,3000));
    /* Above-floor cells do not grant a CUV recovery branch while its
     * retained flag is active. A genuinely low individual cell also fails. */
    model_init(&m);driver_init(&d,&m,&synthetic);assert(verify(&d,0));
    m.registers[0x03]=BQ76922_CUV;m.registers[0x7f]=BQ76922_CHG_FET;
    assert(bq76922_read_sample(&d,100));assert(!discharge(&d,100,8000));assert(!charge(&d,100,3000));
    put_word(&m.registers[0x14],3100);assert(bq76922_read_sample(&d,102));assert(!charge(&d,102,3000));
    model_init(&m);driver_init(&d,&m,&synthetic);assert(verify(&d,0));
    put_word(&m.registers[0x14],3099);put_word(&m.registers[0x34],1049);
    assert(bq76922_read_sample(&d,100));assert(!discharge(&d,100,8000) && !charge(&d,100,3000));
    put_word(&m.registers[0x14],3100);put_word(&m.registers[0x34],1050);
    assert(bq76922_read_sample(&d,102));assert(discharge(&d,102,8000) && !charge(&d,102,3000));
    put_word(&m.registers[0x14],3990);put_word(&m.registers[0x16],3990);put_word(&m.registers[0x1c],3990);
    assert(bq76922_read_sample(&d,104));assert(discharge(&d,104,8000) && charge(&d,104,3000));
    /* Every reserved safety/FET bit and every PF byte fail both directions. */
    for (unsigned i=0;i<12u;++i) {
        const uint8_t reg[]={0x03,0x05,0x07,0x7f,0x0b,0x0d,0x0f,0x11,0x0a,0x0c,0x0e,0x10};
        const uint8_t bits[]={0x01,0x08,0x08,0x80,0x01,0x01,0x01,0x01,0x01,0x01,0x01,0x01};
        model_init(&m);driver_init(&d,&m,&synthetic);assert(verify(&d,0));
        m.registers[reg[i]]|=bits[i];assert(bq76922_read_sample(&d,100));
        assert(!discharge(&d,100,8000) && !charge(&d,100,3000));
    }
    for (unsigned i=0;i<3u;++i) {
        const uint16_t raw[]={0x0008u,0x0100u,0x4000u};
        model_init(&m);driver_init(&d,&m,&synthetic);assert(verify(&d,0));
        put_word(&m.registers[0x64],raw[i]);assert(bq76922_read_sample(&d,100));
        assert(!discharge(&d,100,8000) && !charge(&d,100,3000));
    }
    /* Native directional thermal faults complement the independent OFF pins. */
    model_init(&m);driver_init(&d,&m,&synthetic);assert(verify(&d,0));
    m.registers[0x05]=0x10u;m.registers[0x7f]=BQ76922_DSG_FET;
    assert(bq76922_read_sample(&d,100));assert(discharge(&d,100,8000));assert(!charge(&d,100,3000));
    m.registers[0x05]=0x20u;m.registers[0x7f]=BQ76922_CHG_FET;
    assert(bq76922_read_sample(&d,102));assert(!discharge(&d,102,8000));assert(charge(&d,102,3000));
    /* READY high cannot override a transport failure or a stale observation. */
    model_init(&m);driver_init(&d,&m,&synthetic);assert(verify(&d,0));assert(bq76922_read_sample(&d,100));
    assert(!bq76922_discharge_admitted(&d,100,false,true,100,8000));
    assert(!bq76922_charge_admitted(&d,100,false,true,100,3000));
    assert(!bq76922_discharge_admitted(&d,301,true,true,100,8000));
    m.lost=true;assert(!bq76922_read_sample(&d,102));assert(!discharge(&d,102,8000));
    /* REG1 loss drops supervised READY and immediately discards the adapter's
     * previous sample. A later high does not revive that stale sample. */
    model_init(&m);m.expected=&ducktop2_bq76922_profile;adapter_model=&m;ec_pack_monitor_init();
    for(uint32_t ms=0;ms<=250u;ms+=2u) {ec_pack_monitor_set_ready(true,true,ms);ec_pack_monitor_poll(ms);}
    assert(ec_pack_monitor_sample()->valid);ec_pack_monitor_set_ready(true,false,251);
    assert(!ec_pack_monitor_sample()->valid);ec_pack_monitor_set_ready(true,true,252);
    assert(!ec_pack_monitor_sample()->valid);
    assert(!ec_pack_monitor_discharge_allowed(252,8000) && !ec_pack_monitor_charge_allowed(252,3000));
    assert(!m.write_violation);
    const bq76922_config_row_t unsafe_row = {0x0022u, 1, {0}};
    bq76922_profile_t unsafe = synthetic; unsafe.rows=&unsafe_row; unsafe.row_count=1;
    model_init(&m);driver_init(&d,&m,&unsafe);assert(!verify(&d,0));assert(m.writes==0);
    puts("BQ76922: PASS (CRC/checksum/readback, stale data, loss, individual cells, current direction, directional faults, READY/REG1 loss, qualification locks)");
    return 0;
}
