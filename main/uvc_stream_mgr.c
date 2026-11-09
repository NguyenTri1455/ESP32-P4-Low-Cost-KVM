#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"
#include "esp_log.h"
#include "esp_heap_caps.h"
#include "esp_timer.h"
#include "usb/usb_host.h"
#include "usb/uvc_host.h"

#include "board_pins.h"
#include "uvc_stream_mgr.h"

static const char *TAG = "uvc_mgr";

#define USB_HOST_TASK_PRIORITY      20
#define UVC_STREAM_TASK_PRIORITY    19
#define UVC_STALL_TIMEOUT_US        4000000ULL // 4.0 seconds without frames = stall

/* Frame buffer storage in PSRAM */
static uint8_t *s_frame_buffers[2] = {NULL, NULL};
static size_t s_frame_lengths[2] = {0, 0};
static volatile int s_front_buf_idx = 0;
static volatile uint32_t s_latest_frame_id = 0;
static volatile uint32_t s_total_frames = 0;
static portMUX_TYPE s_spinlock = portMUX_INITIALIZER_UNLOCKED;

/* Stream status, stats, and auto-reconnect flags */
static volatile bool s_is_streaming = false;
static volatile bool s_force_reconnect = false;
static volatile uint32_t s_reconnect_count = 0;
static volatile int64_t s_last_frame_time = 0;

static volatile uint32_t s_target_width = BOARD_UVC_DEFAULT_WIDTH;
static volatile uint32_t s_target_height = BOARD_UVC_DEFAULT_HEIGHT;
static volatile uint32_t s_target_fps = BOARD_UVC_DEFAULT_FPS;

static float s_measured_fps = 0.0f;
static int64_t s_fps_last_time = 0;
static uint32_t s_fps_last_count = 0;

/* UVC Stream Handle */
static uvc_host_stream_hdl_t s_uvc_stream = NULL;

static void update_fps_calc(void)
{
    int64_t now = esp_timer_get_time();
    int64_t elapsed = now - s_fps_last_time;
    if (elapsed >= 1000000) { // 1 second rolling window
        uint32_t count = s_total_frames;
        s_measured_fps = (float)(count - s_fps_last_count) * 1000000.0f / (float)elapsed;
        s_fps_last_count = count;
        s_fps_last_time = now;
        ESP_LOGD(TAG, "Capture FPS: %.1f, Total: %lu, Reconnects: %lu",
                 s_measured_fps, (unsigned long)count, (unsigned long)s_reconnect_count);
    }
}

static bool frame_callback(const uvc_host_frame_t *frame, void *user_ctx)
{
    if (!frame || frame->data_len == 0 || !frame->data) {
        return true;
    }

    // Verify JPEG Magic / SOI marker (0xFF, 0xD8)
    if (frame->data_len < 4 || frame->data[0] != 0xFF || frame->data[1] != 0xD8) {
        return true;
    }

    int back_idx = 1 - s_front_buf_idx;
    if (frame->data_len <= BOARD_UVC_MAX_FRAME_SIZE && s_frame_buffers[back_idx] != NULL) {
        memcpy(s_frame_buffers[back_idx], frame->data, frame->data_len);
        s_frame_lengths[back_idx] = frame->data_len;

        portENTER_CRITICAL(&s_spinlock);
        s_front_buf_idx = back_idx;
        s_latest_frame_id++;
        s_total_frames++;
        s_last_frame_time = esp_timer_get_time();
        portEXIT_CRITICAL(&s_spinlock);

        update_fps_calc();
    } else {
        ESP_LOGW(TAG, "Frame dropped: size %u exceeds buffer %u",
                 (unsigned)frame->data_len, (unsigned)BOARD_UVC_MAX_FRAME_SIZE);
    }

    // Return true to immediately recycle the buffer in UVC driver
    return true;
}

