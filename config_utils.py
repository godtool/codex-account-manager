#!/usr/bin/env python3
"""
配置工具模块 - 简化版本
"""

import re
from pathlib import Path


def get_config_paths():
    """获取配置文件路径 - 项目内存储"""
    # 获取当前脚本所在目录
    script_dir = Path(__file__).parent
    codex_dir = script_dir / "codex-config"
    system_auth_file = Path.home() / ".codex" / "auth.json"
    
    return {
        'codex_dir': codex_dir,
        'auth_file': codex_dir / "auth.json",
        'accounts_dir': codex_dir / "accounts",
        'system_auth_file': system_auth_file
    }


def generate_account_name(email):
    """根据邮箱生成安全的账号名称"""
    if not email:
        return "current_backup"
    
    # 直接用邮箱用户名，替换特殊字符为下划线
    username = email.split('@')[0]
    return re.sub(r'[^a-zA-Z0-9_]', '_', username)