#pragma once

#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief Start the HTTP web server on port 80 (serving MJPEG stream and KVM Web UI)
 *
 * @return ESP_OK on success, or error code.
 */
esp_err_t web_server_start(void);

/**
 * @brief Stop the HTTP web server
 *
 * @return ESP_OK on success, or error code.
 */
esp_err_t web_server_stop(void);

#ifdef __cplusplus
}
#endif
