#include "keyboard_rgb.h"
#include "keyboard_rgb_map.h"
#include "gpio.h"
#include "i2c.h"
#include <string.h>

enum stage { OFF, WAIT_POWER, RESET, CONFIGURE, LOAD_PWM, LOAD_SCALE, ENABLE, READY };
static enum stage stage;
static bool requested, fault;
static uint32_t powered_at;
static uint8_t pixels[KEYBOARD_RGB_CHANNELS], brightness, cursor;
static bool dirty[KEYBOARD_RGB_BANKS];

static bool write_reg(uint8_t reg, uint8_t value)
{
    return i2c1_write(KEYBOARD_RGB_ADDRESS,reg,value);
}

static bool page(uint8_t value)
{
    return write_reg(0xfeu,0xc5u) && write_reg(0xfdu,value);
}

static void stop_on_fault(void)
{
    fault=true;
    stage=OFF;
    gpio_set_keyboard_rgb_enable(false);
}

static bool send_bank(uint8_t bank, bool scaling)
{
    uint8_t bytes[19];
    bytes[0]=(uint8_t)(bank*18u+1u);
    for (unsigned i=0;i<18u;i++) {
        unsigned index=(unsigned)bank*18u+i;
        bytes[i+1u]=scaling ? (index<195u ? 255u : 0u) :
            (uint8_t)(((uint16_t)pixels[index]*brightness+127u)/255u);
    }
    return page(scaling?1u:0u) && i2c1_write_raw(KEYBOARD_RGB_ADDRESS,bytes,sizeof(bytes));
}

void keyboard_rgb_init(void)
{
    requested=fault=false;
    stage=OFF;
    brightness=64u;
    cursor=0u;
    memset(pixels,0,sizeof(pixels));
    memset(dirty,0,sizeof(dirty));
    keyboard_rgb_set_all(255u,255u,255u);
    gpio_set_keyboard_rgb_enable(false);
}

bool keyboard_rgb_request(bool enable, uint32_t now_ms)
{
    if (!enable) {
        requested=fault=false;
        stage=OFF;
        gpio_set_keyboard_rgb_enable(false);
        return true;
    }
    if (requested) return true;
    requested=true;
    fault=false;
    cursor=0u;
    powered_at=now_ms;
    stage=WAIT_POWER;
    gpio_set_keyboard_rgb_enable(true);
    return true;
}

bool keyboard_rgb_set_key(uint8_t index, uint8_t red, uint8_t green, uint8_t blue)
{
    if (index>=KEYBOARD_RGB_KEYS) return false;
    const uint8_t rgb[3]={red,green,blue};
    for (unsigned c=0;c<3u;c++) {
        unsigned channel=(unsigned)keyboard_rgb_map[index][c]-1u;
        if (pixels[channel]!=rgb[c]) {
            pixels[channel]=rgb[c];
            dirty[channel/18u]=true;
        }
    }
    return true;
}

void keyboard_rgb_set_all(uint8_t red, uint8_t green, uint8_t blue)
{
    for (uint8_t i=0;i<KEYBOARD_RGB_KEYS;i++)
        (void)keyboard_rgb_set_key(i,red,green,blue);
}

void keyboard_rgb_set_brightness(uint8_t value)
{
    if (brightness!=value) {
        brightness=value;
        for (unsigned i=0;i<KEYBOARD_RGB_BANKS;i++) dirty[i]=true;
    }
}

bool keyboard_rgb_ready(void) { return stage==READY && !fault; }
bool keyboard_rgb_faulted(void) { return fault; }

void keyboard_rgb_service(uint32_t now_ms)
{
    if (!requested || fault) return;
    if (!gpio_get_keyboard_rgb_fault_n()) { stop_on_fault(); return; }
    bool ok=true;
    switch (stage) {
    case WAIT_POWER:
        if ((uint32_t)(now_ms-powered_at)>=20u) stage=RESET;
        return;
    case RESET:
        ok=page(2u) && write_reg(0x2fu,0xaeu);
        powered_at=now_ms;
        stage=CONFIGURE;
        break;
    case CONFIGURE:
        if ((uint32_t)(now_ms-powered_at)<2u) return;
        /* Keep the matrix dark until every PWM/scaling register is written. */
        ok=page(2u) && write_reg(0x00u,0x08u) && write_reg(0x01u,0u);
        cursor=0u;
        stage=LOAD_PWM;
        break;
    case LOAD_PWM:
        ok=send_bank(cursor,false);
        dirty[cursor]=false;
        if (++cursor==KEYBOARD_RGB_BANKS) { cursor=0u; stage=LOAD_SCALE; }
        break;
    case LOAD_SCALE:
        ok=send_bank(cursor,true);
        if (++cursor==KEYBOARD_RGB_BANKS) { cursor=0u; stage=ENABLE; }
        break;
    case ENABLE: {
        uint8_t config=0u;
        ok=page(2u) && write_reg(0x02u,0x33u) && write_reg(0x25u,0u) &&
           write_reg(0x01u,255u) && write_reg(0x00u,0x09u) &&
           i2c1_read(KEYBOARD_RGB_ADDRESS,0x00u,&config,1u) && config==0x09u;
        stage=READY;
        break;
    }
    case READY:
        /* One bank per call keeps lighting traffic out of the power-control path. */
        for (unsigned n=0;n<KEYBOARD_RGB_BANKS;n++) {
            cursor=(uint8_t)((cursor+1u)%KEYBOARD_RGB_BANKS);
            if (dirty[cursor]) {
                ok=send_bank(cursor,false);
                dirty[cursor]=false;
                break;
            }
        }
        break;
    case OFF:
        return;
    }
    if (!ok) stop_on_fault();
}
