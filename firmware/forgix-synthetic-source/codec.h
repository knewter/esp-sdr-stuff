#ifndef FORGIX_SYNTHETIC_CODEC_H
#define FORGIX_SYNTHETIC_CODEC_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define FSG_RECORD_BYTES 16u
#define FSG_FRAME_BYTES 512u
#define FSG_HEADER_BYTES 64u
#define FSG_MAX_RECORDS 26u

typedef enum {
    FSG_OK = 0, FSG_ARGUMENT, FSG_LENGTH, FSG_HEADER, FSG_FRAME_CRC,
    FSG_RECORD_CRC, FSG_NONCE, FSG_PROFILE, FSG_PATTERN, FSG_DUPLICATE,
    FSG_REORDER, FSG_GAP, FSG_TICK, FSG_TIMESTAMP, FSG_COUNT, FSG_CLOSED,
    FSG_TRUNCATED, FSG_CHUNK
} fsg_error;

typedef struct {
    uint32_t sequence, tick32, pattern, crc32;
} fsg_record;

typedef struct {
    uint32_t frame_sequence;
    uint64_t device_time_us;
    uint8_t nonce[16];
    uint32_t period_cycles, target_records;
    uint16_t count;
    fsg_record records[FSG_MAX_RECORDS];
} fsg_batch;

typedef struct {
    uint8_t nonce[16];
    uint32_t period_cycles, target_records, next_frame, next_record;
    uint64_t start_tick64, last_device_time_us, last_fpga_tick64;
    uint32_t tick32_wraps;
    fsg_error failure;
    bool failed, have_timestamp, finished;
} fsg_stream;

/* All input/output buffers are caller owned. Output is unchanged on failure.
 * Stream failures latch forever; caller must retain raw frame/prefix bytes.
 * CRC input may be NULL only for length0. No heap, device or transport access.
 */
uint32_t fsg_crc32(const uint8_t *data, size_t length);
fsg_error fsg_record_create(uint32_t sequence, uint32_t tick32,
                            const uint8_t nonce[16], fsg_record *out);
fsg_error fsg_record_encode(const fsg_record *record, const uint8_t nonce[16],
                            uint8_t out[FSG_RECORD_BYTES]);
fsg_error fsg_record_decode(const uint8_t *data, size_t length,
                            const uint8_t nonce[16], fsg_record *out);
fsg_error fsg_batch_encode(const fsg_batch *batch, uint8_t out[FSG_FRAME_BYTES]);
fsg_error fsg_batch_decode(const uint8_t *data, size_t length,
                           const uint8_t expected_nonce[16], fsg_batch *out);
fsg_error fsg_stream_init(fsg_stream *stream, const uint8_t nonce[16],
                          uint32_t period_cycles, uint32_t target_records,
                          uint64_t start_tick64);
fsg_error fsg_stream_accept(fsg_stream *stream, const uint8_t *data, size_t length);
fsg_error fsg_stream_finish(fsg_stream *stream);
#endif
