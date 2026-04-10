#!/usr/bin/env python3
"""
AutoInfo Platform - 系统诊断工具
检查当前系统状态，识别需要重构的部分
"""

import os
import sys
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def print_section(title):
    """打印分隔线"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def check_file_exists(filepath, description):
    """检查文件是否存在"""
    full_path = PROJECT_ROOT / filepath
    exists = full_path.exists()
    status = "✅" if exists else "❌"
    print(f"  {status} {description}: {filepath}")
    return exists


def check_database_tables():
    """检查数据库表结构"""
    print_section("数据库表结构检查")

    db_path = PROJECT_ROOT / "output" / "workflow.db"
    if not db_path.exists():
        print("  ❌ 数据库文件不存在")
        return

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = [row[0] for row in cursor.fetchall()]

        expected_tables = [
            "inspiration_records",
            "pipeline_records",
            "publish_logs",
        ]

        for table in expected_tables:
            if table in tables:
                # 获取记录数
                cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"  ✅ {table}: {count} 条记录")

                # 获取表结构
                cursor = conn.execute(f"PRAGMA table_info({table})")
                columns = [row[1] for row in cursor.fetchall()]
                print(f"     字段: {', '.join(columns[:5])}...")
            else:
                print(f"  ❌ {table}: 不存在")

        conn.close()
    except Exception as e:
        print(f"  ❌ 数据库检查失败: {e}")


def check_feishu_dependencies():
    """检查飞书依赖"""
    print_section("飞书依赖检查")

    files_to_check = [
        ("core/manager.py", "主管理器"),
        ("core/manager_inspiration.py", "灵感库管理器"),
        ("modules/processor.py", "内容处理器"),
        ("modules/publisher.py", "发布器"),
    ]

    feishu_imports = 0
    for filepath, description in files_to_check:
        full_path = PROJECT_ROOT / filepath
        if full_path.exists():
            content = full_path.read_text(encoding='utf-8')
            feishu_refs = content.count('FeishuBitable') + content.count('feishu.')
            if feishu_refs > 0:
                print(f"  ⚠️  {description} ({filepath}): {feishu_refs} 处飞书引用")
                feishu_imports += 1
            else:
                print(f"  ✅ {description} ({filepath}): 无飞书引用")

    if feishu_imports > 0:
        print(f"\n  📊 共有 {feishu_imports} 个文件需要移除飞书依赖")


def check_ai_caller():
    """检查AI调用模块"""
    print_section("AI调用模块检查")

    ai_caller_path = PROJECT_ROOT / "modules" / "ai_caller.py"
    if not ai_caller_path.exists():
        print("  ❌ ai_caller.py 不存在")
        return

    content = ai_caller_path.read_text(encoding='utf-8')

    # 检查关键方法
    methods = ['rewrite', 'analyze', 'call_with_fallback']
    for method in methods:
        if method in content:
            print(f"  ✅ 方法 {method} 存在")
        else:
            print(f"  ❌ 方法 {method} 缺失")

    # 检查模型配置
    if 'DEFAULT_MODEL_PRIORITY' in content:
        print("  ✅ 模型优先级配置存在")
    else:
        print("  ❌ 模型优先级配置缺失")


def check_frontend_components():
    """检查前端组件"""
    print_section("前端组件检查")

    components_dir = PROJECT_ROOT / "frontend" / "admin" / "src" / "components"

    components = [
        ("InspirationBoard.vue", "灵感库组件"),
        ("PipelineBoard.vue", "流水线组件（应已移除）"),
        ("PublishBoard.vue", "发布管理组件"),
        ("OverviewBoard.vue", "概览组件"),
    ]

    for filename, description in components:
        filepath = components_dir / filename
        if filepath.exists():
            if filename == "PipelineBoard.vue":
                print(f"  ⚠️  {description}: {filename} (需要移除)")
            else:
                print(f"  ✅ {description}: {filename}")
        else:
            if filename == "PipelineBoard.vue":
                print(f"  ✅ {description}: 已移除")
            else:
                print(f"  ❌ {description}: {filename} 不存在")


def check_api_endpoints():
    """检查API端点"""
    print_section("API端点检查")

    admin_server = PROJECT_ROOT / "admin_server.py"
    if not admin_server.exists():
        print("  ❌ admin_server.py 不存在")
        return

    content = admin_server.read_text(encoding='utf-8')

    # 检查关键API
    endpoints = [
        ('/api/health', "健康检查"),
        ('/api/inspiration/list', "灵感库列表"),
        ('/api/inspiration/add', "添加灵感"),
        ('/api/publish/draft', "发布草稿"),
        ('/api/accounts', "账户管理"),
    ]

    for endpoint, description in endpoints:
        if endpoint in content:
            print(f"  ✅ {description}: {endpoint}")
        else:
            print(f"  ❌ {description}: {endpoint} 缺失")


def generate_recommendations():
    """生成重构建议"""
    print_section("重构建议")

    recommendations = [
        ("HIGH", "移除 core/manager.py 中的飞书文档依赖"),
        ("HIGH", "重构 core/manager_inspiration.py 移除飞书Bitable依赖"),
        ("HIGH", "实现 article_contents 表存储文章内容"),
        ("MEDIUM", "实现 plugin_tasks 表跟踪插件执行"),
        ("MEDIUM", "创建 AIScorePlugin 插件类"),
        ("MEDIUM", "创建 AIRewritePlugin 插件类"),
        ("MEDIUM", "创建 PublishPlugin 插件类"),
        ("LOW", "添加 Markdown 导出功能"),
        ("LOW", "完善前端操作按钮回调"),
    ]

    for priority, recommendation in recommendations:
        icon = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(priority, "⚪")
        print(f"  {icon} [{priority}] {recommendation}")


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("  AutoInfo Platform - 系统诊断报告")
    print("=" * 60)

    check_database_tables()
    check_feishu_dependencies()
    check_ai_caller()
    check_frontend_components()
    check_api_endpoints()
    generate_recommendations()

    print_section("诊断完成")
    print("  详细重构计划请查看: REFACTOR_PLAN.md")
    print("  测试脚本请查看: tests/test_full_system.py")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
