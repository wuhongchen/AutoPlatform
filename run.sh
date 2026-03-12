#!/bin/bash

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=======================================${NC}"
echo -e "${BLUE}   🚀 OpenClaw 全自动运营发布工具      ${NC}"
echo -e "${BLUE}=======================================${NC}"

# 1. 检查环境变量
if [ ! -f ".env" ] && [ ! -f "../mp-draft-push/.env" ]; then
    echo -e "${YELLOW}⚠️  警告: 未找到 .env 配置文件，请先配置 AppID 和 Secret。${NC}"
fi

# 2. 检查并安装依赖
if [ ! -d "venv" ]; then
    echo -e "${BLUE}📦 正在检查 Python 依赖...${NC}"
    pip install -r requirements.txt > /dev/null 2>&1 || pip3 install -r requirements.txt > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ 依赖项已就绪${NC}"
    else
        echo -e "${YELLOW}⚠️  自动安装依赖失败，您可以尝试手动运行: pip3 install -r requirements.txt${NC}"
    fi
fi

# 3. 获取文章 URL 及可选参数
ARTICLE_URL=$1
ROLE=$2
MODEL=$3

if [ -z "$ARTICLE_URL" ]; then
    echo -e "${YELLOW}请输入要采集的文章 URL:${NC}"
    read -p "> " ARTICLE_URL
fi

if [ -z "$ARTICLE_URL" ]; then
    echo -e "${RED}❌ 错误: 未提供有效的文章 URL，程序退出。${NC}"
    exit 1
fi

# 4. 执行主程序
echo -e "${BLUE}⚙️  正在启动自动化发布流程...${NC}"
echo -e "${BLUE}🎭 角色: ${ROLE:-tech_expert} | 🧠 模型: ${MODEL:-kimi}${NC}"

python3 core/manager.py "$ARTICLE_URL" "$ROLE" "$MODEL"

if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}=======================================${NC}"
    echo -e "${GREEN}✨ 任务执行成功！请登录公众平台确认草稿箱。${NC}"
    echo -e "${GREEN}=======================================${NC}"
else
    echo -e "\n${RED}‼️  流程执行中遇到错误，请检查日志输出。${NC}"
    echo -e "${YELLOW}提示: 如果是因为模型请求失败，请检查 .env 中的 API Key 是否正确。${NC}"
fi
