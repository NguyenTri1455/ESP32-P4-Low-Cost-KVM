import sys

html_content = r'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ESP32-P4 HDMI-over-Ethernet KVM</title>
    <style>
        :root {
            --bg-base: #070a12;
            --bg-card: rgba(14, 21, 37, 0.82);
            --bg-card-hover: rgba(24, 34, 58, 0.92);
            --border: rgba(255, 255, 255, 0.08);
            --border-glow: rgba(0, 210, 255, 0.25);
            --accent: #00d2ff;
            --accent-gradient: linear-gradient(135deg, #00d2ff 0%, #3a7bd5 100%);
            --accent-glow: rgba(0, 210, 255, 0.35);
            --text-main: #f8fafc;
            --text-dim: #94a3b8;
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background: radial-gradient(ellipse at 50% 0%, #131c31 0%, #070a12 100%);
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            overflow-x: hidden;
        }
        /* Top Navigation Header */
        header {
            background: var(--bg-card);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border-bottom: 1px solid var(--border);
            padding: 8px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            z-index: 100;
            gap: 12px;
            flex-wrap: wrap;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
        }
        .brand-box {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .brand-chip {
            background: var(--accent-gradient);
            color: #fff;
            font-weight: 800;
            font-size: 0.75rem;
            padding: 4px 9px;
            border-radius: 6px;
            letter-spacing: 0.5px;
            box-shadow: 0 0 14px var(--accent-glow);
        }
        .brand-title h1 {
            font-size: 1.0rem;
            font-weight: 700;
            color: var(--text-main);
            letter-spacing: -0.3px;
        }
        .brand-title p {
            font-size: 0.70rem;
            color: var(--text-dim);
        }
        .telemetry-cluster {
            display: flex;
            gap: 8px;
            align-items: center;
            flex-wrap: wrap;
        }
        .stat-pill {
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid var(--border);
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 0.74rem;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .stat-pill span { color: var(--text-dim); }
        .stat-pill b { color: var(--accent); font-weight: 600; }
        .led-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            display: inline-block;
        }
        .led-dot.online {
            background: var(--success);
            box-shadow: 0 0 8px var(--success);
        }
        .led-dot.offline {
            background: var(--danger);
            box-shadow: 0 0 8px var(--danger);
        }
        /* Main Video Canvas Area */
        main {
            flex: 1;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 12px 18px;
            gap: 12px;
            position: relative;
        }
        .screen-wrapper {
            position: relative;
            background: #000;
            border-radius: 14px;
            overflow: hidden;
            border: 1px solid var(--border);
            box-shadow: 0 16px 48px rgba(0, 0, 0, 0.75);
            max-width: 100%;
            display: flex;
            justify-content: center;
            align-items: center;
            cursor: crosshair;
            transition: border-color 0.25s, box-shadow 0.25s;
        }
        .screen-wrapper.ratio-fit {
            width: 1280px;
            max-height: calc(100vh - 190px);
            aspect-ratio: 16 / 9;
        }
        .screen-wrapper.pointer-locked {
            border-color: var(--accent);
            box-shadow: 0 0 28px var(--accent-glow), 0 0 0 1px var(--accent);
        }
        #stream-view {
            width: 100%;
            height: 100%;
            object-fit: contain;
            display: block;
            transition: filter 0.15s ease;
        }
        .reconnect-overlay {
            position: absolute;
            inset: 0;
            background: rgba(7, 10, 18, 0.90);
            backdrop-filter: blur(8px);
            display: none;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: 14px;
            z-index: 10;
        }
        .reconnect-overlay.show { display: flex; }
        .spinner {
            width: 44px;
            height: 44px;
            border: 3px solid rgba(255, 255, 255, 0.1);
            border-top: 3px solid var(--accent);
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
        }
        @keyframes spin { 100% { transform: rotate(360deg); } }
        /* Floating Control Dock */
        .control-dock {
            display: flex;
            gap: 6px;
            flex-wrap: wrap;
            align-items: center;
            background: var(--bg-card);
            border: 1px solid var(--border);
            padding: 6px 12px;
            border-radius: 12px;
            backdrop-filter: blur(16px);
            box-shadow: 0 8px 30px rgba(0, 0, 0, 0.5);
        }
        .btn {
            background: rgba(255, 255, 255, 0.05);
            color: var(--text-main);
            border: 1px solid var(--border);
            padding: 6px 12px;
            border-radius: 8px;
            font-size: 0.78rem;
            font-weight: 500;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 5px;
            transition: all 0.2s ease;
            outline: none;
            user-select: none;
        }
        .btn:hover {
            background: var(--bg-card-hover);
            border-color: var(--accent);
            box-shadow: 0 0 10px var(--accent-glow);
        }
        .btn:active { transform: translateY(1px); }
        .btn.active {
            background: var(--accent-gradient);
            color: #fff;
            border-color: transparent;
            box-shadow: 0 0 12px var(--accent-glow);
        }
        .btn.btn-primary {
            background: var(--accent-gradient);
            color: #fff;
            border-color: transparent;
            font-weight: 600;
        }
        .btn.btn-danger:hover {
            border-color: var(--danger);
            box-shadow: 0 0 10px rgba(239, 68, 68, 0.3);
        }
        /* Drawers */
        .drawer {
            display: none;
            margin-top: 6px;
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 8px 16px;
            gap: 14px;
            align-items: center;
            flex-wrap: wrap;
            font-size: 0.78rem;
            max-width: 95vw;
        }
        .drawer.open { display: flex; }
        .drawer-item {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .drawer-item input[type="range"] {
            accent-color: var(--accent);
            cursor: pointer;
            width: 85px;
        }
        .key-tag {
            background: rgba(0, 210, 255, 0.15);
            color: var(--accent);
            padding: 2px 7px;
            border-radius: 4px;
            font-family: monospace;
            font-size: 0.82rem;
        }
        .select-res {
            background: rgba(255, 255, 255, 0.08);
            color: var(--text-main);
            border: 1px solid var(--border);
            padding: 5px 8px;
            border-radius: 8px;
            font-size: 0.78rem;
            outline: none;
            cursor: pointer;
            transition: border-color 0.2s;
        }
        .select-res:focus, .select-res:hover {
            border-color: var(--accent);
        }
        .select-res option {
            background: #121a2b;
            color: #fff;
        }
        .terminal-drawer {
            display: none;
            flex-direction: column;
            width: 100%;
            max-width: 1200px;
            margin-top: 10px;
            background: rgba(8, 12, 20, 0.95);
            border: 1px solid var(--border);
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 8px 32px rgba(0,0,0,0.5);
        }
        .terminal-drawer.open { display: flex; }
        .terminal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: rgba(18, 26, 43, 0.9);
            padding: 8px 14px;
            border-bottom: 1px solid var(--border);
            font-size: 0.78rem;
            font-weight: 600;
        }
        .terminal-body {
            font-family: 'Consolas', 'Menlo', 'Courier New', monospace;
            font-size: 0.76rem;
            line-height: 1.45;
            padding: 10px 14px;
            height: 200px;
            overflow-y: auto;
            color: #cbd5e1;
            background: #04070c;
            white-space: pre-wrap;
            word-break: break-all;
        }
        .log-line { margin-bottom: 2px; }
        .log-I { color: #38bdf8; }
        .log-W { color: #f59e0b; }
        .log-E { color: #ef4444; font-weight: bold; }
        .log-D { color: #64748b; }

        /* Floating Draggable Performance HUD (Always Displayed) */
        .perf-hud {
            position: fixed;
            top: 70px;
            right: 20px;
            width: 310px;
            background: rgba(10, 16, 28, 0.88);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid rgba(0, 210, 255, 0.3);
            border-radius: 14px;
            box-shadow: 0 16px 40px rgba(0, 0, 0, 0.7), 0 0 18px rgba(0, 210, 255, 0.15);
            z-index: 950;
            overflow: hidden;
            user-select: none;
            transition: box-shadow 0.2s ease, opacity 0.2s ease;
        }
        .perf-hud.dragging {
            box-shadow: 0 22px 50px rgba(0, 0, 0, 0.9), 0 0 28px rgba(0, 210, 255, 0.45);
            border-color: var(--accent);
            opacity: 0.94;
        }
        .perf-hud-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 12px;
            background: rgba(18, 28, 48, 0.92);
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
            cursor: grab;
        }
        .perf-hud.dragging .perf-hud-header {
            cursor: grabbing;
        }
        .perf-hud-title {
            display: flex;
            align-items: center;
            gap: 7px;
            font-size: 0.76rem;
            font-weight: 700;
            color: var(--text-main);
            letter-spacing: 0.4px;
        }
        .drag-grip {
            color: var(--accent);
            font-size: 1.05rem;
            line-height: 1;
            opacity: 0.85;
        }
        .hud-pulse-dot {
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background: #10b981;
            box-shadow: 0 0 8px #10b981;
            animation: pulse-dot 1.5s infinite;
        }
        @keyframes pulse-dot {
            0% { transform: scale(0.9); opacity: 0.7; }
            50% { transform: scale(1.2); opacity: 1; box-shadow: 0 0 12px #10b981; }
            100% { transform: scale(0.9); opacity: 0.7; }
        }
        .hud-summary-tag {
            font-size: 0.68rem;
            padding: 2px 6px;
            border-radius: 10px;
            background: rgba(0, 210, 255, 0.15);
            color: var(--accent);
            font-weight: 600;
            font-family: monospace;
        }
        .perf-hud-tools {
            display: flex;
            align-items: center;
            gap: 4px;
        }
        .hud-btn {
            background: transparent;
            border: 1px solid rgba(255, 255, 255, 0.12);
            color: var(--text-dim);
            width: 22px;
            height: 22px;
            border-radius: 5px;
            font-size: 0.75rem;
            line-height: 1;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.15s;
        }
        .hud-btn:hover {
            color: #fff;
            border-color: var(--accent);
            background: rgba(0, 210, 255, 0.2);
        }
        .perf-hud-body {
            padding: 10px 12px;
        }
        .perf-hud.collapsed .perf-hud-body {
            display: none;
        }
        .perf-metric {
            margin-bottom: 9px;
        }
        .perf-label {
            display: flex;
            justify-content: space-between;
            font-size: 0.72rem;
            margin-bottom: 3px;
            color: var(--text-dim);
        }
        .perf-label b { color: var(--text-main); font-weight: 600; }
        .perf-bar-bg {
            background: rgba(255, 255, 255, 0.07);
            border-radius: 5px;
            height: 7px;
            overflow: hidden;
        }
        .perf-bar {
            height: 100%;
            border-radius: 5px;
            background: var(--accent-gradient);
            transition: width 0.3s ease;
        }
        .perf-chip-grid {
            margin-top: 8px;
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 5px;
        }
        .perf-chip {
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 3px 6px;
            font-size: 0.66rem;
            color: var(--text-dim);
            display: flex;
            justify-content: space-between;
        }
        .perf-chip b { color: var(--text-main); font-weight: 600; }

        /* Modals */
        .modal-overlay {
            position: fixed;
            inset: 0;
            background: rgba(5, 8, 14, 0.88);
            backdrop-filter: blur(14px);
            -webkit-backdrop-filter: blur(14px);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 1000;
            padding: 16px;
        }
        .modal-card {
            background: rgba(18, 26, 43, 0.95);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 24px;
            box-shadow: 0 16px 48px rgba(0, 0, 0, 0.6);
            width: 100%;
            max-width: 440px;
            position: relative;
        }
        .input-field {
            width: 100%;
            background: rgba(255, 255, 255, 0.06);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 10px 14px;
            color: #fff;
            font-size: 0.85rem;
            margin-bottom: 12px;
            outline: none;
            transition: border-color 0.2s;
        }
        .input-field:focus {
            border-color: var(--accent);
            box-shadow: 0 0 10px var(--accent-glow);
        }

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
        footer {
            text-align: center;
            padding: 8px;
            font-size: 0.70rem;
            color: var(--text-dim);
            border-top: 1px solid var(--border);
        }
    </style>
</head>
<body>
    <!-- Login Modal -->
    <div id="login-modal" class="modal-overlay" style="display:none;">
        <div class="modal-card">
            <span class="brand-chip" style="margin-bottom:12px;display:inline-block;">JC-ESP32P4 KVM</span>
            <h2 style="font-size:1.2rem;margin-bottom:6px;">&#x1F512; System Authentication</h2>
            <p style="color:var(--text-dim);font-size:0.8rem;margin-bottom:16px;">Sign in with administrator credentials to access the live video and controls.</p>
            <div id="login-err" style="display:none;color:var(--danger);font-size:0.8rem;margin-bottom:10px;"></div>
            <input type="text" id="login-user" placeholder="Username (default: admin)" class="input-field" value="admin" />
            <input type="password" id="login-pass" placeholder="Password (default: admin)" class="input-field" value="admin" />
            <button class="btn btn-primary" style="width:100%;padding:10px;margin-top:6px;" onclick="doLogin()">Sign In</button>
            <p style="font-size:0.7rem;color:var(--text-dim);margin-top:12px;text-align:center;">Hardware-level remote KVM</p>
        </div>
    </div>

    <!-- Change Password Modal -->
    <div id="pwd-modal" class="modal-overlay" style="display:none;">
        <div class="modal-card">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
                <h3 style="font-size:1.1rem;">&#x1F511; Change Admin Password</h3>
                <button class="btn" style="padding:2px 8px;font-size:0.8rem;" onclick="closeModal('pwd-modal')">&times;</button>
            </div>
            <div id="pwd-err" style="display:none;color:var(--danger);font-size:0.8rem;margin-bottom:10px;"></div>
            <input type="password" id="pwd-old" placeholder="Current Password" class="input-field" />
            <input type="password" id="pwd-new" placeholder="New Password (min 4 chars)" class="input-field" />
            <input type="password" id="pwd-confirm" placeholder="Confirm New Password" class="input-field" />
            <div style="display:flex;gap:10px;margin-top:10px;">
                <button class="btn btn-primary" style="flex:1;padding:9px;" onclick="submitChangePassword()">Save Password</button>
                <button class="btn" style="flex:1;padding:9px;" onclick="closeModal('pwd-modal')">Cancel</button>
            </div>
        </div>
    </div>
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

    <!-- Floating Draggable Performance HUD (Always Displayed) -->
    <div id="perf-hud" class="perf-hud">
        <div class="perf-hud-header" id="perf-hud-header">
            <div class="perf-hud-title">
                <span class="drag-grip" title="Drag to move HUD">⠿</span>
                <span class="hud-pulse-dot"></span>
                <span>PERFORMANCE</span>
                <span class="hud-summary-tag" id="hud-summary-tag">0.0 Mbps</span>
            </div>
            <div class="perf-hud-tools">
                <button class="hud-btn" id="btn-perf-min" onclick="togglePerfCollapse()" title="Minimize / Expand">_</button>
                <button class="hud-btn" id="btn-perf-close" onclick="togglePerfVisibility()" title="Toggle HUD Display">&times;</button>
            </div>
        </div>
        <div class="perf-hud-body" id="perf-hud-body">
            <div class="perf-metric">
                <div class="perf-label">
                    <span>Core 0 (Network &amp; KVM):</span>
                    <b id="perf-cpu0">0.0%</b>
                </div>
                <div class="perf-bar-bg"><div class="perf-bar" id="bar-cpu0" style="width:0%;"></div></div>
            </div>
            <div class="perf-metric">
                <div class="perf-label">
                    <span>Core 1 (UVC Stream):</span>
                    <b id="perf-cpu1">0.0%</b>
                </div>
                <div class="perf-bar-bg"><div class="perf-bar" id="bar-cpu1" style="width:0%;background:linear-gradient(90deg,#00d2ff,#a855f7);"></div></div>
            </div>
            <div class="perf-metric">
                <div class="perf-label">
                    <span>Network TX:</span>
                    <b id="perf-net" style="color:var(--accent);">0.00 Mbps (0 KB/s)</b>
                </div>
            </div>
            <div class="perf-metric">
                <div class="perf-label">
                    <span>Hex-PSRAM (32 MB @ 200MHz):</span>
                    <b id="perf-psram">0 / 32 MB (0%)</b>
                </div>
                <div class="perf-bar-bg"><div class="perf-bar" id="bar-psram" style="width:0%;background:linear-gradient(90deg,#10b981,#00d2ff);"></div></div>
            </div>
            <div class="perf-metric">
                <div class="perf-label">
                    <span>Internal SRAM (Heap):</span>
                    <b id="perf-sram">0 / 512 KB (0%)</b>
                </div>
                <div class="perf-bar-bg"><div class="perf-bar" id="bar-sram" style="width:0%;background:linear-gradient(90deg,#3a7bd5,#f59e0b);"></div></div>
                <div style="font-size:0.68rem;color:var(--text-dim);margin-top:3px;display:flex;justify-content:space-between;">
                    <span>Free: <b id="perf-sram-free" style="color:var(--text-main);">---</b></span>
                    <span>Min: <b id="perf-sram-min" style="color:var(--text-main);">---</b></span>
                </div>
            </div>
            <div class="perf-chip-grid">
                <div class="perf-chip"><span>Part:</span> <b id="perf-part">---</b></div>
                <div class="perf-chip"><span>Video:</span> <b id="perf-vid">---</b></div>
                <div class="perf-chip"><span>USB HID:</span> <b id="perf-hid">---</b></div>
                <div class="perf-chip"><span>Build:</span> <b id="perf-ver">---</b></div>
            </div>
        </div>
    </div>
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
                <button class="vk-key vk-w-12" onclick="onVkKey(0x31)">\ |</button>
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
                <button class="vk-key" onclick="onVkKey(0x34)">' "</button>
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


    <header>
        <div class="brand-box">
            <span class="brand-chip">JC-ESP32P4</span>
            <div class="brand-title">
                <h1>HDMI KVM OVER ETHERNET</h1>
                <p>Hardware IP101 RMII &bull; USB 2.0 High-Speed UVC Host</p>
            </div>
        </div>
        <div class="telemetry-cluster">
            <div class="stat-pill"><span id="led-signal" class="led-dot"></span><span id="val-status">Connecting...</span></div>
            <div class="stat-pill"><span id="led-hid" class="led-dot offline"></span><span>USB HID:</span> <b id="val-hid">Waiting</b></div>
            <div class="stat-pill"><span>FPS:</span> <b id="val-fps">0.0</b></div>
            <div class="stat-pill"><span>Res:</span> <b id="val-res">---</b></div>
            <div class="stat-pill"><span>IP:</span> <b id="val-ip">---</b></div>
            <div class="stat-pill"><span>Uptime:</span> <b id="val-uptime">00:00:00</b></div>
            <button class="btn active" id="btn-perf-toggle" style="padding:4px 9px;font-size:0.75rem;" onclick="togglePerfVisibility()">&#x1F4CA; HUD</button>
            <button class="btn" id="btn-vk-toggle" style="padding:4px 9px;font-size:0.75rem;" onclick="toggleVirtualKeyboard()">&#x2328; Keyboard</button>
            <button class="btn" id="btn-settings-toggle" style="padding:4px 9px;font-size:0.75rem;" onclick="openSettingsModal()">&#x2699; Settings</button>
            <button class="btn" style="padding:4px 9px;font-size:0.75rem;" onclick="openModal('pwd-modal')">&#x1F511; Password</button>
            <button class="btn btn-danger" style="padding:4px 9px;font-size:0.75rem;" onclick="doLogout()">&#x1F6AA; Logout</button>
        </div>
    </header>

    <main>
        <div class="screen-wrapper ratio-fit" id="screen-box">
            <img id="stream-view" src="/stream" alt="Live Video Feed" />
            <div class="reconnect-overlay" id="reconnect-card">
                <div class="spinner"></div>
                <h3 id="overlay-title">HDMI Capture Disconnected</h3>
                <p id="overlay-desc">Waiting for USB-to-HDMI capture dongle. Auto-reconnecting in background...</p>
                <button class="btn" onclick="forceUsbReconnect()">&#x21BB; Force USB Reconnect Now</button>
            </div>
        </div>

        <!-- Controls Dock -->
        <div class="control-dock">
            <div style="display:inline-flex;align-items:center;gap:6px;">
                <span style="font-size:0.75rem;color:var(--text-dim);">&#x1F4FA; Res:</span>
                <select class="select-res" id="select-res" onchange="changeResolution(this.value)">
                    <option value="1920x1080@30">1080p 30fps</option>
                    <option value="1280x720@30">720p 30fps</option>
                    <option value="1280x720@60">720p 60fps</option>
                    <option value="1024x768@30">1024x768 30fps</option>
                    <option value="800x600@30">800x600 30fps</option>
                    <option value="640x480@30">480p 30fps</option>
                </select>
            </div>
            <button class="btn" id="btn-full" onclick="toggleFullscreen()">&#x26F6; Fullscreen</button>
            <button class="btn" id="btn-snap" onclick="downloadSnapshot()">&#x1F4F7; Snapshot</button>
            <button class="btn" id="btn-pause" onclick="togglePause()">&#x23F8; Pause</button>
            <button class="btn" id="btn-reload" onclick="reloadStreamFeed()">&#x21BB; Reload Feed</button>
            <button class="btn btn-danger" id="btn-reconnect" onclick="forceUsbReconnect()">&#x26A1; Reconnect USB</button>
            <button class="btn" id="btn-filters" onclick="toggleDrawer('filters-drawer')">&#x1F3A8; Picture Settings</button>
            <button class="btn" id="btn-kvm" onclick="toggleKvmMode()">&#x2328; KVM Mode</button>
            <button class="btn" id="btn-vk-dock" onclick="toggleVirtualKeyboard()">&#x2328; Virtual Keyboard</button>
            <button class="btn" id="btn-ota" onclick="toggleDrawer('ota-drawer')">&#x1F4E5; OTA Firmware</button>
            <button class="btn" id="btn-logs" onclick="toggleDrawer('terminal-drawer')">&#x1F4DF; Live Logs</button>
        </div>

        <!-- Picture Adjustments Drawer -->
        <div class="drawer" id="filters-drawer">
            <div class="drawer-item">
                <span>Brightness:</span>
                <input type="range" id="slide-bright" min="50" max="150" value="100" oninput="applyImageFilters()">
            </div>
            <div class="drawer-item">
                <span>Contrast:</span>
                <input type="range" id="slide-contrast" min="50" max="150" value="100" oninput="applyImageFilters()">
            </div>
            <div class="drawer-item">
                <span>Saturation:</span>
                <input type="range" id="slide-saturate" min="0" max="200" value="100" oninput="applyImageFilters()">
            </div>
            <button class="btn" onclick="resetImageFilters()">Reset Defaults</button>
        </div>

        <!-- KVM Shortcuts & Capture Drawer -->
        <div class="drawer" id="kvm-drawer">
            <span style="font-weight:600;color:var(--accent);">&#x2328; KVM Controls:</span>
            <button class="btn" id="btn-lock-pointer" onclick="requestScreenPointerLock()">&#x1F5B1; Capture Mouse</button>
            <span id="kvm-hint" style="color:var(--text-dim);font-size:0.75rem;">(Click video to capture mouse &amp; keyboard; press ESC to release)</span>
            <div style="display:inline-flex;gap:6px;align-items:center;">
                <span style="font-size:0.75rem;color:var(--text-dim);">Macros:</span>
                <button class="btn" onclick="sendMacro('CAD')">Ctrl + Alt + Del</button>
                <button class="btn" onclick="sendMacro('ALT_TAB')">Alt + Tab</button>
                <button class="btn" onclick="sendMacro('WIN')">&#x229E; Win</button>
                <button class="btn" onclick="sendMacro('ESC')">Esc</button>
                <button class="btn" onclick="sendMacro('PRINT')">PrtScn</button>
                <button class="btn btn-danger" onclick="sendReleaseAll()">&#x21BA; Release All Keys</button>
            </div>
            <span style="margin-left:auto;font-size:0.75rem;">Last Key: <span class="key-tag" id="key-indicator">None</span></span>
        </div>

        <!-- OTA Firmware Drawer -->
        <div class="drawer" id="ota-drawer" style="flex-direction:column;align-items:stretch;gap:10px;">
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <b>&#x1F4E5; Firmware OTA Update via Network</b>
                <span style="font-size:0.75rem;color:var(--text-dim);">Upload build/esp32p4_hdmi_kvm.bin (Up to 7.5MB)</span>
            </div>
            <div style="display:flex;gap:10px;align-items:center;">
                <input type="file" id="ota-file" accept=".bin" style="font-size:0.8rem;color:var(--text-main);flex:1;">
                <button class="btn btn-primary" onclick="uploadOtaFirmware()">&#x26A1; Flash &amp; Reboot</button>
            </div>
            <div id="ota-progress-box" style="display:none;background:rgba(255,255,255,0.06);border-radius:6px;overflow:hidden;height:12px;">
                <div id="ota-progress-bar" style="background:var(--accent-gradient);width:0%;height:100%;transition:width 0.2s;"></div>
            </div>
            <div id="ota-status-msg" style="font-size:0.75rem;color:var(--accent);"></div>
        </div>

        <!-- Live Terminal Logs Drawer -->
        <div class="terminal-drawer" id="terminal-drawer">
            <div class="terminal-header">
                <span>&#x1F4DF; ESP32-P4 Real-Time System Log Stream <span id="log-count" style="color:var(--text-dim);font-weight:normal;">(0 lines)</span></span>
                <div style="display:flex;gap:8px;">
                    <button class="btn" style="padding:2px 8px;font-size:0.75rem;" onclick="clearLogs()">Clear</button>
                    <button class="btn" style="padding:2px 8px;font-size:0.75rem;" onclick="toggleDrawer('terminal-drawer')">&times;</button>
                </div>
            </div>
            <div class="terminal-body" id="log-terminal"></div>
        </div>
    </main>

    <footer>
        Guition JC-ESP32P4-M3-DEV &bull; Dual-Core RISC-V @ 400 MHz &bull; 32MB Hex-PSRAM &bull; Zero-Copy Hardware Pipeline
    </footer>

    <script>
        const streamView = document.getElementById('stream-view');
        const screenBox = document.getElementById('screen-box');
        const reconnectCard = document.getElementById('reconnect-card');
        const ledSignal = document.getElementById('led-signal');
        const ledHid = document.getElementById('led-hid');
        const valStatus = document.getElementById('val-status');
        const valHid = document.getElementById('val-hid');
        const valFps = document.getElementById('val-fps');
        const valRes = document.getElementById('val-res');
        const valIp = document.getElementById('val-ip');
        const valUptime = document.getElementById('val-uptime');
        const selectRes = document.getElementById('select-res');
        const logTerminal = document.getElementById('log-terminal');
        const logCount = document.getElementById('log-count');
        const keyIndicator = document.getElementById('key-indicator');

        let ws = null;
        let wsReconnectTimer = null;
        let isPaused = false;
        let kvmActive = false;
        let totalLogLines = 0;

        /* Multi-Tab Arbitration: Only focused tab runs stream */
        const tabChannel = ('BroadcastChannel' in window) ? new BroadcastChannel('esp32p4_kvm_tab') : null;
        const currentTabId = Math.random().toString(36).substring(2);
        let isTabActive = true;

        if (tabChannel) {
            tabChannel.postMessage({ type: 'claim', tabId: currentTabId });
            tabChannel.onmessage = (e) => {
                if (e.data && e.data.type === 'claim' && e.data.tabId !== currentTabId) {
                    isTabActive = false;
                    if (streamView) streamView.src = '';
                    if (valStatus) valStatus.textContent = 'Standby (Other tab)';
                    if (ledSignal) ledSignal.className = 'led-dot offline';
                }
            };
        }

        window.addEventListener('focus', () => {
            if (!isTabActive) {
                isTabActive = true;
                if (tabChannel) tabChannel.postMessage({ type: 'claim', tabId: currentTabId });
                reloadStreamFeed();
                initWebSocket();
            }
        });

        /* Modals & Authentication */
        function openModal(id) {
            const m = document.getElementById(id);
            if (m) m.style.display = 'flex';
        }

        function closeModal(id) {
            const m = document.getElementById(id);
            if (m) m.style.display = 'none';
        }

        function checkAuth() {
            const token = localStorage.getItem('kvm_token');
            if (!token) {
                openModal('login-modal');
                if (streamView) streamView.src = '';
            } else {
                closeModal('login-modal');
                initWebSocket();
                if (streamView && (!streamView.src || streamView.src.endsWith('/stream') === false)) {
                    streamView.src = '/stream';
                }
            }
        }

        function doLogin() {
            const u = document.getElementById('login-user').value.trim();
            const p = document.getElementById('login-pass').value.trim();
            const errDiv = document.getElementById('login-err');
            errDiv.style.display = 'none';
            fetch('/api/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username: u, password: p })
            })
            .then(r => r.json())
            .then(data => {
                if (data.status === 'ok') {
                    localStorage.setItem('kvm_token', data.token);
                    localStorage.setItem('kvm_user', data.username);
                    closeModal('login-modal');
                    initWebSocket();
                    if (streamView) streamView.src = '/stream';
                } else {
                    errDiv.textContent = data.message || 'Invalid username or password';
                    errDiv.style.display = 'block';
                }
            })
            .catch(err => {
                errDiv.textContent = 'Network communication error';
                errDiv.style.display = 'block';
            });
        }

        function doLogout() {
            localStorage.removeItem('kvm_token');
            if (ws) { ws.close(); ws = null; }
            if (streamView) streamView.src = '';
            openModal('login-modal');
        }

        function submitChangePassword() {
            const oldP = document.getElementById('pwd-old').value;
            const newP = document.getElementById('pwd-new').value;
            const confP = document.getElementById('pwd-confirm').value;
            const errDiv = document.getElementById('pwd-err');
            errDiv.style.display = 'none';

            if (newP !== confP) {
                errDiv.textContent = 'New passwords do not match';
                errDiv.style.display = 'block';
                return;
            }
            if (newP.length < 4) {
                errDiv.textContent = 'New password must be at least 4 characters';
                errDiv.style.display = 'block';
                return;
            }

            fetch('/api/change_password', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ old_password: oldP, new_password: newP })
            })
            .then(r => r.json())
            .then(data => {
                if (data.status === 'ok') {
                    alert('Password changed successfully! Please log in again.');
                    closeModal('pwd-modal');
                    doLogout();
                } else {
                    errDiv.textContent = data.message || 'Error changing password';
                    errDiv.style.display = 'block';
                }
            })
            .catch(err => {
                errDiv.textContent = 'Network error while updating password';
                errDiv.style.display = 'block';
            });
        }

        function formatUptime(seconds) {
            const h = Math.floor(seconds / 3600).toString().padStart(2, '0');
            const m = Math.floor((seconds % 3600) / 60).toString().padStart(2, '0');
            const s = Math.floor(seconds % 60).toString().padStart(2, '0');
            return `${h}:${m}:${s}`;
        }

        function handleTelemetry(data) {
            valIp.textContent = data.ip || '---';
            valRes.textContent = data.res || '---';
            valFps.textContent = (data.fps || 0.0).toFixed(1);
            valUptime.textContent = formatUptime(data.uptime || 0);

            if (data.hid_mounted) {
                if (ledHid) ledHid.className = 'led-dot online';
                if (valHid) valHid.textContent = 'Ready';
            } else {
                if (ledHid) ledHid.className = 'led-dot offline';
                if (valHid) valHid.textContent = 'Unplugged';
            }

            // Update Live Performance Floating HUD
            if (data.cpu0 !== undefined) {
                const el = document.getElementById('perf-cpu0');
                if (el) el.textContent = data.cpu0.toFixed(1) + '%';
                const bar = document.getElementById('bar-cpu0');
                if (bar) bar.style.width = Math.min(100, Math.max(0, data.cpu0)) + '%';
            }
            if (data.cpu1 !== undefined) {
                const el = document.getElementById('perf-cpu1');
                if (el) el.textContent = data.cpu1.toFixed(1) + '%';
                const bar = document.getElementById('bar-cpu1');
                if (bar) bar.style.width = Math.min(100, Math.max(0, data.cpu1)) + '%';
            }
            if (data.net_mbps !== undefined) {
                const el = document.getElementById('perf-net');
                if (el) el.textContent = `${data.net_mbps.toFixed(2)} Mbps (${data.net_kbps.toFixed(0)} KB/s)`;
                const sumTag = document.getElementById('hud-summary-tag');
                if (sumTag) sumTag.textContent = `${data.net_mbps.toFixed(1)} Mbps`;
            }
            if (data.psram_total_kb !== undefined) {
                const usedMb = (data.psram_used_kb / 1024).toFixed(1);
                const totMb = (data.psram_total_kb / 1024).toFixed(1);
                const el = document.getElementById('perf-psram');
                if (el) el.textContent = `${usedMb} / ${totMb} MB (${data.psram_used_pct.toFixed(1)}%)`;
                const bar = document.getElementById('bar-psram');
                if (bar) bar.style.width = data.psram_used_pct.toFixed(1) + '%';
            }
            if (data.sram_total_kb !== undefined) {
                const el = document.getElementById('perf-sram');
                if (el) el.textContent = `${data.sram_total_kb - data.sram_free_kb} / ${data.sram_total_kb} KB (${data.sram_used_pct.toFixed(1)}%)`;
                const bar = document.getElementById('bar-sram');
                if (bar) bar.style.width = data.sram_used_pct.toFixed(1) + '%';
                const freeEl = document.getElementById('perf-sram-free');
                if (freeEl) freeEl.textContent = data.sram_free_kb + ' KB';
                const minEl = document.getElementById('perf-sram-min');
                if (minEl) minEl.textContent = data.sram_min_free_kb + ' KB';
            }
            const partEl = document.getElementById('perf-part');
            if (partEl && data.partition) partEl.textContent = data.partition;
            const verEl = document.getElementById('perf-ver');
            if (verEl && data.version) verEl.textContent = data.version;
            const vidEl = document.getElementById('perf-vid');
            if (vidEl) vidEl.textContent = `${data.res} @ ${(data.fps || 0).toFixed(1)} FPS`;
            const hidEl = document.getElementById('perf-hid');
            if (hidEl) hidEl.textContent = data.hid_mounted ? 'Ready' : 'Unplugged';

            if (selectRes && document.activeElement !== selectRes && data.res) {
                for (let i = 0; i < selectRes.options.length; i++) {
                    if (selectRes.options[i].value.startsWith(data.res)) {
                        selectRes.selectedIndex = i;
                        break;
                    }
                }
            }
        }

        function appendLog(line) {
            if (!logTerminal) return;
            const div = document.createElement('div');
            div.className = 'log-line';
            if (line.includes(' E ')) div.className += ' log-E';
            else if (line.includes(' W ')) div.className += ' log-W';
            else if (line.includes(' I ')) div.className += ' log-I';
            else if (line.includes(' D ')) div.className += ' log-D';
            div.textContent = line;
            logTerminal.appendChild(div);

            totalLogLines++;
            if (logCount) logCount.textContent = `(${totalLogLines} lines)`;
            if (logTerminal.children.length > 500) {
                logTerminal.removeChild(logTerminal.firstChild);
            }
            logTerminal.scrollTop = logTerminal.scrollHeight;
        }

        function clearLogs() {
            if (logTerminal) logTerminal.innerHTML = '';
            totalLogLines = 0;
            if (logCount) logCount.textContent = '(0 lines)';
        }

        /* WebSocket Connection with Single-Instance Guarantee */
        function initWebSocket() {
            if (!isTabActive) return;
            if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
                return;
            }
            if (wsReconnectTimer) {
                clearTimeout(wsReconnectTimer);
                wsReconnectTimer = null;
            }
            const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${location.host}/ws`;

            try {
                ws = new WebSocket(wsUrl);
            } catch (e) {
                scheduleWsReconnect();
                return;
            }

            ws.onopen = function() {
                console.log('WebSocket connected to ESP32-P4');
                if (ledSignal) ledSignal.className = 'led-dot online';
                if (valStatus) valStatus.textContent = 'Connected';
            };

            ws.onmessage = function(event) {
                try {
                    const msg = JSON.parse(event.data);
                    if (msg.type === 'telemetry') {
                        handleTelemetry(msg);
                    } else if (msg.type === 'log') {
                        appendLog(msg.msg);
                    }
                } catch (e) {}
            };

            ws.onclose = function() {
                if (ledSignal) ledSignal.className = 'led-dot offline';
                if (valStatus) valStatus.textContent = 'Disconnected';
                scheduleWsReconnect();
            };

            ws.onerror = function() {
                if (ledSignal) ledSignal.className = 'led-dot offline';
                if (valStatus) valStatus.textContent = 'Error';
                scheduleWsReconnect();
            };
        }

        function scheduleWsReconnect() {
            if (wsReconnectTimer) clearTimeout(wsReconnectTimer);
            wsReconnectTimer = setTimeout(initWebSocket, 2000);
        }

        function sendWs(obj) {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify(obj));
            }
        }

        function reloadStreamFeed() {
            if (isPaused || !isTabActive) return;
            streamView.src = '';
            setTimeout(() => {
                streamView.src = '/stream?t=' + Date.now();
            }, 100);
        }

        function forceUsbReconnect() {
            fetch('/api/reconnect_usb', { method: 'POST' })
                .then(r => r.json())
                .then(data => {
                    console.log('USB Reconnect requested:', data);
                    valStatus.textContent = 'Reconnecting...';
                    reconnectCard.classList.add('show');
                    setTimeout(reloadStreamFeed, 1200);
                })
                .catch(err => console.error('Failed to trigger USB reconnect:', err));
        }

        function changeResolution(val) {
            const parts = val.split('@');
            const dims = parts[0].split('x');
            const w = parseInt(dims[0], 10);
            const h = parseInt(dims[1], 10);
            const fps = parseInt(parts[1] || '30', 10);

            fetch('/api/resolution', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ width: w, height: h, fps: fps })
            })
            .then(r => r.json())
            .then(data => {
                console.log('Resolution set to:', data);
                reloadStreamFeed();
            })
            .catch(err => console.error('Resolution change error:', err));
        }

        function toggleFullscreen() {
            if (!document.fullscreenElement) {
                if (screenBox.requestFullscreen) screenBox.requestFullscreen();
            } else {
                if (document.exitFullscreen) document.exitFullscreen();
            }
        }

        function togglePause() {
            isPaused = !isPaused;
            const btn = document.getElementById('btn-pause');
            if (isPaused) {
                streamView.src = '';
                btn.textContent = '▶ Resume';
                btn.classList.add('active');
            } else {
                btn.textContent = '⏸ Pause';
                btn.classList.remove('active');
                reloadStreamFeed();
            }
        }

        function downloadSnapshot() {
            const a = document.createElement('a');
            a.href = '/snapshot?t=' + Date.now();
            a.download = `esp32p4_kvm_${Date.now()}.jpg`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        }

        function toggleDrawer(id) {
            const d = document.getElementById(id);
            if (!d) return;
            const wasOpen = d.classList.contains('open');
            document.querySelectorAll('.drawer, .terminal-drawer').forEach(el => {
                if (el.id !== 'kvm-drawer' || id === 'kvm-drawer') el.classList.remove('open');
            });
            if (!wasOpen) d.classList.add('open');
        }

        function applyImageFilters() {
            const b = document.getElementById('slide-bright').value;
            const c = document.getElementById('slide-contrast').value;
            const s = document.getElementById('slide-saturate').value;
            streamView.style.filter = `brightness(${b}%) contrast(${c}%) saturate(${s}%)`;
        }

        function resetImageFilters() {
            document.getElementById('slide-bright').value = 100;
            document.getElementById('slide-contrast').value = 100;
            document.getElementById('slide-saturate').value = 100;
            streamView.style.filter = 'none';
        }

        /* Draggable Performance HUD Engine */
        const perfHud = document.getElementById('perf-hud');
        const perfHudHeader = document.getElementById('perf-hud-header');
        let isDraggingHud = false;
        let hudStartX = 0, hudStartY = 0;
        let hudInitLeft = 0, hudInitTop = 0;

        function loadPerfHudState() {
            const savedX = localStorage.getItem('perf_hud_x');
            const savedY = localStorage.getItem('perf_hud_y');
            const isCollapsed = localStorage.getItem('perf_hud_collapsed') === 'true';
            const isHidden = localStorage.getItem('perf_hud_hidden') === 'true';

            if (isHidden) {
                perfHud.style.display = 'none';
                const navBtn = document.getElementById('btn-perf-toggle');
                if (navBtn) navBtn.classList.remove('active');
            } else {
                perfHud.style.display = 'block';
                const navBtn = document.getElementById('btn-perf-toggle');
                if (navBtn) navBtn.classList.add('active');
            }

            if (isCollapsed) {
                perfHud.classList.add('collapsed');
                const btn = document.getElementById('btn-perf-min');
                if (btn) btn.textContent = '+';
            }

            if (savedX !== null && savedY !== null) {
                const maxX = Math.max(10, window.innerWidth - 60);
                const maxY = Math.max(10, window.innerHeight - 40);
                const x = Math.min(Math.max(10, parseInt(savedX, 10)), maxX);
                const y = Math.min(Math.max(10, parseInt(savedY, 10)), maxY);
                perfHud.style.left = x + 'px';
                perfHud.style.top = y + 'px';
                perfHud.style.right = 'auto';
            }
        }

        function togglePerfCollapse() {
            perfHud.classList.toggle('collapsed');
            const collapsed = perfHud.classList.contains('collapsed');
            localStorage.setItem('perf_hud_collapsed', collapsed ? 'true' : 'false');
            const btn = document.getElementById('btn-perf-min');
            if (btn) btn.textContent = collapsed ? '+' : '_';
        }

        function togglePerfVisibility() {
            if (perfHud.style.display === 'none') {
                perfHud.style.display = 'block';
                localStorage.setItem('perf_hud_hidden', 'false');
            } else {
                perfHud.style.display = 'none';
                localStorage.setItem('perf_hud_hidden', 'true');
            }
            const navBtn = document.getElementById('btn-perf-toggle');
            if (navBtn) navBtn.classList.toggle('active', perfHud.style.display !== 'none');
        }

        function onHudStart(clientX, clientY, target) {
            if (target && target.closest('.hud-btn')) return;
            isDraggingHud = true;
            hudStartX = clientX;
            hudStartY = clientY;
            const rect = perfHud.getBoundingClientRect();
            hudInitLeft = rect.left;
            hudInitTop = rect.top;
            perfHud.style.right = 'auto';
            perfHud.style.left = hudInitLeft + 'px';
            perfHud.style.top = hudInitTop + 'px';
            perfHud.classList.add('dragging');
        }

        function onHudMove(clientX, clientY) {
            if (!isDraggingHud) return;
            const dx = clientX - hudStartX;
            const dy = clientY - hudStartY;
            let newX = hudInitLeft + dx;
            let newY = hudInitTop + dy;
            const maxW = window.innerWidth - perfHud.offsetWidth - 10;
            const maxH = window.innerHeight - perfHud.offsetHeight - 10;
            newX = Math.max(10, Math.min(maxW, newX));
            newY = Math.max(10, Math.min(maxH, newY));
            perfHud.style.left = newX + 'px';
            perfHud.style.top = newY + 'px';
        }

        function onHudEnd() {
            if (isDraggingHud) {
                isDraggingHud = false;
                perfHud.classList.remove('dragging');
                localStorage.setItem('perf_hud_x', parseInt(perfHud.style.left, 10));
                localStorage.setItem('perf_hud_y', parseInt(perfHud.style.top, 10));
            }
        }

        if (perfHudHeader) {
            perfHudHeader.addEventListener('mousedown', (e) => {
                onHudStart(e.clientX, e.clientY, e.target);
                e.preventDefault();
            });
            perfHudHeader.addEventListener('touchstart', (e) => {
                if (e.touches.length > 0) {
                    onHudStart(e.touches[0].clientX, e.touches[0].clientY, e.target);
                }
            }, { passive: true });
        }

        window.addEventListener('mousemove', (e) => onHudMove(e.clientX, e.clientY));
        window.addEventListener('touchmove', (e) => {
            if (isDraggingHud && e.touches.length > 0) {
                onHudMove(e.touches[0].clientX, e.touches[0].clientY);
            }
        }, { passive: true });
        window.addEventListener('mouseup', onHudEnd);
        window.addEventListener('touchend', onHudEnd);

        /* KVM Mouse & Pointer Lock */
        function isPointerLocked() {
            return document.pointerLockElement === screenBox;
        }

        function requestScreenPointerLock() {
            if (screenBox.requestPointerLock) {
                screenBox.requestPointerLock();
            }
        }

        screenBox.addEventListener('click', (e) => {
            if (!kvmActive) {
                toggleKvmMode();
            }
            if (!isPointerLocked()) {
                requestScreenPointerLock();
            }
        });

        window.addEventListener('contextmenu', (e) => {
            if (kvmActive && isPointerLocked()) {
                e.preventDefault();
            }
        });

        document.addEventListener('pointerlockchange', () => {
            const locked = isPointerLocked();
            screenBox.classList.toggle('pointer-locked', locked);
            const btnLock = document.getElementById('btn-lock-pointer');
            if (btnLock) btnLock.classList.toggle('active', locked);
            if (!locked && kvmActive) {
                sendReleaseAll();
            }
        });

        let mouseAccumDx = 0;
        let mouseAccumDy = 0;
        let mouseButtons = 0;
        let mouseRafPending = false;

        function flushMouseMove() {
            mouseRafPending = false;
            if (mouseAccumDx !== 0 || mouseAccumDy !== 0) {
                sendWs({
                    type: 'mouse',
                    btn: mouseButtons,
                    dx: Math.max(-127, Math.min(127, mouseAccumDx)),
                    dy: Math.max(-127, Math.min(127, mouseAccumDy)),
                    wheel: 0
                });
                mouseAccumDx = 0;
                mouseAccumDy = 0;
            }
        }

        window.addEventListener('mousemove', (e) => {
            if (!kvmActive || !isPointerLocked()) return;
            mouseAccumDx += e.movementX;
            mouseAccumDy += e.movementY;
            if (!mouseRafPending) {
                mouseRafPending = true;
                requestAnimationFrame(flushMouseMove);
            }
        });

        window.addEventListener('mousedown', (e) => {
            if (!kvmActive || !isPointerLocked()) return;
            if (e.button === 0) mouseButtons |= 0x01;
            else if (e.button === 1) mouseButtons |= 0x04;
            else if (e.button === 2) mouseButtons |= 0x02;
            sendWs({ type: 'mouse', btn: mouseButtons, dx: 0, dy: 0, wheel: 0 });
            e.preventDefault();
        });

        window.addEventListener('mouseup', (e) => {
            if (!kvmActive || !isPointerLocked()) return;
            if (e.button === 0) mouseButtons &= ~0x01;
            else if (e.button === 1) mouseButtons &= ~0x04;
            else if (e.button === 2) mouseButtons &= ~0x02;
            sendWs({ type: 'mouse', btn: mouseButtons, dx: 0, dy: 0, wheel: 0 });
            e.preventDefault();
        });

        window.addEventListener('wheel', (e) => {
            if (!kvmActive || !isPointerLocked()) return;
            const w = e.deltaY < 0 ? 1 : (e.deltaY > 0 ? -1 : 0);
            sendWs({ type: 'mouse', btn: mouseButtons, dx: 0, dy: 0, wheel: w });
            e.preventDefault();
        }, { passive: false });

        /* KVM Keyboard HID mapping */
        const KEY_MAP = {
            'KeyA': 0x04, 'KeyB': 0x05, 'KeyC': 0x06, 'KeyD': 0x07, 'KeyE': 0x08,
            'KeyF': 0x09, 'KeyG': 0x0A, 'KeyH': 0x0B, 'KeyI': 0x0C, 'KeyJ': 0x0D,
            'KeyK': 0x0E, 'KeyL': 0x0F, 'KeyM': 0x10, 'KeyN': 0x11, 'KeyO': 0x12,
            'KeyP': 0x13, 'KeyQ': 0x14, 'KeyR': 0x15, 'KeyS': 0x16, 'KeyT': 0x17,
            'KeyU': 0x18, 'KeyV': 0x19, 'KeyW': 0x1A, 'KeyX': 0x1B, 'KeyY': 0x1C, 'KeyZ': 0x1D,
            'Digit1': 0x1E, 'Digit2': 0x1F, 'Digit3': 0x20, 'Digit4': 0x21, 'Digit5': 0x22,
            'Digit6': 0x23, 'Digit7': 0x24, 'Digit8': 0x25, 'Digit9': 0x26, 'Digit0': 0x27,
            'Enter': 0x28, 'Escape': 0x29, 'Backspace': 0x2A, 'Tab': 0x2B, 'Space': 0x2C,
            'Minus': 0x2D, 'Equal': 0x2E, 'BracketLeft': 0x2F, 'BracketRight': 0x30,
            'Backslash': 0x31, 'Semicolon': 0x33, 'Quote': 0x34, 'Backquote': 0x35,
            'Comma': 0x36, 'Period': 0x37, 'Slash': 0x38, 'CapsLock': 0x39,
            'F1': 0x3A, 'F2': 0x3B, 'F3': 0x3C, 'F4': 0x3D, 'F5': 0x3E, 'F6': 0x3F,
            'F7': 0x40, 'F8': 0x41, 'F9': 0x42, 'F10': 0x43, 'F11': 0x44, 'F12': 0x45,
            'PrintScreen': 0x46, 'ScrollLock': 0x47, 'Pause': 0x48, 'Insert': 0x49,
            'Home': 0x4A, 'PageUp': 0x4B, 'Delete': 0x4C, 'End': 0x4D, 'PageDown': 0x4E,
            'ArrowRight': 0x4F, 'ArrowLeft': 0x50, 'ArrowDown': 0x51, 'ArrowUp': 0x52,
            'NumLock': 0x53, 'NumpadDivide': 0x54, 'NumpadMultiply': 0x55, 'NumpadSubtract': 0x56,
            'NumpadAdd': 0x57, 'Numpad1': 0x59, 'Numpad2': 0x5A, 'Numpad3': 0x5B, 'Numpad4': 0x5C,
            'Numpad5': 0x5D, 'Numpad6': 0x5E, 'Numpad7': 0x5F, 'Numpad8': 0x60,
            'Numpad9': 0x61, 'Numpad0': 0x62, 'NumpadDecimal': 0x63
        };

        const MOD_MAP = {
            'ControlLeft': 0x01, 'ShiftLeft': 0x02, 'AltLeft': 0x04, 'MetaLeft': 0x08,
            'ControlRight': 0x10, 'ShiftRight': 0x20, 'AltRight': 0x40, 'MetaRight': 0x80
        };

        const heldKeys = new Set();
        let activeModifiers = 0;

        function sendKeyReport() {
            const arr = Array.from(heldKeys).slice(0, 6);
            sendWs({
                type: 'key',
                mod: activeModifiers,
                keys: arr
            });
        }

        function sendReleaseAll() {
            heldKeys.clear();
            activeModifiers = 0;
            sendWs({ type: 'release_all' });
            if (keyIndicator) keyIndicator.textContent = 'None';
        }

        function sendMacro(cmd) {
            sendWs({ type: 'macro', name: cmd });
            if (keyIndicator) keyIndicator.textContent = cmd;
            setTimeout(() => { if (keyIndicator) keyIndicator.textContent = 'None'; }, 1200);
        }

        function toggleKvmMode() {
            kvmActive = !kvmActive;
            document.getElementById('btn-kvm').classList.toggle('active', kvmActive);
            document.getElementById('kvm-drawer').classList.toggle('open', kvmActive);
            if (!kvmActive) {
                if (document.exitPointerLock && isPointerLocked()) {
                    document.exitPointerLock();
                }
                sendReleaseAll();
            }
        }

        window.addEventListener('keydown', (e) => {
            if (!kvmActive) return;
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;

            let changed = false;
            if (MOD_MAP[e.code] !== undefined) {
                activeModifiers |= MOD_MAP[e.code];
                changed = true;
            }
            if (KEY_MAP[e.code] !== undefined) {
                heldKeys.add(KEY_MAP[e.code]);
                changed = true;
            }

            if (changed) {
                e.preventDefault();
                sendKeyReport();
                if (keyIndicator) keyIndicator.textContent = e.code;
            }
        });

        window.addEventListener('keyup', (e) => {
            if (!kvmActive) return;
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;

            let changed = false;
            if (MOD_MAP[e.code] !== undefined) {
                activeModifiers &= ~MOD_MAP[e.code];
                changed = true;
            }
            if (KEY_MAP[e.code] !== undefined) {
                heldKeys.delete(KEY_MAP[e.code]);
                changed = true;
            }

            if (changed) {
                e.preventDefault();
                sendKeyReport();
            }
        });

        window.addEventListener('blur', () => {
            if (kvmActive) {
                sendReleaseAll();
            }
        });

        window.addEventListener('beforeunload', () => {
            if (ws) {
                ws.close();
                ws = null;
            }
        });

        function uploadOtaFirmware() {
            const fileInput = document.getElementById('ota-file');
            const file = fileInput.files[0];
            const pBox = document.getElementById('ota-progress-box');
            const pBar = document.getElementById('ota-progress-bar');
            const pMsg = document.getElementById('ota-status-msg');

            if (!file) {
                alert('Please select an ESP32-P4 firmware binary (.bin)');
                return;
            }

            pBox.style.display = 'block';
            pBar.style.width = '0%';
            pMsg.textContent = 'Uploading firmware via Ethernet...';

            const xhr = new XMLHttpRequest();
            xhr.open('POST', '/api/ota', true);
            xhr.setRequestHeader('Content-Type', 'application/octet-stream');

            xhr.upload.onprogress = (e) => {
                if (e.lengthComputable) {
                    const pct = Math.round((e.loaded / e.total) * 100);
                    pBar.style.width = pct + '%';
                    pMsg.textContent = `Uploading firmware: ${pct}% (${(e.loaded/1024).toFixed(0)} / ${(e.total/1024).toFixed(0)} KB)`;
                }
            };

            xhr.onload = () => {
                if (xhr.status === 200) {
                    pBar.style.width = '100%';
                    pMsg.textContent = 'OTA Flash written successfully! Rebooting ESP32-P4...';
                    setTimeout(() => {
                        pMsg.textContent = 'Reconnecting after reboot...';
                        setTimeout(() => location.reload(), 5000);
                    }, 2500);
                } else {
                    pMsg.textContent = 'OTA Error: ' + xhr.responseText;
                }
            };

            xhr.onerror = () => {
                pMsg.textContent = 'OTA Upload failed due to network communication error';
            };
            xhr.send(file);
        }


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

        // Initialize HUD, Virtual Keyboard & Auth on Page Load
        window.addEventListener('DOMContentLoaded', () => {
            loadPerfHudState();
            loadVkState();
            checkAuth();
        });
    </script>
</body>
</html>
'''

# Convert html_content to C escaped string
c_lines = []
for line in html_content.splitlines():
    escaped = line.replace('\\', '\\\\').replace('"', '\\"')
    c_lines.append(f'"{escaped}\\n"')

c_output = "#pragma once\n\nstatic const char HTML_INDEX_PAGE[] = \n" + "\n".join(c_lines) + ";\n"

with open('main/web_ui.h', 'w', encoding='utf-8') as f:
    f.write(c_output)

print("Successfully regenerated main/web_ui.h without kicked-modal!")
