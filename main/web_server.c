#include <stdio.h>
#include <string.h>
#include <stdarg.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/ringbuf.h"
#include "esp_log.h"
#include "esp_log_write.h"
#include "esp_http_server.h"
#include "esp_heap_caps.h"
#include "esp_timer.h"
#include "esp_ota_ops.h"
#include "esp_app_format.h"
#include "esp_system.h"

#include "board_pins.h"
#include "ethernet_mgr.h"
#include "uvc_stream_mgr.h"
#include "hid_device_mgr.h"
#include "cJSON.h"
#include "web_ui.h"
#include "web_server.h"

static const char *TAG = "web_srv";
static httpd_handle_t s_http_server = NULL;
static RingbufHandle_t s_log_ringbuf = NULL;
static vprintf_like_t s_orig_vprintf = NULL;
static volatile bool s_ws_sending = false;
static TaskHandle_t s_ws_task_handle = NULL;

static void get_telemetry_json(char *buf, size_t max_len)
{
    uint32_t width = 0, height = 0, target_fps = 0, total_frames = 0;
    uvc_stream_mgr_get_stats(&width, &height, &target_fps, &total_frames);

    size_t free_psram = heap_caps_get_free_size(MALLOC_CAP_SPIRAM);
    size_t free_sram = heap_caps_get_free_size(MALLOC_CAP_INTERNAL);
    float measured_fps = uvc_stream_mgr_get_measured_fps();
    bool is_streaming = uvc_stream_mgr_is_streaming();
    bool hid_mounted = hid_device_mgr_is_mounted();
    uint32_t reconnects = uvc_stream_mgr_get_reconnect_count();
    const char *ip = ethernet_mgr_get_ip_str();
    int64_t uptime_sec = esp_timer_get_time() / 1000000LL;

    snprintf(buf, max_len,
             "{"
             "\"type\":\"telemetry\","
             "\"board\":\"%s\","
             "\"ip\":\"%s\","
             "\"uvc_connected\":%s,"
             "\"hid_mounted\":%s,"
             "\"reconnect_count\":%lu,"
             "\"res\":\"%lux%lu\","
             "\"fps\":%.1f,"
             "\"target_fps\":%lu,"
             "\"total_frames\":%lu,"
             "\"uptime\":%lld,"
             "\"free_psram\":%u,"
             "\"free_sram\":%u"
             "}",
             BOARD_NAME,
             ip,
             is_streaming ? "true" : "false",
             hid_mounted ? "true" : "false",
             (unsigned long)reconnects,
             (unsigned long)width, (unsigned long)height,
             measured_fps,
             (unsigned long)target_fps,
             (unsigned long)total_frames,
             (long long)uptime_sec,
             (unsigned)free_psram,
             (unsigned)free_sram);
}

static void broadcast_ws_msg(const char *msg)
{
    if (!s_http_server) return;
    size_t num_clients = 16;
    int client_fds[16];
    esp_err_t err = httpd_get_client_list(s_http_server, &num_clients, client_fds);
    if (err != ESP_OK || num_clients == 0) return;

    httpd_ws_frame_t ws_pkt = {
        .final = true,
        .fragmented = false,
        .type = HTTPD_WS_TYPE_TEXT,
        .payload = (uint8_t *)msg,
        .len = strlen(msg)
    };

    s_ws_sending = true;
    for (size_t i = 0; i < num_clients; i++) {
        if (httpd_ws_get_fd_info(s_http_server, client_fds[i]) == HTTPD_WS_CLIENT_WEBSOCKET) {
            httpd_ws_send_frame_async(s_http_server, client_fds[i], &ws_pkt);
        }
    }
    s_ws_sending = false;
}