static void stream_event_callback(const uvc_host_stream_event_data_t *event, void *user_ctx)
{
    switch (event->type) {
    case UVC_HOST_DEVICE_DISCONNECTED:
        ESP_LOGW(TAG, "UVC HDMI Capture Device Disconnected!");
        s_is_streaming = false;
        if (event->device_disconnected.stream_hdl != NULL) {
            uvc_host_stream_close(event->device_disconnected.stream_hdl);
            s_uvc_stream = NULL;
        }
        break;
    case UVC_HOST_TRANSFER_ERROR:
        ESP_LOGW(TAG, "UVC USB Transfer Error: %d", event->transfer_error.error);
        break;
    case UVC_HOST_FRAME_BUFFER_OVERFLOW:
        ESP_LOGW(TAG, "UVC Frame Buffer Overflow");
        break;
    case UVC_HOST_FRAME_BUFFER_UNDERFLOW:
        ESP_LOGW(TAG, "UVC Frame Buffer Underflow");
        break;
    default:
        ESP_LOGD(TAG, "UVC Event: %d", event->type);
        break;
    }
}

static void usb_lib_task(void *arg)
{
    ESP_LOGI(TAG, "USB Host Library Task running");
    while (1) {
        uint32_t event_flags = 0;
        usb_host_lib_handle_events(portMAX_DELAY, &event_flags);
        if (event_flags & USB_HOST_LIB_EVENT_FLAGS_NO_CLIENTS) {
            ESP_LOGD(TAG, "USB: No clients, freeing devices");
            usb_host_device_free_all();
        }
        if (event_flags & USB_HOST_LIB_EVENT_FLAGS_ALL_FREE) {
            ESP_LOGD(TAG, "USB: All devices freed");
        }
    }
}

static void uvc_stream_task(void *arg)
{
    ESP_LOGI(TAG, "UVC Auto-Reconnect Supervisor Task running");

    while (1) {
        s_force_reconnect = false;
        uint32_t req_w = s_target_width;
        uint32_t req_h = s_target_height;
        uint32_t req_fps = s_target_fps;

        const uvc_host_stream_config_t stream_config = {
            .event_cb = stream_event_callback,
            .frame_cb = frame_callback,
            .user_ctx = NULL,
            .usb = {
                .vid = UVC_HOST_ANY_VID,
                .pid = UVC_HOST_ANY_PID,
                .uvc_stream_index = 0,
            },
            .vs_format = {
                .h_res = req_w,
                .v_res = req_h,
                .fps = req_fps,
                .format = UVC_VS_FORMAT_MJPEG,
            },
            .advanced = {
                .frame_size = 0, // Auto-negotiated
                .number_of_frame_buffers = 3,
                .frame_heap_caps = MALLOC_CAP_SPIRAM,
                .number_of_urbs = 4,
                .urb_size = 0, // Default: 4x MPS
            },
        };

        ESP_LOGI(TAG, "Searching for USB-to-HDMI capture card (%ux%u @ %u fps MJPEG)...",
                 (unsigned)req_w, (unsigned)req_h, (unsigned)req_fps);

        s_uvc_stream = NULL;
        esp_err_t err = uvc_host_stream_open(&stream_config, pdMS_TO_TICKS(2000), &s_uvc_stream);
        if (err == ESP_OK && s_uvc_stream != NULL) {
            ESP_LOGI(TAG, "USB-to-HDMI capture device detected and opened!");
            err = uvc_host_stream_start(s_uvc_stream);
            if (err == ESP_OK) {
                ESP_LOGI(TAG, "UVC streaming active! HDMI video is now capturing.");
                s_is_streaming = true;
                s_last_frame_time = esp_timer_get_time();
                s_fps_last_time = s_last_frame_time;
                s_fps_last_count = s_total_frames;

                // Watchdog loop: monitors stream health and frame freshness
                while (s_is_streaming && !s_force_reconnect) {
                    vTaskDelay(pdMS_TO_TICKS(500));

                    // Check for video stream stall (no frames received for >4 seconds while streaming)
                    int64_t time_since_frame = esp_timer_get_time() - s_last_frame_time;
                    if (s_total_frames > 0 && time_since_frame > UVC_STALL_TIMEOUT_US) {
                        ESP_LOGW(TAG, "UVC stream stall detected (no frames for %.1f s). Auto-reconnecting...",
                                 (float)time_since_frame / 1000000.0f);
                        break;
                    }
                }
            } else {
                ESP_LOGE(TAG, "Failed to start UVC stream: %s", esp_err_to_name(err));
            }

            // Clean teardown for reconnection
            s_is_streaming = false;
            if (s_uvc_stream != NULL) {
                ESP_LOGI(TAG, "Closing UVC stream handle for clean reconnect...");
                uvc_host_stream_close(s_uvc_stream);
                s_uvc_stream = NULL;
            }
            usb_host_device_free_all();
            s_reconnect_count++;
            ESP_LOGI(TAG, "USB cleanup complete. Total reconnects: %lu", (unsigned long)s_reconnect_count);
        } else {
            ESP_LOGD(TAG, "Capture device not ready yet (%s). Retrying in 1.5s...", esp_err_to_name(err));
        }

        // Wait before next connection attempt (debounce hotplug)
        vTaskDelay(pdMS_TO_TICKS(1500));
    }
}

