#!/bin/bash
set -e

echo "🚀 开始重启 AutoInfo 服务..."

# 1. 构建前端
echo "📦 构建前端项目..."
cd frontend/admin
npm run build
cd ../..

# 2. 杀死旧进程
echo "🔪 终止旧服务进程..."
pkill -f "admin_server.py" || true
sleep 1

# 3. 启动新服务
echo "🟢 启动新服务..."
nohup python3 admin_server.py > admin_server.log 2>&1 &

echo "✅ 服务重启完成！"
echo "📝 日志文件: admin_server.log"
echo "🌐 访问地址: http://localhost:8701"
