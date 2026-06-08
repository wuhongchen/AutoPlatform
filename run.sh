#!/bin/bash
#
# AutoPlatform 统一入口脚本
# 支持: 后端服务 / 前端开发 / 完整项目
#

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目路径
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"
VENV_PYTHON="$VENV_DIR/bin/python3"
VENV_PIP="$VENV_DIR/bin/pip"

# 显示帮助
show_help() {
    echo -e "${BLUE}AutoPlatform 启动脚本${NC}"
    echo ""
    echo "用法: ./run.sh [命令] [选项]"
    echo ""
    echo "命令:"
    echo "  backend     启动后端 API 服务 (Flask)"
    echo "  frontend    启动前端开发服务器 (Vite)"
    echo "  dev         同时启动前后端 (开发模式)"
    echo "  build       构建前端生产版本"
    echo "  test        运行自动化测试 (pytest)"
    echo "  smoke       运行关键链路冒烟测试"
    echo "  install     安装所有依赖"
    echo "  clean       清理缓存和临时文件"
    echo "  help        显示帮助信息"
    echo ""
    echo "选项:"
    echo "  --host      指定监听地址 (默认: 127.0.0.1)"
    echo "  --port      指定端口 (后端默认: 8701, 前端默认: 5173)"
    echo ""
    echo "示例:"
    echo "  ./run.sh backend              # 启动后端服务"
    echo "  ./run.sh frontend             # 启动前端开发服务器"
    echo "  ./run.sh dev                  # 同时启动前后端"
    echo "  ./run.sh backend --port 8080  # 后端使用 8080 端口"
}

# 打印带颜色的信息
info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查 Python 环境
check_python() {
    if ! command -v python3 &> /dev/null; then
        error "Python3 未安装"
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    info "Python 版本: $PYTHON_VERSION"
}

# 检查 Node.js 环境
check_node() {
    if ! command -v node &> /dev/null; then
        error "Node.js 未安装"
        exit 1
    fi

    if ! command -v npm &> /dev/null; then
        error "npm 未安装"
        exit 1
    fi
    
    NODE_VERSION=$(node --version)
    info "Node.js 版本: $NODE_VERSION"
}

# 创建虚拟环境
setup_venv() {
    if [ ! -d "$VENV_DIR" ]; then
        info "创建 Python 虚拟环境..."
        python3 -m venv "$VENV_DIR"
    fi
    
    # 确保 pip 是最新的
    if [ -f "$VENV_PYTHON" ]; then
        "$VENV_PYTHON" -m pip install -q --upgrade pip 2>/dev/null || true
    fi
}

# 安装后端依赖
install_backend_deps() {
    info "安装后端依赖..."
    setup_venv
    
    if [ ! -f "$VENV_PYTHON" ]; then
        error "虚拟环境创建失败"
        exit 1
    fi
    
    "$VENV_PYTHON" -m pip install -q -r "$PROJECT_DIR/requirements.txt"
    success "后端依赖安装完成"
}

# 安装前端依赖
install_frontend_deps() {
    info "安装前端依赖..."
    cd "$PROJECT_DIR/frontend"
    
    if [ ! -d "node_modules" ]; then
        npm install
    fi
    
    success "前端依赖安装完成"
}

# 安装所有依赖
install_deps() {
    check_python
    check_node
    install_backend_deps
    install_frontend_deps
    success "所有依赖安装完成"
}

# 释放端口（如果被占用）
free_port() {
    local port="$1"
    local pids
    pids=$(lsof -ti:"$port" 2>/dev/null)
    if [ -n "$pids" ]; then
        warning "端口 $port 被占用，正在释放..."
        echo "$pids" | xargs kill -9 2>/dev/null
        sleep 1
        info "端口 $port 已释放"
    fi
}

# 启动后端服务
start_backend() {
    local host="${HOST:-127.0.0.1}"
    local port="${PORT:-8701}"
    
    info "启动后端服务..."
    info "访问地址: http://$host:$port/admin"
    info "API 地址: http://$host:$port/api"
    
    # 检查并释放端口
    free_port "$port"
    
    # 检查虚拟环境和依赖
    local PYTHON_EXEC="$VENV_PYTHON"
    if [ ! -f "$PYTHON_EXEC" ]; then
        warning "虚拟环境 Python 不存在，尝试系统 python3..."
        PYTHON_EXEC="python3"
    fi
    
    # 检查 flask 是否安装
    if ! "$PYTHON_EXEC" -c "import flask" 2>/dev/null; then
        warning "依赖未安装，正在安装..."
        setup_venv
        install_backend_deps
        PYTHON_EXEC="$VENV_PYTHON"
    fi
    
    cd "$PROJECT_DIR"
    export PYTHONPATH="$PROJECT_DIR:$PYTHONPATH"
    
    success "后端服务已启动"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    "$PYTHON_EXEC" main.py server --host "$host" --port "$port"
}

# 启动前端开发服务器
start_frontend() {
    local port="${PORT:-5173}"
    
    info "启动前端开发服务器..."
    check_node
    
    cd "$PROJECT_DIR/frontend"
    
    if [ ! -d "node_modules" ]; then
        warning "未找到 node_modules，正在安装依赖..."
        npm install
    fi
    
    success "前端开发服务器已启动"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    npm run dev -- --port "$port"
}

