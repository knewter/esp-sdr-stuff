/* Beginner-friendly screens for the CYD waterfall build. */
#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include "cyd_display.h"

void cyd_ui_init(const cyd_radio_t *radio);
/* Touch at a screen point; fresh on the first sample of a press. */
void cyd_ui_press(int x, int y, bool fresh, int64_t now);
void cyd_ui_release(void);
/* Radio work and drawing; called from the receiver loop when the host is idle. */
void cyd_ui_tick(int64_t now);
/* Host owns the radio (true) or has gone idle (false). */
void cyd_ui_host(bool active);
/* Redraw the current screen from scratch (after calibration). */
void cyd_ui_redraw(void);
/* Waterfall scroll offset, for mapping screen rows to GRAM in screenshots. */
int cyd_ui_scroll(void);
/* One JSON object of measurements for CYDSTAT. */
void cyd_ui_report(char *out, size_t size);
void cyd_ui_reset_stats(void);
/* Provided by the panel driver: start the three-cross touch calibration. */
void cyd_display_calibrate(void);
