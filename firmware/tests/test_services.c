#include "audio.h"
#include "ssd1306.h"
#include "i2c_mock.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
bool tca9548a_select_channel(uint8_t channel) { return channel<2; }
bool tca9548a_deselect_all(void) { return true; }
int main(void)
{
    i2c_mock_begin();
    assert(audio_headphones(true));
    assert(i2c_mock.regfile[1]==0xc0 && i2c_mock.regfile[2]==0x20);
    assert(audio_headphones(false));
    assert(i2c_mock.regfile[1]==1 && i2c_mock.regfile[2]==0xe0);
    i2c_mock.nack_all=true; assert(!audio_headphones(true));
    uint8_t line[130]; memset(line,0xa5,sizeof(line));
    ssd1306_render_line("A0 ",line+1);
    assert(line[0]==0xa5 && line[129]==0xa5);
    assert(line[1]==0x7e && line[6]==0 && line[7]==0x3e);
    for(unsigned i=13;i<129;i++) assert(line[i]==0);
    puts("services: PASS (audio gates/readback, OLED pixels/bounds)");
}
