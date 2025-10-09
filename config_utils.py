#!/usr/bin/env python3
"""
配置工具模块

Tauri 应用标识: com.codex.account-manager
应用配置目录:
- macOS: ~/Library/Application Support/com.codex.account-manager
- Windows: %APPDATA%/com.codex.account-manager
- Linux: $XDG_CONFIG_HOME/com.codex.account-manager 或 ~/.config/com.codex.account-manager
"""

import os
import sys
import re
from pathlib import Path


def _app_config_base_dir() -> Path:
    """获取与 Tauri 一致的应用配置基础目录"""
    ident = "com.codex.account-manager"
    if sys.platform == "darwin":  # macOS
        return Path.home() / "Library" / "Application Support" / ident
    if sys.platform.startswith("win"):
        appdata = os.getenv("APPDATA", str(Path.home() / "AppData" / "Roaming"))
        return Path(appdata) / ident
    # Linux / others
    xdg = os.getenv("XDG_CONFIG_HOME", str(Path.home() / ".config"))
    return Path(xdg) / ident


def get_config_paths():
    """获取配置文件路径 - 与 Tauri 端一致的 appConfigDir/codex-config 结构"""
    base = _app_config_base_dir()
    codex_dir = base / "codex-config"
    system_auth_file = Path.home() / ".codex" / "auth.json"
    usage_cache_dir = codex_dir / "usage_cache"

    return {
        'codex_dir': codex_dir,
        'auth_file': codex_dir / "auth.json",
        'accounts_dir': codex_dir / "accounts",
        'usage_cache_dir': usage_cache_dir,
        'system_auth_file': system_auth_file
    }


def generate_account_name(email):
    """根据邮箱生成安全的账号名称"""
    if not email:
        return "current_backup"
    
    # 直接用邮箱用户名，替换特殊字符为下划线
    username = email.split('@')[0]
    return re.sub(r'[^a-zA-Z0-9_]', '_', username)