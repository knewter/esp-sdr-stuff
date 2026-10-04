/* Offline candidate: no flash writer; physical admission separate. */
#include "pico/stdlib.h"
#include "hardware/clocks.h"
#include "hardware/pio.h"
#include "hardware/watchdog.h"
#include "tusb.h"
#include "wire.pio.h"
#include "protocol.h"
#include "build_identity.h"
#include <string.h>
#ifdef BRIDGE_EMBEDDED_CONFIG
#include "config.h"
static bool configuration_attempted,configuration_ready;
#endif
#define CS 1u
#define SCK 2u
#define DATA 3u
#define DONE 5u
#define CLOCK_ENABLE 19u
#define MAX_LIFETIME_US UINT64_C(120000000)
#define TRANSACTION_US UINT64_C(20000)
#ifdef BRIDGE_EMBEDDED_CONFIG
const char diagnostic_profile[] = "FORGIX_SPI_CONFIG_RAM_V1;no_flash;rp2350-arm;heap0;stack4096;max120s;sdk2.2.0;tinyusb86ad6e56";
#else
const char diagnostic_profile[] = "FORGIX_SPI_RAM_V1;no_flash;rp2350-arm;heap0;stack4096;max120s;sdk2.2.0;tinyusb86ad6e56";
#endif
static PIO const wire_pio=pio0;
static unsigned sm,tx_offset,rx_offset;
static bool pins_ready;
static uint64_t lifetime_until;
static uint8_t input[BRIDGE_REQUEST_BYTES],output[BRIDGE_RESPONSE_BYTES];
static bool expired(uint64_t until) { return time_us_64()>=until; }
static void wire_end(void) {
 if(!pins_ready)return;
 gpio_put(CS,1); /* Raw CS first: inhibit FPGA before changing the PIO clock/OE. */
 pio_sm_set_enabled(wire_pio,sm,false);
 pio_sm_set_consecutive_pindirs(wire_pio,sm,DATA,1,false);
 pio_sm_set_pins_with_mask(wire_pio,sm,0,1u<<SCK);
 busy_wait_us_32(100); /* No data reacquisition until a fresh qualified idle. */
}
static unsigned wire_prepare(uint64_t arm_until) {
 if(expired(arm_until))return BRIDGE_TIMEOUT;
#ifdef BRIDGE_EMBEDDED_CONFIG
 if(!configuration_ready)return BRIDGE_REFUSED;
#endif
 if(clock_get_hz(clk_sys)!=150000000)return BRIDGE_CLOCK_MISMATCH;
 gpio_init(CS);gpio_put(CS,1);gpio_set_dir(CS,GPIO_OUT);
 gpio_init(SCK);gpio_put(SCK,0);gpio_set_dir(SCK,GPIO_OUT);
 gpio_init(DATA);gpio_disable_pulls(DATA);gpio_set_dir(DATA,GPIO_IN);
 gpio_init(DONE);gpio_disable_pulls(DONE);gpio_set_dir(DONE,GPIO_IN);
 gpio_init(CLOCK_ENABLE);gpio_put(CLOCK_ENABLE,1);gpio_set_dir(CLOCK_ENABLE,GPIO_OUT);
 busy_wait_us_32(100);
 if(!gpio_get(DONE))return BRIDGE_NOT_DONE;
 sm=(unsigned)pio_claim_unused_sm(wire_pio,true);
 tx_offset=pio_add_program(wire_pio,&forgix_request_program);
 rx_offset=pio_add_program(wire_pio,&forgix_response_program);
 pio_sm_set_consecutive_pindirs(wire_pio,sm,DATA,1,false);
 pio_sm_set_consecutive_pindirs(wire_pio,sm,SCK,1,true);
 pio_sm_set_pins_with_mask(wire_pio,sm,0,1u<<SCK);
 pio_gpio_init(wire_pio,DATA);pio_gpio_init(wire_pio,SCK);
 pins_ready=true;wire_end();return BRIDGE_OK;
}
static pio_sm_config wire_config(bool transmit) {
 pio_sm_config c=transmit?forgix_request_program_get_default_config(tx_offset):forgix_response_program_get_default_config(rx_offset);
 sm_config_set_sideset_pins(&c,SCK);sm_config_set_set_pins(&c,DATA,1);
 sm_config_set_out_pins(&c,DATA,1);sm_config_set_in_pins(&c,DATA);
 sm_config_set_out_shift(&c,false,transmit,32);sm_config_set_in_shift(&c,false,!transmit,32);
 sm_config_set_clkdiv_int_frac(&c,4,176); /* 150 MHz / 4.6875 = nominal 32 MHz. */
 if(transmit)sm_config_set_fifo_join(&c,PIO_FIFO_JOIN_TX);
 return c;
}
unsigned bridge_spi_transaction(const bridge_request *r,uint32_t *value) {
 uint8_t request[9],response[64];unsigned count=bridge_wire_request(r,request),status=BRIDGE_TIMEOUT;
 if(!count||!pins_ready)return BRIDGE_REFUSED;
 uint64_t until=time_us_64()+TRANSACTION_US;
 if(lifetime_until<until)until=lifetime_until;
 if(expired(until))return BRIDGE_TIMEOUT;
 wire_end();pio_sm_config c=wire_config(true);
 if(pio_sm_init(wire_pio,sm,tx_offset,&c)!=PICO_OK){wire_end();return BRIDGE_REFUSED;}
 pio_interrupt_clear(wire_pio,0);pio_interrupt_clear(wire_pio,1);
 pio_sm_set_consecutive_pindirs(wire_pio,sm,DATA,1,true);
 /* All request words are queued before CS assertion: no CPU-paced final bit. */
 pio_sm_put(wire_pio,sm,count*8-1);
 for(unsigned i=0;i<count;i+=4){
  uint32_t word=0;for(unsigned j=0;j<4;j++)word=(word<<8)|((i+j<count)?request[i+j]:0);
  pio_sm_put(wire_pio,sm,word);
 }
 if(expired(until))goto finished;
 gpio_put(CS,0);busy_wait_us_32(10);
 if(expired(until))goto finished;
 pio_sm_set_enabled(wire_pio,sm,true);
 while(!pio_interrupt_get(wire_pio,0))if(expired(until))goto finished;
 if(expired(until))goto finished; /* Ready IRQ does not waive an expired deadline. */
 /* PIO has already released DATA and completed its fixed high-clock guard. */
 pio_sm_set_enabled(wire_pio,sm,false);c=wire_config(false);
 if(expired(until))goto finished;
 if(pio_sm_init(wire_pio,sm,rx_offset,&c)!=PICO_OK){status=BRIDGE_REFUSED;goto finished;}
 if(expired(until))goto finished;
 pio_sm_set_enabled(wire_pio,sm,true);
 for(unsigned i=0;i<16;i++){
  while(pio_sm_is_rx_fifo_empty(wire_pio,sm))if(expired(until))goto finished;
  if(expired(until))goto finished;
  uint32_t word=pio_sm_get(wire_pio,sm);
  for(unsigned j=0;j<4;j++)response[i*4+j]=(uint8_t)(word>>(24-8*j));
 }
 while(!pio_interrupt_get(wire_pio,1))if(expired(until))goto finished;
 if(expired(until))goto finished;
 status=bridge_wire_response(r->op==BRIDGE_WRITE,response,value);
finished:
 wire_end();return expired(until)?BRIDGE_TIMEOUT:status;
}
int main(void) {
 uint64_t boot=time_us_64(),finish=0;watchdog_enable(2000,false);
 lifetime_until=boot+MAX_LIFETIME_US;
 if(diagnostic_profile[0]!='F'||!tud_init(0)){watchdog_reboot(0,0,1);while(true)tight_loop_contents();}
 unsigned length=0,pending=0,offset=0;bridge_session session={0};
 while(time_us_64()-boot<MAX_LIFETIME_US){
  tud_task();watchdog_update();uint64_t now=time_us_64();
  if(finish&&now>=finish)break;
  if(!finish&&!pending&&tud_cdc_available()){
   length+=tud_cdc_read(input+length,BRIDGE_REQUEST_BYTES-length);
   if(length==BRIDGE_REQUEST_BYTES){
#ifdef BRIDGE_EMBEDDED_CONFIG
    uint32_t config_nonce;
    if(bridge_config_match(input,&config_nonce)){
     length=0;
     if(!bridge_config_admit(&configuration_attempted,session.attempted,time_us_64()-boot))continue;
     uint64_t until=time_us_64()+UINT64_C(20000000);
     if(boot+UINT64_C(30000000)<until)until=boot+UINT64_C(30000000);
     unsigned config_status=bridge_configure(until);
     configuration_ready=config_status==BRIDGE_OK;
     bridge_config_reply(output,config_nonce,config_status,time_us_64(),BUILD_SOURCE_SHA256);
     pending=BRIDGE_RESPONSE_BYTES;offset=0;continue;
    }
#endif
    bridge_request r;length=0;
    if(!bridge_parse(input,&r))continue; /* Damaged framing never causes GPIO work. */
    unsigned status=BRIDGE_REFUSED;uint32_t value=0;
    unsigned admission=bridge_admit(&session,&r,time_us_64()-boot);
    if(admission==BRIDGE_START)status=wire_prepare(boot+UINT64_C(30000000));
    else if(admission==BRIDGE_COMMAND){
     if(r.op==BRIDGE_FINISH){wire_end();status=BRIDGE_OK;finish=time_us_64()+UINT64_C(1000000);}
     else if(r.op==BRIDGE_READ||r.op==BRIDGE_WRITE)status=bridge_spi_transaction(&r,&value);
    }else if(admission==BRIDGE_INERT)continue;
    bridge_response(output,&r,status,value,time_us_64(),BUILD_SOURCE_SHA256);pending=BRIDGE_RESPONSE_BYTES;offset=0;
   }
  }
  if(pending&&tud_cdc_write_available()){
   unsigned n=tud_cdc_write(output+offset,pending);offset+=n;pending-=n;tud_cdc_write_flush();
  }
 }
 wire_end();watchdog_reboot(0,0,1);while(true)tight_loop_contents();
}
