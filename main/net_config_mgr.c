#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "nvs_flash.h"
#include "nvs.h"
#include "mdns.h"
#include "esp_netif.h"
#include "net_config_mgr.h"

static const char *TAG = "net_config_mgr";
static const char *NVS_NAMESPACE = "kvm_net";

static net_config_t s_config = {
    .dhcp_enabled = true,
    .static_ip = "172.16.1.54",
    .static_netmask = "255.255.255.0",
    .static_gw = "172.16.1.1",
    .static_dns = "8.8.8.8",
    .wifi_enabled = false,
    .wifi_ssid = "",
    .wifi_password = "",
    .mdns_enabled = true,
    .mdns_hostname = "esp32p4-kvm",
};

static bool s_mdns_initialized = false;
static portMUX_TYPE s_config_lock = portMUX_INITIALIZER_UNLOCKED;

esp_err_t net_config_mgr_init(void)
{
    ESP_LOGI(TAG, "Loading network configuration from NVS...");

    nvs_handle_t nvs_h;
    esp_err_t err = nvs_open(NVS_NAMESPACE, NVS_READWRITE, &nvs_h);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to open NVS namespace '%s': %s", NVS_NAMESPACE, esp_err_to_name(err));
        return err;
    }

    uint8_t u8_val = 0;
    size_t req_len = 0;

    // 1. DHCP enabled
    if (nvs_get_u8(nvs_h, "dhcp", &u8_val) == ESP_OK) {
        s_config.dhcp_enabled = (u8_val != 0);
    } else {
        nvs_set_u8(nvs_h, "dhcp", s_config.dhcp_enabled ? 1 : 0);
    }

    // 2. Static IP
    req_len = sizeof(s_config.static_ip);
    if (nvs_get_str(nvs_h, "ip", s_config.static_ip, &req_len) != ESP_OK || strlen(s_config.static_ip) == 0) {
        strncpy(s_config.static_ip, "172.16.1.54", sizeof(s_config.static_ip) - 1);
        nvs_set_str(nvs_h, "ip", s_config.static_ip);
    }

    // 3. Static Netmask
    req_len = sizeof(s_config.static_netmask);
    if (nvs_get_str(nvs_h, "netmask", s_config.static_netmask, &req_len) != ESP_OK || strlen(s_config.static_netmask) == 0) {
        strncpy(s_config.static_netmask, "255.255.255.0", sizeof(s_config.static_netmask) - 1);
        nvs_set_str(nvs_h, "netmask", s_config.static_netmask);
    }

    // 4. Static Gateway
    req_len = sizeof(s_config.static_gw);
    if (nvs_get_str(nvs_h, "gw", s_config.static_gw, &req_len) != ESP_OK || strlen(s_config.static_gw) == 0) {
        strncpy(s_config.static_gw, "172.16.1.1", sizeof(s_config.static_gw) - 1);
        nvs_set_str(nvs_h, "gw", s_config.static_gw);
    }

    // 5. Static DNS
    req_len = sizeof(s_config.static_dns);
    if (nvs_get_str(nvs_h, "dns", s_config.static_dns, &req_len) != ESP_OK || strlen(s_config.static_dns) == 0) {
        strncpy(s_config.static_dns, "8.8.8.8", sizeof(s_config.static_dns) - 1);
        nvs_set_str(nvs_h, "dns", s_config.static_dns);
    }

    // 6. Wi-Fi Enabled
    if (nvs_get_u8(nvs_h, "wifi_en", &u8_val) == ESP_OK) {
        s_config.wifi_enabled = (u8_val != 0);
    } else {
        nvs_set_u8(nvs_h, "wifi_en", s_config.wifi_enabled ? 1 : 0);
    }

    // 7. Wi-Fi SSID
    req_len = sizeof(s_config.wifi_ssid);
    if (nvs_get_str(nvs_h, "wifi_ssid", s_config.wifi_ssid, &req_len) != ESP_OK) {
        s_config.wifi_ssid[0] = '\0';
        nvs_set_str(nvs_h, "wifi_ssid", s_config.wifi_ssid);
    }

    // 8. Wi-Fi Password
    req_len = sizeof(s_config.wifi_password);
    if (nvs_get_str(nvs_h, "wifi_pass", s_config.wifi_password, &req_len) != ESP_OK) {
        s_config.wifi_password[0] = '\0';
        nvs_set_str(nvs_h, "wifi_pass", s_config.wifi_password);
    }

    // 9. mDNS Enabled
    if (nvs_get_u8(nvs_h, "mdns_en", &u8_val) == ESP_OK) {
        s_config.mdns_enabled = (u8_val != 0);
    } else {
        nvs_set_u8(nvs_h, "mdns_en", s_config.mdns_enabled ? 1 : 0);
    }

    // 10. mDNS Hostname
    req_len = sizeof(s_config.mdns_hostname);
    if (nvs_get_str(nvs_h, "mdns_host", s_config.mdns_hostname, &req_len) != ESP_OK || strlen(s_config.mdns_hostname) == 0) {
        strncpy(s_config.mdns_hostname, "esp32p4-kvm", sizeof(s_config.mdns_hostname) - 1);
        nvs_set_str(nvs_h, "mdns_host", s_config.mdns_hostname);
    }

    nvs_commit(nvs_h);
    nvs_close(nvs_h);

    ESP_LOGI(TAG, "Network config loaded: DHCP=%s, IP=%s, mDNS=%s (%s.local), Wi-Fi=%s (SSID: '%s')",
             s_config.dhcp_enabled ? "Enabled" : "Static",
             s_config.dhcp_enabled ? "Auto" : s_config.static_ip,
             s_config.mdns_enabled ? "Enabled" : "Disabled",
             s_config.mdns_hostname,
             s_config.wifi_enabled ? "Enabled" : "Disabled",
             s_config.wifi_ssid);

    return ESP_OK;
}

