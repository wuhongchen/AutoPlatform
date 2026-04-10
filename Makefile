# AutoPlatform Makefile

.PHONY: help install dev-install server cli test clean

help:
	@echo "AutoPlatform 命令快捷方式"
	@echo ""
	@echo "  make install     - 安装依赖"
	@echo "  make dev-install - 安装开发依赖"
	@echo "  make server      - 启动API服务"
	@echo "  make cli         - 进入CLI交互模式"
	@echo "  make test        - 运行测试"
	@echo "  make clean       - 清理临时文件"

install:
	pip install -r requirements.txt

dev-install:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

server:
	python main.py server

cli:
	python -m app.cli.main

test:
	pytest tests/ -v

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	rm -rf .pytest_cache
	rm -rf data/db/*.db
