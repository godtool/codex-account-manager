#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenAI Codex 账号配置管理器
用于管理和切换多个 OpenAI 账号配置
"""

import json
import os
import shutil
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from usage_checker import CodexUsageChecker, extract_email_from_auth
from config_utils import get_config_paths, generate_account_name


class CodexAccountManager:
    def __init__(self):
        # 使用项目内配置路径
        config = get_config_paths()
        self.codex_dir = config['codex_dir']
        self.auth_file = config['auth_file']
        self.accounts_dir = config['accounts_dir']
        self.system_auth_file = config['system_auth_file']
        
        # 确保目录存在
        self.codex_dir.mkdir(parents=True, exist_ok=True)
        self.accounts_dir.mkdir(parents=True, exist_ok=True)
    
    def _load_config(self, file_path):
        """加载 JSON 配置文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"❌ 读取配置失败: {e}")
            return None
    
    def _save_config(self, file_path, config):
        """保存 JSON 配置文件"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            return True
        except (OSError, IOError) as e:
            print(f"❌ 保存配置失败: {e}")
            return False
    
    def _copy_to_system(self):
        """将当前账号复制到系统 Codex 配置"""
        try:
            if self.auth_file.exists():
                self.system_auth_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(self.auth_file, self.system_auth_file)
        except (OSError, IOError) as e:
            print(f"❌ 复制到系统失败: {e}")
            return False
    
    def save_current_account(self, account_name):
        """保存当前账号配置（从系统 Codex 配置读取）"""
        if not self.system_auth_file.exists():
            print("错误: 系统 Codex 配置不存在")
            print(f"请检查: {self.system_auth_file}")
            return False
        
        try:
            # 从系统 Codex 配置读取
            current_config = self._load_config(self.system_auth_file)
            
            # 添加保存时间戳
            current_config['saved_at'] = datetime.now().isoformat()
            current_config['account_name'] = account_name
            
            # 保存到accounts目录
            account_file = self.accounts_dir / f"{account_name}.json"
            if self._save_config(account_file, current_config):
                print(f"✅ 成功保存账号配置: {account_name}")
                print(f"📁 保存位置: {account_file}")
                return True
            return False
            
        except Exception as e:
            print(f"❌ 保存失败: {e}")
            return False
    
    def save_account_from_config(self, account_name, config_data):
        """从提供的配置数据保存账号"""
        try:
            config = json.loads(config_data) if isinstance(config_data, str) else config_data
            config.update({
                'saved_at': datetime.now().isoformat(),
                'account_name': account_name
            })
            
            account_file = self.accounts_dir / f"{account_name}.json"
            if self._save_config(account_file, config):
                print(f"✅ 成功保存账号配置: {account_name}")
                return True
            return False
        except json.JSONDecodeError as e:
            print(f"❌ JSON 格式错误: {e}")
            return False
    
    def list_accounts(self):
        """列出所有保存的账号"""
        account_files = list(self.accounts_dir.glob("*.json"))
        
        if not account_files:
            print("📭 没有保存的账号配置")
            return []
        
        accounts = []
        rows = []
        checker = CodexUsageChecker()
        now = datetime.now()

        def get_used_percent(limit_data):
            try:
                return float(limit_data.get('used_percent', -1))
            except (TypeError, ValueError):
                return -1.0

        def format_limit(limit_data):
            """格式化速率限制显示"""
            if not limit_data:
                return "暂无数据"

            used_percent = limit_data.get('used_percent')
            if isinstance(used_percent, (int, float)):
                used_str = f"{used_percent:.1f}%"
            else:
                used_str = "未知"

            reset_str = ""
            resets_in_seconds = limit_data.get('resets_in_seconds')
            if isinstance(resets_in_seconds, (int, float)):
                reset_time = now + timedelta(seconds=float(resets_in_seconds))
                if reset_time.date() == now.date():
                    reset_str = reset_time.strftime('%H:%M')
                else:
                    reset_str = reset_time.strftime('%m/%d %H:%M')
            else:
                resets_at = limit_data.get('resets_at')
                if isinstance(resets_at, (int, float)):
                    try:
                        reset_time = datetime.fromtimestamp(float(resets_at))
                        if reset_time.date() == now.date():
                            reset_str = reset_time.strftime('%H:%M')
                        else:
                            reset_str = reset_time.strftime('%m/%d %H:%M')
                    except (OverflowError, ValueError):
                        reset_str = ""
                elif isinstance(resets_at, str) and resets_at:
                    reset_str = resets_at

            if reset_str:
                return f"{used_str} ({reset_str}重置)"
            return used_str

        print("\n📋 已保存的账号配置:")
        
        for account_file in sorted(account_files):
            try:
                with open(account_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                account_name = config.get('account_name') or account_file.stem
                saved_at = config.get('saved_at', '未知时间')
                account_id = config.get('tokens', {}).get('account_id', '未知ID')

                email = extract_email_from_auth(config)
                usage_cache = checker.load_usage_data(email) if email else None
                rate_limits = usage_cache.get('rate_limits', {}) if usage_cache else {}

                five_hour_limit = None
                weekly_limit = None
                for limit in rate_limits.values():
                    if not isinstance(limit, dict):
                        continue
                    window_minutes = limit.get('window_minutes')
                    if not isinstance(window_minutes, (int, float)):
                        continue
                    used_percent = get_used_percent(limit)
                    if window_minutes <= 330:
                        if five_hour_limit is None or used_percent > get_used_percent(five_hour_limit):
                            five_hour_limit = limit
                    elif window_minutes > 330:
                        if weekly_limit is None or used_percent > get_used_percent(weekly_limit):
                            weekly_limit = limit

                five_hour_text = format_limit(five_hour_limit)
                weekly_text = format_limit(weekly_limit)

                rows.append([
                    account_name,
                    account_id,
                    saved_at,
                    five_hour_text,
                    weekly_text
                ])

                accounts.append(account_name)
                
            except Exception as e:
                print(f"❌ 读取 {account_file.name} 失败: {e}")

        if rows:
            headers = ["账号名称", "账号ID", "保存时间", "5小时窗口", "周限制"]
            col_widths = [len(h) for h in headers]

            for row in rows:
                for idx, cell in enumerate(row):
                    col_widths[idx] = max(col_widths[idx], len(str(cell)))

            header_line = " | ".join(h.ljust(col_widths[idx]) for idx, h in enumerate(headers))
            separator = "-+-".join("-" * col_widths[idx] for idx in range(len(headers)))
            print(header_line)
            print(separator)

            for row in rows:
                print(" | ".join(str(cell).ljust(col_widths[idx]) for idx, cell in enumerate(row)))
            print()
        
        return accounts
    
    def switch_account(self, account_name):
        """切换到指定账号"""
        account_file = self.accounts_dir / f"{account_name}.json"
        
        if not account_file.exists():
            print(f"❌ 账号配置不存在: {account_name}")
            return False
        
        try:
            # 读取目标账号配置
            target_config = self._load_config(account_file)
            
            # 移除管理字段，只保留原始配置
            clean_config = {
                "OPENAI_API_KEY": target_config.get("OPENAI_API_KEY"),
                "tokens": target_config.get("tokens"),
                "last_refresh": target_config.get("last_refresh")
            }
            
            # 直接写入系统 Codex 配置
            self.system_auth_file.parent.mkdir(parents=True, exist_ok=True)
            if self._save_config(self.system_auth_file, clean_config):
                print(f"✅ 成功切换到账号: {account_name}")
                
                # 显示账号信息
                account_id = target_config.get('tokens', {}).get('account_id', '未知')
                print(f"🔹 账号ID: {account_id}")
                print(f"📂 系统配置: {self.system_auth_file}")
                return True
            
        except Exception as e:
            print(f"❌ 切换失败: {e}")
            return False
    
    
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
        if not self.system_auth_file.exists():
            print("❌ 当前没有活跃的账号配置")
            print(f"请检查: {self.system_auth_file}")
            return
        
        try:
            config = self._load_config(self.system_auth_file)
            
            account_id = config.get('tokens', {}).get('account_id', '未知')
            last_refresh = config.get('last_refresh', '未知')
            
            print("\n🔄 当前活跃账号:")
            print(f"账号ID: {account_id}")
            print(f"最后刷新: {last_refresh}")
            print(f"系统配置: {self.system_auth_file}")
            
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
                
                config = self._load_config(account_file)
                print(f"\n📊 正在查询账号 {account_name} 的用量...")
            else:
                # 检查当前账号
                if not self.system_auth_file.exists():
                    print("❌ 当前没有活跃的账号配置")
                    return False
                
                config = self._load_config(self.system_auth_file)
                print("\n📊 正在查询当前账号的用量...")
            
            # 提取邮箱
            email = extract_email_from_auth(config)
            
            if not email:
                print("❌ 未能提取账号邮箱信息")
                return False
            
            # 创建用量检查器
            checker = CodexUsageChecker()
            
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



def main():
    print("🚀 OpenAI Codex 账号管理器")
    print(f"📁 配置存储: {Path(__file__).parent / 'codex-config'}")
    
    manager = CodexAccountManager()
    
    while True:
        print("\n" + "=" * 50)
        print("🚀 OpenAI Codex 账号管理器")
        print("=" * 50)
        print("1. 保存当前账号配置")
        print("2. 从配置内容添加账号")
        print("3. 列出所有账号")
        print("4. 切换账号")
        print("5. 删除账号配置")
        print("6. 显示当前账号")
        print("7. 刷新当前账号用量（从 session）")
        print("8. 启动自动刷新当前账号用量（每5秒）")
        print("0. 退出")
        print("-" * 50)
        
        try:
            choice = input("请选择操作 (0-8): ").strip()
        except KeyboardInterrupt:
            print("\n👋 再见！")
            break
        
        if choice == "1":
            try:
                account_name = input("请输入账号名称: ").strip()
                if account_name:
                    manager.save_current_account(account_name)
                else:
                    print("❌ 账号名称不能为空")
            except KeyboardInterrupt:
                print("\n⚠️ 操作取消")
                continue
        
        elif choice == "2":
            try:
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
                except KeyboardInterrupt:
                    print("\n⚠️ 操作取消")
                    continue
                
                config_text = '\n'.join(config_lines).strip()
                if config_text:
                    manager.save_account_from_config(account_name, config_text)
                else:
                    print("❌ 配置内容不能为空")
            except KeyboardInterrupt:
                print("\n⚠️ 操作取消")
                continue
        
        elif choice == "3":
            manager.list_accounts()
        
        elif choice == "4":
            accounts = manager.list_accounts()
            if accounts:
                try:
                    account_name = input("请输入要切换的账号名称: ").strip()
                    if account_name in accounts:
                        manager.switch_account(account_name)
                    else:
                        print("❌ 账号名称不存在")
                except KeyboardInterrupt:
                    print("\n⚠️ 操作取消")
                    continue
        
        elif choice == "5":
            accounts = manager.list_accounts()
            if accounts:
                try:
                    account_name = input("请输入要删除的账号名称: ").strip()
                    if account_name in accounts:
                        try:
                            confirm = input(f"确认删除账号 '{account_name}' 吗? (y/N): ").strip().lower()
                            if confirm == 'y':
                                manager.delete_account(account_name)
                        except KeyboardInterrupt:
                            print("\n⚠️ 操作取消")
                            continue
                    else:
                        print("❌ 账号名称不存在")
                except KeyboardInterrupt:
                    print("\n⚠️ 操作取消")
                    continue
        
        elif choice == "6":
            manager.show_current_account()
        
        elif choice == "7":
            manager.check_account_usage(force_refresh=True)

        elif choice == "8":
            print("\n🔁 已启动自动刷新。按 Ctrl+C 停止。")
            try:
                while True:
                    # 清屏以回显最新数据而不滚动
                    print("\033c", end="")
                    print("🔁 自动刷新当前账号用量（每5秒）\n")
                    manager.check_account_usage(force_refresh=True)
                    sys.stdout.flush()
                    print("\n⏳ 将在 5 秒后再次刷新（Ctrl+C 停止）")
                    time.sleep(5)
            except KeyboardInterrupt:
                print("\n⏹️ 自动刷新已停止")
                continue
        
        elif choice == "0":
            print("👋 再见!")
            break
        
        else:
            print("❌ 无效选择，请重试")


if __name__ == "__main__":
    main()
