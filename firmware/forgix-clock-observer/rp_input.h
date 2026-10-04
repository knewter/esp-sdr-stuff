#ifndef FORGIX_CLOCK_OBSERVER_RP_INPUT_H
#define FORGIX_CLOCK_OBSERVER_RP_INPUT_H
#include "observer.h"
/* No USB/main/configuration owner. Only caller-qualified new RAM profile may
 * use this adapter after exact image configuration; no production admission. */
void observer_rp_io(observer_io *io, bool (*cancelled)(void *),void *context);
#endif
