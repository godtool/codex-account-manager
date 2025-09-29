#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenAI Codex 账号配置管理器 - Web版本
用于管理和切换多个 OpenAI 账号配置
"""

import json
import shutil
import base64
import webbrowser
from datetime import datetime
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs
from usage_checker import OpenAIUsageChecker
from config_utils import generate_account_name, get_config_paths


class CodexAccountManagerWeb:
    def __init__(self):
        # 使用简化的配置路径
        config = get_config_paths()
        self.codex_dir = config['codex_dir']
        self.auth_file = config['auth_file']
        self.accounts_dir = config['accounts_dir']
        self.system_auth_file = config['system_auth_file']
        
        # 确保目录存在
        self.codex_dir.mkdir(parents=True, exist_ok=True)
        self.accounts_dir.mkdir(parents=True, exist_ok=True)
    
    def extract_email_from_token(self, config):
        """从token中提取邮箱地址"""
        try:
            if not config or not isinstance(config, dict):
                return None
                
            # 首先尝试从id_token中提取
            if 'tokens' in config and 'id_token' in config['tokens']:
                id_token = config['tokens']['id_token']
                if not id_token:
                    return None
                parts = id_token.split('.')
                if len(parts) >= 2:
                    payload = parts[1]
                    padding = 4 - (len(payload) % 4)
                    if padding != 4:
                        payload += '=' * padding
                    
                    try:
                        decoded = base64.b64decode(payload)
                        token_data = json.loads(decoded.decode('utf-8'))
                        if token_data and isinstance(token_data, dict) and 'email' in token_data:
                            return token_data['email']
                    except:
                        pass
            
            # 备用方法：从access_token中提取
            if 'tokens' in config and 'access_token' in config['tokens']:
                access_token = config['tokens']['access_token']
                if not access_token:
                    return None
                parts = access_token.split('.')
                if len(parts) >= 2:
                    payload = parts[1]
                    padding = 4 - (len(payload) % 4)
                    if padding != 4:
                        payload += '=' * padding
                    
                    try:
                        decoded = base64.b64decode(payload)
                        token_data = json.loads(decoded.decode('utf-8'))
                        if (token_data and isinstance(token_data, dict) and 
                            'https://api.openai.com/profile' in token_data):
                            profile = token_data['https://api.openai.com/profile']
                            if profile and isinstance(profile, dict) and 'email' in profile:
                                return profile['email']
                    except:
                        pass
            
            return None
        except Exception:
            return None


    def get_accounts_data(self):
        """获取所有账号数据"""
        accounts = []
        account_files = list(self.accounts_dir.glob("*.json"))
        
        # 获取当前账号邮箱用于标记
        current_email = None
        try:
            if self.system_auth_file.exists():
                with open(self.system_auth_file, 'r', encoding='utf-8') as f:
                    current_config = json.load(f)
                current_email = self.extract_email_from_token(current_config)
        except:
            pass
        
        for account_file in sorted(account_files):
            try:
                with open(account_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                account_name = account_file.stem
                email = config.get('email', self.extract_email_from_token(config) or '未知')
                saved_at = config.get('saved_at', '未知时间')
                
                # 检查是否是当前账号
                is_current = email == current_email if current_email else False
                
                # 获取账号状态
                plan_type = "未知"
                try:
                    if 'tokens' in config and 'access_token' in config['tokens']:
                        access_token = config['tokens']['access_token']
                        parts = access_token.split('.')
                        if len(parts) >= 2:
                            payload = parts[1]
                            padding = 4 - (len(payload) % 4)
                            if padding != 4:
                                payload += '=' * padding
                            decoded = base64.b64decode(payload)
                            token_data = json.loads(decoded.decode('utf-8'))
                            auth_info = token_data.get('https://api.openai.com/auth', {})
                            plan_type = auth_info.get('chatgpt_plan_type', '未知')
                except:
                    pass
                
                # 格式化时间
                try:
                    if saved_at != '未知时间':
                        dt = datetime.fromisoformat(saved_at.replace('Z', '+00:00'))
                        saved_at = dt.strftime('%m-%d %H:%M')
                except:
                    pass
                
                accounts.append({
                    'name': account_name,
                    'email': email,
                    'plan': plan_type,
                    'saved_at': saved_at,
                    'is_current': is_current
                })
                
            except Exception as e:
                print(f"读取 {account_file.name} 失败: {e}")
        
        return accounts

    def quick_save_account(self):
        """快速保存当前账号"""
        try:
            if not self.system_auth_file.exists():
                return {"error": "系统 auth.json 文件不存在"}
            
            with open(self.system_auth_file, 'r', encoding='utf-8') as f:
                current_config = json.load(f)
            
            email = self.extract_email_from_token(current_config)
            if email:
                account_name = generate_account_name(email)
                current_config['saved_at'] = datetime.now().isoformat()
                current_config['account_name'] = account_name
                current_config['email'] = email
                
                account_file = self.accounts_dir / f"{account_name}.json"
                with open(account_file, 'w', encoding='utf-8') as f:
                    json.dump(current_config, f, indent=2, ensure_ascii=False)
                
                return {"success": f"成功保存账号: {account_name} ({email})"}
            else:
                return {"error": "未能从配置中提取邮箱信息"}
                
        except Exception as e:
            return {"error": f"保存失败: {e}"}


    def switch_account(self, account_name):
        """切换到指定账号"""
        try:
            account_file = self.accounts_dir / f"{account_name}.json"
            
            if not account_file.exists():
                return {"error": f"账号配置不存在: {account_name}"}
            
            # 读取目标账号配置
            with open(account_file, 'r', encoding='utf-8') as f:
                target_config = json.load(f)
            
            # 移除管理字段，只保留原始配置
            clean_config = {
                "OPENAI_API_KEY": target_config.get("OPENAI_API_KEY"),
                "tokens": target_config.get("tokens"),
                "last_refresh": target_config.get("last_refresh")
            }
            
            # 直接写入系统 Codex 配置
            self.system_auth_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.system_auth_file, 'w', encoding='utf-8') as f:
                json.dump(clean_config, f, indent=2, ensure_ascii=False)
            
            return {"success": f"成功切换到账号: {account_name}"}
            
        except Exception as e:
            return {"error": f"切换失败: {e}"}

    def delete_account(self, account_name):
        """删除账号配置"""
        try:
            account_file = self.accounts_dir / f"{account_name}.json"
            if account_file.exists():
                account_file.unlink()
                return {"success": f"成功删除账号: {account_name}"}
            else:
                return {"error": f"账号不存在: {account_name}"}
        except Exception as e:
            return {"error": f"删除失败: {e}"}

    def check_account_usage(self, account_name=None):
        """检查账号用量"""
        try:
            # 获取当前账号邮箱
            current_email = None
            try:
                if self.system_auth_file.exists():
                    with open(self.system_auth_file, 'r', encoding='utf-8') as f:
                        current_config = json.load(f)
                    current_email = self.extract_email_from_token(current_config)
            except:
                pass
            
            # 如果指定了账号名称，读取该账号配置
            if account_name:
                account_file = self.accounts_dir / f"{account_name}.json"
                if not account_file.exists():
                    return {"error": f"账号配置不存在: {account_name}"}
                
                with open(account_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # 提取邮箱
                email = config.get('email') or self.extract_email_from_token(config)
                
                # 判断是否是当前账号
                is_current_account = email == current_email if current_email and email else False
            else:
                # 检查当前账号
                if not self.auth_file.exists():
                    return {"error": "当前没有活跃的账号配置"}
                
                with open(self.auth_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # 提取邮箱
                email = self.extract_email_from_token(config)
                is_current_account = True  # 直接查询当前账号
            
            if not email:
                return {"error": "未能提取账号邮箱信息"}
            
            # 创建用量检查器
            checker = OpenAIUsageChecker()
            
            # 所有账号都只从缓存读取，不自动查询session
            cached_data = checker.load_usage_data(email)
            if cached_data:
                summary = {
                    "email": email,
                    "check_time": cached_data.get("check_time", ""),
                    "status": f"success{'(当前账号缓存)' if is_current_account else '(缓存)'}",
                    "usage_data": cached_data.get("token_usage", {}),
                    "rate_limits": cached_data.get("rate_limits", {}),
                    "errors": cached_data.get("errors", []),
                    "from_cache": True
                }
            else:
                if is_current_account:
                    return {"error": "当前账号暂无用量数据，请先用 codex 发送消息后点击「刷新用量」按钮"}
                else:
                    return {"error": f"账号 {email} 没有缓存数据，请先切换到该账号并在codex中发送一条消息后，点击「刷新用量」按钮"}
            
            return {"success": True, "data": summary}
            
        except Exception as e:
            return {"error": f"检查用量失败: {e}"}


    def add_config(self, account_name, config_content):
        """添加配置文件"""
        try:
            config = json.loads(config_content)
            email = self.extract_email_from_token(config)
            
            config['saved_at'] = datetime.now().isoformat()
            config['account_name'] = account_name
            if email:
                config['email'] = email
            
            account_file = self.accounts_dir / f"{account_name}.json"
            with open(account_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            return {"success": f"成功保存账号配置: {account_name}"}
            
        except json.JSONDecodeError:
            return {"error": "配置内容格式错误，请检查JSON格式"}
        except Exception as e:
            return {"error": f"保存失败: {e}"}

    def refresh_current_usage(self):
        """手动刷新当前账号的用量（从session读取并更新缓存）"""
        try:
            if not self.system_auth_file.exists():
                return {"error": "未找到当前账号配置"}
            
            # 获取当前账号邮箱
            with open(self.system_auth_file, 'r', encoding='utf-8') as f:
                current_config = json.load(f)
            
            email = self.extract_email_from_token(current_config)
            if not email:
                return {"error": "未能提取当前账号邮箱信息"}
            
            # 从session读取最新用量数据
            from usage_checker import OpenAIUsageChecker
            checker = OpenAIUsageChecker()
            summary = checker.get_usage_summary(email)
            
            if summary["status"] == "success":
                # 保存到缓存
                cache_data = {
                    "check_time": summary["check_time"],
                    "status": summary["status"],
                    "token_usage": summary.get("token_usage", {}),
                    "rate_limits": summary.get("rate_limits", {}),
                    "errors": summary.get("errors", [])
                }
                checker.save_usage_data(email, cache_data)
                return {"success": f"已刷新账号 {email} 的用量数据"}
            else:
                errors = summary.get("errors", [])
                error_msg = errors[0] if errors else "未知错误"
                return {"error": f"刷新失败: {error_msg}"}
                
        except Exception as e:
            return {"error": f"刷新失败: {e}"}


class WebHandler(BaseHTTPRequestHandler):
    def __init__(self, manager, *args, **kwargs):
        self.manager = manager
        super().__init__(*args, **kwargs)

    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            self.serve_main_page()
        elif self.path == '/api/accounts':
            self.serve_accounts_api()
        elif self.path.startswith('/api/usage/'):
            account_name = self.path.split('/')[-1]
            self.serve_account_usage_api(account_name)
        elif self.path == '/api/refresh_usage':
            self.serve_refresh_usage_api()
        else:
            self.send_error(404)

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode('utf-8')
        
        if self.path == '/api/quick_save':
            result = self.manager.quick_save_account()
            self.send_json_response(result)
        elif self.path == '/api/switch':
            data = parse_qs(post_data)
            account_name = data.get('account_name', [''])[0]
            result = self.manager.switch_account(account_name)
            self.send_json_response(result)
        elif self.path == '/api/delete':
            data = parse_qs(post_data)
            account_name = data.get('account_name', [''])[0]
            result = self.manager.delete_account(account_name)
            self.send_json_response(result)
        elif self.path == '/api/add_config':
            data = parse_qs(post_data)
            account_name = data.get('account_name', [''])[0]
            config_content = data.get('config_content', [''])[0]
            result = self.manager.add_config(account_name, config_content)
            self.send_json_response(result)
        else:
            self.send_error(404)

    def serve_main_page(self):
        html = self.get_main_html()
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))

    def serve_accounts_api(self):
        accounts = self.manager.get_accounts_data()
        self.send_json_response(accounts)

    def serve_account_usage_api(self, account_name):
        result = self.manager.check_account_usage(account_name)
        self.send_json_response(result)
    
    def serve_refresh_usage_api(self):
        result = self.manager.refresh_current_usage()
        self.send_json_response(result)

    def send_json_response(self, data):
        self.send_response(200)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def get_main_html(self):
        return '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Codex 账号管理器</title>
    <style>
        * { 
            margin: 0; 
            padding: 0; 
            box-sizing: border-box; 
        }
        
        :root {
            --bg: #f8fafc;
            --card-bg: #ffffff;
            --text: #1e293b;
            --text-light: #475569;
            --border: #e2e8f0;
            --border-hover: #cbd5e1;
            --shadow: 0 1px 3px rgba(0, 0, 0, 0.1), 0 1px 2px rgba(0, 0, 0, 0.06);
            --shadow-lg: 0 4px 25px rgba(0, 0, 0, 0.1);
            --radius: 12px;
            --primary: #3b82f6;
            --primary-hover: #2563eb;
            --success: #10b981;
            --success-hover: #059669;
            --warning: #f59e0b;
            --warning-hover: #d97706;
            --danger: #ef4444;
            --danger-hover: #dc2626;
            --soft: #f1f5f9;
        }

        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif; 
            background: var(--bg);
            min-height: 100vh;
            color: var(--text);
            line-height: 1.6;
        }
        
        .header { 
            background: var(--card-bg);
            padding: 32px 24px; 
            text-align: center; 
            border-bottom: 1px solid var(--border);
            box-shadow: var(--shadow);
            position: sticky;
            top: 0;
            z-index: 100;
        }
        
        .header h1 {
            font-size: 28px;
            font-weight: 700;
            margin-bottom: 8px;
            background: linear-gradient(135deg, var(--primary), var(--success));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        .header p {
            color: var(--text-light);
            font-size: 16px;
        }
        
        .container { 
            max-width: 1400px; 
            margin: 0 auto; 
            padding: 24px; 
        }
        
        .main-grid {
            display: grid;
            grid-template-columns: 1fr 360px;
            gap: 24px;
            align-items: start;
        }
        
        .card { 
            background: var(--card-bg); 
            border-radius: var(--radius); 
            box-shadow: var(--shadow); 
            border: 1px solid var(--border);
            overflow: hidden;
        }
        
        .card-header { 
            background: var(--soft);
            padding: 20px 24px; 
            font-weight: 600; 
            font-size: 16px;
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .card-body { 
            padding: 24px; 
        }
        
        .accounts-container {
            min-height: 400px;
        }
        
        .toolbar {
            display: flex;
            gap: 12px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }
        
        .accounts-grid { 
            display: grid; 
            gap: 16px; 
        }
        
        .account-card { 
            padding: 20px; 
            border: 2px solid var(--border); 
            border-radius: var(--radius); 
            transition: all 0.2s ease; 
            cursor: pointer;
            background: var(--card-bg);
            position: relative;
            display: grid;
            gap: 12px;
        }
        
        .account-card:hover { 
            border-color: var(--border-hover);
            box-shadow: var(--shadow-lg);
        }
        
        .account-card.selected { 
            border-color: var(--primary);
            box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.1), var(--shadow-lg);
        }
        
        .account-card.current-account {
            border-color: var(--success);
            background: linear-gradient(135deg, rgba(16, 185, 129, 0.05), rgba(16, 185, 129, 0.02));
        }
        
        .account-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
        }
        
        .account-name { 
            font-weight: 700; 
            font-size: 18px;
            color: var(--text);
            margin: 0;
        }
        
        .account-status {
            padding: 4px 8px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .status-current {
            background: var(--success);
            color: white;
        }
        
        .account-info { 
            font-size: 14px; 
            color: var(--text-light);
            display: grid;
            gap: 6px;
        }
        
        .info-row {
            display: flex;
           
        }
        
        .info-label {
            font-weight: 500;
        }
        
        .usage-bar {
            background: var(--soft);
            height: 6px;
            border-radius: 3px;
            overflow: hidden;
            margin: 8px 0;
        }
        
        .usage-fill {
            height: 100%;
            background: linear-gradient(90deg, var(--success), var(--warning));
            border-radius: 3px;
            transition: width 0.3s ease;
        }
        
        .account-actions {
            display: flex;
            gap: 8px;
            margin-top: 12px;
        }
        
        .btn { 
            padding: 8px 16px; 
            border: 2px solid var(--border); 
            border-radius: 8px; 
            cursor: pointer; 
            font-weight: 600; 
            font-size: 14px;
            transition: all 0.2s ease; 
            background: var(--card-bg);
            color: var(--text);
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
            position: relative;
            overflow: hidden;
        }
        
        .btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }
        
        .btn-sm {
            padding: 6px 12px;
            font-size: 13px;
            border-width: 1px;
        }
        
        .btn-primary { 
            border-color: var(--primary);
            color: var(--primary);
        }
        
        .btn-primary:hover:not(:disabled) { 
            background: var(--primary);
            color: white;
        }
        
        .btn-success { 
            border-color: var(--success);
            color: var(--success);
        }
        
        .btn-success:hover:not(:disabled) { 
            background: var(--success);
            color: white;
        }
        
        .btn-warning { 
            border-color: var(--warning);
            color: var(--warning);
        }
        
        .btn-warning:hover:not(:disabled) { 
            background: var(--warning);
            color: white;
        }
        
        .btn-danger { 
            border-color: var(--danger);
            color: var(--danger);
        }
        
        .btn-danger:hover:not(:disabled) { 
            background: var(--danger);
            color: white;
        }
        
        .btn-secondary {
            border-color: var(--border-hover);
            color: var(--text-light);
        }
        
        .btn-secondary:hover:not(:disabled) { 
            background: var(--soft);
            border-color: var(--border);
        }
        
        .sidebar-actions {
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        
        .input-group { 
            margin-bottom: 16px; 
        }
        
        .input-group label { 
            display: block; 
            margin-bottom: 8px; 
            font-weight: 600; 
            color: var(--text);
            font-size: 14px;
        }
        
        .input-group input, 
        .input-group textarea { 
            width: 100%; 
            padding: 12px 16px; 
            border: 2px solid var(--border); 
            border-radius: 8px; 
            font-size: 14px;
            transition: border-color 0.2s;
            background: var(--card-bg);
            resize: vertical;
        }
        
        .input-group input:focus, 
        .input-group textarea:focus {
            outline: none;
            border-color: var(--primary);
        }
        
        .alert { 
            padding: 16px 20px; 
            border-radius: var(--radius); 
            margin: 16px 0; 
            font-weight: 500;
            border: 2px solid;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        
        .alert-success { 
            border-color: var(--success);
            background: rgba(16, 185, 129, 0.1);
            color: var(--success);
        }
        
        .alert-error { 
            border-color: var(--danger);
            background: rgba(239, 68, 68, 0.1);
            color: var(--danger);
        }
        
        .loading-spinner {
            border: 3px solid var(--border);
            border-top: 3px solid var(--primary);
            border-radius: 50%;
            width: 20px;
            height: 20px;
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: var(--text-light);
        }
        
        .empty-state-icon {
            font-size: 48px;
            margin-bottom: 16px;
            opacity: 0.5;
        }
        
        .collapsible {
            border: 1px solid var(--border);
            border-radius: var(--radius);
            margin: 12px 0;
            overflow: hidden;
        }
        
        .collapsible-header {
            background: var(--soft);
            padding: 16px 20px;
            cursor: pointer;
            font-weight: 600;
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: background 0.2s ease;
        }
        
        .collapsible-header:hover {
            background: var(--border);
        }
        
        .collapsible-content {
            padding: 20px;
            border-top: 1px solid var(--border);
            display: none;
        }
        
        .collapsible.open .collapsible-content {
            display: block;
        }
        
        .toast {
            position: fixed;
            top: 24px;
            right: 24px;
            z-index: 1000;
            max-width: 400px;
            padding: 16px 20px;
            border-radius: var(--radius);
            box-shadow: var(--shadow-lg);
            border: 2px solid;
            animation: slideIn 0.3s ease-out;
        }
        
        @keyframes slideIn {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        
        @media (max-width: 1024px) { 
            .main-grid { 
                grid-template-columns: 1fr; 
                gap: 20px;
            }
            
            .container {
                padding: 16px;
            }
            
            .header h1 {
                font-size: 24px;
            }
            
            .toolbar {
                justify-content: center;
            }
        }
        
        @media (max-width: 640px) {
            .card-body {
                padding: 16px;
            }
            
            .account-card {
                padding: 16px;
            }
            
            .toolbar {
                flex-direction: column;
            }
            
            .btn {
                width: 100%;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>Codex 账号管理器</h1>
        <p>智能管理与切换多个 OpenAI 账号配置</p>
    </div>

    <div class="container">
        <div class="main-grid">
            <div class="card accounts-container">
                <div class="card-header">
                    账号列表
                </div>
                <div class="card-body">
                    <div class="toolbar">
                        <button class="btn btn-success" id="quick-save-btn" onclick="quickSave()">
                            快速备份当前账号
                        </button>
                        <button class="btn btn-secondary" onclick="refreshData()">
                            刷新页面
                        </button>
                    </div>
                    <div class="alert" style="background: #f0f9ff; border-color: #0ea5e9; color: #0c4a6e; margin-bottom: 20px;">
                        只能刷新当前账号的用量数据。刷新数据前请先用 codex 发送消息后点击「刷新用量」按钮。
                    </div>
                    <div id="accounts-list" class="accounts-grid">
                        <div class="empty-state">
                            <div class="empty-state-icon"></div>
                            <div>正在加载账号列表...</div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="sidebar-actions">
                <div class="card">
                    <div class="card-header">
                        快速操作
                    </div>
                    <div class="card-body">
                        <div style="display: flex; flex-direction: column; gap: 12px;">
                            <button class="btn btn-warning" onclick="switchAccount()" id="switch-btn">
                                切换账号
                            </button>
                            <button class="btn btn-danger" onclick="deleteAccount()" id="delete-btn">
                                删除账号
                            </button>
                        </div>
                        
                        <div style="margin-top: 16px; padding-top: 16px; border-top: 1px solid var(--border); font-size: 13px; color: var(--text-light);">
                            先选择一个账号来执行操作
                        </div>
                    </div>
                </div>
                
                <div class="collapsible" id="add-config-section">
                    <div class="collapsible-header" onclick="toggleCollapsible('add-config-section')">
                        <span>添加配置文件</span>
                        <span>▼</span>
                    </div>
                    <div class="collapsible-content">
                        <div class="input-group">
                            <label>账号名称:</label>
                            <input type="text" id="config-name" placeholder="输入账号名称">
                        </div>
                        <div class="input-group">
                            <label>配置内容:</label>
                            <textarea id="config-content" rows="6" placeholder="粘贴完整的 auth.json 配置内容"></textarea>
                        </div>
                        <button class="btn btn-success" onclick="addConfig()" style="width: 100%;">
                            保存配置
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <div id="message-area"></div>

    <script>
        let selectedAccount = null;

        // 全局变量
        let isLoading = false;
        
        function showMessage(message, type = 'success') {
            const messageArea = document.getElementById('message-area');
            const icon = type === 'success' ? '[成功]' : '[错误]';
            const alertClass = type === 'success' ? 'alert-success' : 'alert-error';
            
            const toast = document.createElement('div');
            toast.className = `toast ${alertClass}`;
            toast.innerHTML = `${icon} ${message}`;
            
            messageArea.innerHTML = '';
            messageArea.appendChild(toast);
            
            setTimeout(() => {
                toast.style.animation = 'slideIn 0.3s ease-out reverse';
                setTimeout(() => messageArea.removeChild(toast), 300);
            }, 3000);
        }

        function setButtonLoading(buttonId, loading, originalText = '') {
            const button = document.getElementById(buttonId);
            if (!button) return;
            
            if (loading) {
                button.disabled = true;
                button.dataset.originalText = button.innerHTML;
                button.innerHTML = '<div class="loading-spinner"></div> 处理中...';
            } else {
                button.disabled = false;
                button.innerHTML = button.dataset.originalText || originalText;
            }
        }

        function updateActionButtons() {
            const switchBtn = document.getElementById('switch-btn');
            const deleteBtn = document.getElementById('delete-btn');
            
            if (selectedAccount) {
                switchBtn.disabled = false;
                deleteBtn.disabled = false;
                switchBtn.innerHTML = `🔄 切换到 ${selectedAccount}`;
                deleteBtn.innerHTML = `🗑️ 删除 ${selectedAccount}`;
            } else {
                switchBtn.disabled = true;
                deleteBtn.disabled = true;
                switchBtn.innerHTML = '🔄 切换账号';
                deleteBtn.innerHTML = '🗑️ 删除账号';
            }
        }

        async function loadAccounts() {
            if (isLoading) return;
            isLoading = true;
            
            try {
                const container = document.getElementById('accounts-list');
                container.innerHTML = `
                    <div class="empty-state">
                        <div class="loading-spinner"></div>
                        <div style="margin-top: 12px;">正在加载账号列表...</div>
                    </div>
                `;

                const response = await fetch('/api/accounts');
                const accounts = await response.json();
                
                if (accounts.length === 0) {
                    container.innerHTML = `
                        <div class="empty-state">
                            <div class="empty-state-icon"></div>
                            <div>还没有保存的账号配置</div>
                            <button class="btn btn-primary" onclick="toggleCollapsible('add-config-section')" style="margin-top: 16px;">
                                添加第一个账号
                            </button>
                        </div>
                    `;
                    return;
                }

                container.innerHTML = accounts.map(account => `
                    <div class="account-card ${account.is_current ? 'current-account' : ''}" onclick="selectAccount('${account.name}')" data-account="${account.name}">
                        <div class="account-header">
                            <div class="account-name">${account.name}</div>
                            ${account.is_current ? '<div class="account-status status-current">当前</div>' : ''}
                        </div>
                        <div class="account-info">
                            <div class="info-row">
                                <span class="info-label">邮箱：</span>
                                <span>${account.email}</span>
                            </div>
                            <div class="info-row">
                                <span class="info-label">计划：</span>
                                <span>${account.plan}</span>
                            </div>
                            <div class="info-row">
                                <span class="info-label">保存：</span>
                                <span>${account.saved_at}</span>
                            </div>
                        </div>
                        <div class="usage-info" id="usage-${account.name}">
                            <div style="display: flex; align-items: center; gap: 8px; color: var(--text-light); font-size: 12px;">
                                <div class="loading-spinner"></div>
                                <span>正在加载用量...</span>
                            </div>
                        </div>
                        <div class="account-actions">
                            <button class="btn btn-sm btn-warning" onclick="event.stopPropagation(); quickSwitchAccount('${account.name}')">
                                🔄 切换
                            </button>
                            ${account.is_current ? `
                                <button class="btn btn-sm btn-primary" onclick="event.stopPropagation(); refreshCurrentAccountUsage('${account.name}')">
                                    ⚡ 刷新用量
                                </button>
                            ` : `
                                <button class="btn btn-sm btn-danger" onclick="event.stopPropagation(); quickDeleteAccount('${account.name}')">
                                    🗑️ 删除
                                </button>
                            `}
                        </div>
                    </div>
                `).join('');
                
                // 延迟加载用量信息，避免一次性请求过多
                accounts.forEach((account, index) => {
                    setTimeout(() => loadAccountUsage(account.name), index * 200);
                });
                
            } catch (error) {
                const container = document.getElementById('accounts-list');
                container.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon"></div>
                        <div>加载失败: ${error.message}</div>
                        <button class="btn btn-primary" onclick="loadAccounts()" style="margin-top: 16px;">
                            重试
                        </button>
                    </div>
                `;
            } finally {
                isLoading = false;
            }
        }

        function selectAccount(accountName) {
            // 清除之前的选中状态
            document.querySelectorAll('.account-card').forEach(item => {
                item.classList.remove('selected');
            });
            
            // 选中当前账号
            const item = document.querySelector(`[data-account="${accountName}"]`);
            if (item) {
                item.classList.add('selected');
                selectedAccount = accountName;
                updateActionButtons();
            }
        }

        function toggleCollapsible(id) {
            const element = document.getElementById(id);
            const isOpen = element.classList.contains('open');
            
            // 关闭所有折叠面板
            document.querySelectorAll('.collapsible').forEach(el => {
                el.classList.remove('open');
                const arrow = el.querySelector('.collapsible-header span:last-child');
                if (arrow) arrow.textContent = '▼';
            });
            
            if (!isOpen) {
                element.classList.add('open');
                const arrow = element.querySelector('.collapsible-header span:last-child');
                if (arrow) arrow.textContent = '▲';
            }
        }

        async function quickSwitchAccount(accountName) {
            if (!confirm(`确定要切换到账号 '${accountName}' 吗？`)) {
                return;
            }
            
            try {
                showMessage(`正在切换到账号 ${accountName}...`, 'success');
                
                const response = await fetch('/api/switch', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                    body: `account_name=${encodeURIComponent(accountName)}`
                });
                const result = await response.json();
                
                if (result.success) {
                    showMessage(`${result.success}`);
                    selectedAccount = null;
                    updateActionButtons();
                    
                    // 立即刷新界面显示新的当前账号
                    setTimeout(async () => {
                        await loadAccounts();
                        showMessage(`已切换到账号 ${accountName}，请用 codex 发送消息后刷新用量`);
                    }, 1000);
                } else {
                    showMessage(result.error, 'error');
                }
            } catch (error) {
                showMessage('网络错误: ' + error.message, 'error');
            }
        }

        async function quickDeleteAccount(accountName) {
            if (!confirm(`确定要删除账号 '${accountName}' 吗？\n\n此操作不可恢复！`)) {
                return;
            }
            
            try {
                const response = await fetch('/api/delete', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                    body: `account_name=${encodeURIComponent(accountName)}`
                });
                const result = await response.json();
                
                if (result.success) {
                    showMessage(`${result.success}`);
                    if (selectedAccount === accountName) {
                        selectedAccount = null;
                        updateActionButtons();
                    }
                    await loadAccounts();
                } else {
                    showMessage(result.error, 'error');
                }
            } catch (error) {
                showMessage('网络错误: ' + error.message, 'error');
            }
        }

        async function loadAccountUsage(accountName) {
            const usageElement = document.getElementById(`usage-${accountName}`);
            if (!usageElement) return;

            try {
                const response = await fetch(`/api/usage/${accountName}`);
                const result = await response.json();

                if (result.success) {
                    const summary = result.data;
                    
                    let usageText = '';
                    if (summary.status && summary.status.includes('success')) {
                        let primaryPercent = 0;
                        let secondaryPercent = 0;
                        let primaryResetInfo = '';
                        let secondaryResetInfo = '';
                        let cacheIcon = '';
                        
                        if (summary.from_cache) {
                            cacheIcon = '<span style="color: var(--text-light);">[缓存]</span>';
                        }
                        
                        if (summary.rate_limits) {
                            if (summary.rate_limits.primary) {
                                primaryPercent = parseInt(summary.rate_limits.primary.used_percent) || 0;
                                const resetSeconds = summary.rate_limits.primary.resets_in_seconds;
                                const resetTime = new Date(Date.now() + resetSeconds * 1000);
                                primaryResetInfo = resetTime.toLocaleTimeString('zh-CN', {hour: '2-digit', minute: '2-digit'});
                            }
                            if (summary.rate_limits.secondary) {
                                secondaryPercent = parseInt(summary.rate_limits.secondary.used_percent) || 0;
                                const resetSeconds = summary.rate_limits.secondary.resets_in_seconds;
                                const resetTime = new Date(Date.now() + resetSeconds * 1000);
                                secondaryResetInfo = `${resetTime.toLocaleDateString('zh-CN', {month: '2-digit', day: '2-digit'})} ${resetTime.toLocaleTimeString('zh-CN', {hour: '2-digit', minute: '2-digit'})}`;
                            }
                        }
                        const maxPercent = Math.max(primaryPercent, secondaryPercent);
                        const barColor = maxPercent > 80 ? 'var(--danger)' : maxPercent > 60 ? 'var(--warning)' : 'var(--success)';
                        usageText = `
                            <div style="margin-top: 8px;">
                                <div class="usage-bar">
                                    <div class="usage-fill" style="width: ${maxPercent}%; background: ${barColor};"></div>
                                </div>
                                <div style="font-size: 14px; color: var(--text-light); display: flex; justify-content: space-between;">
                                    <span>5h: ${primaryPercent}% ${primaryResetInfo ? `(${primaryResetInfo}重置)` : ''}</span>
                                    <span>${cacheIcon}</span>
                                </div>
                                <div style="font-size: 14px; color: var(--text-light);">
                                    周: ${secondaryPercent}% ${secondaryResetInfo ? `(${secondaryResetInfo}重置)` : ''}
                                </div>
                            </div>
                        `;
                    } else {
                        usageText = `<div style="color: var(--warning); font-size: 12px; margin-top: 8px;">[查询失败]</div>`;
                    }
                    usageElement.innerHTML = usageText;
                } else {
                    usageElement.innerHTML = `<div style="color: var(--danger); font-size: 12px; margin-top: 8px;">[错误] ${result.error}</div>`;
                }
            } catch (error) {
                usageElement.innerHTML = `<div style="color: var(--danger); font-size: 12px; margin-top: 8px;">[网络错误]</div>`;
            }
        }

        async function quickSave() {
            try {
                setButtonLoading('quick-save-btn', true);
                showMessage('正在备份当前账号...', 'success');
                const response = await fetch('/api/quick_save', { method: 'POST' });
                const result = await response.json();
                if (result.success) {
                    showMessage(`${result.success}`);
                    await loadAccounts();
                } else {
                    showMessage(result.error, 'error');
                }
            } catch (error) {
                showMessage('网络错误: ' + error.message, 'error');
            } finally {
                setButtonLoading('quick-save-btn', false);
            }
        }

        async function switchAccount() {
            if (!selectedAccount) {
                showMessage('请先选择要切换的账号', 'error');
                return;
            }

            if (!confirm(`确定要切换到账号 '${selectedAccount}' 吗？`)) {
                return;
            }

            try {
                setButtonLoading('switch-btn', true);
                showMessage('正在切换账号...', 'success');
                
                const response = await fetch('/api/switch', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                    body: `account_name=${encodeURIComponent(selectedAccount)}`
                });
                const result = await response.json();
                
                if (result.success) {
                    showMessage(`${result.success}`);
                    selectedAccount = null;
                    await loadAccounts();
                    updateActionButtons();
                } else {
                    showMessage(result.error, 'error');
                }
            } catch (error) {
                showMessage('网络错误: ' + error.message, 'error');
            } finally {
                setButtonLoading('switch-btn', false);
            }
        }

        async function deleteAccount() {
            if (!selectedAccount) {
                showMessage('请先选择要删除的账号', 'error');
                return;
            }

            if (!confirm(`确定要删除账号 '${selectedAccount}' 吗？\n\n此操作不可恢复！`)) {
                return;
            }

            try {
                setButtonLoading('delete-btn', true);
                
                const response = await fetch('/api/delete', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                    body: `account_name=${encodeURIComponent(selectedAccount)}`
                });
                const result = await response.json();
                
                if (result.success) {
                    showMessage(`${result.success}`);
                    selectedAccount = null;
                    updateActionButtons();
                    await loadAccounts();
                } else {
                    showMessage(result.error, 'error');
                }
            } catch (error) {
                showMessage('网络错误: ' + error.message, 'error');
            } finally {
                setButtonLoading('delete-btn', false);
            }
        }

        async function addConfig() {
            const accountName = document.getElementById('config-name').value.trim();
            const configContent = document.getElementById('config-content').value.trim();

            if (!accountName || !configContent) {
                showMessage('请输入账号名称和配置内容', 'error');
                return;
            }

            try {
                showMessage('正在保存配置...', 'success');
                
                const response = await fetch('/api/add_config', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                    body: `account_name=${encodeURIComponent(accountName)}&config_content=${encodeURIComponent(configContent)}`
                });
                const result = await response.json();
                
                if (result.success) {
                    showMessage(`${result.success}`);
                    document.getElementById('config-name').value = '';
                    document.getElementById('config-content').value = '';
                    toggleCollapsible('add-config-section'); // 自动关闭面板
                    await loadAccounts();
                } else {
                    showMessage(result.error, 'error');
                }
            } catch (error) {
                showMessage('网络错误: ' + error.message, 'error');
            }
        }

        async function refreshUsage() {
            try {
                setButtonLoading('refresh-usage-btn', true);
                showMessage('正在刷新当前账号用量数据...', 'success');
                
                const response = await fetch('/api/refresh_usage');
                const result = await response.json();
                
                if (result.success) {
                    showMessage(`${result.success}`);
                    // 刷新成功后重新加载账号显示
                    setTimeout(() => {
                        loadAccounts();
                    }, 500);
                } else {
                    showMessage(result.error, 'error');
                }
            } catch (error) {
                showMessage('网络错误: ' + error.message, 'error');
            } finally {
                setButtonLoading('refresh-usage-btn', false);
            }
        }

        async function refreshCurrentAccountUsage(accountName) {
            try {
                showMessage(`正在刷新账号 ${accountName} 的用量数据...`, 'success');
                
                const response = await fetch('/api/refresh_usage');
                const result = await response.json();
                
                if (result.success) {
                    showMessage(`${result.success}`);                    // 刷新成功后重新加载用量显示
                    setTimeout(() => {
                        loadAccountUsage(accountName);
                    }, 500);
                } else {
                    showMessage(result.error, 'error');
                }
                
            } catch (error) {
                showMessage('刷新失败: ' + error.message, 'error');
            }
        }

        function refreshData() {
            if (!isLoading) {
                selectedAccount = null;
                updateActionButtons();
                loadAccounts();
            }
        }

        // 页面加载完成后初始化
        document.addEventListener('DOMContentLoaded', function() {
            updateActionButtons();
            refreshData();
        });

        // 页面获得焦点时刷新数据（用户可能在其他地方修改了配置）
        window.addEventListener('focus', function() {
            refreshData();
        });
    </script>
</body>
</html>'''

    def log_message(self, format, *args):
        # 禁用默认的日志输出
        pass



def create_handler(manager):
    def handler(*args, **kwargs):
        WebHandler(manager, *args, **kwargs)
    return handler


def main():
    manager = CodexAccountManagerWeb()
    
    port = 8890
    server = HTTPServer(('localhost', port), create_handler(manager))
    
    print(f"OpenAI Codex 账号管理器已启动")
    print(f"配置存储: {Path(__file__).parent / 'codex-config'}")
    print(f"请在浏览器中访问: http://localhost:{port}")
    print("按 Ctrl+C 退出")
    
    # 自动打开浏览器
    try:
        webbrowser.open(f'http://localhost:{port}')
    except:
        pass
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 服务已停止")
        server.shutdown()


if __name__ == "__main__":
    main()