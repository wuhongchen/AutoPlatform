"""
任务执行器
基于 ThreadPoolExecutor 的异步任务执行系统
"""

import asyncio
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Optional

from app.core.logger import get_logger

logger = get_logger("executor")


class TaskExecutor:
    """任务执行器（单例）"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, max_workers: int = 3):
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        self.executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="task_worker"
        )
        self._manager = None
        self._storage = None

    def set_manager(self, manager):
        """设置管理器引用（懒加载，避免循环导入）"""
        self._manager = manager
        self._storage = manager.storage

    def submit(self, task_id: str):
        """提交任务到线程池执行"""
        future = self.executor.submit(self._execute_task, task_id)
        logger.info(f"[executor] task submitted: {task_id}")
        return future

    def _run_async(self, coro):
        """在线程中运行异步协程"""
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    def _execute_task(self, task_id: str):
        """执行单个任务"""
        from app.models import TaskStatus

        task = self._storage.get_task(task_id)
        if not task:
            logger.error(f"[executor] task not found: {task_id}")
            return

        # 已取消的任务不执行
        if task.status == TaskStatus.CANCELLED:
            logger.info(f"[executor] task cancelled, skip: {task_id}")
            return

        # 更新为运行中
        self._storage.update_task(task_id, {
            "status": TaskStatus.RUNNING,
            "started_at": datetime.now(),
            "retry_count": task.retry_count + 1,
        })
        logger.info(f"[executor] task running: {task_id} ({task.name.value})")

        try:
            result = self._dispatch_task(task)
            self._storage.update_task(task_id, {
                "status": TaskStatus.COMPLETED,
                "completed_at": datetime.now(),
                "result": result,
                "error_message": "",
            })
            logger.info(f"[executor] task completed: {task_id}")
        except Exception as e:
            error_msg = str(e)
            tb = traceback.format_exc()
            logger.error(f"[executor] task failed: {task_id}: {error_msg}\n{tb}")

            task = self._storage.get_task(task_id)
            if task and task.retry_count < task.max_retries:
                # 可重试，回到 pending
                self._storage.update_task(task_id, {
                    "status": TaskStatus.PENDING,
                    "error_message": error_msg,
                })
                logger.info(f"[executor] task will retry: {task_id} ({task.retry_count}/{task.max_retries})")
            else:
                # 超过重试次数，标记失败
                self._storage.update_task(task_id, {
                    "status": TaskStatus.FAILED,
                    "completed_at": datetime.now(),
                    "error_message": error_msg,
                })

    def _dispatch_task(self, task):
        """根据任务类型分发到对应的业务方法"""
        name = task.name.value
        payload = task.payload
        account_id = task.account_id

        if name == "collect":
            return self._run_collect(payload, account_id)
        elif name == "rewrite":
            return self._run_rewrite(payload)
        elif name == "publish":
            return self._run_publish(payload)
        elif name == "batch":
            return self._run_batch(payload, account_id)
        else:
            raise ValueError(f"Unknown task name: {name}")

    def _run_collect(self, payload: dict, account_id: str):
        """执行采集任务"""
        result = self._run_async(
            self._manager.collect_inspiration(
                url=payload["url"],
                account_id=account_id or payload.get("account_id", "default"),
            )
        )
        return {"record_id": result.id, "title": result.title}

    def _run_rewrite(self, payload: dict):
        """执行改写任务"""
        result = self._run_async(
            self._manager.rewrite_article(
                article_id=payload["article_id"],
                style=payload.get("style"),
                use_references=payload.get("use_references", True),
                custom_instructions=payload.get("custom_instructions"),
                inspiration_ids=payload.get("inspiration_ids"),
            )
        )
        return {"article_id": result.id, "status": result.status.value}

    def _run_publish(self, payload: dict):
        """执行发布任务"""
        result = self._run_async(
            self._manager.publish_article(
                article_id=payload["article_id"],
                template=payload.get("template", "default"),
            )
        )
        return {
            "article_id": result.id,
            "status": result.status.value,
            "draft_id": result.wechat_draft_id,
        }

    def _run_batch(self, payload: dict, account_id: str):
        """执行批量处理任务"""
        from app.models import ArticleStatus

        articles = self._storage.list_articles(
            account_id=account_id,
            status=ArticleStatus.PENDING.value,
            limit=payload.get("batch_size", 3),
        )

        results = []
        for article in articles:
            try:
                self._run_async(
                    self._manager.rewrite_article(
                        article_id=article.id,
                        style=payload.get("style"),
                    )
                )
                published = self._run_async(
                    self._manager.publish_article(
                        article_id=article.id,
                        template=payload.get("template", "default"),
                    )
                )
                results.append({
                    "article_id": article.id,
                    "status": "success",
                    "draft_id": published.wechat_draft_id,
                })
            except Exception as e:
                results.append({
                    "article_id": article.id,
                    "status": "failed",
                    "error": str(e),
                })

        return {
            "results": results,
            "total": len(articles),
            "success": sum(1 for r in results if r["status"] == "success"),
        }

    def shutdown(self, wait: bool = True):
        """关闭执行器"""
        self.executor.shutdown(wait=wait)
        logger.info("[executor] shutdown")
