#!/usr/bin/env python3
"""
AutoPlatform 统一入口
支持：server / dev / cli
"""
import sys
import os
import argparse
import subprocess
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.logger import get_logger

logger = get_logger("main")


def free_port(port: int):
    """释放被占用的端口（macOS/Linux）"""
    try:
        result = subprocess.run(
            ["lsof", "-ti", f":{port}"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            pids = result.stdout.strip().split("\n")
            for pid in pids:
                pid = pid.strip()
                if pid:
                    logger.warning(f"端口 {port} 被进程 {pid} 占用，正在释放...")
                    os.kill(int(pid), 9)
            time.sleep(0.5)
            logger.info(f"端口 {port} 已释放")
    except FileNotFoundError:
        # lsof 不存在，跳过
        pass
    except Exception as e:
        logger.warning(f"释放端口 {port} 失败: {e}")


def start_server(host="127.0.0.1", port=8701, debug=False):
    """启动 API 服务"""
    from app.api.server import run_server
    free_port(port)
    logger.info(f"Starting server at http://{host}:{port}/")
    run_server(host=host, port=port, debug=debug)


def start_dev():
    """开发模式：同时启动前后端"""
    logger.info("Starting dev mode (backend + frontend)...")

    backend = subprocess.Popen(
        [sys.executable, __file__, "server"],
        cwd=os.path.dirname(os.path.abspath(__file__))
    )

    frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")
    if os.path.exists(os.path.join(frontend_dir, "package.json")):
        frontend = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=frontend_dir
        )
    else:
        logger.warning("Frontend package.json not found, only backend started")
        frontend = None

    try:
        backend.wait()
        if frontend:
            frontend.wait()
    except KeyboardInterrupt:
        logger.info("Shutting down dev mode...")
        backend.terminate()
        if frontend:
            frontend.terminate()


def run_cli():
    """进入 CLI"""
    from app.cli.main import app as cli_app
    cli_app()


def main():
    parser = argparse.ArgumentParser(
        description="AutoPlatform 统一入口",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py server          # 启动 API 服务
  python main.py server --port 8080
  python main.py dev             # 开发模式（前后端同时）
  python main.py cli             # 进入 CLI（默认）
  python main.py account-list    # 直接执行 CLI 命令
        """
    )

    parser.add_argument(
        "command",
        nargs="?",
        default="cli",
        choices=["server", "dev", "cli"],
        help="执行命令 (默认: cli)"
    )
    parser.add_argument("--host", default="127.0.0.1", help="监听地址 (默认: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8701, help="监听端口 (默认: 8701)")
    parser.add_argument("--debug", action="store_true", help="调试模式")

    args, unknown = parser.parse_known_args()

    if args.command == "server":
        start_server(host=args.host, port=args.port, debug=args.debug)
    elif args.command == "dev":
        start_dev()
    else:
        if unknown:
            sys.argv = [sys.argv[0]] + unknown
        run_cli()


if __name__ == "__main__":
    main()
