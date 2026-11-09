#pragma once

#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief Initialize USB Host subsystem and UVC video capture driver
 *
 * @return ESP_OK on success, or error code.
 */
esp_err_t uvc_stream_mgr_init(void);

/**
 * @brief Check if UVC capture device (USB-to-HDMI) is actively streaming
 *
 * @return true if streaming, false otherwise.
 */
bool uvc_stream_mgr_is_streaming(void);

/**
 * @brief Force a clean USB UVC reconnection cycle
 *
 * Shuts down the current stream handle, frees USB resources, and initiates
 * a fresh search and format negotiation with the capture card.
 *
 * @return ESP_OK on triggering reconnection.
 */
esp_err_t uvc_stream_mgr_force_reconnect(void);

/**
 * @brief Retrieve total number of USB reconnections performed since boot
 *
 * @return uint32_t reconnect count
 */
uint32_t uvc_stream_mgr_get_reconnect_count(void);

/**
 * @brief Retrieve a pointer to the latest completed video frame (JPEG)
 *
 * The returned pointer is guaranteed valid until the next frame completes.
 * Caller should process or stream it promptly.
 *
 * @param[out] out_buf      Pointer to frame data buffer
 * @param[out] out_len      Length of frame data in bytes
 * @param[out] out_frame_id Unique sequential frame identifier
 * @return ESP_OK if a frame is available, ESP_ERR_NOT_FOUND if no frames captured yet.
 */
esp_err_t uvc_stream_mgr_get_frame(const uint8_t **out_buf, size_t *out_len, uint32_t *out_frame_id);

/**
 * @brief Get the latest frame identifier (increments on every received frame)
 *
 * @return uint32_t frame id
 */
uint32_t uvc_stream_mgr_get_frame_id(void);

/**
 * @brief Wait for a new frame to become ready in PSRAM (event-driven notification)
 *
 * Blocks the calling task until a new video frame completes capturing into PSRAM
 * or until the timeout expires. Eliminates busy polling loops and reduces latency.
 *
 * @param timeout_ms Maximum time to wait in milliseconds
 * @return ESP_OK if a new frame is ready, ESP_ERR_TIMEOUT on timeout.
 */
esp_err_t uvc_stream_mgr_wait_for_frame(uint32_t timeout_ms);

/**
 * @brief Get the currently measured capture FPS
 *
 * @return float frames per second
 */
float uvc_stream_mgr_get_measured_fps(void);

/**
 * @brief Change the UVC capture resolution and target frame rate
 *
 * @param width       Horizontal resolution in pixels (e.g. 1920, 1280, 800, 640)
 * @param height      Vertical resolution in pixels (e.g. 1080, 720, 600, 480)
 * @param fps         Target frame rate (e.g. 30, 60)
 * @return ESP_OK on success or reconnection scheduled.
 */
esp_err_t uvc_stream_mgr_set_resolution(uint32_t width, uint32_t height, uint32_t fps);

/**
 * @brief Get stream parameters and statistics
 *
 * @param[out] width        Configured width
 * @param[out] height       Configured height
 * @param[out] target_fps   Configured target FPS
 * @param[out] total_frames Total frames captured since boot
 */
void uvc_stream_mgr_get_stats(uint32_t *width, uint32_t *height, uint32_t *target_fps, uint32_t *total_frames);

#ifdef __cplusplus
}
#endif
