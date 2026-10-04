/* New input-only boundary; never included by existing firmware/build profiles. */
#include "rp_input.h"
#include "pico/stdlib.h"
#include "hardware/clocks.h"
#include "hardware/pio.h"
#include "hardware/watchdog.h"
#include "period.pio.h"
#define CS 1u
#define SCK 2u
#define DATA 3u
static PIO const owner=pio0;
static int sm=-1;
static unsigned offset;
static bool touched,loaded;
static bool (*cancel_fn)(void *);
static void *cancel_context;
static bool cancelled(void *ctx){(void)ctx;return cancel_fn(cancel_context);}
static uint64_t now(void *ctx){(void)ctx;return time_us_64();}
static bool late(uint64_t until){return cancelled(NULL)||time_us_64()>=until;}
static bool prepare(void *ctx,uint64_t until){
 (void)ctx;
 if(late(until)||clock_get_hz(clk_sys)!=150000000u||
    gpio_get_function(CS)!=GPIO_FUNC_SIO||gpio_get_dir(CS)!=GPIO_OUT||!gpio_get(CS)||
    gpio_get_function(SCK)!=GPIO_FUNC_SIO||gpio_get_dir(SCK)!=GPIO_OUT||
    gpio_get_function(DATA)!=GPIO_FUNC_SIO||gpio_get_dir(DATA)!=GPIO_IN)return false;
 touched=true;
 /* Reuse established config ownership; do not tristate/reinitialize CS. */
 gpio_put(SCK,0);gpio_disable_pulls(DATA);
 if(late(until)||gpio_get_dir(DATA)!=GPIO_IN||
    gpio_get_function(DATA)!=GPIO_FUNC_SIO)return false;
 if(!pio_can_add_program(owner,&forgix_clock_period_program))return false;
 sm=pio_claim_unused_sm(owner,false);if(sm<0)return false;
 offset=pio_add_program(owner,&forgix_clock_period_program);loaded=true;
 pio_sm_config c=forgix_clock_period_program_get_default_config(offset);
 sm_config_set_in_pins(&c,DATA);sm_config_set_jmp_pin(&c,DATA);
 sm_config_set_clkdiv_int_frac(&c,1,0);
 sm_config_set_fifo_join(&c,PIO_FIFO_JOIN_RX);
 if(pio_sm_init(owner,(unsigned)sm,offset,&c)!=PICO_OK)return false;
 /* No output/set/side-set pins and no instruction capable of changing DATA. */
 pio_sm_set_consecutive_pindirs(owner,(unsigned)sm,DATA,1,false);
 pio_gpio_init(owner,DATA);
 if(late(until)||gpio_get_function(DATA)!=GPIO_FUNC_PIO0||
    (owner->dbg_padoe&(1u<<DATA)))return false;
 busy_wait_us_32(100);return !late(until);
}
static bool start(void *ctx,uint64_t until){
 (void)ctx;if(sm<0||!loaded||late(until)||(owner->dbg_padoe&(1u<<DATA)))return false;
 gpio_put(CS,0);
 if(late(until))return false;
 pio_sm_set_enabled(owner,(unsigned)sm,true);return !late(until);
}
static bool ready(void *ctx){(void)ctx;return !pio_sm_is_rx_fifo_empty(owner,(unsigned)sm);}
static uint32_t take(void *ctx){(void)ctx;return pio_sm_get(owner,(unsigned)sm);}
static void service(void *ctx){(void)ctx;watchdog_update();}
static bool stop(void *ctx){
 (void)ctx;
 if(touched)gpio_put(CS,1); /* Raw inhibit before stopping or returning. */
 if(sm>=0){
  pio_sm_set_enabled(owner,(unsigned)sm,false);
  pio_sm_set_consecutive_pindirs(owner,(unsigned)sm,DATA,1,false);
  pio_sm_clear_fifos(owner,(unsigned)sm);
  if(loaded)pio_remove_program(owner,&forgix_clock_period_program,offset);
  pio_sm_unclaim(owner,(unsigned)sm);sm=-1;loaded=false;
 }
 if(touched){
  gpio_set_dir(DATA,GPIO_IN);gpio_set_function(DATA,GPIO_FUNC_SIO);
  busy_wait_us_32(100);
  return gpio_get(CS)&&gpio_get_dir(DATA)==GPIO_IN&&gpio_get_function(DATA)==GPIO_FUNC_SIO;
 }
 return true;
}
void observer_rp_io(observer_io *io,bool (*cancel)(void *),void *context){
 cancel_fn=cancel;cancel_context=context;
 *io=(observer_io){NULL,now,cancel?cancelled:NULL,prepare,start,ready,take,service,stop};
}
