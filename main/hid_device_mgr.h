#pragma once

#include <stdint.h>
#include <stdbool.h>
#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief Initialize TinyUSB HID Device (Keyboard + Mouse) on Full-Speed USB port (USB2)
 *
 * @return ESP_OK on success, or error code.
 */
esp_err_t hid_device_mgr_init(void);

/**
 * @brief Check if USB HID device is mounted and ready on target computer
 *
 * @return true if mounted, false otherwise.
 */
bool hid_device_mgr_is_mounted(void);

/**
 * @brief Send a keyboard keystroke (press and release) or raw report
 *
 * @param modifier Bitmask of modifier keys (Ctrl, Shift, Alt, GUI)
 * @param keycodes Array of up to 6 HID keycodes
 */
esp_err_t hid_device_mgr_send_keyboard(uint8_t modifier, const uint8_t keycodes[6]);

/**
 * @brief Release all pressed keyboard keys
 */
esp_err_t hid_device_mgr_keyboard_release_all(void);

/**
 * @brief Send mouse movement, buttons, and scroll
 *
 * @param buttons Bitmask of buttons (1=Left, 2=Right, 4=Middle)
 * @param dx      Relative X movement (-127 to 127)
 * @param dy      Relative Y movement (-127 to 127)
 * @param wheel   Vertical scroll (-127 to 127)
 */
esp_err_t hid_device_mgr_send_mouse(uint8_t buttons, int8_t dx, int8_t dy, int8_t wheel);

/**
 * @brief Execute a named KVM macro shortcut
 *
 * Supports: "CAD" (Ctrl+Alt+Del), "ALT_TAB", "WIN", "ESC", "ENTER", etc.
 *
 * @param macro_name Name of the macro
 */
esp_err_t hid_device_mgr_send_macro(const char *macro_name);

#ifdef __cplusplus
}
#endif