static void send_log_to_ws(const char *raw_log)
{
    char json_buf[512];
    int j = 0;
    j += snprintf(json_buf + j, sizeof(json_buf) - j, "{\"type\":\"log\",\"msg\":\"");
    for (int i = 0; raw_log[i] != '\0' && j < (int)sizeof(json_buf) - 8; i++) {
        char c = raw_log[i];
        if (c == '"') {
            if (j + 2 < (int)sizeof(json_buf) - 8) { json_buf[j++] = '\\'; json_buf[j++] = '"'; }
        } else if (c == '\\') {
            if (j + 2 < (int)sizeof(json_buf) - 8) { json_buf[j++] = '\\'; json_buf[j++] = '\\'; }
        } else if (c == '\n') {
            if (j + 2 < (int)sizeof(json_buf) - 8) { json_buf[j++] = '\\'; json_buf[j++] = 'n'; }
        } else if (c == '\r') {
            // omit \r
        } else if (c == '\t') {
            if (j + 2 < (int)sizeof(json_buf) - 8) { json_buf[j++] = '\\'; json_buf[j++] = 't'; }
        } else if ((unsigned char)c >= 32) {
            json_buf[j++] = c;
        }
    }
    snprintf(json_buf + j, sizeof(json_buf) - j, "\"}");
    broadcast_ws_msg(json_buf);
}

static int web_log_vprintf(const char *fmt, va_list args)
{
    va_list copy;
    va_copy(copy, args);
    int ret = 0;
    if (s_orig_vprintf) {
        ret = s_orig_vprintf(fmt, args);
    } else {
        ret = vprintf(fmt, args);
    }

    if (!s_log_ringbuf || s_ws_sending || (s_ws_task_handle != NULL && xTaskGetCurrentTaskHandle() == s_ws_task_handle)) {
        va_end(copy);
        return ret;
    }

    char log_line[256];
    int len = vsnprintf(log_line, sizeof(log_line), fmt, copy);
    va_end(copy);

    if (len > 0) {
        while (len > 0 && (log_line[len - 1] == '\r' || log_line[len - 1] == '\n')) {
            log_line[--len] = '\0';
        }
        if (len > 0) {
            xRingbufferSend(s_log_ringbuf, log_line, len + 1, 0);
        }
    }

    return ret;
}

static void ws_broadcast_task(void *pvParameter)
{
    s_ws_task_handle = xTaskGetCurrentTaskHandle();
    int64_t last_telemetry_time = 0;

    while (1) {
        // Drain up to 8 log messages
        for (int i = 0; i < 8; i++) {
            size_t item_size = 0;
            char *log_msg = (char *)xRingbufferReceive(s_log_ringbuf, &item_size, pdMS_TO_TICKS(15));
            if (log_msg != NULL) {
                send_log_to_ws(log_msg);
                vRingbufferReturnItem(s_log_ringbuf, (void *)log_msg);
            } else {
                break;
            }
        }

        // Broadcast telemetry once every second
        int64_t now = esp_timer_get_time();
        if (now - last_telemetry_time >= 1000000LL) {
            last_telemetry_time = now;
            char telem_buf[512];
            get_telemetry_json(telem_buf, sizeof(telem_buf));
            broadcast_ws_msg(telem_buf);
        }

        vTaskDelay(pdMS_TO_TICKS(40));
    }
}

static esp_err_t index_handler(httpd_req_t *req)
{
    httpd_resp_set_type(req, "text/html");
    return httpd_resp_send(req, HTML_INDEX_PAGE, HTTPD_RESP_USE_STRLEN);
}

static esp_err_t snapshot_handler(httpd_req_t *req)
{
    const uint8_t *frame_buf = NULL;
    size_t frame_len = 0;
    uint32_t frame_id = 0;

    esp_err_t err = uvc_stream_mgr_get_frame(&frame_buf, &frame_len, &frame_id);
    if (err != ESP_OK || !frame_buf || frame_len == 0) {
        httpd_resp_send_err(req, HTTPD_500_INTERNAL_SERVER_ERROR, "No HDMI frame captured yet");
        return ESP_FAIL;
    }

    httpd_resp_set_type(req, "image/jpeg");
    httpd_resp_set_hdr(req, "Content-Disposition", "inline; filename=capture.jpg");
    httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
    return httpd_resp_send(req, (const char *)frame_buf, frame_len);
}

