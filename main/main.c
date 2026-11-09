#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_system.h"
#include "esp_log.h"
#include "nvs_flash.h"
#include "esp_heap_caps.h"

#include "board_pins.h"
#include "ethernet_mgr.h"
#include "uvc_stream_mgr.h"
#include "web_server.h"
#include "hid_device_mgr.h"
#include "system_stats.h"
#include "auth_mgr.h"

static const char *TAG = "app_main";

static void monitor_task(void *pvParameters)
{
    while (1) {
        vTaskDelay(pdMS_TO_TICKS(5000));

        uint32_t width = 0, height = 0, target_fps = 0, total_frames = 0;
        uvc_stream_mgr_get_stats(&width, &height, &target_fps, &total_frames);
        float measured_fps = uvc_stream_mgr_get_measured_fps();
        bool uvc_active = uvc_stream_mgr_is_streaming();
        bool hid_active = hid_device_mgr_is_mounted();
        bool eth_connected = ethernet_mgr_is_connected();
        const char *ip_str = ethernet_mgr_get_ip_str();

        size_t free_psram = heap_caps_get_free_size(MALLOC_CAP_SPIRAM);
        size_t free_sram = heap_caps_get_free_size(MALLOC_CAP_INTERNAL);

        uint32_t reconnects = uvc_stream_mgr_get_reconnect_count();

        ESP_LOGI(TAG, "------------------- SYSTEM STATUS -------------------");
        ESP_LOGI(TAG, "Ethernet: %s | IP: http://%s/",
                 eth_connected ? "LINK UP" : "WAITING FOR CABLE", ip_str);
        ESP_LOGI(TAG, "USB HID : %s (Target PC Keyboard/Mouse emulation on FS port)",
                 hid_active ? "CONNECTED / READY" : "NOT MOUNTED");
        ESP_LOGI(TAG, "HDMI UVC: %s | Res: %lux%lu @ %lu fps | Actual: %.1f FPS | Frames: %lu | Reconnects: %lu",
                 uvc_active ? "STREAMING" : "NO DEVICE",
                 (unsigned long)width, (unsigned long)height,
                 (unsigned long)target_fps,
                 measured_fps,
                 (unsigned long)total_frames,
                 (unsigned long)reconnects);
        ESP_LOGI(TAG, "Memory: Free PSRAM: %u KB / %u KB | Free SRAM: %u KB",
                 (unsigned)(free_psram / 1024),
                 (unsigned)(heap_caps_get_total_size(MALLOC_CAP_SPIRAM) / 1024),
                 (unsigned)(free_sram / 1024));
        ESP_LOGI(TAG, "-----------------------------------------------------");
    }
}

void app_main(void)
{
    ESP_LOGI(TAG, "=========================================================");
    ESP_LOGI(TAG, " Starting ESP32-P4 HDMI-over-Ethernet KVM System");
    ESP_LOGI(TAG, " Board: %s", BOARD_NAME);
    ESP_LOGI(TAG, "=========================================================");

    // 1. Initialize NVS (required for network stack, auth, and configs)
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);

    // Initialize System Stats & Authentication subsystems
    system_stats_init();
    auth_mgr_init();

    // 2. Report Memory
    size_t total_psram = heap_caps_get_total_size(MALLOC_CAP_SPIRAM);
    size_t free_psram = heap_caps_get_free_size(MALLOC_CAP_SPIRAM);
    size_t free_sram = heap_caps_get_free_size(MALLOC_CAP_INTERNAL);
    ESP_LOGI(TAG, "Total PSRAM: %u KB, Free PSRAM: %u KB, Free SRAM: %u KB",
             (unsigned)(total_psram / 1024),
             (unsigned)(free_psram / 1024),
             (unsigned)(free_sram / 1024));

    if (total_psram == 0) {
        ESP_LOGW(TAG, "WARNING: No PSRAM detected! Video streaming requires PSRAM.");
    }

    // 3. Initialize 100M Ethernet (IP101 PHY)
    ESP_LOGI(TAG, "Initializing Ethernet subsystem...");
    ESP_ERROR_CHECK(ethernet_mgr_init());

    // 4. Initialize USB Host UVC (HDMI video capture)
    ESP_LOGI(TAG, "Initializing USB Host UVC subsystem...");
    ESP_ERROR_CHECK(uvc_stream_mgr_init());

    // 5. Initialize USB Device HID (Keyboard & Mouse on FS port)
    ESP_LOGI(TAG, "Initializing USB Device HID subsystem (Full-Speed port)...");
    ESP_ERROR_CHECK(hid_device_mgr_init());

    // 6. Start HTTP Server for Web UI and Video Streaming
    ESP_LOGI(TAG, "Starting Web Display Server...");
    ESP_ERROR_CHECK(web_server_start());

    // 7. Create background diagnostic monitor task on Core 0 (low-priority maintenance)
    xTaskCreatePinnedToCore(monitor_task, "monitor_task", 4096, NULL, 1, NULL, 0);

    ESP_LOGI(TAG, "ESP32-P4 KVM Initialization complete! System is running.");
}
