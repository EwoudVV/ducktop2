#include "keyboard_rgb.h"
#include "keyboard_rgb_map.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

static uint8_t regs[3][256], selected_page;
static bool power_on, fault_n=true, nack, unlocked;
static unsigned transfers, pwm_written, scaling_written;

void gpio_set_keyboard_rgb_enable(bool enable) { power_on=enable; }
bool gpio_get_keyboard_rgb_fault_n(void) { return fault_n; }

bool i2c1_write(uint8_t address,uint8_t reg,uint8_t value)
{
    assert(address==0x2fu && power_on);
    ++transfers;
    if (nack) return false;
    if (reg==0xfeu) { unlocked=value==0xc5u; return true; }
    if (reg==0xfdu) { assert(unlocked && value<3u); selected_page=value; unlocked=false; return true; }
    if (selected_page==2u && reg==0x2fu) {
        assert(value==0xaeu);
        memset(regs,0,sizeof(regs)); selected_page=0u;
        pwm_written=scaling_written=0u;
        return true;
    }
    if (selected_page==2u && reg==0u && (value&1u)) {
        assert(pwm_written==198u && scaling_written==198u);
        assert(regs[2][1]==255u);
    }
    regs[selected_page][reg]=value;
    return true;
}

bool i2c1_write_raw(uint8_t address,uint8_t *data,uint16_t size)
{
    assert(address==0x2fu && power_on && size==19u && selected_page<2u);
    assert(data[0]>=1u && data[0]+17u<=198u);
    ++transfers;
    if (nack) return false;
    for (unsigned i=1;i<size;i++) regs[selected_page][data[0]+i-1u]=data[i];
    if (!(regs[2][0]&1u)) {
        if (selected_page==0u) pwm_written+=18u;
        else scaling_written+=18u;
    }
    return true;
}

bool i2c1_read(uint8_t address,uint8_t reg,uint8_t *data,uint16_t size)
{
    assert(address==0x2fu && power_on && size==1u);
    ++transfers;
    if (nack) return false;
    *data=regs[selected_page][reg];
    return true;
}

static void run_until_ready(uint32_t start)
{
    for (unsigned i=0;i<80u && !keyboard_rgb_ready();i++)
        keyboard_rgb_service(start+i*20u);
    assert(keyboard_rgb_ready());
}

int main(void)
{
    bool channels[198]={false};
    for (unsigned key=0;key<65u;key++) for (unsigned color=0;color<3u;color++) {
        unsigned reg=keyboard_rgb_map[key][color];
        assert(reg>=1u && reg<=195u && !channels[reg-1u]);
        channels[reg-1u]=true;
    }
    assert(keyboard_rgb_map[0][0]==1u);
    assert(keyboard_rgb_map[27][0]==43u); /* reversed second physical row */
    keyboard_rgb_init();
    assert(!power_on && !keyboard_rgb_ready());
    keyboard_rgb_service(1000u); assert(transfers==0u);
    assert(!keyboard_rgb_set_key(65u,1u,2u,3u));
    assert(keyboard_rgb_request(true,100u));
    keyboard_rgb_service(119u); assert(transfers==0u);
    run_until_ready(120u);
    assert(regs[2][0]==0x09u && power_on);
    for (unsigned reg=1;reg<=195u;reg++) assert(regs[0][reg]==64u && regs[1][reg]==255u);
    for (unsigned reg=196;reg<=198u;reg++) assert(regs[0][reg]==0u && regs[1][reg]==0u);
    keyboard_rgb_set_brightness(255u);
    keyboard_rgb_set_all(0u,0u,0u);
    assert(keyboard_rgb_set_key(0u,10u,20u,30u));
    for (unsigned i=0;i<11u;i++) keyboard_rgb_service(2000u+i*20u);
    assert(regs[0][1]==10u && regs[0][2]==20u && regs[0][3]==30u);
    for (unsigned reg=4;reg<=198u;reg++) assert(regs[0][reg]==0u);
    unsigned before=transfers; keyboard_rgb_service(3000u); assert(transfers==before);
    nack=true; keyboard_rgb_set_all(255u,0u,0u); keyboard_rgb_service(3020u);
    assert(keyboard_rgb_faulted() && !power_on && !keyboard_rgb_ready());
    before=transfers; keyboard_rgb_request(true,3040u); keyboard_rgb_service(4000u);
    assert(!power_on && transfers==before);
    keyboard_rgb_request(false,4000u); nack=false;
    keyboard_rgb_request(true,0xfffffff0u); run_until_ready(4u);
    fault_n=false; keyboard_rgb_service(2000u); assert(!power_on && keyboard_rgb_faulted());
    keyboard_rgb_request(false,2001u); assert(!keyboard_rgb_faulted());
    puts("keyboard RGB startup, mapping, updates, fault latch and timer wrap passed");
    return 0;
}
