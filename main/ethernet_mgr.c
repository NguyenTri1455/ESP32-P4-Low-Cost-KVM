#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "esp_eth.h"
#include "esp_netif.h"
#include "esp_event.h"
#include "driver/gpio.h"
#if __has_include("esp_eth_phy_ip101.h")
#include "esp_eth_phy_ip101.h"
#endif

#include "board_pins.h"
#include "ethernet_mgr.h"

static const char *TAG = "eth_mgr";

static esp_netif_t *s_eth_netif = NULL;
static esp_eth_handle_t s_eth_handle = NULL;
static bool s_is_connected = false;
static char s_ip_str[16] = "0.0.0.0";

static void eth_event_handler(void *arg, esp_event_base_t event_base,
                              int32_t event_id, void *event_data)
{
    uint8_t mac_addr[6] = {0};
    esp_eth_handle_t eth_handle = *(esp_eth_handle_t *)event_data;

    switch (event_id) {
    case ETHERNET_EVENT_CONNECTED:
        esp_eth_ioctl(eth_handle, ETH_CMD_G_MAC_ADDR, mac_addr);
        ESP_LOGI(TAG, "Ethernet Link Up");
        ESP_LOGI(TAG, "Ethernet HW Addr: %02x:%02x:%02x:%02x:%02x:%02x",
                 mac_addr[0], mac_addr[1], mac_addr[2],
                 mac_addr[3], mac_addr[4], mac_addr[5]);
        break;
    case ETHERNET_EVENT_DISCONNECTED:
        ESP_LOGW(TAG, "Ethernet Link Down");
        s_is_connected = false;
        strncpy(s_ip_str, "0.0.0.0", sizeof(s_ip_str));
        break;
    case ETHERNET_EVENT_START:
        ESP_LOGI(TAG, "Ethernet Started");
        break;
    case ETHERNET_EVENT_STOP:
        ESP_LOGI(TAG, "Ethernet Stopped");
        s_is_connected = false;
        break;
    default:
        break;
    }
}

static void ip_event_handler(void *arg, esp_event_base_t event_base,
                             int32_t event_id, void *event_data)
{
    ip_event_got_ip_t *event = (ip_event_got_ip_t *)event_data;
    const esp_netif_ip_info_t *ip_info = &event->ip_info;

    snprintf(s_ip_str, sizeof(s_ip_str), IPSTR, IP2STR(&ip_info->ip));
    s_is_connected = true;

    ESP_LOGI(TAG, "===============================================");
    ESP_LOGI(TAG, "Ethernet Got IPv4: %s", s_ip_str);
    ESP_LOGI(TAG, "Netmask:          " IPSTR, IP2STR(&ip_info->netmask));
    ESP_LOGI(TAG, "Gateway:          " IPSTR, IP2STR(&ip_info->gw));
    ESP_LOGI(TAG, "Web KVM stream ready at http://%s/", s_ip_str);
    ESP_LOGI(TAG, "Direct MJPEG stream at  http://%s/stream", s_ip_str);
    ESP_LOGI(TAG, "===============================================");
}

