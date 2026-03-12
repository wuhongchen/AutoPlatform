#!/bin/bash

# --- 飞书内容灵感库 启动脚本 ---

# 获取脚本所在目录的绝对路径
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# 检查环境变量文件
if [ ! -f ".env" ]; then
    echo "❌ 错误: 找不到 .env 配置文件"
    exit 1
fi

# 检查虚拟环境 (可选，如果用户使用了 venv)
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# 检查依赖 (可选)
# pip install -r requirements.txt

echo "🚀 正在启动 飞书内容灵感库 管理引擎..."
echo "------------------------------------------------"
echo "1. 扫描灵感库中的新 URL 进行 AI 分析"
echo "2. 监听同步状态并流转至发布流水线"
echo "------------------------------------------------"

# 运行主控程序 (已迁移至 core 目录)
python3 -u core/manager_inspiration.py

