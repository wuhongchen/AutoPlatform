"""
基础测试
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import get_settings
from app.services import StorageService, AIService, CollectorService


def test_config():
    """测试配置"""
    settings = get_settings()
    print(f"✓ 配置加载成功")
    print(f"  - 数据库: {settings.database.url}")
    print(f"  - AI模型: {settings.ai.model}")


def test_storage():
    """测试存储"""
    storage = StorageService()
    print("✓ 存储服务初始化成功")
    
    # 测试统计
    stats = storage.get_stats()
    print(f"  - 当前统计: {stats}")


def test_collector():
    """测试采集器"""
    collector = CollectorService()
    print("✓ 采集器初始化成功")


def test_ai():
    """测试AI服务"""
    ai = AIService()
    print("✓ AI服务初始化成功")
    print(f"  - 可用角色: {list(ai.ROLES.keys())}")


def main():
    print("=" * 50)
    print("AutoPlatform 基础测试")
    print("=" * 50)
    
    try:
        test_config()
        test_storage()
        test_collector()
        test_ai()
        print("=" * 50)
        print("✓ 所有测试通过")
        print("=" * 50)
        return 0
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
