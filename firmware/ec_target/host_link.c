#include "host_link.h"
#include <string.h>

static uint32_t generation, acknowledged_generation, desired_mw, received_at, lease_ms;
static bool usb_clear_pending;
static uint32_t previous_requests;
static ec_host_usb_status_t usb_status;
static ec_host_state_t state;
static uint8_t report[EC_HOST_REPORT_BYTES];
static void put16(uint8_t *p, uint16_t v) { p[0]=(uint8_t)v; p[1]=(uint8_t)(v>>8); }
static void put32(uint8_t *p, uint32_t v) { put16(p,(uint16_t)v); put16(p+2,(uint16_t)(v>>16)); }
static uint32_t get32(const uint8_t *p) { return (uint32_t)p[0] | ((uint32_t)p[1]<<8) | ((uint32_t)p[2]<<16) | ((uint32_t)p[3]<<24); }
void ec_host_init(void)
{
    generation=1; desired_mw=received_at=lease_ms=acknowledged_generation=0;
    usb_clear_pending=false; previous_requests=0;
    memset(&usb_status,0,sizeof(usb_status));
    memset(&state,0,sizeof(state)); memset(report,0,sizeof(report));
}
bool ec_host_request_budget(uint32_t mw)
{
    if (mw != desired_mw) {
        desired_mw=mw; ++generation;
        if (!generation) generation=1;
        if (!mw || state.budget_mw>mw) state.valid=false;
    }
    /* Acknowledges delivery to the local mailbox only. Applied state is
     * independently reported by ec_host_state after a matching host reply. */
    return true;
}
void ec_host_receive(const uint8_t *p, uint16_t size, uint32_t now_ms)
{
    if (!p || size != EC_HOST_REPORT_BYTES || memcmp(p,"DT2\1",4) ||
        get32(p+4) != generation) return;
    uint32_t applied=get32(p+8), mu=get32(p+12), aux=get32(p+16), ttl=get32(p+24);
    if (!desired_mw || !applied || applied>desired_mw || mu>applied ||
        aux>100000u || ttl<250u || ttl>5000u || (get32(p+20) & ~255u) || (p[28]&~127u)) return;
    for (unsigned i=29;i<EC_HOST_REPORT_BYTES;i++) if (p[i]) return;
    state.valid=true; state.budget_mw=applied; state.estimated_mu_mw=mu;
    state.estimated_aux_mw=aux; state.requests=get32(p+20);
    state.usb_requested_mask=p[28]; acknowledged_generation=generation;
    if ((state.requests & EC_HOST_REQUEST_USB_CLEAR) &&
        !(previous_requests & EC_HOST_REQUEST_USB_CLEAR)) usb_clear_pending=true;
    previous_requests=state.requests;
    received_at=now_ms; lease_ms=ttl;
}
ec_host_state_t ec_host_state(uint32_t now_ms)
{
    if (state.valid && now_ms-received_at>=lease_ms) state.valid=false;
    return state;
}
bool ec_host_take_usb_clear(uint32_t now_ms)
{
    bool take=usb_clear_pending && ec_host_state(now_ms).valid;
    usb_clear_pending=false;
    return take;
}
void ec_host_publish_usb(const ec_host_usb_status_t *status)
{
    if (status) usb_status=*status;
}
void ec_host_publish(const ec_telemetry_snapshot_t *t, const ec_battery_report_t *b,
                      uint16_t flags,uint16_t fault,uint16_t rpm,uint32_t now_ms)
{
    memset(report,0,sizeof(report)); memcpy(report,"DT2\1",4);
    put32(report+4,generation); put16(report+8,t->valid_flags); put16(report+10,flags);
    report[12]=b->soc_percent; report[13]=(uint8_t)b->state;
    put16(report+14,b->voltage_mv); put32(report+16,(uint32_t)b->current_ma);
    put32(report+20,t->remaining_capacity_mah); put32(report+24,t->full_capacity_mah);
    put32(report+28,b->time_to_empty_s); put32(report+32,b->time_to_full_s);
    put32(report+36,desired_mw); put32(report+40,ec_host_state(now_ms).valid?acknowledged_generation:0u);
    put16(report+44,fault); put16(report+46,rpm); put32(report+48,now_ms);
    report[52]=usb_status.applied_mask; report[53]=usb_status.denied_mask;
    report[54]=usb_status.phase; report[55]=usb_status.pd_roles;
    put16(report+56,usb_status.current_upper_ma); put16(report+58,usb_status.voltage_mv);
    put32(report+60,usb_status.reservation_mw);
}
const uint8_t *ec_host_report(void) { return report; }
