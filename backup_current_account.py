#!/usr/bin/env python3
"""
备份当前账号配置脚本
"""

import json
import shutil
from datetime import datetime
from pathlib import Path
from usage_checker import extract_email_from_auth
from config_utils import get_config_paths, generate_account_name


def backup_current_account(account_name=None):
    """备份当前账号配置"""
    paths = get_config_paths()
    codex_dir = paths['codex_dir']
    auth_file = paths['auth_file']
    accounts_dir = paths['accounts_dir']
    system_auth_file = paths['system_auth_file']
    
    # 确保目录存在
    accounts_dir.mkdir(parents=True, exist_ok=True)
    
    # 先从系统同步配置
    if system_auth_file != auth_file and system_auth_file.exists():
        try:
            auth_file.parent.mkdir(exist_ok=True)
            shutil.copy2(system_auth_file, auth_file)
            print(f"📥 已从系统同步配置")
        except Exception as e:
            print(f"⚠️ 同步失败: {e}")
    
    # 检查配置文件是否存在
    if not auth_file.exists():
        print(f"❌ 配置文件不存在: {auth_file}")
        return False
    
    try:
        # 读取当前配置
        with open(auth_file, 'r', encoding='utf-8') as f:
            current_config = json.load(f)
        
        # 如果没有指定账号名称，则自动从配置中提取
        if account_name is None:
            email = extract_email_from_auth(current_config)
            if email:
                account_name = generate_account_name(email)
                print(f"🔍 检测到邮箱: {email}")
                print(f"📝 自动生成账号名称: {account_name}")
            else:
                account_name = "current_backup"
                print("⚠️ 未能检测到邮箱，使用默认名称: current_backup")
        
        # 添加保存时间戳
        current_config['saved_at'] = datetime.now().isoformat()
        current_config['account_name'] = account_name
        
        # 保存到accounts目录
        account_file = accounts_dir / f"{account_name}.json"
        with open(account_file, 'w', encoding='utf-8') as f:
            json.dump(current_config, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 成功保存账号配置: {account_name}")
        print(f"📁 保存位置: {account_file}")
        
        # 显示账号信息
        account_id = current_config.get('tokens', {}).get('account_id', '未知')
        print(f"🔹 账号ID: {account_id}")
        
        return True
        
    except Exception as e:
        print(f"❌ 备份失败: {e}")
        return False


if __name__ == "__main__":
    import sys
    # 支持命令行参数指定账号名称，如果不指定则自动提取
    account_name = sys.argv[1] if len(sys.argv) > 1 else None
    backup_current_account(account_name)