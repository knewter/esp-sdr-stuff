#pragma once
#include "protocol.h"
extern const uint8_t bridge_fpga_image[], bridge_fpga_sha256[32];
extern const uint32_t bridge_fpga_image_bytes, bridge_fpga_crc32;
bool bridge_config_match(const uint8_t input[48], uint32_t *nonce);
bool bridge_config_admit(bool *attempted, bool register_attempted, uint64_t age_us);
unsigned bridge_configure(uint64_t until);
void bridge_config_reply(uint8_t output[128], uint32_t nonce, unsigned status,
                         uint64_t now, const char source[64]);
