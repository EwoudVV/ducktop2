#include "tusb.h"
#include <string.h>
static const tusb_desc_device_t device={.bLength=18,.bDescriptorType=TUSB_DESC_DEVICE,
 .bcdUSB=0x0200,.bMaxPacketSize0=64,.idVendor=0x1209,.idProduct=0x2329,.bcdDevice=0x0100,
 .iManufacturer=1,.iProduct=2,.iSerialNumber=0,.bNumConfigurations=1};
static const uint8_t report[]={0x06,0,0xff,0x09,1,0xa1,1,0x15,0,0x26,0xff,0,
 0x75,8,0x95,64,0x09,1,0x81,2,0x09,2,0xb1,2,0xc0};
static const uint8_t config[]={TUD_CONFIG_DESCRIPTOR(1,1,0,34,TUSB_DESC_CONFIG_ATT_SELF_POWERED,0),
 TUD_HID_DESCRIPTOR(0,0,HID_ITF_PROTOCOL_NONE,sizeof(report),0x81,64,10)};
uint8_t const *tud_descriptor_device_cb(void){return (const uint8_t*)&device;}
uint8_t const *tud_descriptor_configuration_cb(uint8_t index){return index?NULL:config;}
uint8_t const *tud_hid_descriptor_report_cb(uint8_t instance){return instance?NULL:report;}
uint16_t const *tud_descriptor_string_cb(uint8_t index,uint16_t language)
{
 (void)language;static uint16_t buffer[32];
 const char *text=index==1?"Duck Inds.":index==2?"Ducktop2 maker":NULL;
 if(index==0){buffer[0]=0x0304;buffer[1]=0x0409;return buffer;}
 if(!text)return NULL;
 size_t size=strlen(text);for(size_t i=0;i<size;i++)buffer[i+1]=(uint8_t)text[i];
 buffer[0]=(uint16_t)(0x0300|((size+1)*2));return buffer;
}
