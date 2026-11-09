#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "nvs_flash.h"
#include "nvs.h"
#include "esp_random.h"

#include "auth_mgr.h"

static const char *TAG = "auth_mgr";
static const char *NVS_NAMESPACE = "kvm_auth";
static const char *KEY_USER = "username";
static const char *KEY_PASS = "password";

static char s_current_username[32] = AUTH_DEFAULT_USERNAME;
static char s_current_password[64] = AUTH_DEFAULT_PASSWORD;
static char s_active_session_token[AUTH_TOKEN_LEN] = {0};
static portMUX_TYPE s_auth_spinlock = portMUX_INITIALIZER_UNLOCKED;

static void generate_token(char *out_token, size_t max_len)
{
    uint32_t r[4];
    for (int i = 0; i < 4; i++) {
        r[i] = esp_random();
    }
    snprintf(out_token, max_len, "%08lx%08lx%08lx%08lx",
             (unsigned long)r[0], (unsigned long)r[1],
             (unsigned long)r[2], (unsigned long)r[3]);
}

esp_err_t auth_mgr_init(void)
{
    ESP_LOGI(TAG, "Initializing KVM authentication subsystem...");

    nvs_handle_t nvs_h;
    esp_err_t err = nvs_open(NVS_NAMESPACE, NVS_READWRITE, &nvs_h);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to open NVS namespace '%s': %s", NVS_NAMESPACE, esp_err_to_name(err));
        return err;
    }

    // 1. Read or initialize username
    size_t req_len = sizeof(s_current_username);
    memset(s_current_username, 0, sizeof(s_current_username));
    err = nvs_get_str(nvs_h, KEY_USER, s_current_username, &req_len);
    if (err != ESP_OK || strlen(s_current_username) == 0) {
        strncpy(s_current_username, AUTH_DEFAULT_USERNAME, sizeof(s_current_username) - 1);
        s_current_username[sizeof(s_current_username) - 1] = '\0';
        nvs_set_str(nvs_h, KEY_USER, s_current_username);
        nvs_commit(nvs_h);
        ESP_LOGI(TAG, "Default username created in NVS: '%s'", s_current_username);
    }

    // 2. Read or initialize password
    req_len = sizeof(s_current_password);
    memset(s_current_password, 0, sizeof(s_current_password));
    err = nvs_get_str(nvs_h, KEY_PASS, s_current_password, &req_len);
    if (err != ESP_OK || strlen(s_current_password) == 0) {
        strncpy(s_current_password, AUTH_DEFAULT_PASSWORD, sizeof(s_current_password) - 1);
        s_current_password[sizeof(s_current_password) - 1] = '\0';
        nvs_set_str(nvs_h, KEY_PASS, s_current_password);
        nvs_commit(nvs_h);
        ESP_LOGI(TAG, "Default password created in NVS: '%s'", s_current_password);
    }

    nvs_close(nvs_h);

    // 3. Generate initial session token
    generate_token(s_active_session_token, sizeof(s_active_session_token));

    ESP_LOGI(TAG, "Authentication subsystem ready (Admin user: '%s')", s_current_username);
    return ESP_OK;
}

esp_err_t auth_mgr_authenticate(const char *username, const char *password, char *out_token, size_t max_token_len)
{
    if (!username || !password || !out_token || max_token_len < AUTH_TOKEN_LEN) {
        return ESP_ERR_INVALID_ARG;
    }

    portENTER_CRITICAL(&s_auth_spinlock);
    bool match = (strcmp(username, s_current_username) == 0 &&
                  strcmp(password, s_current_password) == 0);

    if (match) {
        generate_token(s_active_session_token, sizeof(s_active_session_token));
        strncpy(out_token, s_active_session_token, max_token_len - 1);
        out_token[max_token_len - 1] = '\0';
    }
    portEXIT_CRITICAL(&s_auth_spinlock);

    if (match) {
        ESP_LOGI(TAG, "Authentication SUCCESS for user '%s'", username);
        return ESP_OK;
    } else {
        ESP_LOGW(TAG, "Authentication FAILED for user '%s'", username);
        return ESP_ERR_INVALID_ARG;
    }
}

bool auth_mgr_validate_token(const char *token)
{
    if (!token || token[0] == '\0') {
        return false;
    }

    portENTER_CRITICAL(&s_auth_spinlock);
    bool valid = (s_active_session_token[0] != '\0' &&
                  strcmp(token, s_active_session_token) == 0);
    portEXIT_CRITICAL(&s_auth_spinlock);

    return valid;
}

esp_err_t auth_mgr_change_password(const char *old_password, const char *new_password)
{
    if (!old_password || !new_password || strlen(new_password) < 4) {
        return ESP_ERR_INVALID_ARG;
    }

    portENTER_CRITICAL(&s_auth_spinlock);
    if (strcmp(old_password, s_current_password) != 0) {
        portEXIT_CRITICAL(&s_auth_spinlock);
        ESP_LOGW(TAG, "Change password rejected: old password mismatch");
        return ESP_ERR_INVALID_ARG;
    }

    strncpy(s_current_password, new_password, sizeof(s_current_password) - 1);
    s_current_password[sizeof(s_current_password) - 1] = '\0';

    // Invalidate old tokens and issue new active session token
    generate_token(s_active_session_token, sizeof(s_active_session_token));
    portEXIT_CRITICAL(&s_auth_spinlock);

    // Persist new password to NVS
    nvs_handle_t nvs_h;
    esp_err_t err = nvs_open(NVS_NAMESPACE, NVS_READWRITE, &nvs_h);
    if (err == ESP_OK) {
        nvs_set_str(nvs_h, KEY_PASS, s_current_password);
        nvs_commit(nvs_h);
        nvs_close(nvs_h);
        ESP_LOGI(TAG, "Administrator password successfully updated in NVS!");
    } else {
        ESP_LOGE(TAG, "Failed to persist new password to NVS: %s", esp_err_to_name(err));
        return err;
    }

    return ESP_OK;
}

void auth_mgr_get_username(char *out_buf, size_t max_len)
{
    if (!out_buf || max_len == 0) return;
    portENTER_CRITICAL(&s_auth_spinlock);
    strncpy(out_buf, s_current_username, max_len - 1);
    out_buf[max_len - 1] = '\0';
    portEXIT_CRITICAL(&s_auth_spinlock);
}
