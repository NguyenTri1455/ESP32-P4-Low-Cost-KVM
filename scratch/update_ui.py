# -*- coding: utf-8 -*-
"""
Helper script to update scratch/generate_web_ui.py with:
1. Virtual Keyboard UI (floating draggable on-screen keyboard)
2. Settings Dialog (DHCP/Static IP, Wi-Fi Client, mDNS Responder)
3. Header & control dock buttons
"""

import sys

with open('scratch/generate_web_ui.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. CSS for Virtual Keyboard & Settings Modal
css_addition = '''
        /* Virtual Keyboard */
        .virtual-kb {
            position: fixed;
            bottom: 24px;
            right: 24px;
            width: 800px;
            max-width: calc(100vw - 30px);
            background: rgba(13, 20, 36, 0.95);
            backdrop-filter: blur(24px);
            -webkit-backdrop-filter: blur(24px);
            border: 1px solid rgba(0, 210, 255, 0.35);
            border-radius: 12px;
            box-shadow: 0 16px 45px rgba(0, 0, 0, 0.8), 0 0 25px rgba(0, 210, 255, 0.15);
            z-index: 1050;
            user-select: none;
            -webkit-user-select: none;
            display: none;
            flex-direction: column;
            overflow: hidden;
            transition: box-shadow 0.2s ease;
        }
        .virtual-kb.visible { display: flex; }
        .virtual-kb.collapsed .vk-body { display: none; }
        .vk-header {
            background: linear-gradient(90deg, rgba(22, 33, 58, 0.95), rgba(12, 18, 34, 0.95));
            padding: 7px 12px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            cursor: grab;
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        }
        .vk-header:active { cursor: grabbing; }
        .vk-title {
            font-size: 0.76rem;
            font-weight: 700;
            letter-spacing: 0.06em;
            color: var(--accent);
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .vk-tools { display: flex; align-items: center; gap: 6px; }
        .vk-body {
            padding: 10px;
            display: flex;
            flex-direction: column;
            gap: 5px;
            background: rgba(8, 12, 22, 0.85);
        }
        .vk-macros {
            display: flex;
            align-items: center;
            gap: 6px;
            flex-wrap: wrap;
            padding-bottom: 6px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.06);
        }
        .vk-macro-btn {
            background: rgba(30, 42, 70, 0.7);
            border: 1px solid rgba(0, 210, 255, 0.25);
            color: var(--text-main);
            border-radius: 5px;
            padding: 3px 8px;
            font-size: 0.72rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.15s;
        }
        .vk-macro-btn:hover {
            background: var(--accent-gradient);
            color: #fff;
            box-shadow: 0 0 10px rgba(0, 210, 255, 0.4);
        }
        .vk-row {
            display: flex;
            gap: 4px;
            justify-content: space-between;
            width: 100%;
        }
        .vk-key {
            flex: 1;
            min-width: 26px;
            height: 36px;
            background: rgba(22, 30, 50, 0.85);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-bottom: 2px solid rgba(0, 0, 0, 0.6);
            border-radius: 4px;
            color: #e2e8f0;
            font-family: inherit;
            font-size: 0.75rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: all 0.08s ease;
            touch-action: manipulation;
        }
        .vk-key:hover {
            background: rgba(36, 50, 80, 0.95);
            border-color: rgba(0, 210, 255, 0.5);
            color: #fff;
        }
        .vk-key:active {
            transform: translateY(2px);
            border-bottom-width: 1px;
            background: rgba(0, 210, 255, 0.35);
        }
        .vk-key.active {
            background: rgba(0, 210, 255, 0.35);
            border-color: var(--accent);
            color: #fff;
            box-shadow: 0 0 10px rgba(0, 210, 255, 0.6);
        }
        .vk-w-12 { flex: 1.25; }
        .vk-w-15 { flex: 1.5; }
        .vk-w-17 { flex: 1.75; }
        .vk-w-20 { flex: 2; }
        .vk-w-space { flex: 5.5; }

        /* Settings Modal Tabs & Controls */
        .settings-tabs {
            display: flex;
            border-bottom: 1px solid var(--border);
            margin-bottom: 16px;
            gap: 6px;
        }
        .settings-tab {
            padding: 8px 14px;
            background: none;
            border: none;
            border-bottom: 2px solid transparent;
            color: var(--text-dim);
            font-size: 0.82rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }
        .settings-tab:hover { color: #fff; }
        .settings-tab.active {
            color: var(--accent);
            border-bottom-color: var(--accent);
        }
        .tab-pane { display: none; }
        .tab-pane.active { display: block; }
        .form-group { margin-bottom: 14px; }
        .form-label {
            display: block;
            font-size: 0.78rem;
            font-weight: 600;
            color: var(--text-dim);
            margin-bottom: 6px;
        }
        .radio-group {
            display: flex;
            gap: 16px;
            margin-bottom: 12px;
        }
        .radio-item {
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 0.82rem;
            cursor: pointer;
        }
        .switch-group {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 10px 12px;
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid var(--border);
            border-radius: 8px;
            margin-bottom: 14px;
        }
        .switch {
            position: relative;
            display: inline-block;
            width: 44px;
            height: 24px;
        }
        .switch input { opacity: 0; width: 0; height: 0; }
        .slider {
            position: absolute;
            cursor: pointer;
            top: 0; left: 0; right: 0; bottom: 0;
            background-color: rgba(255, 255, 255, 0.15);
            transition: .3s;
            border-radius: 24px;
        }
        .slider:before {
            position: absolute;
            content: "";
            height: 18px;
            width: 18px;
            left: 3px;
            bottom: 3px;
            background-color: white;
            transition: .3s;
            border-radius: 50%;
        }
        input:checked + .slider { background-color: var(--accent); }
        input:checked + .slider:before { transform: translateX(20px); }
'''

target_css = '        footer {\n'
if target_css in content:
    content = content.replace(target_css, css_addition + target_css, 1)
else:
    print("Error: target_css not found!")
    sys.exit(1)

# 2. Add Settings Modal HTML
settings_modal_html = '''
    <!-- Network & System Settings Modal -->
    <div id="settings-modal" class="modal-overlay" style="display:none;">
        <div class="modal-card" style="max-width:540px;width:95%;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
                <h3 style="font-size:1.15rem;display:flex;align-items:center;gap:8px;">
                    <span>&#x2699;</span> Network &amp; System Settings
                </h3>
                <button class="btn" style="padding:2px 8px;font-size:0.8rem;" onclick="closeModal('settings-modal')">&times;</button>
            </div>
            
            <div id="settings-status-msg" style="display:none;padding:8px 12px;border-radius:6px;font-size:0.8rem;margin-bottom:12px;"></div>

            <div class="settings-tabs">
                <button class="settings-tab active" onclick="switchSettingsTab('tab-eth', this)">&#x1F310; Ethernet (IP)</button>
                <button class="settings-tab" onclick="switchSettingsTab('tab-wifi', this)">&#x1F4F6; Wi-Fi Client</button>
                <button class="settings-tab" onclick="switchSettingsTab('tab-mdns', this)">&#x1F3F7; mDNS</button>
            </div>

            <!-- Tab 1: Ethernet / IP -->
            <div id="tab-eth" class="tab-pane active">
                <div style="margin-bottom:12px;padding:8px 12px;background:rgba(0,210,255,0.06);border:1px solid rgba(0,210,255,0.2);border-radius:6px;font-size:0.78rem;display:flex;justify-content:space-between;align-items:center;">
                    <span>Active Interface: <b>IP101 100M RMII</b></span>
                    <span>Current IP: <b id="settings-cur-ip" style="color:var(--accent);">---</b></span>
                </div>
                <div class="form-group">
                    <label class="form-label">IP Mode Configuration</label>
                    <div class="radio-group">
                        <label class="radio-item">
                            <input type="radio" name="net_mode" id="mode-dhcp" value="dhcp" checked onchange="toggleIpFields()">
                            <span>DHCP (Automatic IP - Recommended)</span>
                        </label>
                        <label class="radio-item">
                            <input type="radio" name="net_mode" id="mode-static" value="static" onchange="toggleIpFields()">
                            <span>Static IP</span>
                        </label>
                    </div>
                </div>
                <div id="static-fields" style="display:none;">
                    <div class="form-group">
                        <label class="form-label">Static IPv4 Address</label>
                        <input type="text" id="net-ip" class="input-field" placeholder="172.16.1.54" />
                    </div>
                    <div style="display:flex;gap:10px;">
                        <div class="form-group" style="flex:1;">
                            <label class="form-label">Subnet Mask</label>
                            <input type="text" id="net-mask" class="input-field" placeholder="255.255.255.0" />
                        </div>
                        <div class="form-group" style="flex:1;">
                            <label class="form-label">Default Gateway</label>
                            <input type="text" id="net-gw" class="input-field" placeholder="172.16.1.1" />
                        </div>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Primary DNS Server</label>
                        <input type="text" id="net-dns" class="input-field" placeholder="8.8.8.8" />
                    </div>
                </div>
            </div>

            <!-- Tab 2: Wi-Fi Client -->
            <div id="tab-wifi" class="tab-pane">
                <div class="switch-group">
                    <div>
                        <div style="font-weight:600;font-size:0.85rem;">Enable Wi-Fi Client</div>
                        <div style="font-size:0.72rem;color:var(--text-dim);">Connect to Wi-Fi AP via onboard ESP32-C6 coprocessor</div>
                    </div>
                    <label class="switch">
                        <input type="checkbox" id="net-wifi-en">
                        <span class="slider"></span>
                    </label>
                </div>
                <div class="form-group">
                    <label class="form-label">Wi-Fi Network Name (SSID)</label>
                    <input type="text" id="net-wifi-ssid" class="input-field" placeholder="Enter SSID" />
                </div>
                <div class="form-group">
                    <label class="form-label">Wi-Fi Password</label>
                    <div style="position:relative;">
                        <input type="password" id="net-wifi-pass" class="input-field" placeholder="Enter Wi-Fi Password" style="padding-right:40px;margin-bottom:0;" />
                        <button type="button" style="position:absolute;right:10px;top:50%;transform:translateY(-50%);background:none;border:none;color:var(--text-dim);cursor:pointer;" onclick="togglePasswordVisibility('net-wifi-pass')">&#x1F441;</button>
                    </div>
                    <div id="net-wifi-pass-hint" style="font-size:0.7rem;color:var(--text-dim);margin-top:4px;">Leave blank to keep existing password.</div>
                </div>
            </div>

            <!-- Tab 3: mDNS Responder -->
            <div id="tab-mdns" class="tab-pane">
                <div class="switch-group">
                    <div>
                        <div style="font-weight:600;font-size:0.85rem;">Enable mDNS Responder</div>
                        <div style="font-size:0.72rem;color:var(--text-dim);">Resolve device via local multicast hostname</div>
                    </div>
                    <label class="switch">
                        <input type="checkbox" id="net-mdns-en" checked>
                        <span class="slider"></span>
                    </label>
                </div>
                <div class="form-group">
                    <label class="form-label">mDNS Hostname</label>
                    <div style="display:flex;align-items:center;">
                        <input type="text" id="net-mdns-host" class="input-field" placeholder="esp32p4-kvm" style="margin-bottom:0;border-top-right-radius:0;border-bottom-right-radius:0;" oninput="updateMdnsPreview(this.value)" />
                        <span style="background:rgba(255,255,255,0.08);border:1px solid var(--border);border-left:none;padding:10px 12px;border-top-right-radius:8px;border-bottom-right-radius:8px;font-size:0.85rem;color:var(--text-dim);">.local</span>
                    </div>
                </div>
                <div style="padding:10px 12px;background:rgba(255,255,255,0.04);border-radius:6px;font-size:0.78rem;margin-top:10px;">
                    <span>Direct Access URL: </span>
                    <a id="net-mdns-preview" href="http://esp32p4-kvm.local/" target="_blank" style="color:var(--accent);font-weight:600;text-decoration:none;">http://esp32p4-kvm.local/</a>
                </div>
            </div>

            <!-- Modal Footer -->
            <div style="display:flex;gap:10px;margin-top:18px;border-top:1px solid var(--border);padding-top:14px;flex-wrap:wrap;">
                <button class="btn btn-primary" style="flex:1;padding:9px;" onclick="saveNetworkSettings(false)">&#x1F4BE; Save Settings</button>
                <button class="btn btn-warning" style="flex:1;padding:9px;" onclick="saveNetworkSettings(true)">&#x21BB; Save &amp; Reboot</button>
                <button class="btn" style="padding:9px 16px;" onclick="closeModal('settings-modal')">Cancel</button>
            </div>
        </div>
    </div>
'''

target_pwd_end = '            </div>\n        </div>\n    </div>\n\n    <!-- Floating Draggable Performance HUD'
if target_pwd_end in content:
    content = content.replace(target_pwd_end, '            </div>\n        </div>\n    </div>' + settings_modal_html + '\n    <!-- Floating Draggable Performance HUD', 1)
else:
    print("Error: target_pwd_end not found!")
    sys.exit(1)

# 3. Add Virtual Keyboard HTML
virtual_kb_html = '''
    <!-- Floating Draggable Virtual Keyboard -->
    <div id="virtual-kb" class="virtual-kb">
        <div class="vk-header" id="vk-header">
            <div class="vk-title">
                <span class="drag-grip" title="Drag to move Keyboard">&#x283F;</span>
                <span>&#x2328; VIRTUAL KEYBOARD</span>
            </div>
            <div class="vk-tools">
                <button class="hud-btn" id="btn-vk-min" onclick="toggleVkCollapse()" title="Minimize / Expand">_</button>
                <button class="hud-btn" id="btn-vk-close" onclick="toggleVirtualKeyboard()" title="Close Keyboard">&times;</button>
            </div>
        </div>
        <div class="vk-body" id="vk-body">
            <!-- Macros Bar -->
            <div class="vk-macros">
                <span style="font-size:0.7rem;color:var(--text-dim);margin-right:4px;">Macros:</span>
                <button class="vk-macro-btn" onclick="sendMacro('CAD')">Ctrl+Alt+Del</button>
                <button class="vk-macro-btn" onclick="sendMacro('ALT_TAB')">Alt+Tab</button>
                <button class="vk-macro-btn" onclick="onVkMacro('WIN_R')">Win+R</button>
                <button class="vk-macro-btn" onclick="onVkMacro('ALT_F4')">Alt+F4</button>
                <button class="vk-macro-btn" onclick="onVkKey(0x29)">Esc</button>
                <button class="vk-macro-btn" style="color:var(--danger);border-color:rgba(239,68,68,0.3);" onclick="clearVkModifiers()">Clear Modifiers</button>
            </div>

            <!-- Row 0: Function Keys -->
            <div class="vk-row">
                <button class="vk-key" onclick="onVkKey(0x29)">Esc</button>
                <button class="vk-key" onclick="onVkKey(0x3A)">F1</button>
                <button class="vk-key" onclick="onVkKey(0x3B)">F2</button>
                <button class="vk-key" onclick="onVkKey(0x3C)">F3</button>
                <button class="vk-key" onclick="onVkKey(0x3D)">F4</button>
                <button class="vk-key" onclick="onVkKey(0x3E)">F5</button>
                <button class="vk-key" onclick="onVkKey(0x3F)">F6</button>
                <button class="vk-key" onclick="onVkKey(0x40)">F7</button>
                <button class="vk-key" onclick="onVkKey(0x41)">F8</button>
                <button class="vk-key" onclick="onVkKey(0x42)">F9</button>
                <button class="vk-key" onclick="onVkKey(0x43)">F10</button>
                <button class="vk-key" onclick="onVkKey(0x44)">F11</button>
                <button class="vk-key" onclick="onVkKey(0x45)">F12</button>
                <button class="vk-key" onclick="onVkKey(0x46)">PrtSc</button>
                <button class="vk-key" onclick="onVkKey(0x4C)">Del</button>
            </div>

            <!-- Row 1: Numbers -->
            <div class="vk-row">
                <button class="vk-key" onclick="onVkKey(0x35)">` ~</button>
                <button class="vk-key" onclick="onVkKey(0x1E)">1 !</button>
                <button class="vk-key" onclick="onVkKey(0x1F)">2 @</button>
                <button class="vk-key" onclick="onVkKey(0x20)">3 #</button>
                <button class="vk-key" onclick="onVkKey(0x21)">4 $</button>
                <button class="vk-key" onclick="onVkKey(0x22)">5 %</button>
                <button class="vk-key" onclick="onVkKey(0x23)">6 ^</button>
                <button class="vk-key" onclick="onVkKey(0x24)">7 &amp;</button>
                <button class="vk-key" onclick="onVkKey(0x25)">8 *</button>
                <button class="vk-key" onclick="onVkKey(0x26)">9 (</button>
                <button class="vk-key" onclick="onVkKey(0x27)">0 )</button>
                <button class="vk-key" onclick="onVkKey(0x2D)">- _</button>
                <button class="vk-key" onclick="onVkKey(0x2E)">= +</button>
                <button class="vk-key vk-w-15" onclick="onVkKey(0x2A)">&#x232B; Bksp</button>
            </div>

            <!-- Row 2: Tab / QWERTY -->
            <div class="vk-row">
                <button class="vk-key vk-w-12" onclick="onVkKey(0x2B)">Tab &#x21E5;</button>
                <button class="vk-key" onclick="onVkKey(0x14)">Q</button>
                <button class="vk-key" onclick="onVkKey(0x15)">W</button>
                <button class="vk-key" onclick="onVkKey(0x16)">E</button>
                <button class="vk-key" onclick="onVkKey(0x17)">R</button>
                <button class="vk-key" onclick="onVkKey(0x18)">T</button>
                <button class="vk-key" onclick="onVkKey(0x19)">Y</button>
                <button class="vk-key" onclick="onVkKey(0x1A)">U</button>
                <button class="vk-key" onclick="onVkKey(0x1B)">I</button>
                <button class="vk-key" onclick="onVkKey(0x1C)">O</button>
                <button class="vk-key" onclick="onVkKey(0x1D)">P</button>
                <button class="vk-key" onclick="onVkKey(0x2F)">[ {</button>
                <button class="vk-key" onclick="onVkKey(0x30)">] }</button>
                <button class="vk-key vk-w-12" onclick="onVkKey(0x31)">\\ |</button>
            </div>

            <!-- Row 3: Caps / ASDF -->
            <div class="vk-row">
                <button class="vk-key vk-w-15" onclick="onVkKey(0x39)">Caps &#x21EA;</button>
                <button class="vk-key" onclick="onVkKey(0x04)">A</button>
                <button class="vk-key" onclick="onVkKey(0x05)">S</button>
                <button class="vk-key" onclick="onVkKey(0x06)">D</button>
                <button class="vk-key" onclick="onVkKey(0x07)">F</button>
                <button class="vk-key" onclick="onVkKey(0x08)">G</button>
                <button class="vk-key" onclick="onVkKey(0x09)">H</button>
                <button class="vk-key" onclick="onVkKey(0x0A)">J</button>
                <button class="vk-key" onclick="onVkKey(0x0B)">K</button>
                <button class="vk-key" onclick="onVkKey(0x0C)">L</button>
                <button class="vk-key" onclick="onVkKey(0x33)">; :</button>
                <button class="vk-key" onclick="onVkKey(0x34)">' \"</button>
                <button class="vk-key vk-w-17" onclick="onVkKey(0x28)">&#x21B5; Enter</button>
            </div>

            <!-- Row 4: Shift / ZXCV -->
            <div class="vk-row">
                <button class="vk-key vk-mod vk-w-20" id="vk-lshift" onclick="onVkMod(0x02, this)">&#x21E7; Shift</button>
                <button class="vk-key" onclick="onVkKey(0x1D)">Z</button>
                <button class="vk-key" onclick="onVkKey(0x1B)">X</button>
                <button class="vk-key" onclick="onVkKey(0x06)">C</button>
                <button class="vk-key" onclick="onVkKey(0x19)">V</button>
                <button class="vk-key" onclick="onVkKey(0x05)">B</button>
                <button class="vk-key" onclick="onVkKey(0x11)">N</button>
                <button class="vk-key" onclick="onVkKey(0x10)">M</button>
                <button class="vk-key" onclick="onVkKey(0x36)">, &lt;</button>
                <button class="vk-key" onclick="onVkKey(0x37)">. &gt;</button>
                <button class="vk-key" onclick="onVkKey(0x38)">/ ?</button>
                <button class="vk-key vk-mod vk-w-20" id="vk-rshift" onclick="onVkMod(0x20, this)">&#x21E7; Shift</button>
            </div>

            <!-- Row 5: Modifiers, Space, Arrows -->
            <div class="vk-row">
                <button class="vk-key vk-mod vk-w-12" id="vk-lctrl" onclick="onVkMod(0x01, this)">Ctrl</button>
                <button class="vk-key vk-mod" id="vk-lmeta" onclick="onVkMod(0x08, this)">&#x229E; Win</button>
                <button class="vk-key vk-mod" id="vk-lalt" onclick="onVkMod(0x04, this)">Alt</button>
                <button class="vk-key vk-w-space" onclick="onVkKey(0x2C)">&#x2423; Space</button>
                <button class="vk-key vk-mod" id="vk-ralt" onclick="onVkMod(0x40, this)">Alt</button>
                <button class="vk-key vk-mod vk-w-12" id="vk-rctrl" onclick="onVkMod(0x10, this)">Ctrl</button>
                <button class="vk-key" onclick="onVkKey(0x50)">&#x25C0;</button>
                <button class="vk-key" onclick="onVkKey(0x52)">&#x25B2;</button>
                <button class="vk-key" onclick="onVkKey(0x51)">&#x25BC;</button>
                <button class="vk-key" onclick="onVkKey(0x4F)">&#x25B6;</button>
            </div>
        </div>
    </div>
'''

target_hud_end = '        </div>\n    </div>\n\n    <header>'
if target_hud_end in content:
    content = content.replace(target_hud_end, '        </div>\n    </div>' + virtual_kb_html + '\n\n    <header>', 1)
else:
    print("Error: target_hud_end not found!")
    sys.exit(1)

# 4. Add Buttons to Header
target_header_btns = '<button class="btn active" id="btn-perf-toggle" style="padding:4px 9px;font-size:0.75rem;" onclick="togglePerfVisibility()">&#x1F4CA; HUD</button>'
header_btns_addition = '''<button class="btn active" id="btn-perf-toggle" style="padding:4px 9px;font-size:0.75rem;" onclick="togglePerfVisibility()">&#x1F4CA; HUD</button>
            <button class="btn" id="btn-vk-toggle" style="padding:4px 9px;font-size:0.75rem;" onclick="toggleVirtualKeyboard()">&#x2328; Keyboard</button>
            <button class="btn" id="btn-settings-toggle" style="padding:4px 9px;font-size:0.75rem;" onclick="openSettingsModal()">&#x2699; Settings</button>'''

if target_header_btns in content:
    content = content.replace(target_header_btns, header_btns_addition, 1)
else:
    print("Error: target_header_btns not found!")
    sys.exit(1)

# 5. Add Button to Control Dock
target_dock_btn = '<button class="btn" id="btn-kvm" onclick="toggleKvmMode()">&#x2328; KVM Mode</button>'
dock_btn_addition = '''<button class="btn" id="btn-kvm" onclick="toggleKvmMode()">&#x2328; KVM Mode</button>
            <button class="btn" id="btn-vk-dock" onclick="toggleVirtualKeyboard()">&#x2328; Virtual Keyboard</button>'''

if target_dock_btn in content:
    content = content.replace(target_dock_btn, dock_btn_addition, 1)
else:
    print("Error: target_dock_btn not found!")
    sys.exit(1)

# 6. Add JavaScript for Virtual Keyboard & Settings Modal
js_addition = '''
        /* Virtual Keyboard Logic */
        const vkPanel = document.getElementById('virtual-kb');
        const vkHeader = document.getElementById('vk-header');
        let isDraggingVk = false;
        let vkStartX = 0, vkStartY = 0, vkInitLeft = 0, vkInitTop = 0;
        let vkModifiers = 0;

        function loadVkState() {
            if (!vkPanel) return;
            const isVisible = localStorage.getItem('vk_visible') === 'true';
            const isCollapsed = localStorage.getItem('vk_collapsed') === 'true';
            const savedX = localStorage.getItem('vk_x');
            const savedY = localStorage.getItem('vk_y');

            if (isVisible) {
                vkPanel.classList.add('visible');
                updateVkButtonStates(true);
            } else {
                vkPanel.classList.remove('visible');
                updateVkButtonStates(false);
            }

            if (isCollapsed) {
                vkPanel.classList.add('collapsed');
                const btn = document.getElementById('btn-vk-min');
                if (btn) btn.textContent = '+';
            }

            if (savedX !== null && savedY !== null) {
                const maxX = Math.max(10, window.innerWidth - 80);
                const maxY = Math.max(10, window.innerHeight - 60);
                const x = Math.min(Math.max(10, parseInt(savedX, 10)), maxX);
                const y = Math.min(Math.max(10, parseInt(savedY, 10)), maxY);
                vkPanel.style.left = x + 'px';
                vkPanel.style.top = y + 'px';
                vkPanel.style.right = 'auto';
                vkPanel.style.bottom = 'auto';
            }
        }

        function updateVkButtonStates(active) {
            const hBtn = document.getElementById('btn-vk-toggle');
            if (hBtn) hBtn.classList.toggle('active', active);
            const dBtn = document.getElementById('btn-vk-dock');
            if (dBtn) dBtn.classList.toggle('active', active);
        }

        function toggleVirtualKeyboard() {
            if (!vkPanel) return;
            const willShow = !vkPanel.classList.contains('visible');
            vkPanel.classList.toggle('visible', willShow);
            updateVkButtonStates(willShow);
            localStorage.setItem('vk_visible', willShow ? 'true' : 'false');
        }

        function toggleVkCollapse() {
            if (!vkPanel) return;
            vkPanel.classList.toggle('collapsed');
            const collapsed = vkPanel.classList.contains('collapsed');
            localStorage.setItem('vk_collapsed', collapsed ? 'true' : 'false');
            const btn = document.getElementById('btn-vk-min');
            if (btn) btn.textContent = collapsed ? '+' : '_';
        }

        function onVkMod(mask, btn) {
            if (vkModifiers & mask) {
                vkModifiers &= ~mask;
                btn.classList.remove('active');
            } else {
                vkModifiers |= mask;
                btn.classList.add('active');
            }
        }

        function clearVkModifiers() {
            vkModifiers = 0;
            document.querySelectorAll('.vk-mod').forEach(b => b.classList.remove('active'));
        }

        function onVkKey(hidCode) {
            sendWs({
                type: 'key',
                mod: vkModifiers,
                keys: [hidCode]
            });
            if (keyIndicator) keyIndicator.textContent = '0x' + hidCode.toString(16).toUpperCase();
            setTimeout(() => {
                sendWs({
                    type: 'key',
                    mod: 0,
                    keys: []
                });
                clearVkModifiers();
                if (keyIndicator) keyIndicator.textContent = 'None';
            }, 80);
        }

        function onVkMacro(name) {
            if (name === 'WIN_R') {
                sendWs({ type: 'key', mod: 0x08, keys: [0x15] });
                setTimeout(() => sendWs({ type: 'key', mod: 0, keys: [] }), 80);
            } else if (name === 'ALT_F4') {
                sendWs({ type: 'key', mod: 0x04, keys: [0x3D] });
                setTimeout(() => sendWs({ type: 'key', mod: 0, keys: [] }), 80);
            }
        }

        function onVkStart(clientX, clientY, target) {
            if (target && target.closest('.hud-btn')) return;
            isDraggingVk = true;
            vkStartX = clientX;
            vkStartY = clientY;
            const rect = vkPanel.getBoundingClientRect();
            vkInitLeft = rect.left;
            vkInitTop = rect.top;
            vkPanel.style.right = 'auto';
            vkPanel.style.bottom = 'auto';
            vkPanel.style.left = vkInitLeft + 'px';
            vkPanel.style.top = vkInitTop + 'px';
        }

        function onVkMove(clientX, clientY) {
            if (!isDraggingVk) return;
            const dx = clientX - vkStartX;
            const dy = clientY - vkStartY;
            let newX = vkInitLeft + dx;
            let newY = vkInitTop + dy;
            const maxW = window.innerWidth - vkPanel.offsetWidth - 10;
            const maxH = window.innerHeight - vkPanel.offsetHeight - 10;
            newX = Math.max(10, Math.min(maxW, newX));
            newY = Math.max(10, Math.min(maxH, newY));
            vkPanel.style.left = newX + 'px';
            vkPanel.style.top = newY + 'px';
        }

        function onVkEnd() {
            if (isDraggingVk) {
                isDraggingVk = false;
                localStorage.setItem('vk_x', parseInt(vkPanel.style.left, 10));
                localStorage.setItem('vk_y', parseInt(vkPanel.style.top, 10));
            }
        }

        if (vkHeader) {
            vkHeader.addEventListener('mousedown', (e) => {
                onVkStart(e.clientX, e.clientY, e.target);
                e.preventDefault();
            });
            vkHeader.addEventListener('touchstart', (e) => {
                if (e.touches.length > 0) {
                    onVkStart(e.touches[0].clientX, e.touches[0].clientY, e.target);
                }
            }, { passive: true });
        }

        window.addEventListener('mousemove', (e) => onVkMove(e.clientX, e.clientY));
        window.addEventListener('touchmove', (e) => {
            if (isDraggingVk && e.touches.length > 0) {
                onVkMove(e.touches[0].clientX, e.touches[0].clientY);
            }
        }, { passive: true });
        window.addEventListener('mouseup', onVkEnd);
        window.addEventListener('touchend', onVkEnd);

        /* Network & System Settings Modal Logic */
        function openSettingsModal() {
            openModal('settings-modal');
            const statusEl = document.getElementById('settings-status-msg');
            if (statusEl) statusEl.style.display = 'none';

            fetch('/api/network')
                .then(r => r.json())
                .then(d => {
                    if (d.status === 'ok') {
                        const curIpEl = document.getElementById('settings-cur-ip');
                        if (curIpEl) curIpEl.textContent = d.current_ip || '---';

                        if (d.dhcp_enabled) {
                            document.getElementById('mode-dhcp').checked = true;
                            document.getElementById('mode-static').checked = false;
                            document.getElementById('static-fields').style.display = 'none';
                        } else {
                            document.getElementById('mode-dhcp').checked = false;
                            document.getElementById('mode-static').checked = true;
                            document.getElementById('static-fields').style.display = 'block';
                        }

                        document.getElementById('net-ip').value = d.static_ip || '';
                        document.getElementById('net-mask').value = d.static_netmask || '255.255.255.0';
                        document.getElementById('net-gw').value = d.static_gw || '';
                        document.getElementById('net-dns').value = d.static_dns || '8.8.8.8';

                        document.getElementById('net-wifi-en').checked = !!d.wifi_enabled;
                        document.getElementById('net-wifi-ssid').value = d.wifi_ssid || '';
                        document.getElementById('net-wifi-pass').value = '';
                        const pHint = document.getElementById('net-wifi-pass-hint');
                        if (pHint) {
                            pHint.textContent = d.wifi_pass_set ? 'Password is currently set. Leave blank to keep existing.' : 'Leave blank if unencrypted.';
                        }

                        document.getElementById('net-mdns-en').checked = !!d.mdns_enabled;
                        document.getElementById('net-mdns-host').value = d.mdns_hostname || 'esp32p4-kvm';
                        updateMdnsPreview(d.mdns_hostname || 'esp32p4-kvm');
                    }
                })
                .catch(err => {
                    console.error('Failed to load network settings:', err);
                });
        }

        function switchSettingsTab(tabId, btn) {
            document.querySelectorAll('.settings-tab').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
            if (btn) btn.classList.add('active');
            const targetPane = document.getElementById(tabId);
            if (targetPane) targetPane.classList.add('active');
        }

        function toggleIpFields() {
            const isStatic = document.getElementById('mode-static').checked;
            const fields = document.getElementById('static-fields');
            if (fields) fields.style.display = isStatic ? 'block' : 'none';
        }

        function updateMdnsPreview(val) {
            const host = (val || 'esp32p4-kvm').trim();
            const link = document.getElementById('net-mdns-preview');
            if (link) {
                link.textContent = 'http://' + host + '.local/';
                link.href = 'http://' + host + '.local/';
            }
        }

        function togglePasswordVisibility(id) {
            const el = document.getElementById(id);
            if (el) el.type = el.type === 'password' ? 'text' : 'password';
        }

        function saveNetworkSettings(reboot) {
            const statusEl = document.getElementById('settings-status-msg');
            const isDhcp = document.getElementById('mode-dhcp').checked;
            const staticIp = document.getElementById('net-ip').value.trim();
            const staticNetmask = document.getElementById('net-mask').value.trim();
            const staticGw = document.getElementById('net-gw').value.trim();
            const staticDns = document.getElementById('net-dns').value.trim();

            if (!isDhcp && (!staticIp || !staticNetmask || !staticGw)) {
                if (statusEl) {
                    statusEl.style.display = 'block';
                    statusEl.style.background = 'rgba(239, 68, 68, 0.15)';
                    statusEl.style.border = '1px solid var(--danger)';
                    statusEl.style.color = 'var(--danger)';
                    statusEl.textContent = 'Please fill out all Static IP fields (IP, Netmask, Gateway).';
                }
                return;
            }

            const payload = {
                dhcp_enabled: isDhcp,
                static_ip: staticIp || '172.16.1.54',
                static_netmask: staticNetmask || '255.255.255.0',
                static_gw: staticGw || '172.16.1.1',
                static_dns: staticDns || '8.8.8.8',
                wifi_enabled: document.getElementById('net-wifi-en').checked,
                wifi_ssid: document.getElementById('net-wifi-ssid').value.trim(),
                wifi_password: document.getElementById('net-wifi-pass').value,
                mdns_enabled: document.getElementById('net-mdns-en').checked,
                mdns_hostname: document.getElementById('net-mdns-host').value.trim() || 'esp32p4-kvm',
                reboot: !!reboot
            };

            if (statusEl) {
                statusEl.style.display = 'block';
                statusEl.style.background = 'rgba(0, 210, 255, 0.15)';
                statusEl.style.border = '1px solid var(--accent)';
                statusEl.style.color = '#fff';
                statusEl.textContent = reboot ? 'Saving and restarting device...' : 'Saving network configuration...';
            }

            fetch('/api/network', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            })
            .then(r => r.json())
            .then(d => {
                if (d.status === 'ok') {
                    if (reboot) {
                        let countdown = 6;
                        const targetUrl = isDhcp ? ('http://' + (payload.mdns_hostname || 'esp32p4-kvm') + '.local/') : ('http://' + payload.static_ip + '/');
                        statusEl.innerHTML = `Settings saved! ESP32-P4 is rebooting.<br>Reconnecting in <b>${countdown}</b>s to <a href="${targetUrl}" style="color:var(--accent);">${targetUrl}</a>...`;
                        const iv = setInterval(() => {
                            countdown--;
                            if (countdown <= 0) {
                                clearInterval(iv);
                                window.location.href = targetUrl;
                            } else {
                                statusEl.innerHTML = `Settings saved! ESP32-P4 is rebooting.<br>Reconnecting in <b>${countdown}</b>s to <a href="${targetUrl}" style="color:var(--accent);">${targetUrl}</a>...`;
                            }
                        }, 1000);
                    } else {
                        statusEl.style.background = 'rgba(16, 185, 129, 0.15)';
                        statusEl.style.border = '1px solid var(--success)';
                        statusEl.style.color = 'var(--success)';
                        statusEl.textContent = 'Settings saved successfully to NVS! Static IP changes will take effect on next reboot.';
                        setTimeout(() => { if (statusEl) statusEl.style.display = 'none'; }, 4000);
                    }
                } else {
                    throw new Error(d.message || 'Server error');
                }
            })
            .catch(err => {
                if (statusEl) {
                    statusEl.style.display = 'block';
                    statusEl.style.background = 'rgba(239, 68, 68, 0.15)';
                    statusEl.style.border = '1px solid var(--danger)';
                    statusEl.style.color = 'var(--danger)';
                    statusEl.textContent = 'Failed to save settings: ' + err.message;
                }
            });
        }
'''

target_init = '''        // Initialize HUD & Auth on Page Load
        window.addEventListener('DOMContentLoaded', () => {
            loadPerfHudState();
            checkAuth();
        });'''

init_addition = '''        // Initialize HUD, Virtual Keyboard & Auth on Page Load
        window.addEventListener('DOMContentLoaded', () => {
            loadPerfHudState();
            loadVkState();
            checkAuth();
        });'''

if target_init in content:
    content = content.replace(target_init, js_addition + '\n' + init_addition, 1)
else:
    print("Error: target_init not found!")
    sys.exit(1)

with open('scratch/generate_web_ui.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully updated scratch/generate_web_ui.py!")
