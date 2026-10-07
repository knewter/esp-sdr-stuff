/* Drawing primitives shared by the CYD panel driver and UI screens. */
#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

/* DMA line buffer: CYD_LINE_ROWS full-width rows of byte-swapped RGB565. */
#define CYD_LINE_ROWS 12
extern uint16_t *gfx_line;

void gfx_command(uint8_t cmd, const uint8_t *data, size_t length);
void gfx_window(int x0, int y0, int x1, int y1);
/* RAMWR restarts at the window origin; later chunks continue (RAMWRC). */
void gfx_push(const uint16_t *pixels, size_t count, bool first);
void gfx_fill(int x, int y, int w, int h, uint16_t colour);
void gfx_text(int x, int y, const char *s, int size, uint16_t fg, uint16_t bg);
void gfx_text_centered(int cx, int y, const char *s, int size, uint16_t fg, uint16_t bg);
static inline uint16_t gfx_swap(uint16_t v) { return (uint16_t)(v >> 8 | v << 8); }
/* Vertical-scroll start line (absolute GRAM row). */
void gfx_scroll_start(int line);
