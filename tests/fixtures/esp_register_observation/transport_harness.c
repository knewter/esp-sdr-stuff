/* Actual original common parser plus actual diagnostic receiver; no hardware. */
#define REGOBS_ACTUAL_SERIAL 1
#define main unused_receiver_fixture_main
#include "harness.c"
#undef main
#include "burst_serial.c"

static const char *rx_pending;
static unsigned baud_writes;
static int uart_param_config(int port,const uart_config_t *cfg) { assert(!port && cfg->baud_rate==921600); return 0; }
static int uart_set_pin(int port,int tx,int rx,int rts,int cts) { assert(!port && tx==1 && rx==3 && rts==-1 && cts==-1); return 0; }
static int uart_driver_install(int port,int rx,int tx,int queue,void *handle,int flags) { (void)handle; assert(!port && rx==8192 && !tx && !queue && !flags); return 0; }
static int uart_flush_input(int port) { assert(!port); rx_pending=NULL; return 0; }
static int uart_wait_tx_done(int port,int timeout) { assert(!port && timeout==1000); return 0; }
static int uart_set_baudrate(int port,unsigned baud) { assert(!port && baud==1000000); baud_writes++; return 0; }
static int uart_read_bytes(int port,void *bytes,size_t length,int timeout) {
    assert(!port && !timeout);
    if(!rx_pending || !*rx_pending) return 0;
    size_t n=strlen(rx_pending); if(n>length)n=length;
    memcpy(bytes,rx_pending,n); rx_pending+=n; return n;
}
static int uart_tx_chars(int port,const char *bytes,size_t length) {
    assert(!port && wire_used+length<sizeof(wire));
    memcpy(wire+wire_used,bytes,length); wire_used+=length; return length;
}
static int submit(const char *text) {
    char command_line[128];rx_pending=text;
    int result=burst_serial_poll_line(command_line,sizeof(command_line));
    if(result==1)command(command_line);
    return result;
}
int main(int argc,char **argv) {
    assert(argc==2);unsigned which=(unsigned)strtoul(argv[1],NULL,10);assert(which<4);
    burst_serial_init();gain_max=72;
    assert(submit("INFO\n")==1);assert(submit("BAUD?\n")==0);
    if(which==0) {
        assert(submit("BAUD 1000000\n")==0);
        assert(baud_writes==1 && burst_serial_baud()==1000000 && regobs_state==REGOBS_NEW);
    } else {
        submit("FREQ 2401\n");submit("BANDWIDTH 20\n");submit("GAIN MANUAL 48\n");
        submit("REGOBS1 BEGIN 0123456789abcdef0123456789abcdef\n");assert(regobs_state==REGOBS_ARMED);
        const char *bad=which==1 ? "BAUD?\n" : which==2 ? "BAUD 1000000\n" : "BAUD\n";
        assert(submit(bad)==0);assert(!baud_writes && burst_serial_baud()==921600 && regobs_state==REGOBS_FAILED);
        unsigned writes=gain_writes;submit("CAP20 16380 6\n");assert(!triggers && gain_writes==writes);
    }
    fwrite(wire,1,wire_used,stdout);return 0;
}
