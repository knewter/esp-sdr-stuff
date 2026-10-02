/* Actual original common parser plus actual diagnostic receiver; no hardware. */
#define REGOBS_ACTUAL_SERIAL 1
#define main unused_receiver_fixture_main
#include "harness.c"
#undef main
#include "burst_serial.c"

static const char *rx_pending;
static size_t rx_remaining;
static unsigned baud_writes;
static bool fail_payload, data_header_sent, payload_prefix_sent;
static int uart_param_config(int port,const uart_config_t *cfg) { assert(!port && cfg->baud_rate==921600); return 0; }
static int uart_set_pin(int port,int tx,int rx,int rts,int cts) { assert(!port && tx==1 && rx==3 && rts==-1 && cts==-1); return 0; }
static int uart_driver_install(int port,int rx,int tx,int queue,void *handle,int flags) { (void)handle; assert(!port && rx==8192 && !tx && !queue && !flags); return 0; }
static int uart_flush_input(int port) { assert(!port); rx_pending=NULL; rx_remaining=0; return 0; }
static int uart_wait_tx_done(int port,int timeout) { assert(!port && timeout==1000); return 0; }
static int uart_set_baudrate(int port,unsigned baud) { assert(!port && baud==1000000); baud_writes++; return 0; }
static int uart_read_bytes(int port,void *bytes,size_t length,int timeout) {
    assert(!port && !timeout);
    if(!rx_remaining) return 0;
    size_t n=rx_remaining; if(n>length)n=length;
    memcpy(bytes,rx_pending,n); rx_pending+=n; rx_remaining-=n; return n;
}
static int uart_tx_chars(int port,const char *bytes,size_t length) {
    assert(!port && wire_used+length<sizeof(wire));
    if(fail_payload && data_header_sent) {
        if(payload_prefix_sent) return -1;
        assert(length>=17); length=17; payload_prefix_sent=true;
    }
    if(length>=5 && !memcmp(bytes,"DATA ",5)) data_header_sent=true;
    memcpy(wire+wire_used,bytes,length); wire_used+=length; return length;
}
static int submit_bytes(const char *text,size_t length) {
    char command_line[128];rx_pending=text;rx_remaining=length;
    int result;
    do {
        result=burst_serial_poll_line(command_line,sizeof(command_line));
        regobs_dispatch_status(result,command_line);
    } while(rx_remaining && !result);
    return result;
}
static int submit(const char *text) { return submit_bytes(text,strlen(text)); }
int main(int argc,char **argv) {
    assert(argc==2);unsigned which=(unsigned)strtoul(argv[1],NULL,10);assert(which<10);
    burst_serial_init();gain_max=72;
    assert(submit("INFO\n")==1);assert(submit("BAUD?\n")==0);
    char overlong[201];memset(overlong,'X',200);overlong[200]='\n';
    const char embedded[]="CAP20 16380 6\0trailing\n";
    if(which==0) {
        assert(submit("BAUD 1000000\n")==0);
        assert(baud_writes==1 && burst_serial_baud()==1000000 && regobs_state==REGOBS_NEW);
    } else if(which==5) {
        assert(submit_bytes(overlong,sizeof(overlong))==-1);
        assert(!triggers && regobs_state==REGOBS_NEW);
    } else if(which==8) {
        assert(submit_bytes(embedded,sizeof(embedded)-1)==1);
        assert(triggers==1 && regobs_state==REGOBS_NEW);
    } else {
        submit("FREQ 2401\n");submit("BANDWIDTH 20\n");submit("GAIN MANUAL 48\n");
        submit("REGOBS1 BEGIN 0123456789abcdef0123456789abcdef\n");assert(regobs_state==REGOBS_ARMED);
        if(which==6 || which==9) {
            fail_payload=true;assert(submit("CAP20 16380 6\n")==1);
            assert(regobs_wire_broken && triggers==1 && payload_prefix_sent);
            size_t prior=wire_used;
            if(which==6) assert(submit_bytes(overlong,sizeof(overlong))==-1);
            else assert(submit_bytes(embedded,sizeof(embedded)-1)==0);
            assert(wire_used==prior);
            fwrite(wire,1,wire_used,stdout);return 0;
        }
        if(which==4) assert(submit_bytes(overlong,sizeof(overlong))==-1);
        else if(which==7) assert(submit_bytes(embedded,sizeof(embedded)-1)==0);
        else {
            const char *bad=which==1 ? "BAUD?\n" : which==2 ? "BAUD 1000000\n" : "BAUD\n";
            assert(submit(bad)==0);
        }
        assert(!baud_writes && burst_serial_baud()==921600 && regobs_state==REGOBS_FAILED);
        unsigned writes=gain_writes;submit("CAP20 16380 6\n");assert(!triggers && gain_writes==writes);
    }
    fwrite(wire,1,wire_used,stdout);return 0;
}
