"""
重构后的 AutoPlatformManager - 移除飞书依赖，使用本地 SQLite + 插件系统
"""
import os
import sys
import time
import uuid
from typing import Dict, List, Optional

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from config import Config
from modules.workflow_store import WorkflowStore
from modules.plugins import AIScorePlugin, AIRewritePlugin, PublishPlugin, get_plugin
from modules.collector import ContentCollector
from modules.publisher import WeChatPublisher


def _now_str() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _safe_text(value) -> str:
    return str(value or "").strip()


class AutoPlatformManager:
    """全自动内容发布管理器 - 无飞书依赖版本"""
    
    def __init__(self, account_id: str = None):
        self.account_id = account_id or (os.getenv("OPENCLAW_ACCOUNT_ID") or "default").strip() or "default"
        self.workflow = WorkflowStore(Config.WORKFLOW_DB)
        self.collector = ContentCollector()
        self.publisher = WeChatPublisher(
            appid=Config.WECHAT_APPID,
            secret=Config.WECHAT_SECRET,
            author=Config.WECHAT_AUTHOR
        )
        
        # 初始化插件
        self.score_plugin = AIScorePlugin(self.workflow, self.account_id)
        self.rewrite_plugin = AIRewritePlugin(self.workflow, self.account_id)
        self.publish_plugin = PublishPlugin(self.workflow, self.account_id)
    
    def run_pipeline_once(self, batch_size: int = 3) -> Dict:
        """执行一次流水线处理"""
        results = {
            "processed": 0,
            "errors": [],
            "tasks": []
        }
        
        # 1. 获取待评分记录
        pending_score = self.workflow.list_inspiration(
            account_id=self.account_id,
            status="待评分",
            limit=batch_size
        )
        
        for item in pending_score:
            try:
                record_id = item.get("record_id")
                result = self.score_plugin.execute(record_id)
                results["tasks"].append({
                    "record_id": record_id,
                    "action": "score",
                    "success": result.success,
                    "message": result.message
                })
                if result.success:
                    results["processed"] += 1
            except Exception as e:
                results["errors"].append(f"Score {item.get('record_id')}: {str(e)}")
        
        # 2. 获取待改写记录
        pending_rewrite = self.workflow.list_inspiration(
            account_id=self.account_id,
            status="待改写",
            limit=batch_size
        )
        
        for item in pending_rewrite:
            try:
                record_id = item.get("record_id")
                result = self.rewrite_plugin.execute(record_id)
                results["tasks"].append({
                    "record_id": record_id,
                    "action": "rewrite",
                    "success": result.success,
                    "message": result.message
                })
                if result.success:
                    results["processed"] += 1
            except Exception as e:
                results["errors"].append(f"Rewrite {item.get('record_id')}: {str(e)}")
        
        # 3. 获取待发布记录
        pending_publish = self.workflow.list_inspiration(
            account_id=self.account_id,
            status="待发布",
            limit=batch_size
        )
        
        for item in pending_publish:
            try:
                record_id = item.get("record_id")
                result = self.publish_plugin.execute(record_id)
                results["tasks"].append({
                    "record_id": record_id,
                    "action": "publish",
                    "success": result.success,
                    "message": result.message
                })
                if result.success:
                    results["processed"] += 1
            except Exception as e:
                results["errors"].append(f"Publish {item.get('record_id')}: {str(e)}")
        
        return results
    
    def add_inspiration(self, url: str, **kwargs) -> Dict:
        """添加灵感"""
        record_id = f"ins_{uuid.uuid4().hex[:16]}"
        
        # 抓取文章
        article = self.collector.collect(url)
        
        # 保存灵感记录
        inspiration = {
            "record_id": record_id,
            "account_id": self.account_id,
            "title": article.get("title", ""),
            "url": url,
            "source_name": kwargs.get("source_name", ""),
            "status": "待评分",
            "ai_score": 0,
            "ai_insight": "",
            "category": "",
        }
        
        self.workflow.upsert_inspiration(inspiration)
        
        # 保存文章内容
        self.workflow.save_article_content(
            record_id=record_id,
            account_id=self.account_id,
            original_html=article.get("content_html", ""),
            original_text=article.get("content_text", ""),
            original_json=article
        )
        
        return {
            "record_id": record_id,
            "title": article.get("title"),
            "status": "待评分"
        }
    
    def score_article(self, record_id: str) -> Dict:
        """评分文章"""
        result = self.score_plugin.execute(record_id)
        return result.to_dict()
    
    def rewrite_article(self, record_id: str, role: str = "tech_expert", model: str = "auto") -> Dict:
        """改写文章"""
        result = self.rewrite_plugin.execute(record_id, role=role, model=model)
        return result.to_dict()
    
    def publish_article(self, record_id: str) -> Dict:
        """发布文章"""
        result = self.publish_plugin.execute(record_id)
        return result.to_dict()
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            "inspiration_counts": self.workflow.inspiration_status_counts(self.account_id),
            "publish_counts": self.workflow.publish_status_counts(self.account_id),
            "total_inspiration": len(self.workflow.list_inspiration(self.account_id, limit=1000)),
            "total_publish": len(self.workflow.list_publish_logs(self.account_id, limit=1000)),
        }


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="AutoPlatform Manager (Refactored)")
    parser.add_argument("action", choices=["pipeline", "add", "score", "rewrite", "publish", "stats"])
    parser.add_argument("--account-id", default=None)
    parser.add_argument("--url", default=None)
    parser.add_argument("--record-id", default=None)
    parser.add_argument("--role", default="tech_expert")
    parser.add_argument("--model", default="auto")
    parser.add_argument("--batch-size", type=int, default=3)
    
    args = parser.parse_args()
    
    manager = AutoPlatformManager(account_id=args.account_id)
    
    if args.action == "pipeline":
        result = manager.run_pipeline_once(batch_size=args.batch_size)
        print(f"Processed: {result['processed']}")
        for task in result["tasks"]:
            print(f"  [{task['action']}] {task['record_id']}: {task['message']}")
    
    elif args.action == "add":
        if not args.url:
            print("Error: --url required")
            return
        result = manager.add_inspiration(args.url)
        print(f"Added: {result['record_id']} - {result['title']}")
    
    elif args.action == "score":
        if not args.record_id:
            print("Error: --record-id required")
            return
        result = manager.score_article(args.record_id)
        print(f"Score: {result['message']}")
    
    elif args.action == "rewrite":
        if not args.record_id:
            print("Error: --record-id required")
            return
        result = manager.rewrite_article(args.record_id, args.role, args.model)
        print(f"Rewrite: {result['message']}")
    
    elif args.action == "publish":
        if not args.record_id:
            print("Error: --record-id required")
            return
        result = manager.publish_article(args.record_id)
        print(f"Publish: {result['message']}")
    
    elif args.action == "stats":
        stats = manager.get_stats()
        print(json.dumps(stats, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
