"""
统一日志模块
提供全项目统一的日志配置和 logger 实例
"""

import logging
import os
import sys
from typing import Optional


class ColoredFormatter(logging.Formatter):
    """带颜色的日志格式化器"""

    COLORS = {
        "DEBUG": "\033[36m",      # 青色
        "INFO": "\033[32m",       # 绿色
        "WARNING": "\033[33m",    # 黄色
        "ERROR": "\033[31m",      # 红色
        "CRITICAL": "\033[35m",   # 紫色
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, "")
        record.levelname_colored = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logging(
    level: Optional[str] = None,
    use_colors: bool = True
) -> logging.Logger:
    """
    配置 AutoPlatform 全局日志

    Args:
        level: 日志级别 (DEBUG/INFO/WARNING/ERROR)，默认从环境变量 LOG_LEVEL 读取
        use_colors: 是否在终端输出颜色
    """
    log_level = (level or os.getenv("LOG_LEVEL", "INFO")).upper()
    logger = logging.getLogger("autoplatform")

    # 避免重复添加 handler
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, log_level, logging.INFO))

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)

    if use_colors and sys.stdout.isatty():
        formatter = ColoredFormatter(
            "%(asctime)s | %(levelname_colored)-18s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # 禁止日志向上传播到 root logger（避免重复输出）
    logger.propagate = False

    return logger


# 全局 logger 实例
logger = setup_logging()


def get_logger(name: str) -> logging.Logger:
    """
    获取命名子 logger

    示例：
        from app.core.logger import get_logger
        log = get_logger("ai")
        log.info("rewrite started")
    """
    return logging.getLogger(f"autoplatform.{name}")
