"""
API 路由模块
按业务领域拆分为 Flask Blueprint
"""
from flask import Blueprint, jsonify


def api_error(message: str, code: str = "BAD_REQUEST", status_code: int = 400):
    """统一 API 错误响应格式（向后兼容：保留 error 字段）"""
    return jsonify({
        "success": False,
        "error": message,
        "code": code,
    }), status_code


# 全局 manager 实例（由 server.py 初始化时注入）
_manager_instance = None


def set_manager_instance(manager):
    """设置全局 manager 实例（测试可通过 monkeypatch 替换）"""
    global _manager_instance
    _manager_instance = manager


def get_manager_instance():
    """获取全局 manager 实例（懒加载兜底）"""
    global _manager_instance
    if _manager_instance is None:
        from app.core import AppManager
        _manager_instance = AppManager()
    return _manager_instance
