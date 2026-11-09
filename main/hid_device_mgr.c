#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "tinyusb.h"
#include "tinyusb_default_config.h"
#include "class/hid/hid_device.h"
#include "soc/usb_wrap_struct.h"
#include "soc/usb_serial_jtag_struct.h"
#include "soc/lp_system_struct.h"
#include "hal/usb_serial_jtag_ll.h"
#include "hal/usb_wrap_ll.h"

#include "hid_device_mgr.h"

static const char *TAG = "hid_dev";
static bool s_is_initialized = false;

static void tusb_event_cb(tinyusb_event_t *event, void *arg)
{
    if (event->id == TINYUSB_EVENT_ATTACHED) {
        ESP_LOGI(TAG, "===> USB HID Device MOUNTED by Host PC! Ready for keyboard and mouse control! <===");
    } else if (event->id == TINYUSB_EVENT_DETACHED) {
        ESP_LOGW(TAG, "USB HID Device UNMOUNTED by Host PC.");
    }
}

/************* TinyUSB Descriptors ****************/

#define REPORT_ID_KEYBOARD   1
#define REPORT_ID_MOUSE      2

#define TUSB_DESC_TOTAL_LEN  (TUD_CONFIG_DESC_LEN + CFG_TUD_HID * TUD_HID_DESC_LEN)

/**
 * @brief Composite HID report descriptor (Keyboard + Mouse)
 */
static const uint8_t hid_report_descriptor[] = {
    TUD_HID_REPORT_DESC_KEYBOARD(HID_REPORT_ID(REPORT_ID_KEYBOARD)),
    TUD_HID_REPORT_DESC_MOUSE(HID_REPORT_ID(REPORT_ID_MOUSE))
};

static const char *hid_string_descriptor[] = {
    (char[]){0x09, 0x04},         // 0: Supported language: English (0x0409)
    "Espressif Systems",          // 1: Manufacturer
    "ESP32-P4 KVM USB Keyboard",  // 2: Product Name
    "1234567890",                 // 3: Serial Number
    "KVM HID Interface",          // 4: HID Interface
};

static const uint8_t hid_configuration_descriptor[] = {
    // Configuration number, interface count, string index, total length, attribute, power in mA
    TUD_CONFIG_DESCRIPTOR(1, 1, 0, TUSB_DESC_TOTAL_LEN, TUSB_DESC_CONFIG_ATT_REMOTE_WAKEUP, 100),

    // Interface number, string index, boot protocol, report descriptor len, EP In address, size & polling interval
    TUD_HID_DESCRIPTOR(0, 4, false, sizeof(hid_report_descriptor), 0x81, 16, 10),
};

/********* TinyUSB HID Callbacks ***************/

uint8_t const *tud_hid_descriptor_report_cb(uint8_t instance)
{
    return hid_report_descriptor;
}

uint16_t tud_hid_get_report_cb(uint8_t instance, uint8_t report_id, hid_report_type_t report_type, uint8_t *buffer, uint16_t reqlen)
{
    return 0;
}

void tud_hid_set_report_cb(uint8_t instance, uint8_t report_id, hid_report_type_t report_type, uint8_t const *buffer, uint16_t bufsize)
{
    ESP_LOGD(TAG, "HID set report: id %d, type %d, size %d", report_id, report_type, bufsize);
}

/********* Public API ***************/

esp_err_t hid_device_mgr_init(void)
{
    if (s_is_initialized) {
        ESP_LOGW(TAG, "HID device manager already initialized");
        return ESP_OK;
    }

    ESP_LOGI(TAG, "Initializing USB Full-Speed HID Device (Keyboard & Mouse) on USB2 port...");

    // 1. Map USB_WRAP (OTG 1.1 Full-Speed controller) to USB FSLS PHY 0 (pins 42/43 on USB2 port)
    usb_wrap_ll_phy_select(&USB_WRAP, 0);
    usb_wrap_ll_phy_set_defaults(&USB_WRAP);

    // 2. Disconnect internal USB Serial / JTAG controller and force a physical D+/D- disconnect
    // so the host PC sees a clean unplug and re-enumeration for TinyUSB HID
    USB_SERIAL_JTAG.conf0.usb_pad_enable = 0;
    USB_SERIAL_JTAG.conf0.dp_pullup = 0;
    USB_SERIAL_JTAG.conf0.dm_pullup = 0;
    USB_SERIAL_JTAG.conf0.dp_pulldown = 1;
    USB_SERIAL_JTAG.conf0.dm_pulldown = 1;
    USB_SERIAL_JTAG.conf0.pad_pull_override = 1;

    USB_WRAP.otg_conf.dp_pullup = 0;
    USB_WRAP.otg_conf.dm_pullup = 0;
    USB_WRAP.otg_conf.dp_pulldown = 1;
    USB_WRAP.otg_conf.dm_pulldown = 1;
    USB_WRAP.otg_conf.pad_pull_override = 1;

    vTaskDelay(pdMS_TO_TICKS(150));

    USB_SERIAL_JTAG.conf0.pad_pull_override = 0;
    USB_WRAP.otg_conf.pad_pull_override = 0;

    tinyusb_config_t tusb_cfg = TINYUSB_CONFIG_FULL_SPEED(NULL, NULL);
    tusb_cfg.port = TINYUSB_PORT_FULL_SPEED_0; // Explicitly assign to USB OTG 1.1 Full Speed port
    tusb_cfg.descriptor.device = NULL;
    tusb_cfg.descriptor.full_speed_config = hid_configuration_descriptor;
    tusb_cfg.descriptor.string = (const char **)hid_string_descriptor;
    tusb_cfg.descriptor.string_count = sizeof(hid_string_descriptor) / sizeof(hid_string_descriptor[0]);
    tusb_cfg.event_cb = tusb_event_cb;

    esp_err_t err = tinyusb_driver_install(&tusb_cfg);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to install TinyUSB HID driver: %s", esp_err_to_name(err));
        return err;
    }

    s_is_initialized = true;
    ESP_LOGI(TAG, "TinyUSB Full-Speed HID Driver successfully started on USB2 (FS port)!");
    return ESP_OK;
}

