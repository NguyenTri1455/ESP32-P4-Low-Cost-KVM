#pragma once

#include <stdbool.h>
#include <stddef.h>
#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

#define AUTH_DEFAULT_USERNAME   "admin"
#define AUTH_DEFAULT_PASSWORD   "admin"
#define AUTH_TOKEN_LEN          33  // 32 hex chars + null terminator

/**
 * @brief Initialize authentication subsystem and load credentials from NVS
 */
esp_err_t auth_mgr_init(void);

/**
 * @brief Verify login credentials and generate a new session token
 *
 * @param username Input username
 * @param password Input password
 * @param[out] out_token Buffer to receive session token
 * @param max_token_len Size of out_token buffer
 * @return ESP_OK if authenticated, ESP_ERR_INVALID_ARG otherwise
 */
esp_err_t auth_mgr_authenticate(const char *username, const char *password, char *out_token, size_t max_token_len);

/**
 * @brief Check if a session token is valid and active
 *
 * @param token Session token string
 * @return true if valid, false otherwise
 */
bool auth_mgr_validate_token(const char *token);

/**
 * @brief Change the administrator password in NVS
 *
 * @param old_password Current password for verification
 * @param new_password New password to set
 * @return ESP_OK on success, ESP_ERR_INVALID_ARG if old password wrong
 */
esp_err_t auth_mgr_change_password(const char *old_password, const char *new_password);

/**
 * @brief Get the configured administrator username
 *
 * @param[out] out_buf Destination buffer
 * @param max_len Size of destination buffer
 */
void auth_mgr_get_username(char *out_buf, size_t max_len);

#ifdef __cplusplus
}
#endif