void net_config_mgr_get(net_config_t *out_cfg)
{
    if (!out_cfg) return;
    portENTER_CRITICAL(&s_config_lock);
    memcpy(out_cfg, &s_config, sizeof(net_config_t));
    portEXIT_CRITICAL(&s_config_lock);
}

esp_err_t net_config_mgr_save(const net_config_t *new_cfg)
{
    if (!new_cfg) return ESP_ERR_INVALID_ARG;

    nvs_handle_t nvs_h;
    esp_err_t err = nvs_open(NVS_NAMESPACE, NVS_READWRITE, &nvs_h);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to open NVS namespace: %s", esp_err_to_name(err));
        return err;
    }

    portENTER_CRITICAL(&s_config_lock);
    memcpy(&s_config, new_cfg, sizeof(net_config_t));
    // Ensure null terminators
    s_config.static_ip[sizeof(s_config.static_ip) - 1] = '\0';
    s_config.static_netmask[sizeof(s_config.static_netmask) - 1] = '\0';
    s_config.static_gw[sizeof(s_config.static_gw) - 1] = '\0';
    s_config.static_dns[sizeof(s_config.static_dns) - 1] = '\0';
    s_config.wifi_ssid[sizeof(s_config.wifi_ssid) - 1] = '\0';
    s_config.wifi_password[sizeof(s_config.wifi_password) - 1] = '\0';
    s_config.mdns_hostname[sizeof(s_config.mdns_hostname) - 1] = '\0';
    portEXIT_CRITICAL(&s_config_lock);

    nvs_set_u8(nvs_h, "dhcp", s_config.dhcp_enabled ? 1 : 0);
    nvs_set_str(nvs_h, "ip", s_config.static_ip);
    nvs_set_str(nvs_h, "netmask", s_config.static_netmask);
    nvs_set_str(nvs_h, "gw", s_config.static_gw);
    nvs_set_str(nvs_h, "dns", s_config.static_dns);
    nvs_set_u8(nvs_h, "wifi_en", s_config.wifi_enabled ? 1 : 0);
    nvs_set_str(nvs_h, "wifi_ssid", s_config.wifi_ssid);
    nvs_set_str(nvs_h, "wifi_pass", s_config.wifi_password);
    nvs_set_u8(nvs_h, "mdns_en", s_config.mdns_enabled ? 1 : 0);
    nvs_set_str(nvs_h, "mdns_host", s_config.mdns_hostname);

    err = nvs_commit(nvs_h);
    nvs_close(nvs_h);

    ESP_LOGI(TAG, "Network configuration saved to NVS.");
    return err;
}

esp_err_t net_config_mgr_apply_eth(esp_netif_t *eth_netif)
{
    if (!eth_netif) return ESP_ERR_INVALID_ARG;

    if (s_config.dhcp_enabled) {
        ESP_LOGI(TAG, "Ethernet configured for DHCP client");
        esp_netif_dhcp_status_t status;
        esp_err_t err = esp_netif_dhcpc_get_status(eth_netif, &status);
        if (err == ESP_OK && status != ESP_NETIF_DHCP_STARTED) {
            esp_netif_dhcpc_start(eth_netif);
        }
    } else {
        ESP_LOGI(TAG, "Ethernet configured for Static IP: %s (Mask: %s, GW: %s)",
                 s_config.static_ip, s_config.static_netmask, s_config.static_gw);
        esp_netif_dhcp_status_t status;
        esp_err_t err = esp_netif_dhcpc_get_status(eth_netif, &status);
        if (err == ESP_OK && status == ESP_NETIF_DHCP_STARTED) {
            esp_netif_dhcpc_stop(eth_netif);
        }

        esp_netif_ip_info_t ip_info;
        memset(&ip_info, 0, sizeof(ip_info));
        ip_info.ip.addr = esp_ip4addr_aton(s_config.static_ip);
        ip_info.netmask.addr = esp_ip4addr_aton(s_config.static_netmask);
        ip_info.gw.addr = esp_ip4addr_aton(s_config.static_gw);
        esp_netif_set_ip_info(eth_netif, &ip_info);

        if (strlen(s_config.static_dns) > 0) {
            esp_netif_dns_info_t dns_info;
            dns_info.ip.u_addr.ip4.addr = esp_ip4addr_aton(s_config.static_dns);
            dns_info.ip.type = ESP_IPADDR_TYPE_V4;
            esp_netif_set_dns_info(eth_netif, ESP_NETIF_DNS_MAIN, &dns_info);
        }
    }

    return ESP_OK;
}

esp_err_t net_config_mgr_start_mdns(void)
{
    if (!s_config.mdns_enabled) {
        if (s_mdns_initialized) {
            mdns_free();
            s_mdns_initialized = false;
            ESP_LOGI(TAG, "mDNS stopped.");
        }
        return ESP_OK;
    }

    if (!s_mdns_initialized) {
        esp_err_t err = mdns_init();
        if (err != ESP_OK) {
            ESP_LOGE(TAG, "mdns_init failed: %s", esp_err_to_name(err));
            return err;
        }
        s_mdns_initialized = true;
    }

    mdns_hostname_set(s_config.mdns_hostname);
    mdns_instance_name_set("ESP32-P4 HDMI KVM");
    mdns_service_add("KVM Web Server", "_http", "_tcp", 80, NULL, 0);

    ESP_LOGI(TAG, "mDNS active: http://%s.local/", s_config.mdns_hostname);
    return ESP_OK;
}
