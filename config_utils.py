#!/usr/bin/env python3
"""
配置工具模块
提供统一的配置路径管理和项目模式检测
"""

from pathlib import Path


def detect_project_mode():
    """检测是否在项目目录中运行"""
    current_dir = Path.cwd()
    
    if "codex-account-manager" in str(current_dir) or (current_dir / "codex-account-manager").exists():
        project_dir = current_dir if current_dir.name == "codex-account-manager" else current_dir / "codex-account-manager"
        return project_dir
    
    return None


def get_config_paths():
    """获取配置文件路径"""
    project_dir = detect_project_mode()
    
    if project_dir:
        # 项目模式
        codex_dir = project_dir / "codex-config"
        auth_file = codex_dir / "auth.json"
        accounts_dir = codex_dir / "accounts"
        system_auth_file = Path.home() / ".codex" / "auth.json"
        print(f"🎯 项目模式: {project_dir}")
    else:
        # 系统模式
        codex_dir = Path.home() / ".codex"
        auth_file = codex_dir / "auth.json"
        accounts_dir = codex_dir / "accounts"
        system_auth_file = auth_file
        print("🏠 系统模式")
    
    return codex_dir, auth_file, accounts_dir, system_auth_file


def generate_account_name(email):
    """根据邮箱生成账号名称"""
    import re
    
    if not email:
        return "current_backup"
    
    username = email.split('@')[0]
    safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', username)
    domain = email.split('@')[1] if '@' in email else 'unknown'
    
    if 'gmail' in domain:
        safe_name += '_gmail'
    elif 'hotmail' in domain or 'outlook' in domain:
        safe_name += '_outlook'
    elif 'yahoo' in domain:
        safe_name += '_yahoo'
    else:
        domain_part = domain.split('.')[0]
        safe_name += f'_{domain_part}'
    
    return safe_name