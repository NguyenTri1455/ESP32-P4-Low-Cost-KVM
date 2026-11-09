#pragma once

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    float cpu0_usage;        // Core 0 CPU load percentage (0.0 - 100.0)
    float cpu1_usage;        // Core 1 CPU load percentage (0.0 - 100.0)
    size_t psram_total_kb;   // Total external PSRAM in KB
    size_t psram_free_kb;    // Free external PSRAM in KB
    size_t psram_used_kb;    // Used external PSRAM in KB
    float psram_used_pct;    // PSRAM used percentage
    size_t sram_total_kb;    // Total internal SRAM in KB
    size_t sram_free_kb;     // Free internal SRAM in KB
    size_t sram_min_free_kb; // Minimum free SRAM watermark in KB
    float sram_used_pct;     // SRAM used percentage
    float net_tx_mbps;       // Network TX bandwidth in Megabits per second
    float net_tx_kbps;       // Network TX bandwidth in Kilobytes per second
    uint64_t net_total_bytes;// Total TX bytes since boot
} system_metrics_t;

/**
 * @brief Initialize system stats tracking (registers zero-overhead idle hooks)
 */
esp_err_t system_stats_init(void);

/**
 * @brief Record transmitted network bytes (called on socket sends)
 * @param bytes Number of bytes sent
 */
void system_stats_record_tx_bytes(size_t bytes);

/**
 * @brief Calculate and retrieve current live system metrics
 * Should be called periodically (e.g. once per second by telemetry task)
 *
 * @param[out] out_metrics Pointer to struct to populate
 */
void system_stats_get_metrics(system_metrics_t *out_metrics);

#ifdef __cplusplus
}
#endif
