idf_component_register(SRCS "main.c" "privacy_crypto.c" INCLUDE_DIRS "."
    PRIV_REQUIRES bt mbedtls nvs_flash esp_timer esp_driver_uart)
