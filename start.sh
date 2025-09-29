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
    echo "1. 备份当前账号"
    echo "2. 查看所有账号"
    echo "3. 切换账号"
    echo "4. 查看账号用量"
    echo "5. Web 管理界面"
    echo "6. 完整管理界面"
    echo "0. 退出"
    echo ""
    read -p "请输入选择 (0-6): " choice
    
    case $choice in
        1)
            read -p "请输入账号名称 (回车使用默认): " account_name
            if [ -z "$account_name" ]; then
                python3 backup_current_account.py
            else
                python3 backup_current_account.py "$account_name"
            fi
            echo ""
            ;;
        2)
            python3 switch_account.py
            echo ""
            ;;
        3)
            # 先显示可用账号
            echo "可用账号:"
            python3 switch_account.py
            echo ""
            read -p "请输入要切换的账号名称: " account_name
            if [ -n "$account_name" ]; then
                python3 switch_account.py "$account_name"
            else
                echo "❌ 账号名称不能为空"
            fi
            echo ""
            ;;
        4)
            echo "用量查询选项:"
            echo "a. 当前账号用量"
            echo "b. 指定账号用量"
            echo "c. 所有账号用量"
            echo ""
            read -p "请选择 (a/b/c): " usage_choice
            case $usage_choice in
                a)
                    python3 check_usage.py -d
                    ;;
                b)
                    echo "可用账号:"
                    python3 switch_account.py
                    echo ""
                    read -p "请输入账号名称: " account_name
                    if [ -n "$account_name" ]; then
                        python3 check_usage.py -a "$account_name" -d
                    else
                        echo "❌ 账号名称不能为空"
                    fi
                    ;;
                c)
                    python3 check_usage.py --all
                    ;;
                *)
                    echo "❌ 无效选择"
                    ;;
            esac
            echo ""
            ;;
        5)
            python3 codex_account_manager_web.py
            echo ""
            ;;
        6)
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