esp_err_t ethernet_mgr_init(void)
{
    ESP_LOGI(TAG, "Initializing Ethernet on %s (IP101 PHY)...", BOARD_NAME);

    // 1. Initialize TCP/IP and event loop if not already done
    ESP_ERROR_CHECK(esp_netif_init());
    esp_err_t err = esp_event_loop_create_default();
    if (err != ESP_OK && err != ESP_ERR_INVALID_STATE) {
        ESP_LOGE(TAG, "Failed to create event loop: %s", esp_err_to_name(err));
        return err;
    }

    // 2. Create esp_netif instance for Ethernet
    esp_netif_config_t netif_cfg = ESP_NETIF_DEFAULT_ETH();
    s_eth_netif = esp_netif_new(&netif_cfg);
    if (!s_eth_netif) {
        ESP_LOGE(TAG, "Failed to allocate netif");
        return ESP_FAIL;
    }

    // 3. Power-cycle the IP101 PHY via GPIO 51
    if (BOARD_ETH_PWR_RST_GPIO >= 0) {
        ESP_LOGI(TAG, "Resetting IP101 PHY on GPIO %d...", BOARD_ETH_PWR_RST_GPIO);
        gpio_config_t io_conf = {
            .pin_bit_mask = (1ULL << BOARD_ETH_PWR_RST_GPIO),
            .mode = GPIO_MODE_OUTPUT,
            .pull_up_en = GPIO_PULLUP_ENABLE,
            .pull_down_en = GPIO_PULLDOWN_DISABLE,
            .intr_type = GPIO_INTR_DISABLE,
        };
        gpio_config(&io_conf);
        gpio_set_level(BOARD_ETH_PWR_RST_GPIO, 0); // Active Low Reset / Power off
        vTaskDelay(pdMS_TO_TICKS(20));
        gpio_set_level(BOARD_ETH_PWR_RST_GPIO, 1); // Power on
        vTaskDelay(pdMS_TO_TICKS(50));              // Allow PHY clock to stabilize
    }

    // 4. Configure MAC
    eth_mac_config_t mac_config = ETH_MAC_DEFAULT_CONFIG();
    eth_esp32_emac_config_t esp32_emac_config = ETH_ESP32_EMAC_DEFAULT_CONFIG();
    esp32_emac_config.smi_gpio.mdc_num = BOARD_ETH_MDC_GPIO;
    esp32_emac_config.smi_gpio.mdio_num = BOARD_ETH_MDIO_GPIO;
    esp32_emac_config.interface = EMAC_DATA_INTERFACE_RMII;
#ifdef CONFIG_ETH_CLK_EXT_IN
    esp32_emac_config.clock_config.rmii.clock_mode = EMAC_CLK_EXT_IN;
#else
    esp32_emac_config.clock_config.rmii.clock_mode = EMAC_CLK_EXT_IN;
#endif
    esp32_emac_config.clock_config.rmii.clock_gpio = BOARD_ETH_RMII_CLK_GPIO;

    esp_eth_mac_t *mac = esp_eth_mac_new_esp32(&esp32_emac_config, &mac_config);
    if (!mac) {
        ESP_LOGE(TAG, "Failed to create EMAC instance");
        return ESP_FAIL;
    }

    // 5. Configure IP101 PHY
    eth_phy_config_t phy_config = ETH_PHY_DEFAULT_CONFIG();
    phy_config.phy_addr = BOARD_ETH_PHY_ADDR;
    phy_config.reset_gpio_num = BOARD_ETH_PWR_RST_GPIO;
    phy_config.reset_timeout_ms = 100;

    esp_eth_phy_t *phy = esp_eth_phy_new_ip101(&phy_config);
    if (!phy) {
        ESP_LOGE(TAG, "Failed to create IP101 PHY instance");
        return ESP_FAIL;
    }

    // 6. Install driver
    esp_eth_config_t eth_config = ETH_DEFAULT_CONFIG(mac, phy);
    err = esp_eth_driver_install(&eth_config, &s_eth_handle);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to install Ethernet driver: %s", esp_err_to_name(err));
        return err;
    }

    // 7. Attach Ethernet driver to TCP/IP stack
    ESP_ERROR_CHECK(esp_netif_attach(s_eth_netif, esp_eth_new_netif_glue(s_eth_handle)));

    // 8. Register Event Handlers
    ESP_ERROR_CHECK(esp_event_handler_register(ETH_EVENT, ESP_EVENT_ANY_ID, &eth_event_handler, NULL));
    ESP_ERROR_CHECK(esp_event_handler_register(IP_EVENT, IP_EVENT_ETH_GOT_IP, &ip_event_handler, NULL));

    // 9. Start Ethernet driver
    ESP_LOGI(TAG, "Starting Ethernet...");
    err = esp_eth_start(s_eth_handle);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to start Ethernet: %s", esp_err_to_name(err));
        return err;
    }

    ESP_LOGI(TAG, "Ethernet initialized. Waiting for cable connection and DHCP IP...");
    return ESP_OK;
}

bool ethernet_mgr_is_connected(void)
{
    return s_is_connected;
}

const char *ethernet_mgr_get_ip_str(void)
{
    return s_ip_str;
}

esp_netif_t *ethernet_mgr_get_netif(void)
{
    return s_eth_netif;
}
