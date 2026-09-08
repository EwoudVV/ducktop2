#include "ssd1306.h"
#include "i2c.h"
#include <string.h>

/* Five columns, seven rows. Lowercase uses the uppercase glyph. */
static const uint8_t letters[26][5]={
 {0x7e,9,9,9,0x7e},{0x7f,0x49,0x49,0x49,0x36},{0x3e,0x41,0x41,0x41,0x22},
 {0x7f,0x41,0x41,0x22,0x1c},{0x7f,0x49,0x49,0x49,0x41},{0x7f,9,9,9,1},
 {0x3e,0x41,0x49,0x49,0x7a},{0x7f,8,8,8,0x7f},{0x41,0x41,0x7f,0x41,0x41},
 {0x20,0x40,0x41,0x3f,1},{0x7f,8,0x14,0x22,0x41},{0x7f,0x40,0x40,0x40,0x40},
 {0x7f,2,0xc,2,0x7f},{0x7f,4,8,0x10,0x7f},{0x3e,0x41,0x41,0x41,0x3e},
 {0x7f,9,9,9,6},{0x3e,0x41,0x51,0x21,0x5e},{0x7f,9,0x19,0x29,0x46},
 {0x26,0x49,0x49,0x49,0x32},{1,1,0x7f,1,1},{0x3f,0x40,0x40,0x40,0x3f},
 {0x1f,0x20,0x40,0x20,0x1f},{0x3f,0x40,0x30,0x40,0x3f},
 {0x63,0x14,8,0x14,0x63},{7,8,0x70,8,7},{0x61,0x51,0x49,0x45,0x43}};
static const uint8_t digits[10][5]={
 {0x3e,0x51,0x49,0x45,0x3e},{0,0x42,0x7f,0x40,0},{0x62,0x51,0x49,0x49,0x46},
 {0x22,0x41,0x49,0x49,0x36},{0x18,0x14,0x12,0x7f,0x10},{0x27,0x45,0x45,0x45,0x39},
 {0x3c,0x4a,0x49,0x49,0x30},{1,0x71,9,5,3},{0x36,0x49,0x49,0x49,0x36},{6,0x49,0x49,0x29,0x1e}};
void ssd1306_render_line(const char *text,uint8_t page[128])
{
    memset(page,0,128);
    if (!text) return;
    for (unsigned pos=0;pos<21 && text[pos];pos++) {
        unsigned char c=(unsigned char)text[pos];
        if(c>='a' && c<='z') c-=32;
        uint8_t *out=page+pos*6;
        if(c>='A' && c<='Z') memcpy(out,letters[c-'A'],5);
        else if(c>='0' && c<='9') memcpy(out,digits[c-'0'],5);
        else if(c=='-') memset(out,8,5);
        else if(c=='.') out[2]=0x40;
        else if(c==':') out[2]=0x24;
        else if(c=='/') {out[0]=0x60;out[1]=0x10;out[2]=8;out[3]=4;out[4]=3;}
        else if(c=='%') {out[0]=0x63;out[1]=0x13;out[2]=8;out[3]=0x64;out[4]=0x63;}
        else if(c!=' ') {out[0]=2;out[1]=1;out[2]=0x59;out[3]=9;out[4]=6;}
    }
}
static void number(char *line,const char *label,int32_t value,const char *unit,bool valid)
{
    unsigned at=0;
    while(*label && at<21) line[at++]=*label++;
    if(!valid) {for(unsigned i=0;i<2 && at<21;i++) line[at++]='-';}
    else {
        uint32_t magnitude=value<0 ? 0u-(uint32_t)value : (uint32_t)value;
        if(value<0 && at<21) line[at++]='-';
        char reverse[10];unsigned count=0;
        do {reverse[count++]=(char)('0'+magnitude%10);magnitude/=10;}while(magnitude && count<10);
        while(count && at<21) line[at++]=reverse[--count];
    }
    while(*unit && at<21) line[at++]=*unit++;
    line[at]=0;
}
void ssd1306_status_step(const ec_telemetry_snapshot_t *t,uint16_t flags,uint16_t fault,
                         uint16_t rpm,uint8_t duty,int16_t skin,int16_t mu,uint32_t now)
{
    static bool ready[2]; static uint8_t next; static uint32_t due;
    if((int32_t)(now-due)<0) return;
    due=now+20; uint8_t channel=next/8, page=next%8;
    next=(uint8_t)((next+1)%16);
    if(!tca9548a_select_channel(channel)) {ready[channel]=false;tca9548a_deselect_all();return;}
    if(!ready[channel]) {
        /* SSD1306 128x64 with internal charge pump. Module identity still
         * needs the assembly check; the address alone cannot identify it. */
        uint8_t init[]={0,0xae,0xd5,0x80,0xa8,0x3f,0xd3,0,0x40,0x8d,0x14,
                         0x20,2,0xa1,0xc8,0xda,0x12,0x81,0x40,0xd9,0xf1,0xdb,0x40,0xa4,0xa6,0xaf};
        ready[channel]=i2c1_write_raw(0x3c,init,sizeof(init));
        tca9548a_deselect_all();return;
    }
    char line[22];
    if(channel==0) {
        switch(page) {
        case 0: number(line,"SOURCE ",t->active_input,"",t->valid_flags&EC_TELEMETRY_VALID_ACTIVE_INPUT); break;
        case 1: number(line,"BAT ",t->soc_percent,"%",t->valid_flags&EC_TELEMETRY_VALID_SOC); break;
        case 2: number(line,"PACK ",t->pack_voltage_mv,"MV",t->valid_flags&EC_TELEMETRY_VALID_PACK_VOLTAGE); break;
        case 3: number(line,"CURRENT ",t->pack_current_ma,"MA",t->valid_flags&EC_TELEMETRY_VALID_PACK_CURRENT); break;
        case 4: number(line,"LEFT ",(int32_t)t->remaining_capacity_mah,"MAH",t->valid_flags&EC_TELEMETRY_VALID_REMAINING_CAPACITY); break;
        case 5: number(line,"FULL ",(int32_t)t->full_capacity_mah,"MAH",t->valid_flags&EC_TELEMETRY_VALID_FULL_CAPACITY); break;
        case 6: number(line,"TO EMPTY ",(int32_t)t->time_to_empty_s,"S",t->valid_flags&EC_TELEMETRY_VALID_TIME_TO_EMPTY); break;
        default: number(line,"CHARGING ",(flags&64)!=0,"",true); break;
        }
    } else {
        switch(page) {
        case 0: number(line,"FAN ",rpm,"RPM",true); break;
        case 1: number(line,"DUTY ",duty,"%",true); break;
        case 2: number(line,"SKIN ",skin,"DECIC",skin!=-32768); break;
        case 3: number(line,"MU ",mu,"DECIC",mu!=-32768); break;
        case 4: number(line,"LID CLOSED ",(flags&2)!=0,"",true); break;
        case 5: number(line,"HEADPHONES ",(flags&8)!=0,"",true); break;
        case 6: number(line,"FAULT ",fault,"",true); break;
        default: number(line,"HOST LIMIT ",(flags&128)!=0,"",true); break;
        }
    }
    uint8_t command[]={0,(uint8_t)(0xb0|page),0,0x10}, pixels[129]; pixels[0]=0x40;
    ssd1306_render_line(line,pixels+1);
    ready[channel]=i2c1_write_raw(0x3c,command,sizeof(command)) && i2c1_write_raw(0x3c,pixels,sizeof(pixels));
    tca9548a_deselect_all();
}
