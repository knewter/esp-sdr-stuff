/* Application-only support for original ESP32's SDK-forced host privacy.
 * Semantics: pinned NimBLE host/src/ble_sm_alg.c ble_sm_alg_encrypt(), lines
 * 118-206 in ESP-IDF 25fe69f946311abdaf9ad56591f25fedbc20ac98.
 * The SDK omits that definition when both connection roles are disabled.
 * This implements the required real AES primitive; no SDK code is changed.
 */
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include "psa/crypto.h"
#include "host/ble_hs.h"

static void clear(uint8_t *buffer, size_t size) {
    volatile uint8_t *p = buffer;
    while (size--) *p++ = 0;
}

int ble_sm_alg_encrypt(const uint8_t *key, const uint8_t *plaintext, uint8_t *output) {
    if (!key || !plaintext || !output) return BLE_HS_EUNKNOWN;
    uint8_t reversed_key[16], reversed_input[16], encrypted[16] = {0};
    for (size_t i = 0; i < 16; ++i) {
        reversed_key[i] = key[15-i];
        reversed_input[i] = plaintext[15-i];
    }
    psa_key_attributes_t attributes = PSA_KEY_ATTRIBUTES_INIT;
    psa_set_key_usage_flags(&attributes, PSA_KEY_USAGE_ENCRYPT);
    psa_set_key_algorithm(&attributes, PSA_ALG_ECB_NO_PADDING);
    psa_set_key_type(&attributes, PSA_KEY_TYPE_AES);
    psa_set_key_bits(&attributes, 128);
    psa_key_id_t id = 0;
    psa_status_t status = psa_import_key(&attributes, reversed_key, 16, &id);
    psa_reset_key_attributes(&attributes);
    int result = BLE_HS_EUNKNOWN;
    if (status == PSA_SUCCESS) {
        size_t output_size = 0;
        status = psa_cipher_encrypt(id, PSA_ALG_ECB_NO_PADDING, reversed_input,
                                    16, encrypted, 16, &output_size);
        psa_status_t destroy_status = psa_destroy_key(id);
        if (status == PSA_SUCCESS && output_size == 16 && destroy_status == PSA_SUCCESS) {
            for (size_t i = 0; i < 16; ++i) output[i] = encrypted[15-i];
            result = 0;
        }
    }
    clear(reversed_key, sizeof reversed_key);
    clear(reversed_input, sizeof reversed_input);
    clear(encrypted, sizeof encrypted);
    return result;
}

/* NIST FIPS 197 (2001) Appendix C.1 vector, reversed for NimBLE little-endian API.
 * Run before NimBLE initialization: failure never reaches CONFIG or scanning.
 */
int native_privacy_crypto_selftest(void) {
    static const uint8_t key[16] = {0x0f,0x0e,0x0d,0x0c,0x0b,0x0a,0x09,0x08,
                                   0x07,0x06,0x05,0x04,0x03,0x02,0x01,0x00};
    static const uint8_t plaintext[16] = {0xff,0xee,0xdd,0xcc,0xbb,0xaa,0x99,0x88,
                                         0x77,0x66,0x55,0x44,0x33,0x22,0x11,0x00};
    static const uint8_t expected[16] = {0x5a,0xc5,0xb4,0x70,0x80,0xb7,0xcd,0xd8,
                                        0x30,0x04,0x7b,0x6a,0xd8,0xe0,0xc4,0x69};
    uint8_t output[16];
    if (psa_crypto_init() != PSA_SUCCESS) return BLE_HS_EUNKNOWN;
    int result = ble_sm_alg_encrypt(key, plaintext, output);
    if (result || memcmp(output, expected, 16)) result = BLE_HS_EUNKNOWN;
    if (!result) {
        memcpy(output, plaintext, 16);
        result = ble_sm_alg_encrypt(key, output, output);
        if (result || memcmp(output, expected, 16)) result = BLE_HS_EUNKNOWN;
    }
    clear(output, sizeof output);
    return result;
}
