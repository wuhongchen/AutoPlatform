#!/usr/bin/env python3
"""
DEPRECATED: 请使用 `python main.py server` 代替
保留此文件以兼容历史调用
"""
import warnings
import sys

warnings.warn(
    "run_admin_web.py is deprecated. Use `python main.py server` instead.",
    DeprecationWarning,
    stacklevel=2
)

if __name__ == "__main__":
    from app.api.server import run_server
    run_server()