static esp_err_t status_handler(httpd_req_t *req)
{
    char json_buf[512];
    get_telemetry_json(json_buf, sizeof(json_buf));

    httpd_resp_set_type(req, "application/json");
    httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
    return httpd_resp_send(req, json_buf, HTTPD_RESP_USE_STRLEN);
}

static void restart_task(void *pvParameter)
{
    ESP_LOGI(TAG, "Rebooting system in 1.5 seconds...");
    vTaskDelay(pdMS_TO_TICKS(1500));
    esp_restart();
}

static esp_err_t ota_update_handler(httpd_req_t *req)
{
    if (req->content_len <= 0) {
        ESP_LOGE(TAG, "OTA failed: Content-Length must be > 0");
        httpd_resp_send_err(req, HTTPD_400_BAD_REQUEST, "Content-Length header required");
        return ESP_FAIL;
    }

    const esp_partition_t *update_partition = esp_ota_get_next_update_partition(NULL);
    if (update_partition == NULL) {
        ESP_LOGE(TAG, "OTA failed: No inactive OTA partition found");
        httpd_resp_set_type(req, "application/json");
        httpd_resp_set_status(req, "500 Internal Server Error");
        httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
        httpd_resp_send(req, "{\"status\":\"error\",\"message\":\"No OTA partition available in partition table. Flash dual-OTA partition table via USB first.\"}", HTTPD_RESP_USE_STRLEN);
        return ESP_FAIL;
    }

    ESP_LOGI(TAG, "Starting OTA flashing to partition '%s' (0x%08lx, size %lu KB), total image size: %d bytes",
             update_partition->label, (unsigned long)update_partition->address,
             (unsigned long)(update_partition->size / 1024), req->content_len);

    esp_ota_handle_t ota_handle = 0;
    esp_err_t err = esp_ota_begin(update_partition, OTA_WITH_SEQUENTIAL_WRITES, &ota_handle);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "esp_ota_begin failed: %s", esp_err_to_name(err));
        httpd_resp_send_err(req, HTTPD_500_INTERNAL_SERVER_ERROR, "OTA flash erase failed");
        return ESP_FAIL;
    }

    char *buf = (char *)heap_caps_malloc(4096, MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT);
    if (!buf) {
        ESP_LOGE(TAG, "Failed to allocate 4KB OTA receive buffer");
        esp_ota_abort(ota_handle);
        httpd_resp_send_err(req, HTTPD_500_INTERNAL_SERVER_ERROR, "No memory for OTA buffer");
        return ESP_FAIL;
    }

    int remaining = req->content_len;
    bool is_first_chunk = true;
    int progress_interval = req->content_len / 10;
    if (progress_interval <= 0) progress_interval = 1024;
    int next_log = progress_interval;

    while (remaining > 0) {
        int to_recv = (remaining < 4096) ? remaining : 4096;
        int recved = httpd_req_recv(req, buf, to_recv);
        if (recved <= 0) {
            if (recved == HTTPD_SOCK_ERR_TIMEOUT) {
                continue;
            }
            ESP_LOGE(TAG, "OTA network error during receive: %d", recved);
            esp_ota_abort(ota_handle);
            free(buf);
            httpd_resp_send_err(req, HTTPD_500_INTERNAL_SERVER_ERROR, "Network receive error during OTA");
            return ESP_FAIL;
        }

        if (is_first_chunk) {
            if (recved >= sizeof(esp_image_header_t)) {
                esp_image_header_t *img_hdr = (esp_image_header_t *)buf;
                if (img_hdr->magic != ESP_IMAGE_HEADER_MAGIC) {
                    ESP_LOGE(TAG, "OTA rejected: Invalid image magic (0x%02x, expected 0x%02x)",
                             img_hdr->magic, ESP_IMAGE_HEADER_MAGIC);
                    esp_ota_abort(ota_handle);
                    free(buf);
                    httpd_resp_send_err(req, HTTPD_400_BAD_REQUEST, "Invalid binary image format");
                    return ESP_FAIL;
                }
            }
            is_first_chunk = false;
        }

        err = esp_ota_write(ota_handle, (const void *)buf, recved);
        if (err != ESP_OK) {
            ESP_LOGE(TAG, "esp_ota_write failed: %s", esp_err_to_name(err));
            esp_ota_abort(ota_handle);
            free(buf);
            httpd_resp_send_err(req, HTTPD_500_INTERNAL_SERVER_ERROR, "Flash write failed");
            return ESP_FAIL;
        }

        remaining -= recved;
        int written = req->content_len - remaining;
        if (written >= next_log || remaining == 0) {
            ESP_LOGI(TAG, "OTA Progress: %d / %d bytes (%d%%)",
                     written, req->content_len, (int)((written * 100LL) / req->content_len));
            next_log += progress_interval;
        }
    }
    free(buf);

    err = esp_ota_end(ota_handle);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "esp_ota_end failed: %s (image corrupted or invalid checksum)", esp_err_to_name(err));
        httpd_resp_send_err(req, HTTPD_500_INTERNAL_SERVER_ERROR, "Image checksum validation failed");
        return ESP_FAIL;
    }

    err = esp_ota_set_boot_partition(update_partition);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "esp_ota_set_boot_partition failed: %s", esp_err_to_name(err));
        httpd_resp_send_err(req, HTTPD_500_INTERNAL_SERVER_ERROR, "Failed to switch boot partition");
        return ESP_FAIL;
    }

    ESP_LOGI(TAG, "OTA Successful! New active partition: '%s'. Restarting in 1.5s...", update_partition->label);

    httpd_resp_set_type(req, "application/json");
    httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
    httpd_resp_send(req, "{\"status\":\"ok\",\"message\":\"OTA update complete! Rebooting device into new firmware...\"}", HTTPD_RESP_USE_STRLEN);

    // Schedule reboot
    xTaskCreate(restart_task, "restart_task", 2048, NULL, 5, NULL);
    return ESP_OK;
}

