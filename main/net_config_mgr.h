#pragma once

#include <stdbool.h>
#include <stdint.h>
#include "esp_err.h"
#include "esp_netif.h"

#ifdef __cplusplus
extern "C" {
#endif

#define NET_MAX_HOST_LEN    32
#define NET_MAX_SSID_LEN    32
#define NET_MAX_PASS_LEN    64
#define NET_MAX_IP_LEN      16

typedef struct {
    // Ethernet IPv4 configuration
    bool dhcp_enabled;                   // true = DHCP Client, false = Static IP
    char static_ip[NET_MAX_IP_LEN];       // e.g. "172.16.1.54"
    char static_netmask[NET_MAX_IP_LEN];  // e.g. "255.255.255.0"
    char static_gw[NET_MAX_IP_LEN];       // e.g. "172.16.1.1"
    char static_dns[NET_MAX_IP_LEN];      // e.g. "8.8.8.8"

    // Wi-Fi Client configuration
    bool wifi_enabled;                   // true = Wi-Fi client enabled
    char wifi_ssid[NET_MAX_SSID_LEN];     // Wi-Fi SSID
    char wifi_password[NET_MAX_PASS_LEN]; // Wi-Fi Password

    // mDNS Responder configuration
    bool mdns_enabled;                   // true = mDNS responder enabled
    char mdns_hostname[NET_MAX_HOST_LEN]; // Hostname, e.g. "esp32p4-kvm" (resolves to esp32p4-kvm.local)
} net_config_t;

/**
 * @brief Initialize network configuration manager from NVS
 * @return ESP_OK on success
 */
esp_err_t net_config_mgr_init(void);

/**
 * @brief Get copy of current active network configuration
 * @param[out] out_cfg Pointer to destination struct
 */
void net_config_mgr_get(net_config_t *out_cfg);

/**
 * @brief Save and update network configuration in NVS
 * @param[in] new_cfg New network configuration
 * @return ESP_OK on success
 */
esp_err_t net_config_mgr_save(const net_config_t *new_cfg);

/**
 * @brief Apply IP configuration (DHCP vs Static) to the Ethernet netif
 * @param[in] eth_netif Pointer to Ethernet esp_netif
 * @return ESP_OK on success
 */
esp_err_t net_config_mgr_apply_eth(esp_netif_t *eth_netif);

/**
 * @brief Start or update mDNS responder according to current config
 * @return ESP_OK on success
 */
esp_err_t net_config_mgr_start_mdns(void);

#ifdef __cplusplus
}
#endif
