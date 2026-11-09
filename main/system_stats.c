#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_freertos_hooks.h"
#include "esp_heap_caps.h"
#include "esp_timer.h"
#include "esp_log.h"

#include "system_stats.h"

static const char *TAG = "sys_stats";

// Idle tick counters (only incremented when a core is completely idle)
static volatile uint32_t s_idle_counts[2] = {0, 0};
static uint32_t s_max_idle[2] = {0, 0};
static float s_cached_cpu[2] = {0.0f, 0.0f};

// Network throughput tracking
static volatile uint64_t s_net_tx_bytes = 0;
static uint64_t s_net_last_tx_bytes = 0;
static int64_t s_last_calc_time = 0;
static float s_cached_tx_mbps = 0.0f;
static float s_cached_tx_kbps = 0.0f;

static bool idle_hook_core0(void)
{
    s_idle_counts[0]++;
    return true;
}

static bool idle_hook_core1(void)
{
    s_idle_counts[1]++;
    return true;
}

esp_err_t system_stats_init(void)
{
    ESP_LOGI(TAG, "Initializing zero-overhead system statistics hooks...");

    // Register idle hooks for Core 0 and Core 1
    esp_err_t err0 = esp_register_freertos_idle_hook_for_cpu(idle_hook_core0, 0);
    esp_err_t err1 = esp_register_freertos_idle_hook_for_cpu(idle_hook_core1, 1);

    if (err0 != ESP_OK || err1 != ESP_OK) {
        ESP_LOGW(TAG, "Could not register idle hooks (Core 0: %d, Core 1: %d)", err0, err1);
    }

    s_last_calc_time = esp_timer_get_time();
    return ESP_OK;
}

void system_stats_record_tx_bytes(size_t bytes)
{
    s_net_tx_bytes += bytes;
}

void system_stats_get_metrics(system_metrics_t *out_metrics)
{
    if (!out_metrics) return;

    int64_t now = esp_timer_get_time();
    int64_t elapsed_us = now - s_last_calc_time;

    // Recalculate rates every ~1 second (minimum 500ms)
    if (elapsed_us >= 500000LL) {
        float elapsed_sec = (float)elapsed_us / 1000000.0f;

        // 1. CPU Usage calculation from idle hooks
        uint32_t count0 = s_idle_counts[0];
        uint32_t count1 = s_idle_counts[1];
        s_idle_counts[0] = 0;
        s_idle_counts[1] = 0;

        // Auto-calibrate maximum possible idle loops per unit time
        uint32_t rate0 = (uint32_t)((float)count0 / elapsed_sec);
        uint32_t rate1 = (uint32_t)((float)count1 / elapsed_sec);

        if (rate0 > s_max_idle[0]) s_max_idle[0] = rate0;
        if (rate1 > s_max_idle[1]) s_max_idle[1] = rate1;

        if (s_max_idle[0] > 0) {
            float idle0 = (float)rate0 / (float)s_max_idle[0];
            if (idle0 > 1.0f) idle0 = 1.0f;
            s_cached_cpu[0] = (1.0f - idle0) * 100.0f;
        } else {
            s_cached_cpu[0] = 0.0f;
        }

        if (s_max_idle[1] > 0) {
            float idle1 = (float)rate1 / (float)s_max_idle[1];
            if (idle1 > 1.0f) idle1 = 1.0f;
            s_cached_cpu[1] = (1.0f - idle1) * 100.0f;
        } else {
            s_cached_cpu[1] = 0.0f;
        }

        // 2. Network throughput calculation
        uint64_t curr_tx = s_net_tx_bytes;
        uint64_t delta_bytes = (curr_tx >= s_net_last_tx_bytes) ? (curr_tx - s_net_last_tx_bytes) : 0;
        s_net_last_tx_bytes = curr_tx;

        s_cached_tx_kbps = ((float)delta_bytes / 1024.0f) / elapsed_sec;
        s_cached_tx_mbps = (s_cached_tx_kbps * 8.0f) / 1000.0f;

        s_last_calc_time = now;
    }

    out_metrics->cpu0_usage = s_cached_cpu[0];
    out_metrics->cpu1_usage = s_cached_cpu[1];

    // 3. PSRAM Metrics
    size_t psram_total = heap_caps_get_total_size(MALLOC_CAP_SPIRAM);
    size_t psram_free = heap_caps_get_free_size(MALLOC_CAP_SPIRAM);
    size_t psram_used = (psram_total >= psram_free) ? (psram_total - psram_free) : 0;

    out_metrics->psram_total_kb = psram_total / 1024;
    out_metrics->psram_free_kb = psram_free / 1024;
    out_metrics->psram_used_kb = psram_used / 1024;
    out_metrics->psram_used_pct = (psram_total > 0) ? (((float)psram_used / (float)psram_total) * 100.0f) : 0.0f;

    // 4. SRAM (Heap) Metrics
    size_t sram_total = heap_caps_get_total_size(MALLOC_CAP_INTERNAL);
    size_t sram_free = heap_caps_get_free_size(MALLOC_CAP_INTERNAL);
    size_t sram_min_free = heap_caps_get_minimum_free_size(MALLOC_CAP_INTERNAL);
    size_t sram_used = (sram_total >= sram_free) ? (sram_total - sram_free) : 0;

    out_metrics->sram_total_kb = sram_total / 1024;
    out_metrics->sram_free_kb = sram_free / 1024;
    out_metrics->sram_min_free_kb = sram_min_free / 1024;
    out_metrics->sram_used_pct = (sram_total > 0) ? (((float)sram_used / (float)sram_total) * 100.0f) : 0.0f;

    // 5. Network Metrics
    out_metrics->net_tx_mbps = s_cached_tx_mbps;
    out_metrics->net_tx_kbps = s_cached_tx_kbps;
    out_metrics->net_total_bytes = s_net_tx_bytes;
}
