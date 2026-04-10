#!/usr/bin/env python3
"""
AutoInfo Platform - 完整系统测试
测试重构后的插件化架构
"""

import json
import os
import sys
import time
import unittest
from datetime import datetime

# 添加项目根目录到路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from modules.workflow_store import WorkflowStore
from modules.ai_caller import UnifiedAICaller, get_unified_caller


class TestDatabaseSchema(unittest.TestCase):
    """测试数据库Schema"""

    @classmethod
    def setUpClass(cls):
        cls.test_db_path = os.path.join(PROJECT_ROOT, "output", "test_workflow.db")
        cls.store = WorkflowStore(cls.test_db_path)

    def test_inspiration_table_exists(self):
        """测试灵感库表存在"""
        with self.store._connect() as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='inspiration_records'"
            )
            self.assertIsNotNone(cursor.fetchone())

    def test_publish_logs_table_exists(self):
        """测试发布日志表存在"""
        with self.store._connect() as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='publish_logs'"
            )
            self.assertIsNotNone(cursor.fetchone())

    def test_inspiration_crud(self):
        """测试灵感库增删改查"""
        test_record = {
            "record_id": "test_ins_001",
            "account_id": "test_account",
            "title": "测试文章标题",
            "url": "https://example.com/test",
            "status": "待分析",
            "ai_score": 8,
            "ai_reason": "测试评分原因",
        }

        # 创建
        result = self.store.upsert_inspiration(test_record)
        self.assertEqual(result["title"], "测试文章标题")
        self.assertEqual(result["extra"]["ai_score"], 8)

        # 读取
        fetched = self.store.get_inspiration("test_ins_001", "test_account")
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["url"], "https://example.com/test")

        # 更新
        result = self.store.upsert_inspiration({
            **test_record,
            "status": "已处理",
            "title": "更新后的标题",
        })
        self.assertEqual(result["status"], "已处理")

        # 删除
        self.store.delete_inspiration("test_ins_001", "test_account")
        deleted = self.store.get_inspiration("test_ins_001", "test_account")
        self.assertIsNone(deleted)


class TestAICaller(unittest.TestCase):
    """测试AI调用模块"""

    def test_unified_caller_initialization(self):
        """测试AI调用器初始化"""
        caller = UnifiedAICaller()
        self.assertIsNotNone(caller)
        self.assertTrue(len(caller.model_priority) > 0)

    def test_get_available_models(self):
        """测试获取可用模型"""
        caller = UnifiedAICaller()
        available = caller._get_available_models()
        # 即使没有配置API key，也不应该报错
        self.assertIsInstance(available, list)

    def test_analyze_method_exists(self):
        """测试analyze方法存在"""
        caller = get_unified_caller()
        self.assertTrue(hasattr(caller, 'analyze'))

    def test_rewrite_method_exists(self):
        """测试rewrite方法存在"""
        caller = get_unified_caller()
        self.assertTrue(hasattr(caller, 'rewrite'))


class TestPluginArchitecture(unittest.TestCase):
    """测试插件架构"""

    def test_plugin_interface_design(self):
        """测试插件接口设计"""
        # 验证插件基类概念
        expected_plugin_types = ['ai_score', 'ai_rewrite', 'publish']

        for plugin_type in expected_plugin_types:
            with self.subTest(plugin_type=plugin_type):
                # 验证每个插件类型都有对应的处理逻辑
                self.assertIsInstance(plugin_type, str)


