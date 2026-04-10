# AutoPlatform Makefile
# 简化项目运行命令

.PHONY: help install backend frontend dev build clean

# 默认显示帮助
help:
	@echo "AutoPlatform 项目命令"
	@echo ""
	@echo "可用命令:"
	@echo "  make install    安装前后端所有依赖"
	@echo "  make backend    启动后端 API 服务 (http://127.0.0.1:8701)"
	@echo "  make frontend   启动前端开发服务器 (http://127.0.0.1:5173)"
	@echo "  make dev        同时启动前后端 (开发模式)"
	@echo "  make build      构建前端生产版本"
	@echo "  make clean      清理缓存和临时文件"
	@echo ""
	@echo "或使用 ./run.sh 查看更多选项"

# 安装依赖
install:
	./run.sh install

# 启动后端
backend:
	./run.sh backend

# 启动前端
frontend:
	./run.sh frontend

# 开发模式（前后端同时）
dev:
	./run.sh dev

# 构建前端
build:
	./run.sh build

# 清理缓存
clean:
	./run.sh clean
