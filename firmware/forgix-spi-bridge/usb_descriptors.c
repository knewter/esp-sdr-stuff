#include "tusb.h"
#include <string.h>
#include "pico/unique_id.h"
static tusb_desc_device_t const device = {
 .bLength=sizeof(tusb_desc_device_t), .bDescriptorType=TUSB_DESC_DEVICE,
 .bcdUSB=0x0200, .bDeviceClass=TUSB_CLASS_MISC, .bDeviceSubClass=MISC_SUBCLASS_COMMON,
 .bDeviceProtocol=MISC_PROTOCOL_IAD, .bMaxPacketSize0=64,
 .idVendor=0xcafe, .idProduct=0x4012, .bcdDevice=0x0100,
 .iManufacturer=1, .iProduct=2, .iSerialNumber=3, .bNumConfigurations=1
};
uint8_t const *tud_descriptor_device_cb(void) { return (uint8_t const *)&device; }
static uint8_t const config[] = {
 TUD_CONFIG_DESCRIPTOR(1,2,0,TUD_CONFIG_DESC_LEN+TUD_CDC_DESC_LEN,0,100),
 TUD_CDC_DESCRIPTOR(0,0,0x81,8,0x02,0x82,64)
};
uint8_t const *tud_descriptor_configuration_cb(uint8_t index) { (void)index; return config; }
uint16_t const *tud_descriptor_string_cb(uint8_t index, uint16_t language) {
 (void)language;
 static uint16_t text[32];
 char const *strings[]={"", "Local diagnostic", "Forgix SPI RAM bridge v1"};
 unsigned length;
 if (!index) { text[1]=0x0409; length=1; }
 else {
  char serial[2*PICO_UNIQUE_BOARD_ID_SIZE_BYTES+1];const char *value;
  if(index==3){pico_get_unique_board_id_string(serial,sizeof(serial));value=serial;}
  else {if(index>=3)return NULL;value=strings[index];}
  length=strlen(value);if(length>31)length=31;
  for(unsigned i=0;i<length;i++)text[i+1]=(uint8_t)value[i];
 }
 text[0]=(uint16_t)((TUSB_DESC_STRING<<8)|(2*length+2)); return text;
}