esp_err_t uvc_stream_mgr_init(void)
{
    ESP_LOGI(TAG, "Initializing UVC Stream Manager for %s...", BOARD_NAME);

    // 1. Allocate dual frame buffers in external PSRAM
    ESP_LOGI(TAG, "Allocating 2x %u KB frame buffers in PSRAM...", (unsigned)(BOARD_UVC_MAX_FRAME_SIZE / 1024));
    s_frame_buffers[0] = (uint8_t *)heap_caps_malloc(BOARD_UVC_MAX_FRAME_SIZE, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
    s_frame_buffers[1] = (uint8_t *)heap_caps_malloc(BOARD_UVC_MAX_FRAME_SIZE, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);

    if (!s_frame_buffers[0] || !s_frame_buffers[1]) {
        ESP_LOGE(TAG, "Failed to allocate frame buffers in PSRAM! Check SPIRAM config.");
        return ESP_ERR_NO_MEM;
    }
    ESP_LOGI(TAG, "PSRAM frame buffers allocated: [%p, %p]", s_frame_buffers[0], s_frame_buffers[1]);

    // 2. Install USB Host Core Driver
    ESP_LOGI(TAG, "Installing USB Host driver...");
    const usb_host_config_t host_config = {
        .skip_phy_setup = false,
        .intr_flags = ESP_INTR_FLAG_LOWMED,
    };
    esp_err_t err = usb_host_install(&host_config);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "usb_host_install failed: %s", esp_err_to_name(err));
        return err;
    }

    // 3. Create USB library event task
    BaseType_t task_ret = xTaskCreatePinnedToCore(
        usb_lib_task,
        "usb_lib_task",
        4096,
        NULL,
        USB_HOST_TASK_PRIORITY,
        NULL,
        0
    );
    if (task_ret != pdPASS) {
        ESP_LOGE(TAG, "Failed to create usb_lib_task");
        return ESP_FAIL;
    }

    // 4. Install UVC Class Driver
    ESP_LOGI(TAG, "Installing UVC Host Class driver...");
    const uvc_host_driver_config_t uvc_driver_config = {
        .driver_task_stack_size = 4096,
        .driver_task_priority = USB_HOST_TASK_PRIORITY + 1,
        .xCoreID = 0,
        .create_background_task = true,
    };
    err = uvc_host_install(&uvc_driver_config);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "uvc_host_install failed: %s", esp_err_to_name(err));
        return err;
    }

    // 5. Create UVC stream supervisor task
    task_ret = xTaskCreatePinnedToCore(
        uvc_stream_task,
        "uvc_stream_task",
        4096,
        NULL,
        UVC_STREAM_TASK_PRIORITY,
        NULL,
        1 // Run capture supervisor on Core 1
    );
    if (task_ret != pdPASS) {
        ESP_LOGE(TAG, "Failed to create uvc_stream_task");
        return ESP_FAIL;
    }

    ESP_LOGI(TAG, "UVC Stream Manager initialized with auto-reconnect support");
    return ESP_OK;
}

