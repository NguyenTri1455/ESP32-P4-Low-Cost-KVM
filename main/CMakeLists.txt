set(EXTRA_REQUIRES "")
if(IDF_VERSION_MAJOR GREATER_EQUAL 6)
    list(APPEND EXTRA_REQUIRES espressif__ip101)
endif()

idf_component_register(
    SRCS
        "main.c"
        "ethernet_mgr.c"
        "uvc_stream_mgr.c"
        "web_server.c"
        "hid_device_mgr.c"
        "system_stats.c"
        "auth_mgr.c"
        "net_config_mgr.c"
    INCLUDE_DIRS
        "."
    REQUIRES
        esp_eth
        esp_netif
        esp_event
        esp_http_server
        esp_timer
        esp_driver_gpio
        driver
        nvs_flash
        usb
        espressif__usb_host_uvc
        app_update
        esp_ringbuf
        espressif__esp_tinyusb
        json
        espressif__mdns
        ${EXTRA_REQUIRES}
)