static esp_err_t reconnect_usb_handler(httpd_req_t *req)
{
    ESP_LOGI(TAG, "HTTP API: Forced USB Reconnect requested by client");
    uvc_stream_mgr_force_reconnect();

    const char *resp = "{\"status\":\"ok\",\"message\":\"Forced USB reconnect triggered\"}";
    httpd_resp_set_type(req, "application/json");
    httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
    return httpd_resp_send(req, resp, HTTPD_RESP_USE_STRLEN);
}

static void mjpeg_stream_worker_task(void *pvParameters)
{
    httpd_req_t *req = (httpd_req_t *)pvParameters;
    int sockfd = httpd_req_to_sockfd(req);
    ESP_LOGI(TAG, "[Core %d] Dedicated FreeRTOS MJPEG stream task started (sock %d)",
             xPortGetCoreID(), sockfd);

    esp_err_t res = httpd_resp_set_type(req, "multipart/x-mixed-replace; boundary=ESP32P4_FRAME_BOUNDARY");
    if (res == ESP_OK) {
        httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
        httpd_resp_set_hdr(req, "Cache-Control", "no-cache, no-store, must-revalidate");
        httpd_resp_set_hdr(req, "Pragma", "no-cache");

        char part_buf[128];
        static const char *STREAM_BOUNDARY = "\r\n--ESP32P4_FRAME_BOUNDARY\r\n";
        static const char *STREAM_PART = "Content-Type: image/jpeg\r\nContent-Length: %zu\r\n\r\n";

        uint32_t last_frame_id = 0;
        const uint8_t *frame_buf = NULL;
        size_t frame_len = 0;

        while (true) {
            // Wait for a newly completed frame from UVC engine (event-driven, zero-latency wake up)
            esp_err_t wait_err = uvc_stream_mgr_wait_for_frame(50);

            uint32_t current_frame_id = uvc_stream_mgr_get_frame_id();
            if (wait_err == ESP_OK && current_frame_id != last_frame_id && current_frame_id != 0) {
                esp_err_t err = uvc_stream_mgr_get_frame(&frame_buf, &frame_len, &last_frame_id);
                if (err == ESP_OK && frame_buf != NULL && frame_len > 0) {
                    // Send multipart boundary
                    res = httpd_resp_send_chunk(req, STREAM_BOUNDARY, strlen(STREAM_BOUNDARY));
                    if (res != ESP_OK) break;

                    // Send content length header
                    int hlen = snprintf(part_buf, sizeof(part_buf), STREAM_PART, frame_len);
                    res = httpd_resp_send_chunk(req, part_buf, hlen);
                    if (res != ESP_OK) break;

                    // Send frame payload
                    res = httpd_resp_send_chunk(req, (const char *)frame_buf, frame_len);
                    if (res != ESP_OK) break;
                }
            }

            // Check if client disconnected
            if (httpd_req_to_sockfd(req) < 0) {
                break;
            }
        }
    }

    ESP_LOGI(TAG, "MJPEG streaming client disconnected, freeing async FreeRTOS task");
    httpd_req_async_handler_complete(req);
    vTaskDelete(NULL);
}

