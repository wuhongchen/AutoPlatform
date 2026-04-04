#!/bin/bash

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Ensure common Node.js install paths are available in restricted shells.
export PATH="/usr/local/bin:/opt/homebrew/bin:${PATH}"

calc_requirements_hash() {
    if command -v shasum >/dev/null 2>&1; then
        shasum -a 256 requirements.txt | awk '{print $1}'
    elif command -v sha256sum >/dev/null 2>&1; then
        sha256sum requirements.txt | awk '{print $1}'
    else
        md5 -q requirements.txt 2>/dev/null || cat requirements.txt
    fi
}

calc_frontend_hash() {
    if [ ! -d "frontend/admin" ]; then
        echo ""
        return
    fi

    local files
    files="$(find frontend/admin -type f \
        ! -path 'frontend/admin/node_modules/*' \
        ! -path 'frontend/admin/dist/*' \
        | sort)"

    if [ -z "$files" ]; then
        echo ""
        return
    fi

    if command -v shasum >/dev/null 2>&1; then
        printf '%s\n' "$files" | xargs cat | shasum -a 256 | awk '{print $1}'
    elif command -v sha256sum >/dev/null 2>&1; then
        printf '%s\n' "$files" | xargs cat | sha256sum | awk '{print $1}'
    else
        printf '%s\n' "$files" | xargs cat | md5 -q 2>/dev/null || printf '%s' "$files"
    fi
}

ensure_dependencies() {
    if [ "${OPENCLAW_AUTO_INSTALL:-1}" != "1" ]; then
        echo -e "${YELLOW}ℹ️ 已通过 OPENCLAW_AUTO_INSTALL=0 跳过依赖安装${NC}"
        return
    fi

    local cache_dir=".openclaw_cache"
    local hash_file="${cache_dir}/requirements.sha256"
    mkdir -p "$cache_dir"

    local cur_hash
    local prev_hash
    cur_hash="$(calc_requirements_hash)"
    prev_hash="$(cat "$hash_file" 2>/dev/null || true)"

    if [ "$cur_hash" != "$prev_hash" ]; then
        echo -e "${BLUE}📦 检测到依赖变化，正在安装 Python 依赖...${NC}"
        python3 -m pip install -r requirements.txt
        echo "$cur_hash" > "$hash_file"
        echo -e "${GREEN}✅ 依赖项已就绪${NC}"
    else
        echo -e "${GREEN}✅ 依赖未变化，跳过安装${NC}"
    fi
}

ensure_frontend() {
    if [ ! -f "frontend/admin/package.json" ]; then
        return
    fi

    if [ "${ADMIN_BUILD_FRONTEND:-1}" != "1" ]; then
        echo -e "${YELLOW}ℹ️ 已通过 ADMIN_BUILD_FRONTEND=0 跳过 Vue 前端构建${NC}"
        return
    fi

    local cache_dir=".openclaw_cache"
    local hash_file="${cache_dir}/frontend.sha256"
    mkdir -p "$cache_dir"

    local cur_hash
    local prev_hash
    cur_hash="$(calc_frontend_hash)"
    prev_hash="$(cat "$hash_file" 2>/dev/null || true)"

    local node_bin
    local npm_bin
    node_bin="$(command -v node 2>/dev/null || true)"
    npm_bin="$(command -v npm 2>/dev/null || true)"

    if [ -z "$node_bin" ] && [ -x "/usr/local/bin/node" ]; then
        node_bin="/usr/local/bin/node"
    elif [ -z "$node_bin" ] && [ -x "/opt/homebrew/bin/node" ]; then
        node_bin="/opt/homebrew/bin/node"
    fi

    if [ -z "$npm_bin" ] && [ -x "/usr/local/bin/npm" ]; then
        npm_bin="/usr/local/bin/npm"
    elif [ -z "$npm_bin" ] && [ -x "/opt/homebrew/bin/npm" ]; then
        npm_bin="/opt/homebrew/bin/npm"
    fi

    if [ -z "$node_bin" ] || [ -z "$npm_bin" ]; then
        if [ -f "frontend/admin/dist/index.html" ]; then
            echo -e "${YELLOW}⚠️ 检测到前端源码有变更，但当前环境缺少 node/npm。${NC}"
            echo -e "${YELLOW}ℹ️ 将继续使用现有 dist 构建产物启动后台（不会中断）。${NC}"
            echo -e "${YELLOW}💡 如需应用最新前端改动，请先安装 Node.js 后重新运行。${NC}"
            return
        fi
        echo -e "${RED}❌ 未检测到 node/npm，且不存在 frontend/admin/dist 构建产物。${NC}"
        echo -e "${RED}请先安装 Node.js（含 npm）后重试，或先在有 Node 环境的机器构建 dist。${NC}"
        exit 1
    fi

    pushd frontend/admin >/dev/null

    if [ ! -d "node_modules" ]; then
        echo -e "${BLUE}📦 正在安装 Vue 前端依赖...${NC}"
        "$npm_bin" install
    fi

    if [ "$cur_hash" != "$prev_hash" ] || [ ! -f "dist/index.html" ]; then
        echo -e "${BLUE}🎨 检测到 Vue 前端变更，正在构建管理台前端...${NC}"
        "$npm_bin" run build
        echo "$cur_hash" > "../../${hash_file}"
        echo -e "${GREEN}✅ Vue 前端已构建完成${NC}"
    else
        echo -e "${GREEN}✅ Vue 前端未变化，跳过构建${NC}"
    fi

    popd >/dev/null
}

echo -e "${BLUE}=======================================${NC}"
echo -e "${BLUE}   🧭 AutoInfo 管理系统一键启动入口   ${NC}"
echo -e "${BLUE}=======================================${NC}"

if [ -d "venv" ]; then
    echo -e "${BLUE}🐍 检测到 venv，正在激活虚拟环境...${NC}"
    # shellcheck disable=SC1091
    source venv/bin/activate
fi

if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️ 未检测到 .env 文件，后台仍可启动，但部分飞书/公众号功能会不可用。${NC}"
    echo -e "${YELLOW}📘 配置引导: docs/ENV_SETUP_GUIDE.md${NC}"
fi

ensure_dependencies
ensure_frontend

export ADMIN_HOST="${ADMIN_HOST:-127.0.0.1}"
export ADMIN_PORT="${ADMIN_PORT:-8701}"

DASHBOARD_URL="http://${ADMIN_HOST}:${ADMIN_PORT}"

echo -e "${GREEN}✅ 管理后台准备完成${NC}"
echo -e "${BLUE}🌐 访问地址: ${DASHBOARD_URL}${NC}"
echo -e "${BLUE}🧩 Vue 预览: ${DASHBOARD_URL}/vue${NC}"
echo -e "${BLUE}📘 后台说明: docs/ADMIN_DASHBOARD.md${NC}"
echo -e "${BLUE}🖼️ UI 参考存档: docs/UI_REFERENCES.md${NC}"

auto_open="${ADMIN_OPEN_BROWSER:-1}"
if [ "$auto_open" = "1" ] && command -v open >/dev/null 2>&1; then
    echo -e "${BLUE}🪟 正在尝试自动打开浏览器...${NC}"
    open "$DASHBOARD_URL" >/dev/null 2>&1 || true
fi

echo -e "${BLUE}🚀 正在启动管理后台服务...${NC}"
exec python3 admin_server.py
