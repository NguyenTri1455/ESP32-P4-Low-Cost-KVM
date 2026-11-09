#pragma once

#include "sdkconfig.h"

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief Board Definitions for Guition JC-ESP32P4-M3-DEV
 *
 * Primary SoC: ESP32-P4NRW32 (Dual-core RISC-V 360 MHz, 32MB PSRAM, 16MB Flash)
 * Ethernet: IP101 (10/100M RMII PHY)
 * USB: Native USB 2.0 High-Speed OTG (up to 480 Mbps)
 */

#define BOARD_NAME "JC-ESP32P4-M3-DEV"

/* Ethernet (IP101 PHY) Pin Mapping */
#ifndef CONFIG_ETH_MDC_GPIO
#define BOARD_ETH_MDC_GPIO          31
#else
#define BOARD_ETH_MDC_GPIO          CONFIG_ETH_MDC_GPIO
#endif

#ifndef CONFIG_ETH_MDIO_GPIO
#define BOARD_ETH_MDIO_GPIO         52
#else
#define BOARD_ETH_MDIO_GPIO         CONFIG_ETH_MDIO_GPIO
#endif

#ifndef CONFIG_ETH_PWR_RST_GPIO
#define BOARD_ETH_PWR_RST_GPIO      51
#else
#define BOARD_ETH_PWR_RST_GPIO      CONFIG_ETH_PWR_RST_GPIO
#endif

#ifndef CONFIG_ETH_RMII_CLK_GPIO
#define BOARD_ETH_RMII_CLK_GPIO     50
#else
#define BOARD_ETH_RMII_CLK_GPIO     CONFIG_ETH_RMII_CLK_GPIO
#endif

#ifndef CONFIG_ETH_PHY_ADDR
#define BOARD_ETH_PHY_ADDR          1
#else
#define BOARD_ETH_PHY_ADDR          CONFIG_ETH_PHY_ADDR
#endif

/* Video Stream Default Resolutions */
#ifndef CONFIG_UVC_FRAME_WIDTH
#define BOARD_UVC_DEFAULT_WIDTH     1280
#else
#define BOARD_UVC_DEFAULT_WIDTH     CONFIG_UVC_FRAME_WIDTH
#endif

#ifndef CONFIG_UVC_FRAME_HEIGHT
#define BOARD_UVC_DEFAULT_HEIGHT    720
#else
#define BOARD_UVC_DEFAULT_HEIGHT    CONFIG_UVC_FRAME_HEIGHT
#endif

#ifndef CONFIG_UVC_FRAME_FPS
#define BOARD_UVC_DEFAULT_FPS       30
#else
#define BOARD_UVC_DEFAULT_FPS       CONFIG_UVC_FRAME_FPS
#endif

#ifndef CONFIG_UVC_FRAME_BUFFER_SIZE_KB
#define BOARD_UVC_MAX_FRAME_SIZE    (2048 * 1024)
#else
#define BOARD_UVC_MAX_FRAME_SIZE    (CONFIG_UVC_FRAME_BUFFER_SIZE_KB * 1024)
#endif

#ifdef __cplusplus
}
#endif