bool uvc_stream_mgr_is_streaming(void)
{
    return s_is_streaming;
}

esp_err_t uvc_stream_mgr_force_reconnect(void)
{
    ESP_LOGI(TAG, "User requested forced USB reconnection");
    s_force_reconnect = true;
    s_is_streaming = false;
    return ESP_OK;
}

uint32_t uvc_stream_mgr_get_reconnect_count(void)
{
    return s_reconnect_count;
}

esp_err_t uvc_stream_mgr_get_frame(const uint8_t **out_buf, size_t *out_len, uint32_t *out_frame_id)
{
    if (!out_buf || !out_len) {
        return ESP_ERR_INVALID_ARG;
    }

    portENTER_CRITICAL(&s_spinlock);
    int idx = s_front_buf_idx;
    size_t len = s_frame_lengths[idx];
    uint32_t fid = s_latest_frame_id;
    const uint8_t *ptr = s_frame_buffers[idx];
    portEXIT_CRITICAL(&s_spinlock);

    if (len == 0 || ptr == NULL || fid == 0) {
        return ESP_ERR_NOT_FOUND;
    }

    *out_buf = ptr;
    *out_len = len;
    if (out_frame_id) {
        *out_frame_id = fid;
    }
    return ESP_OK;
}

uint32_t uvc_stream_mgr_get_frame_id(void)
{
    return s_latest_frame_id;
}

float uvc_stream_mgr_get_measured_fps(void)
{
    return s_measured_fps;
}

esp_err_t uvc_stream_mgr_set_resolution(uint32_t width, uint32_t height, uint32_t fps)
{
    if (width == 0 || height == 0) {
        return ESP_ERR_INVALID_ARG;
    }
    if (fps == 0) fps = 30;

    ESP_LOGI(TAG, "Resolution change requested: %lux%lu @ %lu fps (was %lux%lu @ %lu fps)",
             (unsigned long)width, (unsigned long)height, (unsigned long)fps,
             (unsigned long)s_target_width, (unsigned long)s_target_height, (unsigned long)s_target_fps);

    s_target_width = width;
    s_target_height = height;
    s_target_fps = fps;

    if (s_uvc_stream != NULL && s_is_streaming) {
        uvc_host_stream_format_t new_fmt = {
            .h_res = width,
            .v_res = height,
            .fps = (float)fps,
            .format = UVC_VS_FORMAT_MJPEG,
        };
        esp_err_t err = uvc_host_stream_format_select(s_uvc_stream, &new_fmt);
        if (err == ESP_OK) {
            ESP_LOGI(TAG, "UVC live format switch successful: %ux%u @ %.1f fps",
                     new_fmt.h_res, new_fmt.v_res, new_fmt.fps);
            return ESP_OK;
        } else {
            ESP_LOGW(TAG, "Live format select not accepted (%s). Initiating clean reconnect with new resolution...",
                     esp_err_to_name(err));
            s_force_reconnect = true;
            s_is_streaming = false;
            return ESP_OK;
        }
    }
    return ESP_OK;
}

void uvc_stream_mgr_get_stats(uint32_t *width, uint32_t *height, uint32_t *target_fps, uint32_t *total_frames)
{
    if (width) *width = s_target_width;
    if (height) *height = s_target_height;
    if (target_fps) *target_fps = s_target_fps;
    if (total_frames) *total_frames = s_total_frames;
}