static esp_err_t stream_handler(httpd_req_t *req)
{
    ESP_LOGI(TAG, "Incoming MJPEG stream request -> spawning dedicated FreeRTOS worker thread");

    httpd_req_t *async_req = NULL;
    esp_err_t err = httpd_req_async_handler_begin(req, &async_req);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to begin async HTTP request: %s", esp_err_to_name(err));
        return err;
    }

    BaseType_t ret = xTaskCreatePinnedToCore(
        mjpeg_stream_worker_task,
        "mjpeg_stream",
        8192,
        (void *)async_req,
        6, // Worker priority (Core 1)
        NULL,
        1  // Pin to Core 1: Video pipeline dedicated core
    );

    if (ret != pdPASS) {
        ESP_LOGE(TAG, "Failed to create FreeRTOS mjpeg_stream task");
        httpd_req_async_handler_complete(async_req);
        return ESP_FAIL;
    }

    // Immediately return ESP_OK: HTTP server main thread remains responsive to all other requests!
    return ESP_OK;
}

static esp_err_t ws_handler(httpd_req_t *req)
{
    if (req->method == HTTP_GET) {
        ESP_LOGI(TAG, "WebSocket client handshake complete");
        return ESP_OK;
    }
    httpd_ws_frame_t ws_pkt;
    memset(&ws_pkt, 0, sizeof(httpd_ws_frame_t));
    ws_pkt.type = HTTPD_WS_TYPE_TEXT;
    esp_err_t ret = httpd_ws_recv_frame(req, &ws_pkt, 0);
    if (ret != ESP_OK) return ret;

    if (ws_pkt.len > 0) {
        uint8_t *buf = calloc(1, ws_pkt.len + 1);
        if (buf) {
            ws_pkt.payload = buf;
            ret = httpd_ws_recv_frame(req, &ws_pkt, ws_pkt.len);
            if (ret == ESP_OK) {
                cJSON *root = cJSON_Parse((const char *)buf);
                if (root) {
                    cJSON *type_item = cJSON_GetObjectItem(root, "type");
                    if (cJSON_IsString(type_item) && (type_item->valuestring != NULL)) {
                        const char *type = type_item->valuestring;
                        if (strcmp(type, "key") == 0) {
                            uint8_t mod = 0;
                            cJSON *mod_item = cJSON_GetObjectItem(root, "mod");
                            if (cJSON_IsNumber(mod_item)) {
                                mod = (uint8_t)mod_item->valueint;
                            }
                            uint8_t keys[6] = {0};
                            cJSON *keys_arr = cJSON_GetObjectItem(root, "keys");
                            if (cJSON_IsArray(keys_arr)) {
                                int count = cJSON_GetArraySize(keys_arr);
                                if (count > 6) count = 6;
                                for (int i = 0; i < count; i++) {
                                    cJSON *k = cJSON_GetArrayItem(keys_arr, i);
                                    if (cJSON_IsNumber(k)) {
                                        keys[i] = (uint8_t)k->valueint;
                                    }
                                }
                            }
                            hid_device_mgr_send_keyboard(mod, keys);
                        } else if (strcmp(type, "mouse") == 0) {
                            uint8_t btn = 0;
                            int8_t dx = 0, dy = 0, wheel = 0;
                            cJSON *btn_item = cJSON_GetObjectItem(root, "btn");
                            if (cJSON_IsNumber(btn_item)) btn = (uint8_t)btn_item->valueint;
                            cJSON *dx_item = cJSON_GetObjectItem(root, "dx");
                            if (cJSON_IsNumber(dx_item)) dx = (int8_t)dx_item->valueint;
                            cJSON *dy_item = cJSON_GetObjectItem(root, "dy");
                            if (cJSON_IsNumber(dy_item)) dy = (int8_t)dy_item->valueint;
                            cJSON *wh_item = cJSON_GetObjectItem(root, "wheel");
                            if (cJSON_IsNumber(wh_item)) wheel = (int8_t)wh_item->valueint;
                            hid_device_mgr_send_mouse(btn, dx, dy, wheel);
                        } else if (strcmp(type, "macro") == 0) {
                            cJSON *name_item = cJSON_GetObjectItem(root, "name");
                            if (cJSON_IsString(name_item) && name_item->valuestring) {
                                hid_device_mgr_send_macro(name_item->valuestring);
                            }
                        } else if (strcmp(type, "release_all") == 0) {
                            hid_device_mgr_keyboard_release_all();
                        }
                    }
                    cJSON_Delete(root);
                }
            }
            free(buf);
        }
    }
    return ESP_OK;
}

