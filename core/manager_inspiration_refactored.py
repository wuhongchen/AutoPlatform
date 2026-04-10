"""
重构后的 InspirationManager - 移除飞书依赖，使用本地 SQLite + 插件系统
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
from modules.plugins import AIScorePlugin, get_plugin
from modules.collector import ContentCollector


def _now_str() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _safe_text(value) -> str:
    return str(value or "").strip()


class InspirationManager:
    """
    灵感库管理器 - 无飞书依赖版本
    功能：自动监控并抓取待选文章，利用 AI 评估爆款潜力并打分
    """
    
    def __init__(self, account_id: str = None):
        self.account_id = account_id or (os.getenv("OPENCLAW_ACCOUNT_ID") or "default").strip() or "default"
        self.workflow = WorkflowStore(Config.WORKFLOW_DB)
        self.collector = ContentCollector()
        self.score_plugin = AIScorePlugin(self.workflow, self.account_id)
    
    def run_once(self) -> Dict:
        """执行一个周期的任务"""
        print(f"\n🔄 [灵感库] 任务周期启动...")
        
        results = {
            "analyzed": 0,
            "errors": []
        }
        
        # 1. 处理待分析任务 (状态为空或待评分)
        pending_records = self.workflow.list_inspiration(
            account_id=self.account_id,
            status="待评分",
            limit=50
        )
        
        # 也包括没有状态的新记录
        all_records = self.workflow.list_inspiration(
            account_id=self.account_id,
            limit=100
        )
        
        for record in all_records:
            status = record.get("status", "")
            if status not in ["", "待评分", None]:
                continue
            
            record_id = record.get("record_id")
            url = record.get("url", "")
            
            if not url:
                continue
            
            try:
                print(f"📄 分析文章: {record.get('title', '未命名')[:50]}...")
                
                # 如果没有内容，先抓取
                content = self.workflow.get_article_content(record_id, self.account_id)
                if not content:
                    article = self.collector.collect(url)
                    self.workflow.save_article_content(
                        record_id=record_id,
                        account_id=self.account_id,
                        original_html=article.get("content_html", ""),
                        original_text=article.get("content_text", ""),
                        original_json=article
                    )
                
                # 执行AI评分
                result = self.score_plugin.execute(record_id)
                
                if result.success:
                    print(f"  ✅ 评分完成: {result.data.get('score', 0)}分")
                    results["analyzed"] += 1
                else:
                    print(f"  ❌ 评分失败: {result.message}")
                    results["errors"].append(f"{record_id}: {result.message}")
                
            except Exception as e:
                error_msg = str(e)
                print(f"  ❌ 处理异常: {error_msg}")
                results["errors"].append(f"{record_id}: {error_msg}")
        
        print(f"\n📊 本次分析: {results['analyzed']} 篇, 错误: {len(results['errors'])} 个")
        return results
    
    def add_url(self, url: str, **kwargs) -> Optional[Dict]:
        """
        手动添加 URL 到灵感库
        
        Args:
            url: 文章URL
            **kwargs: 额外信息如 source_name
            
        Returns:
            创建的记录信息
        """
        if not url:
            print("❌ URL 不能为空")
            return None
        
        # 检查是否已存在
        existing = self.workflow.list_inspiration(self.account_id, limit=1000)
        for item in existing:
            if item.get("url") == url:
                print(f"⚠️ URL 已存在: {item.get('record_id')}")
                return item
        
        try:
            # 抓取文章
            print(f"🔍 抓取文章: {url}")
            article = self.collector.collect(url)
            
            record_id = f"ins_{uuid.uuid4().hex[:16]}"
            
            # 保存灵感记录
            inspiration = {
                "record_id": record_id,
                "account_id": self.account_id,
                "title": article.get("title", ""),
                "url": url,
                "source_name": kwargs.get("source_name", "手动添加"),
                "status": "待评分",
                "ai_score": 0,
                "ai_insight": "",
                "category": "",
                "created_at": _now_str(),
                "updated_at": _now_str(),
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
            
            print(f"✅ 已添加: {record_id} - {article.get('title', '未命名')[:50]}")
            
            return inspiration
            
        except Exception as e:
            print(f"❌ 添加失败: {str(e)}")
            return None
    
    def batch_add_urls(self, urls: List[str], **kwargs) -> List[Dict]:
        """批量添加 URL"""
        results = []
        for url in urls:
            if url.strip():
                result = self.add_url(url.strip(), **kwargs)
                if result:
                    results.append(result)
        return results
    
    def sync_from_wechat(self, mp_id: str, pages: int = 1) -> Dict:
        """
        从微信公众号同步文章到灵感库
        注意: 此功能需要微信登录态，建议通过 wechat_ingest_cli.py 完成
        """
        print(f"ℹ️ 微信同步请使用: python3 scripts/wechat_ingest_cli.py --account-id {self.account_id} sync-inspiration --mp-id {mp_id} --limit {pages * 10}")
        return {"message": "请使用 wechat_ingest_cli.py 进行微信同步"}
    
    def get_stats(self) -> Dict:
        """获取灵感库统计"""
        counts = self.workflow.inspiration_status_counts(self.account_id)
        total = sum(counts.values())
        
        return {
            "total": total,
            "by_status": counts,
            "account_id": self.account_id
        }
    
    def retry_failed(self) -> Dict:
        """重试失败的记录"""
        results = {"reset": 0, "errors": []}
        
        # 获取失败的记录
        all_records = self.workflow.list_inspiration(self.account_id, limit=1000)
        
        for record in all_records:
            status = record.get("status", "")
            if status in ["评分失败", "改写失败", "发布失败"]:
                try:
                    # 重置为待评分状态
                    self.workflow.update_inspiration(
                        record_id=record.get("record_id"),
                        status="待评分",
                        updated_at=_now_str()
                    )
                    results["reset"] += 1
                except Exception as e:
                    results["errors"].append(f"{record.get('record_id')}: {str(e)}")
        
        print(f"✅ 已重置 {results['reset']} 条失败记录为待评分")
        return results


def main():
    """命令行入口"""
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description="Inspiration Manager (Refactored)")
    parser.add_argument("action", choices=["run-once", "add", "batch-add", "stats", "retry-failed"])
    parser.add_argument("--account-id", default=None)
    parser.add_argument("--url", default=None)
    parser.add_argument("--urls-file", default=None)
    
    args = parser.parse_args()
    
    manager = InspirationManager(account_id=args.account_id)
    
    if args.action == "run-once":
        result = manager.run_once()
        print(f"\n分析完成: {result['analyzed']} 篇")
    
    elif args.action == "add":
        if not args.url:
            print("Error: --url required")
            return
        result = manager.add_url(args.url)
        if result:
            print(f"Added: {result['record_id']}")
    
    elif args.action == "batch-add":
        if args.urls_file:
            with open(args.urls_file, 'r') as f:
                urls = [line.strip() for line in f if line.strip()]
        elif args.url:
            urls = [u.strip() for u in args.url.split(',')]
        else:
            print("Error: --url or --urls-file required")
            return
        results = manager.batch_add_urls(urls)
        print(f"Added {len(results)} URLs")
    
    elif args.action == "stats":
        stats = manager.get_stats()
        print(json.dumps(stats, indent=2, ensure_ascii=False))
    
    elif args.action == "retry-failed":
        result = manager.retry_failed()
        print(f"Reset {result['reset']} records")


if __name__ == "__main__":
    main()
