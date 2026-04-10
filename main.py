"""
主入口
"""
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.api.server import run_server
from app.cli.main import app as cli_app

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "server":
        run_server()
    else:
        cli_app()