static esp_err_t resolution_handler(httpd_req_t *req)
{
    char buf[128];
    int total_len = req->content_len;
    if (total_len <= 0 || total_len >= sizeof(buf)) {
        httpd_resp_send_err(req, HTTPD_400_BAD_REQUEST, "Invalid request length");
        return ESP_FAIL;
    }

    int received = httpd_req_recv(req, buf, total_len);
    if (received <= 0) {
        httpd_resp_send_err(req, HTTPD_400_BAD_REQUEST, "Failed to read request body");
        return ESP_FAIL;
    }
    buf[received] = '\0';

    uint32_t w = 0, h = 0, fps = 30;
    // Check if format is e.g. "1920x1080@30" or JSON {"res":"1920x1080@30"} or {"res":"1280x720"}
    if (sscanf(buf, "%lux%lu@%lu", &w, &h, &fps) < 2) {
        char *p_res = strstr(buf, "\"res\":");
        if (p_res) {
            int matched = sscanf(p_res, "\"res\":\"%lux%lu@%lu\"", &w, &h, &fps);
            if (matched < 3) {
                sscanf(p_res, "\"res\":\"%lux%lu\"", &w, &h);
                fps = 30;
            }
        } else {
            char *p_w = strstr(buf, "\"width\":");
            char *p_h = strstr(buf, "\"height\":");
            if (p_w && p_h) {
                sscanf(p_w, "\"width\":%lu", &w);
                sscanf(p_h, "\"height\":%lu", &h);
            }
        }
    }

    if (w == 0 || h == 0) {
        httpd_resp_send_err(req, HTTPD_400_BAD_REQUEST, "Invalid resolution parameters (e.g. 1920x1080@30)");
        return ESP_FAIL;
    }

    ESP_LOGI(TAG, "HTTP API: Change resolution to %lux%lu @ %lu fps",
             (unsigned long)w, (unsigned long)h, (unsigned long)fps);
    uvc_stream_mgr_set_resolution(w, h, fps);

    char resp[128];
    snprintf(resp, sizeof(resp), "{\"status\":\"ok\",\"res\":\"%lux%lu\",\"fps\":%lu}",
             (unsigned long)w, (unsigned long)h, (unsigned long)fps);
    httpd_resp_set_type(req, "application/json");
    httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
    return httpd_resp_send(req, resp, HTTPD_RESP_USE_STRLEN);
}

