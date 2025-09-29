#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenAI Codex 账号配置管理器
用于管理和切换多个 OpenAI 账号配置
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from usage_checker import OpenAIUsageChecker, extract_access_token_from_auth, extract_email_from_auth
from config_utils import detect_project_mode, generate_account_name


class CodexAccountManager:
    def __init__(self, project_dir=None):
        # 如果指定了项目目录，使用项目目录下的配置
        if project_dir:
            self.project_dir = Path(project_dir)
            self.codex_dir = self.project_dir / "codex-config"
            self.auth_file = self.codex_dir / "auth.json"
            self.accounts_dir = self.codex_dir / "accounts"
            # 系统原始配置目录
            self.system_codex_dir = Path.home() / ".codex"
            self.system_auth_file = self.system_codex_dir / "auth.json"
        else:
            # 使用系统默认配置
            self.codex_dir = Path.home() / ".codex"
            self.auth_file = self.codex_dir / "auth.json"
            self.accounts_dir = self.codex_dir / "accounts"
            self.system_codex_dir = self.codex_dir
            self.system_auth_file = self.auth_file
        
        # 确保目录存在
        self.codex_dir.mkdir(exist_ok=True)
        self.accounts_dir.mkdir(exist_ok=True)
    
    def sync_from_system(self):
        """从系统配置同步当前账号"""
        if self.system_auth_file.exists() and self.system_auth_file != self.auth_file:
            try:
                shutil.copy2(self.system_auth_file, self.auth_file)
                print(f"✅ 已同步系统配置到项目目录")
                return True
            except Exception as e:
                print(f"❌ 同步失败: {e}")
                return False
        return True
    
    def sync_to_system(self):
        """将项目配置同步到系统"""
        if self.auth_file.exists() and self.auth_file != self.system_auth_file:
            try:
                # 确保系统目录存在
                self.system_codex_dir.mkdir(exist_ok=True)
                shutil.copy2(self.auth_file, self.system_auth_file)
                print(f"✅ 已同步项目配置到系统目录")
                return True
            except Exception as e:
                print(f"❌ 同步失败: {e}")
                return False
        return True
    
    def save_current_account(self, account_name):
        """保存当前账号配置"""
        # 先同步系统配置
        self.sync_from_system()
        
        if not self.auth_file.exists():
            print("错误: auth.json 文件不存在")
            return False
        
        try:
            # 读取当前配置
            with open(self.auth_file, 'r', encoding='utf-8') as f:
                current_config = json.load(f)
            
            # 添加保存时间戳
            current_config['saved_at'] = datetime.now().isoformat()
            current_config['account_name'] = account_name
            
            # 保存到accounts目录
            account_file = self.accounts_dir / f"{account_name}.json"
            with open(account_file, 'w', encoding='utf-8') as f:
                json.dump(current_config, f, indent=2, ensure_ascii=False)
            
            print(f"✅ 成功保存账号配置: {account_name}")
            print(f"📁 保存位置: {account_file}")
            return True
            
        except Exception as e:
            print(f"❌ 保存失败: {e}")
            return False
    
    def save_account_from_config(self, account_name, config_data):
        """从提供的配置数据保存账号"""
        try:
            # 解析配置数据
            if isinstance(config_data, str):
                config = json.loads(config_data)
            else:
                config = config_data
            
            # 添加保存时间戳
            config['saved_at'] = datetime.now().isoformat()
            config['account_name'] = account_name
            
            # 保存到accounts目录
            account_file = self.accounts_dir / f"{account_name}.json"
            with open(account_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            print(f"✅ 成功保存账号配置: {account_name}")
            print(f"📁 保存位置: {account_file}")
            return True
            
        except Exception as e:
            print(f"❌ 保存失败: {e}")
            return False
    
    def list_accounts(self):
        """列出所有保存的账号"""
        account_files = list(self.accounts_dir.glob("*.json"))
        
        if not account_files:
            print("📭 没有保存的账号配置")
            return []
        
        accounts = []
        print("\n📋 已保存的账号配置:")
        print("-" * 60)
        
        for account_file in sorted(account_files):
            try:
                with open(account_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                account_name = account_file.stem
                saved_at = config.get('saved_at', '未知时间')
                account_id = config.get('tokens', {}).get('account_id', '未知ID')
                
                print(f"🔹 {account_name}")
                print(f"   账号ID: {account_id}")
                print(f"   保存时间: {saved_at}")
                print()
                
                accounts.append(account_name)
                
            except Exception as e:
                print(f"❌ 读取 {account_file.name} 失败: {e}")
        
        return accounts
    
    def switch_account(self, account_name):
        """切换到指定账号"""
        # 在切换前保存当前账号的用量数据
        self.save_current_usage_before_switch()
        
        account_file = self.accounts_dir / f"{account_name}.json"
        
        if not account_file.exists():
            print(f"❌ 账号配置不存在: {account_name}")
            return False
        
        try:
            # 备份当前配置
            if self.auth_file.exists():
                backup_file = self.auth_file.with_suffix('.json.backup')
                shutil.copy2(self.auth_file, backup_file)
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
            
            # 写入项目配置
            with open(self.auth_file, 'w', encoding='utf-8') as f:
                json.dump(clean_config, f, indent=2, ensure_ascii=False)
            
            # 同步到系统配置
            self.sync_to_system()
            
            print(f"✅ 成功切换到账号: {account_name}")
            
            # 显示账号信息
            account_id = target_config.get('tokens', {}).get('account_id', '未知')
            print(f"🔹 账号ID: {account_id}")
            
            return True
            
        except Exception as e:
            print(f"❌ 切换失败: {e}")
            return False
    
    def save_current_usage_before_switch(self):
        """在切换账号前保存当前账号的用量（不查询session，只从缓存读取）"""
        try:
            # 先同步系统配置
            self.sync_from_system()
            
            if not self.auth_file.exists():
                return
            
            with open(self.auth_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 提取邮箱
            email = extract_email_from_auth(config)
            if not email:
                return
            
            # 不进行任何session查询，只是为了保持代码结构
            # 实际的用量数据保存现在只通过手动刷新进行
            print(f"ℹ️ 已切换账号，如需查看用量请使用菜单选项7或8")
            
        except Exception as e:
            print(f"⚠️ 处理时出错: {e}")
    
    def delete_account(self, account_name):
        """删除指定账号配置"""
        account_file = self.accounts_dir / f"{account_name}.json"
        
        if not account_file.exists():
            print(f"❌ 账号配置不存在: {account_name}")
            return False
        
        try:
            account_file.unlink()
            print(f"🗑️ 已删除账号配置: {account_name}")
            return True
        except Exception as e:
            print(f"❌ 删除失败: {e}")
            return False
    
    def show_current_account(self):
        """显示当前账号信息"""
        # 先同步系统配置
        self.sync_from_system()
        
        if not self.auth_file.exists():
            print("❌ 当前没有活跃的账号配置")
            return
        
        try:
            with open(self.auth_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            account_id = config.get('tokens', {}).get('account_id', '未知')
            last_refresh = config.get('last_refresh', '未知')
            
            print("\n🔄 当前活跃账号:")
            print(f"账号ID: {account_id}")
            print(f"最后刷新: {last_refresh}")
            print(f"配置文件: {self.auth_file}")
            
        except Exception as e:
            print(f"❌ 读取当前配置失败: {e}")

    def check_account_usage(self, account_name=None, force_refresh=False):
        """检查账号用量"""
        try:
            # 如果指定了账号名称，读取该账号配置
            if account_name:
                account_file = self.accounts_dir / f"{account_name}.json"
                if not account_file.exists():
                    print(f"❌ 账号配置不存在: {account_name}")
                    return False
                
                with open(account_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                print(f"\n📊 正在查询账号 {account_name} 的用量...")
            else:
                # 检查当前账号
                self.sync_from_system()
                
                if not self.auth_file.exists():
                    print("❌ 当前没有活跃的账号配置")
                    return False
                
                with open(self.auth_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                print("\n📊 正在查询当前账号的用量...")
            
            # 提取邮箱
            email = extract_email_from_auth(config)
            
            if not email:
                print("❌ 未能提取账号邮箱信息")
                return False
            
            # 创建用量检查器
            checker = OpenAIUsageChecker()
            
            if force_refresh:
                # 强制从session刷新
                summary = checker.get_usage_summary(email)
            else:
                # 先尝试从缓存读取
                cached_data = checker.load_usage_data(email)
                if cached_data:
                    print("📁 从缓存读取用量数据...")
                    summary = {
                        "email": email,
                        "check_time": cached_data.get("check_time", ""),
                        "status": "success",
                        "token_usage": cached_data.get("token_usage", {}),
                        "rate_limits": cached_data.get("rate_limits", {}),
                        "errors": cached_data.get("errors", []),
                        "from_cache": True
                    }
                else:
                    print("⚠️ 没有缓存数据，请先用 codex 发送消息")
                    print("💡 提示: 你可以选择菜单项进行强制刷新")
                    return False
            
            # 显示格式化的结果
            print("\n" + "=" * 60)
            formatted_summary = checker.format_usage_summary(summary)
            print(formatted_summary)
            print("=" * 60)
            
            return True
            
        except Exception as e:
            print(f"❌ 检查用量失败: {e}")
            return False

    def check_all_accounts_usage(self):
        """检查所有账号的用量"""
        account_files = list(self.accounts_dir.glob("*.json"))
        
        if not account_files:
            print("❌ 没有保存的账号配置")
            return
        
        print(f"\n📊 正在查询所有账号用量 ({len(account_files)} 个账号)...")
        print("=" * 80)
        
        for i, account_file in enumerate(sorted(account_files), 1):
            account_name = account_file.stem
            print(f"\n[{i}/{len(account_files)}] {account_name}")
            print("-" * 40)
            
            try:
                with open(account_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # 提取访问令牌和邮箱
                access_token = extract_access_token_from_auth(config)
                email = extract_email_from_auth(config)
                
                if not access_token:
                    print("❌ 未找到有效的访问令牌")
                    continue
                
                # 创建用量检查器并获取摘要
                checker = OpenAIUsageChecker(access_token)
                summary = checker.get_account_summary(email)
                
                # 显示简化的摘要
                if summary.get('status') in ['success', 'partial_success']:
                    print(f"✅ 查询成功")
                    print(f"邮箱: {summary.get('email', '未知')}")
                    
                    # 显示账号信息
                    if summary.get('account_info'):
                        account = summary['account_info']
                        if 'name' in account:
                            print(f"用户名: {account['name']}")
                    
                    # 显示订阅信息
                    if summary.get('subscription'):
                        sub = summary['subscription']
                        if 'plan' in sub:
                            plan_name = sub['plan']['title'] if isinstance(sub['plan'], dict) else sub['plan']
                            print(f"订阅计划: {plan_name}")
                        if 'has_payment_method' in sub:
                            payment_status = "已绑定" if sub['has_payment_method'] else "未绑定"
                            print(f"支付方式: {payment_status}")
                    
                    # 显示信用额度
                    if summary.get('credits'):
                        credits = summary['credits']
                        if 'total_available' in credits:
                            print(f"剩余额度: ${credits['total_available']}")
                    
                    # 显示使用统计
                    if summary.get('usage_data') and 'daily_costs' in summary['usage_data']:
                        costs_data = summary['usage_data']['daily_costs'][-7:]  # 最近7天
                        total_cost = sum(day.get('cost', 0) for day in costs_data)
                        print(f"7天费用: ${total_cost:.4f}")
                    
                    if summary.get('billing_data') and 'total_usage' in summary['billing_data']:
                        print(f"月度费用: ${summary['billing_data']['total_usage']:.4f}")
                        
                    if summary.get('errors'):
                        print(f"⚠️ 部分数据获取失败 ({len(summary['errors'])} 个错误)")
                else:
                    print(f"❌ 查询失败: {summary.get('status', '未知')}")
                    if summary.get('errors'):
                        print(f"错误: {summary['errors'][0]}")
            
            except Exception as e:
                print(f"❌ 处理失败: {e}")
        
        print("\n" + "=" * 80)


def main():
    # 检测是否在项目目录中运行
    current_dir = Path.cwd()
    project_dir = None
    
    # 如果当前目录包含codex-account-manager，使用项目模式
    if "codex-account-manager" in str(current_dir) or (current_dir / "codex-account-manager").exists():
        project_dir = current_dir if current_dir.name == "codex-account-manager" else current_dir / "codex-account-manager"
        print(f"🎯 项目模式: 使用 {project_dir}")
    
    manager = CodexAccountManager(project_dir)
    
    while True:
        print("\n" + "=" * 50)
        print("🚀 OpenAI Codex 账号管理器")
        if project_dir:
            print(f"📁 项目模式: {project_dir}")
        print("=" * 50)
        print("1. 保存当前账号配置")
        print("2. 从配置内容添加账号")
        print("3. 列出所有账号")
        print("4. 切换账号")
        print("5. 删除账号配置")
        print("6. 显示当前账号")
        print("7. 查看当前账号用量（缓存）")
        print("8. 查看指定账号用量（缓存）")
        print("9. 刷新当前账号用量（从session）")
        print("10. 查看所有账号用量")
        print("11. 同步系统配置到项目")
        print("12. 同步项目配置到系统")
        print("0. 退出")
        print("-" * 50)
        
        choice = input("请选择操作 (0-12): ").strip()
        
        if choice == "1":
            account_name = input("请输入账号名称: ").strip()
            if account_name:
                manager.save_current_account(account_name)
            else:
                print("❌ 账号名称不能为空")
        
        elif choice == "2":
            account_name = input("请输入账号名称: ").strip()
            if not account_name:
                print("❌ 账号名称不能为空")
                continue
            
            print("请粘贴完整的 auth.json 配置内容 (以 {} 开始和结束):")
            print("输入完成后按 Ctrl+D (Linux/Mac) 或 Ctrl+Z (Windows) 结束:")
            
            config_lines = []
            try:
                while True:
                    line = input()
                    config_lines.append(line)
            except EOFError:
                pass
            
            config_text = '\n'.join(config_lines).strip()
            if config_text:
                manager.save_account_from_config(account_name, config_text)
            else:
                print("❌ 配置内容不能为空")
        
        elif choice == "3":
            manager.list_accounts()
        
        elif choice == "4":
            accounts = manager.list_accounts()
            if accounts:
                account_name = input("请输入要切换的账号名称: ").strip()
                if account_name in accounts:
                    manager.switch_account(account_name)
                else:
                    print("❌ 账号名称不存在")
        
        elif choice == "5":
            accounts = manager.list_accounts()
            if accounts:
                account_name = input("请输入要删除的账号名称: ").strip()
                if account_name in accounts:
                    confirm = input(f"确认删除账号 '{account_name}' 吗? (y/N): ").strip().lower()
                    if confirm == 'y':
                        manager.delete_account(account_name)
                else:
                    print("❌ 账号名称不存在")
        
        elif choice == "6":
            manager.show_current_account()
        
        elif choice == "7":
            manager.check_account_usage()
        
        elif choice == "8":
            accounts = manager.list_accounts()
            if accounts:
                account_name = input("请输入要查看用量的账号名称: ").strip()
                if account_name in accounts:
                    manager.check_account_usage(account_name)
                else:
                    print("❌ 账号名称不存在")
        
        elif choice == "9":
            manager.check_account_usage(force_refresh=True)
        
        elif choice == "10":
            manager.check_all_accounts_usage()
        
        elif choice == "11":
            manager.sync_from_system()
        
        elif choice == "12":
            manager.sync_to_system()
        
        elif choice == "0":
            print("👋 再见!")
            break
        
        else:
            print("❌ 无效选择，请重试")


if __name__ == "__main__":
    main()