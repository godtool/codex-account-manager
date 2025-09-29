#!/usr/bin/env python3
"""
Codex CLI 用量查询模块
支持查询 Codex CLI 的使用情况、剩余额度和重置时间
"""

import json
import os
import glob
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Any

class CodexUsageChecker:
    """Codex CLI 用量检查器"""
    
    def __init__(self, usage_cache_dir=None):
        """初始化用量检查器"""
        self.codex_sessions_dir = Path.home() / ".codex" / "sessions"
        # 用量缓存目录
        if usage_cache_dir:
            self.usage_cache_dir = Path(usage_cache_dir)
        else:
            # 检测是否在项目目录中
            current_dir = Path.cwd()
            if "codex-account-manager" in str(current_dir) or (current_dir / "codex-account-manager").exists():
                project_dir = current_dir if current_dir.name == "codex-account-manager" else current_dir / "codex-account-manager"
                self.usage_cache_dir = project_dir / "codex-config" / "usage_cache"
            else:
                self.usage_cache_dir = Path.home() / ".codex" / "usage_cache"
        
        # 确保缓存目录存在
        self.usage_cache_dir.mkdir(parents=True, exist_ok=True)
        
    def find_latest_session_file(self) -> Optional[Path]:
        """查找最新的有用量数据的 session 文件"""
        if not self.codex_sessions_dir.exists():
            return None
        
        # 查找所有 session 文件
        pattern = str(self.codex_sessions_dir / "**" / "rollout-*.jsonl")
        session_files = glob.glob(pattern, recursive=True)
        
        if not session_files:
            return None
        
        # 按修改时间排序，从最新开始检查
        session_files.sort(key=os.path.getmtime, reverse=True)
        
        # 查找最近的有 token_count 数据的文件
        for session_file in session_files[:20]:  # 只检查最近20个文件
            if self.has_token_count_data(Path(session_file)):
                return Path(session_file)
        
        # 如果都没有找到，返回最新的文件
        return Path(session_files[0]) if session_files else None
    
    def extract_email_from_session(self, session_file: Path) -> Optional[str]:
        """从 session 文件中提取账号邮箱"""
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                # 只读取前几行，查找 session_meta 或其他包含邮箱的信息
                lines = f.readlines()
                for line in lines[:50]:  # 只检查前50行
                    try:
                        data = json.loads(line.strip())
                        # 查找可能包含账号信息的字段
                        if 'payload' in data:
                            payload = data['payload']
                            # 有些 session 可能直接包含 email 信息
                            if 'email' in payload:
                                return payload['email']
                    except json.JSONDecodeError:
                        continue
            return None
        except Exception:
            return None
    
    def has_token_count_data(self, session_file: Path) -> bool:
        """检查 session 文件是否包含 token_count 数据"""
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                # 只读取最后几行来快速检查
                lines = f.readlines()
                for line in reversed(lines[-50:]):  # 检查最后50行
                    try:
                        data = json.loads(line.strip())
                        if data.get('payload', {}).get('type') == 'token_count':
                            return True
                    except json.JSONDecodeError:
                        continue
            return False
        except Exception:
            return False
    
    def refresh_current_usage(self, timeout=30) -> bool:
        """通过执行 codex /status 命令刷新当前账号的用量数据"""
        return self._refresh_usage_subprocess(timeout)
    
    def _refresh_usage_subprocess(self, timeout=30) -> bool:
        """使用 subprocess 的备用方法"""
        try:
            # 创建一个临时脚本来自动化 codex 交互
            script_content = """#!/usr/bin/expect -f
set timeout 30
spawn codex
expect "▌"
send "/status\\r"
expect "▌"
send "\\003"
expect eof
"""
            script_path = Path("/tmp/codex_status.exp")
            with open(script_path, 'w') as f:
                f.write(script_content)
            
            os.chmod(script_path, 0o755)
            
            # 执行脚本
            result = subprocess.run(
                [str(script_path)], 
                timeout=timeout,
                capture_output=True,
                text=True,
                cwd=str(Path.cwd())
            )
            
            # 清理临时脚本
            script_path.unlink(missing_ok=True)
            
            return result.returncode == 0
            
        except Exception as e:
            print(f"使用 subprocess 刷新失败: {e}")
            return False
    
    def parse_session_file(self, session_file: Path) -> Optional[Dict]:
        """解析 session 文件，查找最新的 token_count 事件"""
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # 从后往前查找最新的 token_count 事件
            best_match = None
            for line in reversed(lines):
                try:
                    data = json.loads(line.strip())
                    payload = data.get('payload', {})
                    
                    # 检查是否是 token_count 事件
                    if payload.get('type') == 'token_count':
                        # 优先查找有 rate_limits 的事件
                        if 'rate_limits' in payload:
                            return data
                        # 如果没有找到有 rate_limits 的，至少保存一个有 token_count 的
                        elif best_match is None:
                            best_match = data
                            
                except json.JSONDecodeError:
                    continue
            
            return best_match
            
        except Exception as e:
            print(f"解析 session 文件失败: {e}")
            return None
    
    def save_usage_data(self, email: str, usage_data: Dict[str, Any]) -> bool:
        """保存用量数据到缓存"""
        try:
            if not email:
                return False
            
            # 使用邮箱作为文件名（替换特殊字符）
            safe_email = email.replace('@', '_at_').replace('.', '_').replace('+', '_plus_')
            cache_file = self.usage_cache_dir / f"{safe_email}_usage.json"
            
            # 添加保存时间戳
            cache_data = {
                "email": email,
                "last_updated": datetime.now().isoformat(),
                "usage_data": usage_data
            }
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            print(f"保存用量数据失败: {e}")
            return False
    
    def load_usage_data(self, email: str) -> Optional[Dict[str, Any]]:
        """从缓存加载用量数据"""
        try:
            if not email:
                return None
            
            safe_email = email.replace('@', '_at_').replace('.', '_').replace('+', '_plus_')
            cache_file = self.usage_cache_dir / f"{safe_email}_usage.json"
            
            if not cache_file.exists():
                return None
            
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # 检查数据是否过期（超过24小时认为过期）
            last_updated = datetime.fromisoformat(cache_data.get('last_updated', ''))
            if datetime.now() - last_updated > timedelta(hours=24):
                return None
            
            return cache_data.get('usage_data')
        except Exception:
            return None
    
    def get_usage_summary(self, email: str = None) -> Dict[str, Any]:
        """获取用量摘要（从现有session文件读取）"""
        summary = {
            "check_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": "checking...",
            "session_file": None,
            "token_usage": {},
            "rate_limits": {},
            "errors": [],
            "from_cache": False
        }
        
        # 查找最新的 session 文件
        session_file = self.find_latest_session_file()
        if not session_file:
            summary["errors"].append("未找到 Codex CLI session 文件")
            summary["status"] = "failed"
            return summary
        
        summary["session_file"] = str(session_file)
        
        # 解析 session 文件
        token_data = self.parse_session_file(session_file)
        if not token_data:
            summary["errors"].append("未找到有效的用量数据，请先在当前账号下使用 codex 发送消息")
            summary["status"] = "failed"
            return summary
        
        # 提取数据
        payload = token_data.get('payload', {})
        info = payload.get('info')
        
        if info and isinstance(info, dict) and 'total_token_usage' in info:
            summary["token_usage"] = info['total_token_usage']
        
        if 'rate_limits' in payload:
            summary["rate_limits"] = payload['rate_limits']
        
        summary["status"] = "success"
        
        # 如果提供了邮箱，保存到缓存
        if email and summary["status"] == "success":
            cache_data = {
                "check_time": summary["check_time"],
                "status": summary["status"],
                "session_file": summary["session_file"],
                "token_usage": summary["token_usage"],
                "rate_limits": summary["rate_limits"],
                "errors": summary["errors"]
            }
            self.save_usage_data(email, cache_data)
        
        return summary
    
    def format_usage_summary(self, summary: Dict[str, Any]) -> str:
        """格式化使用情况摘要为可读文本"""
        lines = []
        lines.append(f"Codex CLI 用量查询")
        lines.append(f"查询时间: {summary['check_time']}")
        lines.append(f"状态: {summary['status']}")
        lines.append("-" * 50)
        
        if summary["status"] == "failed":
            lines.append("❌ 查询失败:")
            for error in summary.get("errors", []):
                lines.append(f"  - {error}")
            lines.append("\n💡 提示:")
            lines.append("  - 请确保已经使用过 Codex CLI")
            lines.append("  - 尝试运行 'codex' 命令并发送一条消息")
            lines.append("  - 然后使用 '/status' 命令查看用量")
            return "\n".join(lines)
        
        # Session 文件信息
        if summary.get("session_file"):
            session_path = Path(summary["session_file"])
            lines.append(f"Session 文件: {session_path.name}")
            lines.append(f"文件路径: {session_path.parent}")
        
        # Token 使用情况
        if summary.get("token_usage"):
            usage = summary["token_usage"]
            lines.append("\n📊 Token 使用情况:")
            lines.append(f"  输入 tokens: {usage.get('input_tokens', 0):,}")
            lines.append(f"  缓存 tokens: {usage.get('cached_input_tokens', 0):,}")
            lines.append(f"  输出 tokens: {usage.get('output_tokens', 0):,}")
            lines.append(f"  总计 tokens: {usage.get('total_tokens', 0):,}")
        
        # 速率限制
        if summary.get("rate_limits"):
            limits = summary["rate_limits"]
            lines.append("\n⏰ 速率限制:")
            
            if "primary" in limits:
                primary = limits["primary"]
                used_percent = primary.get("used_percent", 0)
                window_minutes = primary.get("window_minutes", 0)
                resets_in_seconds = primary.get("resets_in_seconds", 0)
                
                # 计算重置时间
                reset_time = datetime.now() + timedelta(seconds=resets_in_seconds)
                reset_str = reset_time.strftime("%H:%M:%S")
                
                # 计算窗口类型
                window_hours = window_minutes / 60
                if window_hours <= 5.5:  # 大约5小时
                    window_type = "5小时窗口"
                else:
                    window_type = "其他窗口"
                
                lines.append(f"  🔄 {window_type}:")
                lines.append(f"    已使用: {used_percent:.1f}%")
                lines.append(f"    重置时间: {reset_str}")
                lines.append(f"    窗口时长: {window_hours:.1f} 小时")
            
            if "secondary" in limits:
                secondary = limits["secondary"]
                used_percent = secondary.get("used_percent", 0)
                window_minutes = secondary.get("window_minutes", 0)
                resets_in_seconds = secondary.get("resets_in_seconds", 0)
                
                # 计算重置时间
                reset_time = datetime.now() + timedelta(seconds=resets_in_seconds)
                reset_str = reset_time.strftime("%m-%d %H:%M")
                
                # 计算窗口类型
                window_hours = window_minutes / 60
                if window_hours >= 150:  # 大约一周
                    window_type = "周限制"
                else:
                    window_type = "其他限制"
                
                lines.append(f"  📅 {window_type}:")
                lines.append(f"    已使用: {used_percent:.1f}%")
                lines.append(f"    重置时间: {reset_str}")
                lines.append(f"    窗口时长: {window_hours:.0f} 小时")
        
        # 使用建议
        lines.append("\n💡 使用建议:")
        if summary.get("rate_limits"):
            primary_used = summary["rate_limits"].get("primary", {}).get("used_percent", 0)
            secondary_used = summary["rate_limits"].get("secondary", {}).get("used_percent", 0)
            
            if primary_used > 80:
                lines.append("  ⚠️  5小时限制即将用尽，建议稍后再使用")
            elif primary_used > 50:
                lines.append("  ⚡ 5小时限制已用过半，注意控制使用量")
            else:
                lines.append("  ✅ 5小时限制充足")
            
            if secondary_used > 80:
                lines.append("  ⚠️  周限制即将用尽，建议等待重置")
            elif secondary_used > 50:
                lines.append("  ⚡ 周限制已用过半，建议合理规划")
            else:
                lines.append("  ✅ 周限制充足")
        
        return "\n".join(lines)