# 同时启动前后端 (开发模式)
cleanup_backend() {
    if [ -n "${BACKEND_PID:-}" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
        kill "$BACKEND_PID" 2>/dev/null || true
        wait "$BACKEND_PID" 2>/dev/null || true
    fi
}

start_dev() {
    info "启动开发模式 (前后端)..."
    
    # 启动后端（后台运行）
    HOST=127.0.0.1 PORT=8701 start_backend &
    BACKEND_PID=$!
    
    # 等待后端启动
    sleep 2
    
    # 启动前端
    trap 'cleanup_backend; exit' INT TERM EXIT
    PORT=5173 start_frontend
}

# 构建前端
build_frontend() {
    info "构建前端生产版本..."
    check_node
    
    cd "$PROJECT_DIR/frontend"
    
    if [ ! -d "node_modules" ]; then
        npm install
    fi
    
    npm run build
    
    success "前端构建完成"
    info "构建输出: $PROJECT_DIR/app/static/dist/"
}

# 运行自动化测试
run_tests() {
    info "运行自动化测试..."
    check_python

    # 检查虚拟环境和依赖
    if [ ! -f "$VENV_PYTHON" ]; then
        warning "虚拟环境不存在，正在创建..."
        setup_venv
        install_backend_deps
    fi

    if ! "$VENV_PYTHON" -c "import pytest" 2>/dev/null; then
        warning "未检测到 pytest，正在安装依赖..."
        install_backend_deps
    fi

    cd "$PROJECT_DIR"
    export PYTHONPATH="$PROJECT_DIR:$PYTHONPATH"
    export DEBUG="${DEBUG:-false}"

    "$VENV_PYTHON" -m pytest -q
}

# 运行关键链路冒烟测试
run_smoke_tests() {
    info "运行关键链路冒烟测试..."
    check_python

    if [ ! -f "$VENV_PYTHON" ]; then
        warning "虚拟环境不存在，正在创建..."
        setup_venv
        install_backend_deps
    fi

    if ! "$VENV_PYTHON" -c "import pytest" 2>/dev/null; then
        warning "未检测到 pytest，正在安装依赖..."
        install_backend_deps
    fi

    cd "$PROJECT_DIR"
    export PYTHONPATH="$PROJECT_DIR:$PYTHONPATH"
    export DEBUG="${DEBUG:-false}"

    "$VENV_PYTHON" -m pytest -q \
        tests/test_api_e2e.py::test_health_and_admin_redirect \
        tests/test_api_e2e.py::test_accounts_crud_stats_and_global_stats \
        tests/test_api_e2e.py::test_inspiration_article_templates_publish_and_pipeline
}

# 清理缓存
clean_cache() {
    info "清理缓存和临时文件..."
    
    # 删除 Python 缓存
    find "$PROJECT_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find "$PROJECT_DIR" -type f -name "*.pyc" -delete 2>/dev/null || true
    find "$PROJECT_DIR" -type f -name "*.pyo" -delete 2>/dev/null || true
    
    # 删除前端构建缓存
    rm -rf "$PROJECT_DIR/frontend/dist" 2>/dev/null || true
    rm -rf "$PROJECT_DIR/app/static/dist" 2>/dev/null || true
    
    success "清理完成"
}

# 一键启动（backend + 构建检查）
start_all() {
    info "AutoPlatform 一键启动..."
    check_python
    
    # 检查前端构建产物
    if [ ! -f "$PROJECT_DIR/app/static/dist/index.html" ]; then
        warning "前端未构建，后台 API 仍可访问"
        info "如需构建前端，运行: ./run.sh build"
    fi
    
    start_backend
}

# 解析参数
HOST="127.0.0.1"
PORT=""
COMMAND=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --host)
            if [[ -z "${2:-}" ]]; then
                error "--host 需要一个参数"
                exit 1
            fi
            HOST="$2"
            shift 2
            ;;
        --port)
            if [[ -z "${2:-}" ]]; then
                error "--port 需要一个参数"
                exit 1
            fi
            PORT="$2"
            shift 2
            ;;
        -*)
            error "未知选项: $1"
            show_help
            exit 1
            ;;
        *)
            if [[ -n "$COMMAND" ]]; then
                error "仅支持一个命令，额外参数: $1"
                show_help
                exit 1
            fi
            COMMAND="$1"
            shift
            ;;
    esac
done

# 执行命令
case "${COMMAND:-help}" in
    start)
        start_all
        ;;
    backend)
        check_python
        start_backend
        ;;
    frontend)
        check_node
        start_frontend
        ;;
    dev)
        check_python
        check_node
        start_dev
        ;;
    build)
        build_frontend
        ;;
    test)
        run_tests
        ;;
    smoke)
        run_smoke_tests
        ;;
    install)
        install_deps
        ;;
    clean)
        clean_cache
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        error "未知命令: $COMMAND"
        show_help
        exit 1
        ;;
esac
