#include "bq76922_charge.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static const bq76922_config_row_t rows[]={{0x9278,1,{82}},{0x91d6,2,{255,255}}};
static bq76922_profile_t profile={.rows=rows,.row_count=2,.complete=true,.qualified=true,
    .cell_voltage_qualified=true,.charge_voltage_qualified=true,.termination_qualified=true,
    .charge_voltage_mv=12120,.charge_cell_max_mv=4100,.charge_spread_max_mv=30,
    .cell_voltage_error_mv=15,.charge_max_rise_mv=9,
    .discharge_cell_min_mv=3100,.normal_charge_cell_min_mv=3100,.cell_max_mv=4200,.pack_min_mv=9000,
    .current_gain_min_permille=1000,.current_lsb_ma=1,.discharge_limit_ma=8000,.charge_limit_ma=3000,
    .dynamic_reserve_ma=100,.sample_max_age_ms=200,.config_max_age_ms=10000};
static bq76922_t d;
static void seed(void)
{
    memset(&d,0,sizeof(d));d.profile=&profile;d.config_valid=true;d.sample.valid=true;
    d.sample.stack_mv=12120;d.sample.fet_status=BQ76922_CHG_FET|BQ76922_DSG_FET;
    d.sample.cell_mv[0]=d.sample.cell_mv[1]=d.sample.cell_mv[2]=4040;
    d.sample.current_ma=100;d.sample.charge_upper_ma=101;
}
static bool step(bq76922_charge_state_t *s,uint32_t now,bool cv,bool on)
{
    d.sample.at_ms=d.config_at_ms=now;
    return bq76922_charge_step(s,&d,now,true,true,now,true,now,12120,cv,on);
}
static bool charge(void){return bq76922_charge_admitted(&d,0,true,true,0,3000);}
static bool discharge(void){return bq76922_discharge_admitted(&d,0,true,true,0,8000);}
static uint32_t run_fresh(bq76922_charge_state_t *s,uint32_t now,uint32_t duration,bool cv,bool on)
{
    assert(duration%100u==0);
    for(uint32_t elapsed=100;elapsed<=duration;elapsed+=100)
        assert(step(s,now+elapsed,cv,on));
    return now+duration;
}
static void test_cv_dwell_budget(void)
{
    bq76922_charge_state_t s;uint32_t now;
    /* a 10Ah pack at 3A already needs more than 3.3h before taper. */
    seed();bq76922_charge_init(&s);d.sample.current_ma=2999;d.sample.charge_upper_ma=3000;
    assert(step(&s,0,false,true));now=run_fresh(&s,0,18000000u,false,true);
    assert(now>4u*3600000u && !s.complete && !s.fault_latched && s.cv_dwell_ms==0);
    /* low input-limited current is not taper without the actual CV loop. */
    seed();bq76922_charge_init(&s);d.sample.current_ma=150;d.sample.charge_upper_ma=151;
    assert(step(&s,0,false,true));run_fresh(&s,0,72000000u,false,true);
    assert(!s.complete && !s.fault_latched && s.cv_dwell_ms==0);
    /* enabled CV above the taper threshold consumes the cumulative budget. */
    seed();bq76922_charge_init(&s);d.sample.current_ma=250;d.sample.charge_upper_ma=251;
    assert(step(&s,0,true,true));now=run_fresh(&s,0,3600000u,true,true);
    assert(s.cv_dwell_ms==3600000u);
    for(unsigned cycle=0;cycle<10;++cycle) {
        uint32_t retained=s.cv_dwell_ms;
        assert(step(&s,now+=100,false,false));
        d.sample.at_ms=d.config_at_ms=now;
        assert(!bq76922_charge_step(&s,&d,now,true,true,now,false,now,12120,true,false));
        now+=3600000u;
        assert(!bq76922_charge_step(&s,&d,now,true,true,now,false,now,12120,true,false));
        assert(s.cv_dwell_ms==retained && !s.fault_latched);
        assert(step(&s,now+=100,true,true));
        now=run_fresh(&s,now,500,true,true);
        assert(s.cv_dwell_ms==retained+500u);
    }
    uint32_t retained=s.cv_dwell_ms;
    /* a stale gap is not retrospectively charged to CV. */
    now+=1000u;
    assert(!bq76922_charge_step(&s,&d,now,true,true,now,true,now,12120,true,true));
    assert(s.cv_dwell_ms==retained && !s.fault_latched);
    assert(step(&s,now+=100,true,true));assert(s.cv_dwell_ms==retained);
    now=run_fresh(&s,now,500,true,true);assert(s.cv_dwell_ms==retained+500u);
    /* a missed polling interval also cannot count unknown/stale history. */
    retained=s.cv_dwell_ms;assert(step(&s,now+=1000,true,true));assert(s.cv_dwell_ms==retained);
    profile.termination_qualified=false;
    assert(!step(&s,now+=100,true,true));assert(s.cv_dwell_ms==retained);
    profile.termination_qualified=true;assert(step(&s,now+=100,true,true));
    uint32_t remaining=BQ76922_CV_DWELL_MAX_MS-s.cv_dwell_ms;
    now=run_fresh(&s,now,remaining-100u,true,true);
    assert(!step(&s,now+=100,true,true) && s.fault_latched && !s.complete);
    assert(s.cv_dwell_ms==BQ76922_CV_DWELL_MAX_MS);
    assert(!step(&s,now+=100,false,false));assert(s.fault_latched);
    now+=3600000u;
    assert(!bq76922_charge_step(&s,&d,now,false,false,now,false,now,12120,false,false));
    assert(s.fault_latched && s.cv_dwell_ms==BQ76922_CV_DWELL_MAX_MS);
    assert(!step(&s,now+=100,true,true));assert(s.fault_latched);
}

