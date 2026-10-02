#pragma once
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <inttypes.h>
#define CONFIG_IDF_TARGET_ESP32 1
#include "rx_bandwidth.h"
#include "rx_tuning.h"
#define BIT(n) (1u << (n))
#define SOC_RESERVE_MEMORY_REGION(start,end,name)
#define DPORT_IRAM_DRAM_AHB_SEL_REG 0x123u
#define DPORT_MAC_DUMP_MODE_M 0x30u
#define DPORT_MAC_DUMP_MODE_S 4
static uint32_t test_samples[16384];
static uint32_t mmio_read(unsigned reg);
static void mmio_write(unsigned reg, uint32_t value);
#define REG_READ(reg) mmio_read(reg)
#define REG_WRITE(reg,value) mmio_write(reg,value)
#define REG_SET_BIT(reg,bit) REG_WRITE(reg,REG_READ(reg)|(bit))
#define REG_CLR_BIT(reg,bit) REG_WRITE(reg,REG_READ(reg)&~(bit))
#define DPORT_REG_READ(reg) REG_READ(reg)
#define DPORT_REG_WRITE(reg,value) REG_WRITE(reg,value)
static int64_t esp_timer_get_time(void);
static uint32_t esp_cpu_get_cycle_count(void);
static void esp_rom_delay_us(unsigned us);
#ifdef REGOBS_ACTUAL_SERIAL
#include "burst_serial.h"
#else
static bool burst_serial_send(const void *data, size_t size);
static unsigned burst_serial_baud(void) { return 921600; }
#endif
static uint32_t esp_rom_crc32_le(uint32_t initial, const uint8_t *bytes, unsigned length);
static unsigned rtc_clk_xtal_freq_get(void) { return 40; }
static void vTaskDelay(unsigned ticks);
typedef bool (*spectrum_acquire_fn)(unsigned,unsigned,const uint32_t **,unsigned *);
static bool spectrum_command(const char *line, unsigned frequency, spectrum_acquire_fn fn) {
    (void)line; (void)frequency; (void)fn; return false;
}
