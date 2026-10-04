#include "codec.h"
#include <string.h>

static uint32_t read32(const uint8_t *p) {
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}
static uint16_t read16(const uint8_t *p) { return (uint16_t)(p[0] | ((uint16_t)p[1] << 8)); }
static uint64_t read64(const uint8_t *p) { return (uint64_t)read32(p) | ((uint64_t)read32(p+4) << 32); }
static void write32(uint8_t *p, uint32_t v) { for (unsigned i=0;i<4;i++) p[i]=(uint8_t)(v>>(8*i)); }
static void write16(uint8_t *p, uint16_t v) { p[0]=(uint8_t)v; p[1]=(uint8_t)(v>>8); }
static void write64(uint8_t *p, uint64_t v) { write32(p,(uint32_t)v); write32(p+4,(uint32_t)(v>>32)); }
static bool valid_nonce(const uint8_t *nonce) {
    if (!nonce) return false;
    uint8_t bits=0; for (unsigned i=0;i<16;i++) bits|=nonce[i];
    return bits!=0;
}
static bool profile(uint32_t period, uint32_t target) {
    return (period==2000000u && target==960u) || (period==500000u && target==3840u) ||
           (period==250000u && target==7680u);
}
static uint32_t pattern(uint32_t seq, const uint8_t nonce[16]) {
    return seq ^ ((seq<<7) | (seq>>25)) ^ read32(nonce) ^ read32(nonce+4) ^
           read32(nonce+8) ^ read32(nonce+12) ^ UINT32_C(0x46534731);
}
uint32_t fsg_crc32(const uint8_t *data, size_t length) {
    uint32_t value=UINT32_MAX;
    for (size_t i=0;i<length;i++) {
        value^=data[i];
        for (unsigned bit=0;bit<8;bit++) value=(value>>1)^((0u-(value&1u))&UINT32_C(0xedb88320));
    }
    return value^UINT32_MAX;
}
static void record_bytes(const fsg_record *record, uint8_t out[16]) {
    write32(out,record->sequence); write32(out+4,record->tick32);
    write32(out+8,record->pattern); write32(out+12,record->crc32);
}
static fsg_error record_check(const fsg_record *record, const uint8_t nonce[16]) {
    uint8_t raw[16]; record_bytes(record,raw);
    if (fsg_crc32(raw,12)!=record->crc32) return FSG_RECORD_CRC;
    if (record->pattern!=pattern(record->sequence,nonce)) return FSG_PATTERN;
    return FSG_OK;
}
fsg_error fsg_record_create(uint32_t sequence, uint32_t tick32, const uint8_t nonce[16], fsg_record *out) {
    if (!out) return FSG_ARGUMENT;
    if (!valid_nonce(nonce)) return FSG_NONCE;
    fsg_record result={sequence,tick32,pattern(sequence,nonce),0}; uint8_t raw[16];
    record_bytes(&result,raw); result.crc32=fsg_crc32(raw,12); *out=result;
    return FSG_OK;
}
fsg_error fsg_record_encode(const fsg_record *record, const uint8_t nonce[16], uint8_t out[16]) {
    if (!record || !out) return FSG_ARGUMENT;
    if (!valid_nonce(nonce)) return FSG_NONCE;
    fsg_record copy=*record;
    fsg_error error=record_check(&copy,nonce); if (error) return error;
    record_bytes(&copy,out); return FSG_OK;
}
fsg_error fsg_record_decode(const uint8_t *data, size_t length, const uint8_t nonce[16], fsg_record *out) {
    if (!data || !out) return FSG_ARGUMENT;
    if (length!=16) return FSG_LENGTH;
    if (!valid_nonce(nonce)) return FSG_NONCE;
    fsg_record result={read32(data),read32(data+4),read32(data+8),read32(data+12)};
    fsg_error error=record_check(&result,nonce); if (error) return error;
    *out=result; return FSG_OK;
}
fsg_error fsg_batch_encode(const fsg_batch *batch, uint8_t out[512]) {
    if (!batch || !out) return FSG_ARGUMENT;
    if (!valid_nonce(batch->nonce)) return FSG_NONCE;
    if (!profile(batch->period_cycles,batch->target_records)) return FSG_PROFILE;
    if (!batch->count || batch->count>26) return FSG_COUNT;
    for (unsigned i=0;i<batch->count;i++) {
        fsg_error error=record_check(&batch->records[i],batch->nonce); if (error) return error;
    }
    fsg_batch copy; memcpy(&copy,batch,sizeof(copy)); batch=&copy;
    memset(out,0,512); memcpy(out,"FSB1",4); out[4]=1; out[5]=1;
    write16(out+6,64); write32(out+8,batch->frame_sequence); write16(out+12,512);
    write16(out+14,batch->count); write16(out+16,(uint16_t)(16*batch->count));
    write64(out+20,batch->device_time_us); memcpy(out+28,batch->nonce,16);
    write32(out+44,batch->records[0].sequence); write32(out+48,batch->period_cycles);
    write32(out+52,batch->target_records);
    for (unsigned i=0;i<batch->count;i++) record_bytes(&batch->records[i],out+64+16*i);
    write32(out+508,fsg_crc32(out,508)); return FSG_OK;
}
fsg_error fsg_batch_decode(const uint8_t *data, size_t length, const uint8_t expected_nonce[16], fsg_batch *out) {
    if (!data || !out) return FSG_ARGUMENT;
    if (length!=512) return FSG_LENGTH;
    if (!valid_nonce(expected_nonce)) return FSG_NONCE;
    if (memcmp(data,"FSB1",4) || data[4]!=1 || data[5]!=1 || read16(data+6)!=64 || read16(data+12)!=512) return FSG_HEADER;
    uint16_t count=read16(data+14),bytes=read16(data+16);
    if (!count || count>26 || bytes!=16*count) return FSG_COUNT;
    if (read16(data+18) || read64(data+56)) return FSG_HEADER;
    for (unsigned i=64+bytes;i<508;i++) if (data[i]) return FSG_HEADER;
    if (read32(data+508)!=fsg_crc32(data,508)) return FSG_FRAME_CRC;
    if (memcmp(data+28,expected_nonce,16)) return FSG_NONCE;
    if (!profile(read32(data+48),read32(data+52))) return FSG_PROFILE;
    fsg_batch result={0}; result.count=count; result.frame_sequence=read32(data+8);
    result.device_time_us=read64(data+20); memcpy(result.nonce,data+28,16);
    result.period_cycles=read32(data+48); result.target_records=read32(data+52);
    for (unsigned i=0;i<count;i++) {
        fsg_error error=fsg_record_decode(data+64+16*i,16,expected_nonce,&result.records[i]);
        if (error) return error;
    }
    if (read32(data+44)!=result.records[0].sequence) return FSG_HEADER;
    *out=result; return FSG_OK;
}
static fsg_error fail(fsg_stream *s, fsg_error error) {
    if (!s->failed) { s->failed=true; s->failure=error; }
    return s->failure;
}
static fsg_error order(uint32_t actual, uint32_t expected) {
    if (actual==expected) return FSG_OK;
    if (actual>expected) return FSG_GAP;
    return actual==expected-1u ? FSG_DUPLICATE : FSG_REORDER;
}
fsg_error fsg_stream_init(fsg_stream *s, const uint8_t nonce[16], uint32_t period, uint32_t target, uint64_t start) {
    if (!s) return FSG_ARGUMENT;
    uint8_t saved_nonce[16]; bool valid=valid_nonce(nonce);
    if (valid) memcpy(saved_nonce,nonce,16);
    memset(s,0,sizeof(*s));
    if (!valid) return fail(s,FSG_NONCE);
    if (!profile(period,target)) return fail(s,FSG_PROFILE);
    if (start>UINT64_MAX-(uint64_t)period*target) return fail(s,FSG_TICK);
    memcpy(s->nonce,saved_nonce,16); s->period_cycles=period; s->target_records=target;
    s->start_tick64=s->last_fpga_tick64=start; return FSG_OK;
}
fsg_error fsg_stream_accept(fsg_stream *s, const uint8_t *data, size_t length) {
    if (!s) return FSG_ARGUMENT;
    if (s->failed) return s->failure;
    if (s->finished) return fail(s,FSG_CLOSED);
    fsg_batch batch;
    fsg_error error=fsg_batch_decode(data,length,s->nonce,&batch); if (error) return fail(s,error);
    if (batch.period_cycles!=s->period_cycles || batch.target_records!=s->target_records) return fail(s,FSG_PROFILE);
    error=order(batch.frame_sequence,s->next_frame); if (error) return fail(s,error);
    if (s->have_timestamp && batch.device_time_us<s->last_device_time_us) return fail(s,FSG_TIMESTAMP);
    if (s->next_record+batch.count>s->target_records) return fail(s,FSG_COUNT);
    uint64_t tick=s->last_fpga_tick64;
    for (unsigned i=0;i<batch.count;i++) {
        uint32_t index=s->next_record+i;
        error=order(batch.records[i].sequence,index); if (error) return fail(s,error);
        tick=s->start_tick64+(uint64_t)(index+1)*s->period_cycles;
        if (batch.records[i].tick32!=(uint32_t)tick) return fail(s,FSG_TICK);
    }
    s->next_frame++; s->next_record+=batch.count; s->last_device_time_us=batch.device_time_us;
    s->have_timestamp=true; s->last_fpga_tick64=tick;
    s->tick32_wraps=(uint32_t)((tick>>32)-(s->start_tick64>>32)); return FSG_OK;
}
fsg_error fsg_stream_finish(fsg_stream *s) {
    if (!s) return FSG_ARGUMENT;
    if (s->failed) return s->failure;
    if (s->finished) return fail(s,FSG_CLOSED);
    if (s->next_record!=s->target_records) return fail(s,FSG_COUNT);
    s->finished=true; return FSG_OK;
}
