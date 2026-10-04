#ifndef FORGIX_BRIDGE_UID_H
#define FORGIX_BRIDGE_UID_H
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#define PICO_UNIQUE_BOARD_ID_SIZE_BYTES 8
bool bridge_uid_init(uint64_t until);
/* Compatible getter name retained for the artifact/USB identity guard. */
void pico_get_unique_board_id_string(char *out, unsigned len);
#endif
