# ESP32-P4 High-Performance HDMI IP-KVM Over Ethernet

Production-ready, dual-USB IP-KVM firmware for the **Guition JC-ESP32P4-M3-DEV** development board. Powered by the **ESP32-P4** (Dual-Core RISC-V @ 360MHz, 32MB Hex-PSRAM), this project transforms the board into an ultra-low latency, driverless, hardware-level remote management system with live HDMI video capture, full keyboard/mouse emulation, and dual-slot network OTA updates.

---

## 📑 Table of Contents

- [System Architecture](#-system-architecture)
- [Key Features](#-key-features)
- [Hardware & Connector Mapping](#-hardware--connector-mapping)
  - [Port Pinout & Functions](#port-pinout--functions)
  - [Ethernet (IP101GRI RMII)](#ethernet-ip101gri-rmii)
  - [ESP32-P4 Internal USB PHY Switching](#esp32-p4-internal-usb-phy-switching)
- [Software Architecture](#-software-architecture)
  - [Core Task Partitioning](#core-task-partitioning)
  - [Memory & PSRAM Zero-Copy Double-Buffering](#memory--psram-zero-copy-double-buffering)
- [Web KVM Control Interface](#-web-kvm-control-interface)
  - [Pointer Lock Mouse Control](#pointer-lock-mouse-control)
  - [Keyboard Mapping & Roll-Over](#keyboard-mapping--roll-over)
  - [Real-Time WebSocket Protocol](#real-time-websocket-protocol)
- [REST API Reference](#-rest-api-reference)
- [Dual-Slot OTA & Build System](#-dual-slot-ota--build-system)
  - [Flash Partition Layout](#flash-partition-layout)
  - [Building and Flashing with Build.bat](#building-and-flashing-with-buildbat)
  - [One-Click Wireless OTA](#one-click-wireless-ota)
- [Troubleshooting & Diagnostics](#-troubleshooting--diagnostics)

---

## 🏗 System Architecture

```
   +-------------------------------------------------------------------------------+
   |                         TARGET PC / SERVER UNDER CONTROL                      |
   +-------------------------------------------------------------------------------+
           |                                                      ^
    HDMI Output Cable                                      USB-C to USB-A Cable
           v                                                      |
   +--------------------+                                         |
   | USB-to-HDMI Dongle |                                         |
   | (MS2109 / MS2130)  |                                         |
   +--------------------+                                         |
           |                                                      |
    High-Speed USB 2.0                                     Full-Speed USB 1.1
         (480 Mbps)                                             (12 Mbps)
           |                                                      |
           v                                                      |
   +===============================================================================+
   |                     GUITION JC-ESP32P4-M3-DEV BOARD                           |
   |                                                                               |
   |  [USB3 / USB-HS]           [USB2 / USB-FS]             [100M RJ45 Ethernet]  |
   |         |                         |                             |             |
   |  USB Host (UVC)             TinyUSB Device                IP101GRI RMII       |
   |   Video Ingest               Composite HID                   TCP/IP &         |
   |  (720p/1080p MJPEG)        (Keyboard + Mouse)               HTTP Server       |
   |         |                         |                             |             |
   |         v                         v                             v             |
   |  +--------------+          +--------------+             +---------------+     |
   |  | 32MB PSRAM   |          | Core 0 Queue |             | Core 1 Stream |     |
   |  | Zero-Copy    |          | WebSocket    |             | Worker Task   |     |
   |  | Double-Buffer|          | Packet Parser|             | (Async HTTP)  |     |
   |  +--------------+          +--------------+             +---------------+     |
   +===============================================================================+
                                                                     |
                                                           100 Mbps LAN Cable
                                                                     |
                                                                     v
                                                            +-----------------+
                                                            |  CLIENT BROWSER |
                                                            |  (Any PC / Mac) |
                                                            | http://<ip>/    |
                                                            +-----------------+
```

---

## 🚀 Key Features

* **Dual USB Controllers Operating Concurrently:**
  * **USB Host (High-Speed @ 480 Mbps):** Ingests live MJPEG video from HDMI capture dongles (MacroSilicon MS2109, MS2130, Cam Link, etc.) with hardware auto-reconnect and resolution negotiation.
  * **USB Device (Full-Speed @ 12 Mbps):** Emulates standard USB HID Keyboard (104-key with 6-key rollover) and Mouse (relative motion + 5 buttons + scroll wheel) using TinyUSB.
* **Low-Latency Streaming Engine:**
  * FreeRTOS dedicated asynchronous MJPEG stream worker pinned to **Core 1** (`httpd_req_async_handler_begin()`).
  * Real-time 30 FPS at 1280x720 with zero UI blocking or network socket stalls.
  * Double-buffering allocated in **32MB external Hex-PSRAM** (200MHz, 16-bit bus).
* **Interactive Glassmorphic Web UI:**
  * HTML5 **Pointer Lock API** for direct relative mouse tracking without mouse escapes or edge clipping.
  * Native 60 Hz input batching via `requestAnimationFrame` over a single low-overhead WebSocket connection (`/ws`).
  * Failsafe automatic key release on browser focus loss or pointer unlock.
  * Quick KVM Macro toolbar: `Ctrl+Alt+Del`, `Alt+Tab`, `Win Key`, `Esc`, `PrtScn`, `Release All Keys`.
  * Dynamic video adjustment controls: Brightness, Contrast, and Saturation shaders.
  * Embedded live serial log drawer streamed directly over WebSocket.
* **On-the-Fly Dynamic Resolution Switching:**
  * Queries capture card USB descriptors for all supported frame formats (`GET /api/formats`).
  * Live resolution switching (`POST /api/resolution`) supporting 720p (1280x720 @ 30 FPS), 1080p (1920x1080 @ 30 FPS / 5 FPS), and 480p (640x480 @ 30 FPS).
* **Dual-Slot OTA Network Upgrades:**
  * Partition layout with dual 4MB OTA slots (`ota_0`, `ota_1`) and `otadata` tracking.
  * Zero-cable firmware flashing over LAN via `POST /api/ota` or `Build.bat ota <IP>`.

---

## 🛠 Hardware & Connector Mapping

The **Guition JC-ESP32P4-M3-DEV** features three USB Type-C ports, an IP101 Ethernet port, and dedicated buttons:

```
 +-----------------------------------------------------------------------+
 | [RJ45 ETH]        [USB3: USB-HS]       [USB2: USB-FS]  [USB1: UART]   |
 |  IP101GRI         Capture Card In      KVM Target Out   Flash / Debug |
 |                                                                       |
 |   [RST]                 ESP32-P4NRW32                    [BOOT]       |
 |   SW2                   Dual RISC-V 360MHz                SW1         |
 |                         32MB Hex-PSRAM                                |
 +-----------------------------------------------------------------------+
```

### Port Pinout & Functions

| Connector Label | Controller / PHY | Role | Target Connection |
| :--- | :--- | :--- | :--- |
| **USB3 (USB-HS)** | ESP32-P4 High-Speed USB 2.0 Host | **HDMI Video Ingest** | USB-to-HDMI Capture Card (MS2109/MS2130) |
| **USB2 (USB-FS)** | ESP32-P4 Full-Speed OTG 1.1 Device | **KVM Keyboard & Mouse** | Target PC / Server USB Port |
| **USB1 (UART)** | CH340C USB-to-UART Bridge | **Console & Flashing** | Developer Workstation (`115200 8-N-1`) |
| **RJ45 (ETH)** | IP101GRI RMII 10/100M PHY | **Network Interface** | Local Network Router / Switch |

### Ethernet (IP101GRI RMII)

The Ethernet transceiver uses the ESP32-P4 EMAC with external 50MHz oscillator clock:

| Signal Name | ESP32-P4 Pin | Description |
| :--- | :--- | :--- |
| **RMII MDC** | `GPIO 31` | Management Data Clock |
| **RMII MDIO** | `GPIO 52` | Management Data I/O |
| **RMII PWR / RST** | `GPIO 51` | PHY Power Enable / Hardware Reset |
| **RMII REF_CLK** | `GPIO 50` | 50MHz Reference Clock (`EMAC_CLK_EXT_IN`) |
| **PHY Address** | `1` | SMI Bus Address |

### ESP32-P4 Internal USB PHY Switching

By default on the ESP32-P4, physical pins 42 and 43 (`USB1P1`) are multiplexed to the internal USB Serial/JTAG debugging controller. To enable the hardware TinyUSB Full-Speed HID stack on **USB2**, the firmware executes low-level register switching at boot:

```c
// 1. Route physical pins GPIO 42 & 43 to USB_WRAP (OTG 1.1 Controller)
usb_wrap_ll_phy_select(&USB_WRAP, 0);
usb_wrap_ll_phy_set_defaults(&USB_WRAP);

// 2. Generate a physical disconnect pulse (>100ms) to trigger re-enumeration
usb_wrap_ll_phy_enable_dp_pulldown(&USB_WRAP, true);
usb_wrap_ll_phy_enable_dp_pullup(&USB_WRAP, false);
vTaskDelay(pdMS_TO_TICKS(150));
```

Additionally, secondary USB serial console mapping is disabled in `sdkconfig.defaults`:
```ini
CONFIG_ESP_CONSOLE_SECONDARY_NONE=y
```

---

## 💻 Software Architecture

### Core Task Partitioning

The firmware leverages the dual-core RISC-V processor to prevent network streaming from starving USB communication or UI responsibilities:

| Core | Task Name | Priority | Responsibilities |
| :--- | :--- | :--- | :--- |
| **Core 0** | `tcpip_thread` | 18 | LWIP 100M network packet processing |
| **Core 0** | `httpd` | 5 | HTTP REST endpoints, WebSocket listener, and JSON parser |
| **Core 0** | `usb_host_lib` | 20 | USB Host UVC driver transfer daemon |
| **Core 0** | `uvc_supervisor` | 4 | Video watchdog, frame stall detection, and auto-recovery |
| **Core 0** | `tinyusb` | 5 | TinyUSB event processing and HID endpoint dispatch |
| **Core 1** | `mjpeg_streamer` | 5 | Dedicated non-blocking multipart MJPEG frame transmitter |

### Memory & PSRAM Zero-Copy Double-Buffering

Video frames are received directly into ping-pong buffers in external **32MB Hex-PSRAM** (`MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT`):
- `Buffer A`: Receives the incoming USB isochronous/bulk MJPEG stream payload.
- `Buffer B`: Read by the HTTP MJPEG streamer task to push boundary chunks to client sockets.
- Switching occurs atomically via pointer swap upon complete frame boundary detection (`0xFFD8` to `0xFFD9`).

---

## 🎮 Web KVM Control Interface

Navigate to `http://<device-ip>/` in any modern web browser (Chrome, Edge, Firefox, Safari).

### Pointer Lock Mouse Control

1. Click **🖱 Capture Mouse** (or click directly on the live video frame).
2. The browser engages the **HTML5 Pointer Lock API**, locking the physical cursor and forwarding relative `movementX` and `movementY` coordinates.
3. Left, right, and middle mouse buttons, along with wheel scrolling, are batched and transmitted to the ESP32-P4 at 60 Hz.
4. Press **`Esc`** at any time to release mouse capture.

### Keyboard Mapping & Roll-Over

The web application intercepts `keydown` and `keyup` events across the entire window:
- Converts DOM `e.code` identifiers (e.g., `KeyA`, `Enter`, `ShiftLeft`) into standard USB HID keyboard usages.
- Tracks up to 6 simultaneous keys plus standard modifiers (Ctrl, Shift, Alt, GUI/Win) with full 6-key rollover (6KRO).
- Automatically triggers a failsafe release (`sendReleaseAll()`) when the browser window loses focus (`blur`) or when pointer lock is exited.

### Real-Time WebSocket Protocol

All mouse, keyboard, macro, telemetry, and logging events pass through a single WebSocket endpoint (`ws://<device-ip>/ws`).

#### Client to ESP32:

* **Mouse Delta:**
  ```json
  {"type": "mouse", "dx": 12, "dy": -4, "wheel": 0, "btn": 1}
  ```
* **Keyboard State:**
  ```json
  {"type": "keyboard", "mod": 2, "keys": [4, 7, 0, 0, 0, 0]}
  ```
* **Hardware Macro Execution:**
  ```json
  {"type": "macro", "name": "CAD"}
  ```
  *(Supported macro names: `CAD` [Ctrl+Alt+Del], `ALT_TAB` [Alt+Tab], `WIN` [Windows Key], `ESC` [Escape], `PRTSCN` [Print Screen]).*
* **Release All Keys:**
  ```json
  {"type": "release_all"}
  ```

#### ESP32 to Client:

* **Real-time Telemetry Broadcast (Every 1000ms):**
  ```json
  {
    "type": "telemetry",
    "board": "JC-ESP32P4-M3-DEV",
    "ip": "172.16.1.54",
    "uvc_connected": true,
    "hid_mounted": true,
    "reconnect_count": 0,
    "res": "1280x720",
    "fps": 30.0,
    "target_fps": 30,
    "total_frames": 18452,
    "uptime": 615,
    "free_psram": 26897116,
    "free_sram": 404028
  }
  ```
* **Real-time Console Logs:**
  ```json
  {
    "type": "log",
    "msg": "I (4336) uvc_mgr: USB-to-HDMI capture device successfully opened!"
  }
  ```

---

## 📡 REST API Reference

| Endpoint | Method | Response Type | Description |
| :--- | :--- | :--- | :--- |
| `/` | `GET` | `text/html` | Glassmorphic Web KVM Single-Page Application |
| `/stream` | `GET` | `multipart/x-mixed-replace` | Live MJPEG Video Stream (OBS / VLC / Web) |
| `/snapshot` | `GET` | `image/jpeg` | Instant single-frame JPEG capture |
| `/api/status` | `GET` | `application/json` | System health, FPS, UVC & HID status, memory stats |
| `/api/formats` | `GET` | `application/json` | List of resolutions supported by the capture card |
| `/api/resolution` | `POST` | `application/json` | Set video stream resolution (`{"width": 1280, "height": 720, "fps": 30}`) |
| `/api/reconnect_usb`| `POST` | `application/json` | Perform software-triggered USB UVC bus reset |
| `/api/ota` | `POST` | `text/plain` | Dual-slot OTA binary upload and reboot |
| `/ws` | `GET` | `WebSocket Upgrade` | Bidirectional KVM control, telemetry, and logs |

---

## 🔄 Dual-Slot OTA & Build System

### Flash Partition Layout

The project defines a custom dual-slot layout in [`partitions.csv`](file:///c:/Users/nguye/Desktop/esp32p4_kvm/partitions.csv) inside the 16MB Flash:

```csv
# Name,     Type,  SubType,  Offset,    Size,     Flags
nvs,        data,  nvs,      0x9000,    0x6000,
otadata,    data,  ota,      0xf000,    0x2000,
phy_init,   data,  phy,      0x11000,   0x1000,
factory,    app,   factory,  0x20000,   0x100000,
ota_0,      app,   ota_0,    0x120000,  0x400000,
ota_1,      app,   ota_1,    0x520000,  0x400000,
```

### Building and Flashing with `Build.bat`

The root directory includes a high-speed automation script [`Build.bat`](file:///c:/Users/nguye/Desktop/esp32p4_kvm/Build.bat) with auto-detection of ESP-IDF toolchains and COM ports:

```cmd
:: Build the project
Build.bat build

:: Build and flash via USB Serial (auto-detects COM port)
Build.bat flash

:: Flash to a specific COM port and open serial monitor
Build.bat flash COM39
Build.bat monitor COM39

:: Launch interactive menuconfig
Build.bat menuconfig

:: Full clean
Build.bat clean
```

### One-Click Wireless OTA

To flash new firmware over the network without plugging into the serial port:

```cmd
Build.bat ota <DEVICE_IP>
```

**Example:**
```cmd
Build.bat ota 172.16.1.54
```

The script builds the project, validates binary integrity, sends the payload via HTTP POST to `/api/ota`, verifies the flashing progress, and the ESP32-P4 automatically switches OTA slots and reboots in under 5 seconds.

---

## 🔍 Troubleshooting & Diagnostics

### 1. "Failed to connect to ESP32-P4: Download mode successfully detected, but getting no sync reply"
* **Cause:** The USB-to-HDMI capture card draws high current during board boot, causing a brief VBUS brownout, or the serial monitor is locking the COM port.
* **Fix:**
  1. Temporarily unplug the capture card from **USB3** during serial flashing.
  2. Close any serial monitor instances (Arduino IDE, PuTTY, VSCode).
  3. Hold **SW1 [BOOT]**, press and release **SW2 [RST]**, then release **SW1 [BOOT]** to enter manual bootloader mode.
  4. Once flashed once, use **Network OTA (`Build.bat ota <IP>`)** for seamless subsequent updates.

### 2. Host PC Shows `COMxx` Serial Port Instead of Keyboard/Mouse on USB2
* **Cause:** ESP32-P4 secondary console was routing USB Serial/JTAG to GPIO 42/43.
* **Fix:** Verify `CONFIG_ESP_CONSOLE_SECONDARY_NONE=y` is set in `sdkconfig` and `usb_wrap_ll_phy_select(&USB_WRAP, 0)` is called in `main/hid_device_mgr.c`.

### 3. Video Stream Stalls or PC Screen Resizes
* **Cause:** The host computer changed resolution, or the capture card froze its internal FIFO.
* **Fix:** The firmware features an integrated **4-second frame watchdog** that automatically restarts the UVC engine without human intervention. You can also click **"Force Reconnect USB"** in the Web UI.

---

## 📄 License

This project is licensed under the Apache 2.0 License. Designed for the Guition JC-ESP32P4-M3-DEV board.
