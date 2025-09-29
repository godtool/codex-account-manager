#!/bin/bash

# OpenAI Codex 账号管理器快速启动脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🚀 OpenAI Codex 账号管理器"
echo "📁 项目目录: $SCRIPT_DIR"
echo ""

# 检查 Python 环境
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装，请先安装 Python3"
    exit 1
fi

# 显示菜单
while true; do
    echo "请选择操作:"
    echo "1. Web 管理界面 (推荐)"
    echo "2. 命令行管理界面"
    echo "0. 退出"
    echo ""
    read -p "请输入选择 (0-2): " choice
    
    case $choice in
        1)
            echo "正在启动 Web 管理界面..."
            python3 codex_account_manager_web.py
            echo ""
            ;;
        2)
            echo "正在启动命令行管理界面..."
            python3 codex_account_manager.py
            echo ""
            ;;
        0)
            echo "👋 再见!"
            exit 0
            ;;
        *)
            echo "❌ 无效选择，请重试"
            echo ""
            ;;
    esac
done