bool hid_device_mgr_is_mounted(void)
{
    return s_is_initialized && tud_mounted();
}

esp_err_t hid_device_mgr_send_keyboard(uint8_t modifier, const uint8_t keycodes[6])
{
    if (!tud_mounted()) {
        return ESP_ERR_INVALID_STATE;
    }

    uint8_t kc[6] = {0};
    if (keycodes) {
        memcpy(kc, keycodes, 6);
    }
    bool ok = tud_hid_keyboard_report(REPORT_ID_KEYBOARD, modifier, kc);
    return ok ? ESP_OK : ESP_FAIL;
}

esp_err_t hid_device_mgr_keyboard_release_all(void)
{
    if (!tud_mounted()) {
        return ESP_OK;
    }
    tud_hid_keyboard_report(REPORT_ID_KEYBOARD, 0, NULL);
    return ESP_OK;
}

esp_err_t hid_device_mgr_send_mouse(uint8_t buttons, int8_t dx, int8_t dy, int8_t wheel)
{
    if (!tud_mounted()) {
        return ESP_ERR_INVALID_STATE;
    }
    bool ok = tud_hid_mouse_report(REPORT_ID_MOUSE, buttons, dx, dy, wheel, 0);
    return ok ? ESP_OK : ESP_FAIL;
}

esp_err_t hid_device_mgr_send_macro(const char *macro_name)
{
    if (!macro_name) return ESP_ERR_INVALID_ARG;
    if (!tud_mounted()) {
        ESP_LOGW(TAG, "Cannot send macro '%s': USB HID port not connected to host PC", macro_name);
        return ESP_ERR_INVALID_STATE;
    }

    ESP_LOGI(TAG, "Executing KVM Macro: %s", macro_name);

    if (strcmp(macro_name, "CAD") == 0) {
        // Ctrl + Alt + Del
        uint8_t del_key[6] = {HID_KEY_DELETE, 0, 0, 0, 0, 0};
        tud_hid_keyboard_report(REPORT_ID_KEYBOARD, 0x01 | 0x04, del_key); // LCtrl + LAlt
        vTaskDelay(pdMS_TO_TICKS(60));
        tud_hid_keyboard_report(REPORT_ID_KEYBOARD, 0, NULL);
    } else if (strcmp(macro_name, "ALT_TAB") == 0) {
        uint8_t tab_key[6] = {HID_KEY_TAB, 0, 0, 0, 0, 0};
        tud_hid_keyboard_report(REPORT_ID_KEYBOARD, 0x04, tab_key); // LAlt
        vTaskDelay(pdMS_TO_TICKS(60));
        tud_hid_keyboard_report(REPORT_ID_KEYBOARD, 0, NULL);
    } else if (strcmp(macro_name, "WIN") == 0) {
        uint8_t none[6] = {0};
        tud_hid_keyboard_report(REPORT_ID_KEYBOARD, 0x08, none); // LGUI
        vTaskDelay(pdMS_TO_TICKS(60));
        tud_hid_keyboard_report(REPORT_ID_KEYBOARD, 0, NULL);
    } else if (strcmp(macro_name, "ESC") == 0) {
        uint8_t esc_key[6] = {HID_KEY_ESCAPE, 0, 0, 0, 0, 0};
        tud_hid_keyboard_report(REPORT_ID_KEYBOARD, 0, esc_key);
        vTaskDelay(pdMS_TO_TICKS(60));
        tud_hid_keyboard_report(REPORT_ID_KEYBOARD, 0, NULL);
    } else if (strcmp(macro_name, "PRINT") == 0) {
        uint8_t prt_key[6] = {HID_KEY_PRINT_SCREEN, 0, 0, 0, 0, 0};
        tud_hid_keyboard_report(REPORT_ID_KEYBOARD, 0, prt_key);
        vTaskDelay(pdMS_TO_TICKS(60));
        tud_hid_keyboard_report(REPORT_ID_KEYBOARD, 0, NULL);
    }

    return ESP_OK;
}
