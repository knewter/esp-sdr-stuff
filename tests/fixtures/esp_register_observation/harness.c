/* Offline synthetic MMIO fixture. Includes the generated receiver unchanged;
 * acquire_iq, capture, apply_gain and command are not replaced by test stubs. */
#define REGOBS_HOST_TEST 1
#include "receiver.c"

static unsigned mode, gain_writes, triggers, rx_reads, filter_writes;
#ifndef REGOBS_ACTUAL_SERIAL
static unsigned sends;
#endif
static uint32_t control, status, byte_map = 0xdeadbeef, owner = 0xa5a50100;
static uint32_t gain_word = (72u << 8) | 0x12;
static unsigned filter[2] = {0x91,0xc2};
static int64_t now_us;
static uint8_t wire[1000000];
static size_t wire_used;
static unsigned trace[30000], trace_used;
enum { SUCCESS, VARIANT, TIMEOUT, WRONG_COUNT, MISSING_SAMPLE, EXTRA_SAMPLE,
       FAIL_HEADER, FAIL_PAYLOAD, FAIL_RECEIPT, DEADLINE, EARLY_END, BAD_NONCE,
       REAPPLY, OVERFLOW, CONFIG_MISMATCH, UNARMED, EXCESS, CAPTURE_DEADLINE };

static void event(unsigned code) { assert(trace_used < 30000); trace[trace_used++] = code; }
static uint32_t mmio_read(unsigned reg) {
    if (reg == RX_GAIN) {
        rx_reads++; event(100);
        if (mode == VARIANT && regobs_state == REGOBS_ARMED) {
            unsigned stage = regobs_used ? (regobs_used-1)%4+1 : 0;
            unsigned selectors[] = {48,48,47,46,45};
            return (gain_word & 0x7fffff) | (selectors[stage] << 24) | (stage == 2 ? 0 : BIT(23));
        }
        return gain_word;
    }
    if (reg == DUMP_CTRL) return control;
    if (reg == DUMP_STATUS) return status;
    if (reg == DUMP_BYTES) return byte_map;
    assert(reg == DPORT_IRAM_DRAM_AHB_SEL_REG); return owner;
}
static void mmio_write(unsigned reg, uint32_t value) {
    if (reg == RX_GAIN) { event(101); gain_writes++; gain_word=value; return; }
    if (reg == DPORT_IRAM_DRAM_AHB_SEL_REG) { event(200); owner=value; return; }
    if (reg == DUMP_BYTES) { event(201); byte_map=value; return; }
    assert(reg == DUMP_CTRL); event(202); control=value;
    if ((value & BIT(19)) && !(value & BIT(18))) {
        event(203); triggers++;
        if (mode == TIMEOUT) { status=0; return; }
        unsigned n=value & 0x7fff;
        for (unsigned j=0;j<n;j++) test_samples[j]=((j*7 & 1023) << 10) | (j*3 & 1023);
        if (mode == MISSING_SAMPLE) test_samples[12]=SENTINEL;
        if (mode == EXTRA_SAMPLE) test_samples[n]=0;
        status=mode == WRONG_COUNT ? n-1 : n;
        control |= BIT(18);
        if (mode == CAPTURE_DEADLINE) now_us=regobs_deadline_us;
    }
}
static int64_t esp_timer_get_time(void) { now_us += mode == TIMEOUT ? 1000 : 1; return now_us; }
static void esp_rom_delay_us(unsigned us) { now_us += us; }
static void vTaskDelay(unsigned ticks) { now_us += 1000*ticks; }
unsigned rom_chip_i2c_readReg(unsigned block,unsigned host,unsigned reg) {
    assert(block == 0x67 && host == 1 && (reg == 1 || reg == 2)); event(300+reg); return filter[reg-1];
}
void rom_chip_i2c_writeReg(unsigned block,unsigned host,unsigned reg,unsigned value) {
    assert(block == 0x67 && host == 1 && (reg == 1 || reg == 2));
    event(310+reg); filter_writes++; filter[reg-1]=value;
}
void rom_pbus_workmode(void) { event(400); }
void rom_pbus_xpd_rx_on(int n) { assert(n == 1); event(401); }
void rom_pbus_xpd_tx_off(void) { event(402); }
void rom_set_rxclk_en(int n) { assert(n == 1); event(403); }
void set_chanfreq(unsigned mhz,unsigned mode_value) { assert(mhz==2412 && !mode_value); event(404); }
void rom_set_rf_freq_offset(unsigned crystal,unsigned mhz,int offset) { assert(!crystal && mhz==2401 && !offset); event(405); }
static uint32_t esp_rom_crc32_le(uint32_t initial,const uint8_t *bytes,unsigned length) {
    uint32_t crc=~initial;
    for(unsigned i=0;i<length;i++) {
        crc^=bytes[i];
        for(unsigned bit=0;bit<8;bit++) crc=(crc >> 1)^((crc & 1) ? 0xedb88320 : 0);
    }
    return ~crc;
}
#ifndef REGOBS_ACTUAL_SERIAL
static bool burst_serial_send(const void *data,size_t size) {
    assert(!control); assert(owner==0xa5a50100 && byte_map==0xdeadbeef);
    assert(filter[0]==0x91 && filter[1]==0xc2); event(500); sends++;
    bool failure=(mode==FAIL_HEADER && size>=5 && !memcmp(data,"DATA ",5)) ||
        (mode==FAIL_PAYLOAD && size==40950) ||
        (mode==FAIL_RECEIPT && size>40 && !memcmp(data,"REGOBS1 ",8) && strstr(data,"\"kind\":\"capture\""));
    size_t copied=failure ? (size < 17 ? size : 17) : size;
    assert(wire_used+copied <= sizeof(wire)); memcpy(wire+wire_used,data,copied); wire_used+=copied;
    now_us+=(int64_t)copied*10000000/921600;
    return !failure;
}
#endif

