#include "audio.h"
#include "i2c.h"
static bool verified(uint8_t reg,uint8_t value,uint8_t mask)
{
    uint8_t actual;
    return i2c1_write(0x60,reg,value) && i2c1_read(0x60,reg,&actual,1) &&
           (actual&mask)==(value&mask);
}
bool audio_headphones(bool enable)
{
    /* TPA6130A2 tables 4/5. Set the volume muted before changing enables;
     * start at code 32 (-10.9 dB) and leave OS mixer control upstream. */
    if(!verified(2,0xe0,0xff)) return false;
    if(!verified(1,enable?0xc0:0x01,0xfdu)) return false;
    return !enable || verified(2,0x20,0xff);
}
