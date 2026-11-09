#pragma once

#include <stdbool.h>
#include "esp_err.h"
#include "esp_netif.h"

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief Initialize Ethernet peripheral (Internal EMAC + IP101 PHY) on JC-ESP32P4-M3-DEV
 *
 * @return ESP_OK on success, or appropriate error code.
 */
esp_err_t ethernet_mgr_init(void);

/**
 * @brief Check if Ethernet is connected and has obtained an IP address
 *
 * @return true if connected and IP acquired, false otherwise.
 */
bool ethernet_mgr_is_connected(void);

/**
 * @brief Get the acquired IPv4 address string
 *
 * @return Pointer to string with IP address (e.g. "192.168.1.100") or "0.0.0.0"
 */
const char *ethernet_mgr_get_ip_str(void);

/**
 * @brief Get the netif handle for Ethernet interface
 *
 * @return Pointer to esp_netif_t or NULL
 */
esp_netif_t *ethernet_mgr_get_netif(void);

#ifdef __cplusplus
}
#endif
