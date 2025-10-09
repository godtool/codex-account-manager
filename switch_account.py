#!/usr/bin/env python3
"""
快速账号切换脚本
用法: python3 switch_account.py <账号名称>
"""

import json
import sys
import shutil
from pathlib import Path
from config_utils import get_config_paths


def sync_to_system(auth_file, system_auth_file):
    """同步配置到系统"""
    if auth_file != system_auth_file and auth_file.exists():
        try:
            system_auth_file.parent.mkdir(exist_ok=True)
            shutil.copy2(auth_file, system_auth_file)
            print(f"✅ 已同步配置到系统")
        except Exception as e:
            print(f"⚠️ 同步到系统失败: {e}")


def switch_account(account_name):
    """切换到指定账号"""
    paths = get_config_paths()
    codex_dir = paths['codex_dir']
    auth_file = paths['auth_file']
    accounts_dir = paths['accounts_dir']
    system_auth_file = paths['system_auth_file']
    account_file = accounts_dir / f"{account_name}.json"
    
    if not account_file.exists():
        print(f"❌ 账号配置不存在: {account_name}")
        print(f"📁 请确保文件存在: {account_file}")
        return False
    
    try:
        # 备份当前配置
        if auth_file.exists():
            backup_file = auth_file.with_suffix('.json.backup')
            shutil.copy2(auth_file, backup_file)
            print(f"📦 已备份当前配置")
        
        # 读取目标账号配置
        with open(account_file, 'r', encoding='utf-8') as f:
            target_config = json.load(f)
        
        # 移除管理字段，只保留原始配置
        clean_config = {
            "OPENAI_API_KEY": target_config.get("OPENAI_API_KEY"),
            "tokens": target_config.get("tokens"),
            "last_refresh": target_config.get("last_refresh")
        }
        
        # 确保目录存在
        auth_file.parent.mkdir(exist_ok=True)
        
        # 写入配置
        with open(auth_file, 'w', encoding='utf-8') as f:
            json.dump(clean_config, f, indent=2, ensure_ascii=False)
        
        # 同步到系统配置
        sync_to_system(auth_file, system_auth_file)
        
        print(f"✅ 成功切换到账号: {account_name}")
        
        # 显示账号信息
        account_id = target_config.get('tokens', {}).get('account_id', '未知')
        print(f"🔹 账号ID: {account_id}")
        
        return True
        
    except Exception as e:
        print(f"❌ 切换失败: {e}")
        return False


def list_accounts():
    """列出所有可用账号"""
    accounts_dir = get_config_paths()['accounts_dir']
    account_files = list(accounts_dir.glob("*.json"))
    
    if not account_files:
        print("📭 没有保存的账号配置")
        return []
    
    print("📋 可用的账号配置:")
    accounts = []
    for account_file in sorted(account_files):
        try:
            with open(account_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            account_name = account_file.stem
            account_id = config.get('tokens', {}).get('account_id', '未知ID')
            saved_at = config.get('saved_at', '未知时间')
            
            print(f"  🔹 {account_name}")
            print(f"     ID: {account_id}")
            print(f"     保存时间: {saved_at}")
            accounts.append(account_name)
        except:
            account_name = account_file.stem
            print(f"  - {account_name}")
            accounts.append(account_name)
    
    return accounts


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("📖 用法: python3 switch_account.py <账号名称>")
        print("\n可用账号:")
        list_accounts()
        sys.exit(1)
    
    account_name = sys.argv[1]
    switch_account(account_name)