esp_err_t web_server_start(void)
{
    if (s_http_server != NULL) {
        ESP_LOGW(TAG, "Web server already running");
        return ESP_OK;
    }

    httpd_config_t config = HTTPD_DEFAULT_CONFIG();
    config.server_port = 80;
    config.ctrl_port = 32768;
    config.max_open_sockets = 7;
    config.stack_size = 8192;
    config.lru_purge_enable = true;
    config.recv_wait_timeout = 30;
    config.send_wait_timeout = 30;
    config.core_id = 0;           // Pin HTTP server & WebSocket listener to Core 0 (Network & Input core)
    config.task_priority = 7;     // Priority 7 (high responsiveness for KVM input handling)

    ESP_LOGI(TAG, "Starting HTTP server on port %d (Core %d, Priority %d)...",
             config.server_port, config.core_id, config.task_priority);
    esp_err_t err = httpd_start(&s_http_server, &config);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to start HTTP server: %s", esp_err_to_name(err));
        return err;
    }

    // Register /
    const httpd_uri_t uri_index = {
        .uri       = "/",
        .method    = HTTP_GET,
        .handler   = index_handler,
        .user_ctx  = NULL
    };
    httpd_register_uri_handler(s_http_server, &uri_index);

    // Register /stream
    const httpd_uri_t uri_stream = {
        .uri       = "/stream",
        .method    = HTTP_GET,
        .handler   = stream_handler,
        .user_ctx  = NULL
    };
    httpd_register_uri_handler(s_http_server, &uri_stream);

    // Register /snapshot
    const httpd_uri_t uri_snapshot = {
        .uri       = "/snapshot",
        .method    = HTTP_GET,
        .handler   = snapshot_handler,
        .user_ctx  = NULL
    };
    httpd_register_uri_handler(s_http_server, &uri_snapshot);

    // Register /api/status
    const httpd_uri_t uri_status = {
        .uri       = "/api/status",
        .method    = HTTP_GET,
        .handler   = status_handler,
        .user_ctx  = NULL
    };
    httpd_register_uri_handler(s_http_server, &uri_status);

    // Register /api/reconnect_usb
    const httpd_uri_t uri_reconnect = {
        .uri       = "/api/reconnect_usb",
        .method    = HTTP_POST,
        .handler   = reconnect_usb_handler,
        .user_ctx  = NULL
    };
    httpd_register_uri_handler(s_http_server, &uri_reconnect);

    // Register /api/ota
    const httpd_uri_t uri_ota = {
        .uri       = "/api/ota",
        .method    = HTTP_POST,
        .handler   = ota_update_handler,
        .user_ctx  = NULL
    };
    httpd_register_uri_handler(s_http_server, &uri_ota);

    // Register /api/resolution
    const httpd_uri_t uri_resolution = {
        .uri       = "/api/resolution",
        .method    = HTTP_POST,
        .handler   = resolution_handler,
        .user_ctx  = NULL
    };
    httpd_register_uri_handler(s_http_server, &uri_resolution);

    // Register /ws
    const httpd_uri_t uri_ws = {
        .uri          = "/ws",
        .method       = HTTP_GET,
        .handler      = ws_handler,
        .user_ctx     = NULL,
        .is_websocket = true
    };
    httpd_register_uri_handler(s_http_server, &uri_ws);

    // Initialize Log Ringbuffer and Interceptor
    if (s_log_ringbuf == NULL) {
        s_log_ringbuf = xRingbufferCreate(32768, RINGBUF_TYPE_NOSPLIT);
        if (s_log_ringbuf != NULL) {
            s_orig_vprintf = esp_log_set_vprintf(web_log_vprintf);
            xTaskCreatePinnedToCore(ws_broadcast_task, "ws_broadcast", 4096, NULL, 4, &s_ws_task_handle, 0);
            ESP_LOGI(TAG, "WebSocket live log streamer and telemetry broadcaster active");
        }
    }

    ESP_LOGI(TAG, "HTTP Server started with endpoints: /, /stream, /snapshot, /ws, /api/status, /api/resolution, /api/reconnect_usb, /api/ota");
    return ESP_OK;
}

esp_err_t web_server_stop(void)
{
    if (s_http_server) {
        ESP_LOGI(TAG, "Stopping HTTP server...");
        httpd_stop(s_http_server);
        s_http_server = NULL;
    }
    return ESP_OK;
}
