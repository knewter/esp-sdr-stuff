#pragma once
#include "protocol.h"
#include <stdbool.h>
#include <stdint.h>
unsigned fs_source_packet(const bridge_request *,uint8_t out[9]);
bool fs_platform_configure(uint64_t until);
bool fs_platform_prepare(uint64_t until);
bool fs_platform_transfer(bool write,uint32_t address,uint32_t *value,uint64_t until);
void fs_platform_safe(void);
void fs_platform_lifetime(uint64_t until);
