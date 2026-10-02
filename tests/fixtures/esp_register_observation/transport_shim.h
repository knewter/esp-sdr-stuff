#pragma once
#include "harness_shim.h"
#include "burst_serial.h"
#define CONFIG_ESP_SDR_UART_ENABLED 1
#define CONFIG_ESP_SDR_UART_BAUD 921600
#define CONFIG_ESP_SDR_UART_TX_PIN 1
#define CONFIG_ESP_SDR_UART_RX_PIN 3
#define SOC_USB_SERIAL_JTAG_SUPPORTED 0
#define IRAM_ATTR
#define UART_NUM_0 0
#define ESP_OK 0
#define ESP_ERROR_CHECK(call) assert((call)==ESP_OK)
#define pdMS_TO_TICKS(value) (value)
#define UART_DATA_8_BITS 8
#define UART_PARITY_DISABLE 0
#define UART_STOP_BITS_1 1
#define UART_HW_FLOWCTRL_DISABLE 0
#define UART_SCLK_DEFAULT 0
#define UART_PIN_NO_CHANGE -1
typedef struct { unsigned baud_rate,data_bits,parity,stop_bits,flow_ctrl,source_clk; } uart_config_t;
static int uart_param_config(int,const uart_config_t *);
static int uart_set_pin(int,int,int,int,int);
static int uart_driver_install(int,int,int,int,void *,int);
static int uart_flush_input(int);
static int uart_wait_tx_done(int,int);
static int uart_set_baudrate(int,unsigned);
static int uart_read_bytes(int,void *,size_t,int);
static int uart_tx_chars(int,const char *,size_t);
