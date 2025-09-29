#!/usr/bin/env python3
"""
OpenAI 账号用量查询工具
快速查看账号使用情况和剩余额度
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from usage_checker import OpenAIUsageChecker, extract_access_token_from_auth, extract_email_from_auth
import json


def load_auth_config(config_path=None):
    """加载认证配置"""
    if config_path:
        if not Path(config_path).exists():
            print(f"❌ 配置文件不存在: {config_path}")
            return None
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ 读取配置文件失败: {e}")
            return None
    
    # 自动查找配置文件
    possible_paths = [
        "codex-config/auth.json",
        Path.home() / ".codex/auth.json",
        Path.home() / ".config/cursor/auth.json",
        Path.home() / ".cursor/auth.json"
    ]
    
    for path in possible_paths:
        try:
            if Path(path).exists():
                with open(path, 'r') as f:
                    config = json.load(f)
                print(f"📂 使用配置文件: {path}")
                return config
        except Exception:
            continue
    
    print("❌ 未找到有效的认证配置文件")
    return None


def check_usage(config_path=None, account_name=None, show_details=False):
    """检查用量"""
    # 获取当前账号邮箱
    current_email = None
    current_config = load_auth_config(config_path)
    if current_config:
        current_email = extract_email_from_auth(current_config)
    
    if account_name:
        # 检查指定账号
        accounts_dir = Path("codex-config/accounts") if Path("codex-config").exists() else Path.home() / ".codex/accounts"
        account_file = accounts_dir / f"{account_name}.json"
        
        if not account_file.exists():
            print(f"❌ 账号配置不存在: {account_name}")
            return False
        
        try:
            with open(account_file, 'r') as f:
                config = json.load(f)
            print(f"📊 查询账号: {account_name}")
            
            # 从配置中提取邮箱
            email = config.get('email') or extract_email_from_auth(config)
            
            # 判断是否是当前账号
            is_current_account = email == current_email if current_email and email else False
        except Exception as e:
            print(f"❌ 读取账号配置失败: {e}")
            return False
    else:
        # 检查当前账号
        config = current_config
        if not config:
            return False
        print("📊 查询当前账号用量")
        
        # 提取邮箱
        email = extract_email_from_auth(config)
        is_current_account = True  # 直接查询当前账号
    
    if not email:
        print("❌ 未能提取账号邮箱信息")
        return False
    
    print(f"👤 账号邮箱: {email}")
    print("⏳ 正在查询...")
    
    # 创建用量检查器并获取摘要
    try:
        checker = OpenAIUsageChecker()
        
        if is_current_account:
            # 当前账号：实时查询并保存到缓存
            summary = checker.get_account_summary(email)
        else:
            # 其他账号：只从缓存读取
            cached_data = checker.load_usage_data(email)
            if cached_data:
                summary = {
                    "email": email,
                    "check_time": cached_data.get("check_time", ""),
                    "status": "success (cached)",
                    "usage_data": cached_data.get("token_usage", {}),
                    "rate_limits": cached_data.get("rate_limits", {}),
                    "errors": cached_data.get("errors", []),
                    "from_cache": True
                }
            else:
                print(f"❌ 账号 {email} 没有缓存数据，请先切换到该账号查询用量")
                return False
        
        print("\n" + "=" * 60)
        
        # 显示数据来源
        if summary.get('from_cache'):
            print("📁 数据来源: 缓存")
        else:
            print("🔄 数据来源: 实时查询")
        
        if show_details:
            # 显示详细信息
            formatted_summary = checker.format_usage_summary(summary)
            print(formatted_summary)
        else:
            # 显示简化信息
            print(f"账号: {summary.get('email', '未知')}")
            print(f"状态: {summary.get('status', 'unknown')}")
            print(f"查询时间: {summary.get('check_time', '')}")
            
            # Token使用情况
            if summary.get('usage_data'):
                usage = summary['usage_data']
                if usage.get('total_tokens'):
                    print(f"总Token: {usage['total_tokens']:,}")
                if usage.get('input_tokens'):
                    print(f"输入Token: {usage['input_tokens']:,}")
                if usage.get('output_tokens'):
                    print(f"输出Token: {usage['output_tokens']:,}")
            
            # 速率限制
            if summary.get('rate_limits'):
                limits = summary['rate_limits']
                if limits.get('primary'):
                    primary = limits['primary']
                    reset_seconds = primary.get('resets_in_seconds', 0)
                    reset_time = datetime.now() + timedelta(seconds=reset_seconds)
                    print(f"5h限制: {primary.get('used_percent', 0):.1f}% (重置时间: {reset_time.strftime('%H:%M:%S')})")
                if limits.get('secondary'):
                    secondary = limits['secondary']
                    reset_seconds = secondary.get('resets_in_seconds', 0)
                    reset_time = datetime.now() + timedelta(seconds=reset_seconds)
                    print(f"周限制: {secondary.get('used_percent', 0):.1f}% (重置时间: {reset_time.strftime('%m-%d %H:%M')})")
            
            # 错误信息
            if summary.get('errors'):
                print(f"⚠️ 错误: {len(summary['errors'])} 个")
                if show_details:
                    for error in summary['errors']:
                        print(f"  - {error}")
        
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"❌ 查询失败: {e}")
        return False


def list_all_accounts():
    """列出所有账号的用量"""
    accounts_dir = Path("codex-config/accounts") if Path("codex-config").exists() else Path.home() / ".codex/accounts"
    
    if not accounts_dir.exists():
        print("❌ 账号配置目录不存在")
        return False
    
    account_files = list(accounts_dir.glob("*.json"))
    if not account_files:
        print("❌ 没有保存的账号配置")
        return False
    
    print(f"📊 查询所有账号用量 ({len(account_files)} 个账号)")
    print("=" * 80)
    
    for i, account_file in enumerate(sorted(account_files), 1):
        account_name = account_file.stem
        print(f"\n[{i}/{len(account_files)}] {account_name}")
        print("-" * 40)
        
        try:
            with open(account_file, 'r') as f:
                config = json.load(f)
            
            # 从配置中提取邮箱
            email = config.get('email') or extract_email_from_auth(config)
            
            if not email:
                print("❌ 无法提取邮箱信息")
                continue
            
            checker = OpenAIUsageChecker()
            summary = checker.get_account_summary(email)
            
            if summary.get('status') in ['success', 'success (cached)']:
                print(f"✅ {email}")
                
                # 显示数据来源
                if summary.get('from_cache'):
                    print("   📁 缓存数据")
                else:
                    print("   🔄 实时数据")
                
                # Token使用情况
                if summary.get('usage_data'):
                    usage = summary['usage_data']
                    if usage.get('total_tokens'):
                        print(f"   总Token: {usage['total_tokens']:,}")
                
                # 速率限制
                if summary.get('rate_limits'):
                    limits = summary['rate_limits']
                    if limits.get('primary'):
                        primary = limits['primary']
                        reset_seconds = primary.get('resets_in_seconds', 0)
                        reset_time = datetime.now() + timedelta(seconds=reset_seconds)
                        print(f"   5h限制: {primary.get('used_percent', 0):.1f}% ({reset_time.strftime('%H:%M')}重置)")
                    if limits.get('secondary'):
                        secondary = limits['secondary']
                        reset_seconds = secondary.get('resets_in_seconds', 0)
                        reset_time = datetime.now() + timedelta(seconds=reset_seconds)
                        print(f"   周限制: {secondary.get('used_percent', 0):.1f}% ({reset_time.strftime('%m-%d %H:%M')}重置)")
            else:
                print(f"❌ 查询失败")
                if summary.get('errors'):
                    print(f"   {summary['errors'][0]}")
        
        except Exception as e:
            print(f"❌ 错误: {e}")
    
    print("\n" + "=" * 80)
    return True


def main():
    parser = argparse.ArgumentParser(
        description="OpenAI 账号用量查询工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python check_usage.py                    # 查询当前账号
  python check_usage.py -a work_account    # 查询指定账号
  python check_usage.py --all              # 查询所有账号
  python check_usage.py -d                 # 显示详细信息
  python check_usage.py -c auth.json       # 指定配置文件
        """
    )
    
    parser.add_argument('-c', '--config', 
                       help='指定配置文件路径')
    parser.add_argument('-a', '--account', 
                       help='指定账号名称')
    parser.add_argument('-d', '--details', action='store_true',
                       help='显示详细信息')
    parser.add_argument('--all', action='store_true',
                       help='查询所有账号')
    
    args = parser.parse_args()
    
    print("🔍 OpenAI 用量查询工具")
    print("-" * 30)
    
    if args.all:
        success = list_all_accounts()
    else:
        success = check_usage(
            config_path=args.config,
            account_name=args.account,
            show_details=args.details
        )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()