int main(void)
{
    seed();assert(charge() && discharge());
    d.sample.cell_mv[0]=4101;assert(!charge() && discharge());
    seed();d.sample.cell_mv[0]=4071;assert(!charge() && discharge());
    d.sample.cell_mv[0]=4070;assert(charge());
    seed();d.sample.cell_mv[0]=3099;assert(!charge() && !discharge());
    seed();profile.cell_voltage_qualified=false;assert(!charge() && !discharge());profile.cell_voltage_qualified=true;
    profile.charge_voltage_mv=12528;assert(!charge() && discharge());profile.charge_voltage_mv=12120;
    profile.termination_qualified=false;assert(!charge());profile.termination_qualified=true;
    bq76922_config_row_t wrong[]={{0x9278,1,{81}},{0x91d6,2,{255,255}}};
    seed();profile.rows=wrong;assert(!charge() && discharge());profile.rows=rows;
    seed();d.sample.at_ms=0;assert(!bq76922_charge_admitted(&d,201,true,true,201,3000));
    seed();bq76922_charge_state_t s;bq76922_charge_init(&s);
    for(uint32_t t=0;t<30000;t+=100)assert(step(&s,t,true,true));
    assert(!step(&s,30000,true,true) && s.complete && s.cv_dwell_ms==30000u);
    assert(!step(&s,30100,true,false) && s.complete);
    d.sample.cell_mv[0]=d.sample.cell_mv[1]=d.sample.cell_mv[2]=3950;
    for(uint32_t t=30200;t<35200;t+=100)assert(!step(&s,t,false,false));
    assert(step(&s,35200,false,false) && !s.complete && s.cv_dwell_ms==0);
    /* stale data cannot clear completion, and restarts the recharge window. */
    s.complete=true;s.recharge_pending=true;s.recharge_at=0;d.sample.at_ms=0;
    assert(!bq76922_charge_step(&s,&d,1000,true,true,1000,true,1000,12120,false,false));
    assert(s.complete && !s.recharge_pending);
    /* CV, bounded positive taper and uninterrupted fresh samples are required. */
    seed();bq76922_charge_init(&s);assert(step(&s,0,true,true));
    assert(step(&s,29900,false,true));assert(!s.taper_pending);
    assert(step(&s,30000,true,true));assert(!s.complete);
    d.sample.current_ma=-1;assert(step(&s,30100,true,true));assert(!s.taper_pending);
    d.sample.current_ma=100;d.sample.charge_upper_ma=201;assert(step(&s,30200,true,true));assert(!s.taper_pending);
    d.sample.charge_upper_ma=101;assert(step(&s,30300,true,true));
    assert(step(&s,31000,true,true) && s.taper_at==31000);
    d.sample.pf_c=1;assert(!step(&s,31100,true,true));assert(!s.taper_pending);
    d.sample.pf_c=0;d.sample.fet_status=BQ76922_DSG_FET;assert(!step(&s,31200,true,true));
    test_cv_dwell_budget();
    seed();bq76922_charge_init(&s);
    assert(!bq76922_charge_step(&s,&d,0,true,true,0,true,0,12528,true,true));
    assert(!bq76922_charge_step(&s,&d,0,false,true,0,true,0,12120,true,true));
    assert(!bq76922_charge_step(&s,&d,201,true,true,201,true,0,12120,true,true));
    /* a fresh resumption cannot clear completion or its accumulated budget. */
    seed();bq76922_charge_init(&s);
    for(uint32_t t=0;t<30000;t+=100)assert(step(&s,t,true,true));
    assert(!step(&s,30000,true,true));uint32_t completed_budget=s.cv_dwell_ms;
    assert(!bq76922_charge_step(&s,&d,31000,false,false,31000,false,31000,12120,false,false));
    assert(!step(&s,31100,true,true) && s.complete && s.cv_dwell_ms==completed_budget);
    /* normal completion and recharge timers also work across tick wrap. */
    seed();bq76922_charge_init(&s);uint32_t start=UINT32_MAX-15000u;
    for(uint32_t elapsed=0;elapsed<30000;elapsed+=100)assert(step(&s,start+elapsed,true,true));
    assert(!step(&s,start+30000,true,true) && s.complete);
    puts("bq charge: pass (directional cell limits, calibration locks, CV/taper, stale data, recharge latch, timeout)");
}