int main(int argc,char **argv) {
    assert(argc==2); mode=(unsigned)strtoul(argv[1],NULL,10); assert(mode<=CAPTURE_DEADLINE);
    assert(esp_rom_crc32_le(0,(const uint8_t *)"123456789",9)==0xcbf43926);
    gain_max=72;
    command("INFO");
    command("FREQ 2401"); command("BANDWIDTH 20"); command("GAIN MANUAL 48");
    assert(gain_writes==2 && gain_code==48 && rx_filter==64);
    assert((gain_word >> 24)==48 && (gain_word & BIT(23)));
    assert((gain_word & 0x7fffff)==((72u << 8)|0x12));
    unsigned before_writes=gain_writes, before_reads=rx_reads, before_trace=trace_used;
    if (mode==UNARMED) {
        command("CAP20 16380 6"); assert(regobs_used==0);
    } else {
        if(mode==CONFIG_MISMATCH) frequency_mhz=2412;
        command("REGOBS1 BEGIN 0123456789abcdef0123456789abcdef");
        if (mode==CONFIG_MISMATCH) assert(regobs_state==REGOBS_FAILED && !triggers);
        else {
            assert(regobs_state==REGOBS_ARMED && regobs_used==1);
            if(mode==DEADLINE) now_us=regobs_deadline_us;
            if(mode==OVERFLOW) {
                regobs_used=REGOBS_LIMIT;regobs_in_capture=true;
                unsigned prior_reads=rx_reads;
                regobs_observe(REGOBS_BEFORE_ACQUIRE);
                assert(regobs_used==REGOBS_LIMIT && rx_reads==prior_reads && !strcmp(regobs_error,"record_capacity"));
                regobs_in_capture=false;
            }
            if(mode==EARLY_END) command("REGOBS1 END 0123456789abcdef0123456789abcdef");
            else if(mode==BAD_NONCE) command("REGOBS1 END 1123456789abcdef0123456789abcdef");
            else if(mode==REAPPLY) command("GAIN MANUAL 48");
            else {
                for(unsigned i=0;i<20 && regobs_state==REGOBS_ARMED;i++) command("CAP20 16380 6");
                if(mode==EXCESS) command("CAP20 16380 6");
                else if(regobs_state==REGOBS_ARMED) command("REGOBS1 END 0123456789abcdef0123456789abcdef");
            }
            if(mode==SUCCESS || mode==VARIANT) assert(regobs_state==REGOBS_DONE && regobs_used==81 && regobs_captures==20 && triggers==20);
            else assert(regobs_state==REGOBS_FAILED);
        }
        /* Rejected session cannot trigger another acquisition or setting write. */
        unsigned prior=triggers;
        command("CAP20 16380 6"); command("GAIN MANUAL 48");
        assert(triggers==prior);
    }
    assert(gain_writes==before_writes && !control);
    assert(owner==0xa5a50100 && byte_map==0xdeadbeef && filter[0]==0x91 && filter[1]==0xc2);
    /* Every armed successful dump has one entry/armed/completed/restored read. */
    if(mode==SUCCESS || mode==VARIANT) assert(rx_reads-before_reads==81);
    for(unsigned i=before_trace;i<trace_used;i++) assert(trace[i]!=101 && trace[i]!=400 && trace[i]!=401 && trace[i]!=402 && trace[i]!=403 && trace[i]!=404 && trace[i]!=405);
    /* Trace the actual acquire_iq body, not just the serialized stage labels.
     * Reads bracket original filter/control operations and all restoration
     * precedes the first post-dump UART call, including failed acquisitions. */
    const unsigned before_trigger[]={100,202,301,311,302,312,200,201,202,100,202};
    const unsigned after_trigger[]={202,100,202,200,201,311,312,100};
    if(mode!=UNARMED) for(unsigned i=before_trace;i<trace_used;i++) if(trace[i]==203) {
        assert(i>=11 && i+8<trace_used);
        for(unsigned j=0;j<11;j++) assert(trace[i-11+j]==before_trigger[j]);
        for(unsigned j=0;j<8;j++) assert(trace[i+1+j]==after_trigger[j]);
    }
    fwrite(wire,1,wire_used,stdout);
    fprintf(stderr,"{\"triggers\":%u,\"records\":%u,\"gain_writes\":%u,\"selector_reads\":%u,\"filter_writes\":%u,\"state\":%u}\n",triggers,regobs_used,gain_writes,rx_reads-before_reads,filter_writes,regobs_state);
    return 0;
}
