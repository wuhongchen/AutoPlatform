#!/usr/bin/env python3
"""
AutoPlatform 管理后台启动脚本
"""
import argparse
from app.api.server import run_server
from app.config import get_settings

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AutoPlatform Admin Web")
    parser.add_argument("--host", default="127.0.0.1", help="监听地址")
    parser.add_argument("--port", type=int, default=8701, help="监听端口")
    parser.add_argument("--debug", action="store_true", help="调试模式")
    
    args = parser.parse_args()
    
    settings = get_settings()
    db_path = settings.data_dir / "db" / "autoplatform.db"

    print(f"🚀 AutoPlatform 管理后台启动中...")
    print(f"📍 访问地址: http://{args.host}:{args.port}/")
    print(f"📍 API 地址: http://{args.host}:{args.port}/api")
    print(f"🗄️  数据库: {db_path}")
    print()
    
    run_server(host=args.host, port=args.port, debug=args.debug)