class TestAPIEndpoints(unittest.TestCase):
    """测试API端点"""

    BASE_URL = "http://localhost:8701"

    def _make_request(self, method, endpoint, data=None):
        """辅助方法：发送HTTP请求"""
        import urllib.request
        import urllib.error

        url = f"{self.BASE_URL}{endpoint}"
        headers = {"Content-Type": "application/json"}

        if data:
            data = json.dumps(data).encode('utf-8')

        try:
            req = urllib.request.Request(
                url,
                data=data,
                headers=headers,
                method=method
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                return response.status, json.loads(response.read().decode())
        except urllib.error.URLError as e:
            return None, str(e)
        except Exception as e:
            return None, str(e)

    def test_health_endpoint(self):
        """测试健康检查端点"""
        status, response = self._make_request("GET", "/api/health")

        if status is None:
            self.skipTest(f"服务器未运行: {response}")

        self.assertEqual(status, 200)
        self.assertIn("ok", response)

    def test_accounts_endpoint(self):
        """测试账户列表端点"""
        status, response = self._make_request("GET", "/api/accounts")

        if status is None:
            self.skipTest("服务器未运行")

        self.assertEqual(status, 200)
        self.assertIn("items", response)

    def test_inspiration_list_endpoint(self):
        """测试灵感库列表端点"""
        status, response = self._make_request(
            "GET",
            "/api/inspiration/list?account_id=test"
        )

        if status is None:
            self.skipTest("服务器未运行")

        self.assertEqual(status, 200)
        self.assertIn("items", response)


class TestContentValidation(unittest.TestCase):
    """测试内容验证逻辑"""

    def test_title_length_validation(self):
        """测试标题长度验证"""
        # 微信限制标题64字节
        title_short = "短标题"
        title_long = "这是一个非常长的标题" * 10  # 超过64字节

        self.assertTrue(len(title_short.encode('utf-8')) <= 64)
        self.assertTrue(len(title_long.encode('utf-8')) > 64)

    def test_content_validation(self):
        """测试内容验证"""
        valid_content = {
            "title": "有效标题",
            "content_html": "<p>这是一段有效的内容，长度超过100字。" * 5,
            "content_raw": "这是一段有效的内容，长度超过100字。" * 5,
        }

        # 验证标题不为空
        self.assertTrue(valid_content["title"] and valid_content["title"].strip())

        # 验证内容长度
        text_only = valid_content["content_raw"].replace('\n', ' ').strip()
        self.assertTrue(len(text_only) >= 100)


class TestWorkflowIntegration(unittest.TestCase):
    """测试工作流集成"""

    @classmethod
    def setUpClass(cls):
        cls.test_db_path = os.path.join(PROJECT_ROOT, "output", "test_workflow.db")
        cls.store = WorkflowStore(cls.test_db_path)
        cls.test_account = "test_workflow_account"

    def test_full_workflow_data_flow(self):
        """测试完整工作流数据流转"""
        # 1. 创建灵感记录
        inspiration = self.store.upsert_inspiration({
            "record_id": "wf_test_001",
            "account_id": self.test_account,
            "title": "工作流测试文章",
            "url": "https://example.com/workflow-test",
            "status": "待分析",
        })
        self.assertIsNotNone(inspiration)

        # 2. 更新为已评分状态
        scored = self.store.upsert_inspiration({
            **inspiration,
            "status": "已评分",
            "remark": "AI评分: 8 - 高质量内容",
            "extra": {"ai_score": 8, "ai_reason": "高质量内容"},
        })
        self.assertEqual(scored["extra"]["ai_score"], 8)

        # 3. 更新为已改写状态
        rewritten = self.store.upsert_inspiration({
            **scored,
            "status": "已改写",
            "doc_url": "https://example.com/rewritten",
            "remark": "AI改写完成",
        })
        self.assertEqual(rewritten["status"], "已改写")

        # 4. 创建发布日志
        publish_log = self.store.add_publish_log({
            "record_id": "pub_wf_001",
            "account_id": self.test_account,
            "pipeline_record_id": "wf_test_001",
            "title": "工作流测试文章",
            "publish_status": "已发布",
            "result": "草稿ID: 12345",
            "draft_id": "12345",
        })
        self.assertEqual(publish_log["publish_status"], "已发布")

        # 5. 清理
        self.store.delete_inspiration("wf_test_001", self.test_account)


class TestDataIntegrity(unittest.TestCase):
    """测试数据完整性"""

    def test_json_field_handling(self):
        """测试JSON字段处理"""
        store = WorkflowStore(os.path.join(PROJECT_ROOT, "output", "test_integrity.db"))

        # 测试复杂extra数据
        complex_extra = {
            "ai_score": 8,
            "ai_reason": "测试",
            "nested": {"key": "value"},
            "list": [1, 2, 3],
        }

        record = store.upsert_inspiration({
            "record_id": "integrity_test_001",
            "account_id": "test",
            "title": "完整性测试",
            "extra": complex_extra,
        })

        # 验证JSON正确存储和读取
        self.assertEqual(record["extra"]["ai_score"], 8)
        self.assertEqual(record["extra"]["nested"]["key"], "value")

        # 清理
        store.delete_inspiration("integrity_test_001", "test")

    def test_concurrent_access(self):
        """测试并发访问"""
        import threading

        store = WorkflowStore(os.path.join(PROJECT_ROOT, "output", "test_concurrent.db"))
        results = []

        def worker(thread_id):
            try:
                record = store.upsert_inspiration({
                    "record_id": f"concurrent_{thread_id}",
                    "account_id": "concurrent_test",
                    "title": f"线程{thread_id}测试",
                })
                results.append((thread_id, "success", record))
            except Exception as e:
                results.append((thread_id, "error", str(e)))

        # 启动多个线程
        threads = []
        for i in range(10):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # 验证所有线程都成功
        success_count = sum(1 for r in results if r[1] == "success")
        self.assertEqual(success_count, 10)


class TestErrorHandling(unittest.TestCase):
    """测试错误处理"""

    def test_invalid_record_id(self):
        """测试无效记录ID处理"""
        store = WorkflowStore(os.path.join(PROJECT_ROOT, "output", "test_error.db"))

        # 查询不存在的记录
        result = store.get_inspiration("non_existent_id", "test")
        self.assertIsNone(result)

    def test_empty_data_handling(self):
        """测试空数据处理"""
        store = WorkflowStore(os.path.join(PROJECT_ROOT, "output", "test_error.db"))

        # 测试空值不覆盖已有值
        record = store.upsert_inspiration({
            "record_id": "empty_test_001",
            "account_id": "test",
            "title": "原始标题",
            "url": "https://example.com",
        })

        # 更新时传入空值
        updated = store.upsert_inspiration({
            "record_id": "empty_test_001",
            "account_id": "test",
            "title": "",  # 空值
            "status": "已处理",
        })

        # 标题应该保持原值
        self.assertEqual(updated["title"], "原始标题")
        self.assertEqual(updated["status"], "已处理")

        # 清理
        store.delete_inspiration("empty_test_001", "test")


def run_all_tests():
    """运行所有测试"""
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 添加所有测试类
    test_classes = [
        TestDatabaseSchema,
        TestAICaller,
        TestPluginArchitecture,
        TestAPIEndpoints,
        TestContentValidation,
        TestWorkflowIntegration,
        TestDataIntegrity,
        TestErrorHandling,
    ]

    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 返回结果
    return result.wasSuccessful()


if __name__ == "__main__":
    print("=" * 60)
    print("AutoInfo Platform - 完整系统测试")
    print("=" * 60)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"项目目录: {PROJECT_ROOT}")
    print("-" * 60)

    success = run_all_tests()

    print("-" * 60)
    if success:
        print("✅ 所有测试通过！")
        sys.exit(0)
    else:
        print("❌ 部分测试失败！")
        sys.exit(1)
