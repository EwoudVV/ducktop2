#include "ducktop2/ec/ec_usb_power.h"
#include <assert.h>
#include <stdio.h>
int main(void)
{
    ec_usb_power_config_t c = {true, 6000, 2100, 5239, 85};
    ec_usb_power_inputs_t in = {true, true, false, 127, 0, 0, 50000};
    ec_usb_power_plan_t p;
    /* These are independent literal port costs, including all five VCONN
     * ceilings. Seven VBUS maxima alone would incorrectly fit at 5500 mA. */
    const unsigned expected[] = {1215,1215,1175,1175,775,900,500};
    for (unsigned port=0;port<7;port++)
        assert(ec_usb_port_reservation_ma((ec_usb_port_t)port,0)==expected[port]);
    assert(ec_usb_port_reservation_ma(EC_USB_J21,1)==315);
    assert(ec_usb_port_reservation_ma(EC_USB_J11,2)==315);
    assert(ec_usb_power_plan(&c,&in,&p));
    assert(p.allowed_mask==0x2f); /* J21/J11/J22/J23/J24 */
    assert(p.denied_mask==0x50 && p.reserved_current_ma==5705);
    assert(p.reserved_input_power_mw==35163); /* ceil(5705*5239/0.85/1000) */
    in.retained_mask=1u<<EC_USB_J12;
    assert(ec_usb_power_plan(&c,&in,&p));
    assert(p.allowed_mask&(1u<<EC_USB_J12));
    assert(p.reserved_current_ma<=6000 && p.right_current_ma<=2100);
    in.available_input_power_mw=8000;in.retained_mask=0;
    assert(ec_usb_power_plan(&c,&in,&p));
    assert(p.allowed_mask==1 && p.reserved_current_ma==1240);
    in.pd_sink_only_mask=1;
    assert(ec_usb_power_plan(&c,&in,&p));
    assert(p.reserved_input_power_mw<=8000);
    in.host_lease_valid=false;
    assert(ec_usb_power_plan(&c,&in,&p) && p.allowed_mask==0);
    in.host_lease_valid=true;in.transfer_active=true;
    assert(ec_usb_power_plan(&c,&in,&p) && p.allowed_mask==0);
    in.transfer_active=false;c.qualified=false;
    assert(ec_usb_power_plan(&c,&in,&p) && p.allowed_mask==0);
    c.qualified=true;in.system_safe=false;
    assert(ec_usb_power_plan(&c,&in,&p) && p.allowed_mask==0);
    in.system_safe=true;in.requested_mask=128;
    assert(!ec_usb_power_plan(&c,&in,&p) && p.allowed_mask==0);
    in.requested_mask=127;c.minimum_efficiency_percent=0;
    assert(!ec_usb_power_plan(&c,&in,&p));
    c.minimum_efficiency_percent=85;c.rail_max_mv=5251;
    assert(!ec_usb_power_plan(&c,&in,&p));
    puts("USB power plan: PASS (literal VCONN reservations, total/remote/source limits, passive gates)");
}
