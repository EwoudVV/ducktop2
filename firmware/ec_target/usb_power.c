#include "usb_power.h"
#include "i2c.h"
#include <string.h>

#define NO_PORT 255u
static bool all_off(usb_power_state_t *s)
{
    if (!usb_power_hw_write(0)) return false;
    s->applied_mask=0;s->starting_port=NO_PORT;
    if (s->phase!=USB_POWER_FAULT) s->phase=USB_POWER_OFF;
    return true;
}
static bool trip(usb_power_state_t *s,usb_power_fault_t fault)
{
    s->fault=fault;s->phase=USB_POWER_FAULT;
    memset(&s->plan,0,sizeof(s->plan));
    return all_off(s);
}
static bool fresh(const usb_power_state_t *s,uint32_t now)
{
    return s->sample.valid && now-s->sample.sample_ms<=s->config.sample_max_age_ms;
}
static bool voltage_valid(const usb_power_state_t *s)
{
    /* Bus-voltage gain has its own 0.1% plus 50 ppm/C full-temperature
     * envelope. Round outward and include one ADC code. */
    uint32_t low=(uint64_t)s->sample.voltage_mv*1000000u/1006000u;
    uint32_t high=((uint64_t)s->sample.voltage_mv*1000000u+993999u)/994000u+2u;
    return low>=s->config.rail_min_mv && high<=s->config.rail_max_mv;
}
bool usb_power_init(usb_power_state_t *s,const usb_power_config_t *c,uint32_t now)
{
    if (!s || !c) return false;
    memset(s,0,sizeof(*s));s->config=*c;s->starting_port=NO_PORT;
    if (c->budget.qualified && (!c->pd_inrush_ma || !c->branch_inrush_ma ||
        c->startup_ceiling_ma>5700u || c->budget.admission_current_ma>5500u ||
        c->startup_ceiling_ma<c->budget.admission_current_ma ||
        c->rail_min_mv<4900u || c->rail_max_mv>5250u || c->rail_min_mv>=c->rail_max_mv ||
        !c->sample_max_age_ms || c->sample_max_age_ms>100u ||
        !c->startup_timeout_ms || c->startup_timeout_ms>1000u ||
        !c->gate_timeout_ms || c->gate_timeout_ms>1000u)) return false;
    s->initialized=usb_power_hw_init(now);s->polled_ms=now;
    return s->initialized;
}
bool usb_power_disable(usb_power_state_t *s)
{
    if (!s || !s->initialized) return false;
    memset(&s->plan,0,sizeof(s->plan));
    return all_off(s);
}
bool usb_power_poll(usb_power_state_t *s,uint32_t now)
{
    if (!s || !s->initialized) return false;
    usb_power_sample_t sample;
    usb_power_hw_result_t result=usb_power_hw_sample(now,&sample);
    if (result==USB_POWER_HW_BUS || result==USB_POWER_HW_CONFIG || result==USB_POWER_HW_RANGE)
        return false;
    if (sample.valid) s->sample=sample;
    if (result==USB_POWER_HW_OVERCURRENT && !trip(s,USB_POWER_OVERCURRENT)) return false;
    for (uint8_t n=0;n<2u;n++) {
        tps25751_port_state_t pd;
        bool valid=tca9548a_select_channel((uint8_t)(2u+n)) &&
                   tps25751_read_port_state((uint8_t)(0x20u+n),&pd);
        if (!tca9548a_deselect_all()) return false;
        memset(&s->pd[n],0,sizeof(s->pd[n]));
        if (valid) s->pd[n]=pd;
    }
    s->polled_ms=now;
    return true;
}
bool usb_power_step(usb_power_state_t *s,const usb_power_request_t *r,uint32_t now)
{
    if (!s || !r || !s->initialized) return false;
    if (s->phase==USB_POWER_FAULT) {
        if (!all_off(s)) return false;
        if (r->clear_fault && fresh(s,now) && s->sample.upper_current_ma<=100u &&
            usb_power_hw_clear_fault(now)) {s->phase=USB_POWER_OFF;s->fault=USB_POWER_NO_FAULT;}
        else return true;
    }
    bool source_changed=s->have_source && s->last_source!=r->active_source;
    s->last_source=r->active_source;s->have_source=true;
    if (!r->host_lease_valid || !r->system_safe || r->transfer_active || source_changed ||
        !s->config.budget.qualified) {
        memset(&s->plan,0,sizeof(s->plan));s->plan.denied_mask=r->requested_mask;
        return all_off(s);
    }
    if (now-s->polled_ms>s->config.sample_max_age_ms || !fresh(s,now)) {
        if (s->phase==USB_POWER_STARTING && now-s->started_ms<=s->config.startup_timeout_ms)
            return true;
        if (s->applied_mask || s->phase==USB_POWER_READY || s->phase==USB_POWER_STARTING)
            return trip(s,USB_POWER_STALE);
        memset(&s->plan,0,sizeof(s->plan));s->plan.denied_mask=r->requested_mask;
        return all_off(s);
    }
    uint8_t requested=r->requested_mask;
    for (uint8_t n=0;n<2;n++) {
        uint8_t bit=(uint8_t)(1u<<n);
        /* Source-only and disabled configurations are not the released dual-
         * role contract. A matching complete state is required for admission. */
        if (!s->pd[n].valid || !s->pd[n].source_profile_valid || (s->pd[n].typec_mode!=0u && s->pd[n].typec_mode!=2u))
            requested&=(uint8_t)~bit;
        if ((s->applied_mask&bit) && s->pd[n].valid && s->pd[n].power_path_fault)
            return trip(s,USB_POWER_PD_PATH);
    }
    ec_usb_power_inputs_t input={
        .host_lease_valid=true,.system_safe=true,.requested_mask=requested,
        .retained_mask=s->applied_mask,.pd_sink_only_mask=0,
        .available_input_power_mw=r->available_input_power_mw
    };
    ec_usb_power_plan_t next;
    if (!ec_usb_power_plan(&s->config.budget,&input,&next)) return false;
    next.denied_mask=r->requested_mask&(uint8_t)~next.allowed_mask;
    s->plan=next;
    uint8_t keep=s->applied_mask&next.allowed_mask;
    if (keep!=s->applied_mask) {
        if (!usb_power_hw_write((uint8_t)(1u|(keep<<1)))) return false;
        s->applied_mask=keep;s->starting_port=NO_PORT;
    }
    if (!next.allowed_mask) return all_off(s);
    if (r->committed_reservation_mw<next.reserved_input_power_mw) {
        /* Drop loads before releasing a reservation, reserve before additions. */
        if (!s->applied_mask && !all_off(s)) return false;
        if (!s->applied_mask) s->phase=USB_POWER_PENDING;
        return true;
    }
    if (s->phase==USB_POWER_OFF || s->phase==USB_POWER_PENDING) {
        if (!usb_power_hw_write(1u)) return false;
        s->phase=USB_POWER_STARTING;s->started_ms=now;
        s->rail_sequence=s->sample.conversion_sequence;return true;
    }
    if (s->phase==USB_POWER_STARTING) {
        if ((s->sample.input1&USB_POWER_IN_PG) && voltage_valid(s) &&
            (int32_t)(s->sample.sample_ms-s->started_ms)>=0 &&
            s->sample.conversion_sequence!=s->rail_sequence) s->phase=USB_POWER_READY;
        else if (now-s->started_ms>s->config.startup_timeout_ms)
            return trip(s,USB_POWER_GATE_TIMEOUT);
        else return true;
    }
    if (!(s->sample.input1&USB_POWER_IN_PG) || !voltage_valid(s))
        return trip(s,USB_POWER_VOLTAGE);
    if (s->sample.upper_current_ma>s->config.startup_ceiling_ma)
        return trip(s,USB_POWER_OVERCURRENT);
    if (s->starting_port!=NO_PORT) {
        uint8_t port=s->starting_port;
        bool after=(int32_t)(s->sample.sample_ms-s->gate_started_ms)>=0 &&
                   s->sample.conversion_sequence!=s->gate_sequence;
        bool pg=port>1u || (s->sample.input1&(uint8_t)(USB_POWER_IN_PD1_PG<<port));
        if (after && pg) s->starting_port=NO_PORT;
        else if (now-s->gate_started_ms>s->config.gate_timeout_ms)
            return trip(s,USB_POWER_GATE_TIMEOUT);
        else return true;
    }
    static const uint8_t startup_order[]={EC_USB_J25,EC_USB_J12,EC_USB_J24,
                                         EC_USB_J22,EC_USB_J23,EC_USB_J21,EC_USB_J11};
    for (uint8_t order=0;order<EC_USB_PORT_COUNT;order++) {
        uint8_t port=startup_order[order];
        uint8_t bit=(uint8_t)(1u<<port);
        if (!(next.allowed_mask&bit) || (s->applied_mask&bit)) continue;
        uint16_t cost=ec_usb_port_reservation_ma((ec_usb_port_t)port,0);
        uint16_t peak=port<2u?s->config.pd_inrush_ma:s->config.branch_inrush_ma;
        if (peak<cost) peak=cost;
        uint32_t reserved=25u;
        for (uint8_t n=0;n<EC_USB_PORT_COUNT;n++)
            if (s->applied_mask&(1u<<n)) reserved+=ec_usb_port_reservation_ma((ec_usb_port_t)n,0);
        if (reserved+peak>s->config.startup_ceiling_ma ||
            (uint32_t)s->sample.upper_current_ma+peak>s->config.startup_ceiling_ma) continue;
        uint8_t mask=s->applied_mask|bit;
        if (!usb_power_hw_write((uint8_t)(1u|(mask<<1)))) return false;
        s->applied_mask=mask;s->starting_port=port;s->gate_started_ms=now;
        s->gate_sequence=s->sample.conversion_sequence;
        break; /* one gate per new measured conversion */
    }
    return true;
}
uint32_t usb_power_reservation_mw(const usb_power_state_t *s)
{
    return s?s->plan.reserved_input_power_mw:0u;
}
ec_host_usb_status_t usb_power_status(const usb_power_state_t *s,uint32_t now)
{
    ec_host_usb_status_t status={0};
    if (!s) return status;
    status.applied_mask=s->applied_mask;status.denied_mask=s->plan.denied_mask;
    status.phase=(uint8_t)(s->phase|((uint8_t)s->fault<<4));
    for (uint8_t n=0;n<2;n++) {
        if (!s->pd[n].valid) continue;
        status.pd_roles|=(uint8_t)(1u<<(n*4u));
        if (s->pd[n].connected) status.pd_roles|=(uint8_t)(2u<<(n*4u));
        if (s->pd[n].source) status.pd_roles|=(uint8_t)(4u<<(n*4u));
        if (s->pd[n].vconn_enabled) status.pd_roles|=(uint8_t)(8u<<(n*4u));
    }
    if (fresh(s,now)) {status.current_upper_ma=s->sample.upper_current_ma;status.voltage_mv=s->sample.voltage_mv;}
    status.reservation_mw=usb_power_reservation_mw(s);
    return status;
}