def extract_access_token_from_auth(auth_data: Dict) -> Optional[str]:
    """从认证数据中提取访问令牌（为兼容性保留）"""
    try:
        if "tokens" in auth_data and "access_token" in auth_data["tokens"]:
            return auth_data["tokens"]["access_token"]
    except (KeyError, TypeError):
        pass
    return None


def extract_email_from_auth(auth_data: Dict) -> Optional[str]:
    """从认证数据中提取邮箱地址（为兼容性保留）"""
    try:
        # 尝试从 id_token 中解析邮箱
        import base64
        id_token = auth_data.get("tokens", {}).get("id_token", "")
        if id_token:
            # JWT token 的 payload 部分
            parts = id_token.split(".")
            if len(parts) >= 2:
                # 添加必要的 padding
                payload = parts[1]
                payload += "=" * (4 - len(payload) % 4)
                try:
                    decoded = base64.b64decode(payload)
                    token_data = json.loads(decoded)
                    return token_data.get("email")
                except:
                    pass
    except:
        pass
    return None


# 为了兼容性，保留旧的类名
class OpenAIUsageChecker(CodexUsageChecker):
    """兼容性别名"""
    
    def __init__(self, access_token: str = None, usage_cache_dir=None):
        super().__init__(usage_cache_dir)
        self.access_token = access_token
    
    def get_account_summary(self, email: str = None) -> Dict[str, Any]:
        """获取账号使用情况摘要（兼容性方法）"""
        summary = self.get_usage_summary(email)
        # 转换格式以保持兼容性
        return {
            "email": email or "Codex CLI",
            "check_time": summary["check_time"],
            "status": summary["status"],
            "usage_data": summary.get("token_usage", {}),
            "rate_limits": summary.get("rate_limits", {}),
            "errors": summary.get("errors", []),
            "from_cache": summary.get("from_cache", False)
        }


if __name__ == "__main__":
    # 测试代码
    checker = CodexUsageChecker()
    summary = checker.get_usage_summary()
    formatted = checker.format_usage_summary(summary)
    print(formatted)

