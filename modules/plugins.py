"""
插件系统 - 提供AI评分、改写和发布功能的插件化实现
"""
import json
import uuid
import threading
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Callable

from modules.workflow_store import WorkflowStore
from modules.ai_caller import UnifiedAICaller
from modules.publisher import WeChatPublisher
from modules.collector import ContentCollector
from config import Config


def _now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _safe_text(value) -> str:
    return str(value or "").strip()


class PluginResult:
    """插件执行结果"""
    def __init__(self, success: bool, message: str = "", data: dict = None):
        self.success = success
        self.message = message
        self.data = data or {}
        self.timestamp = _now_str()
    
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "message": self.message,
            "data": self.data,
            "timestamp": self.timestamp
        }


class BasePlugin(ABC):
    """插件基类"""
    
    def __init__(self, workflow_store: WorkflowStore, account_id: str = "default"):
        self.workflow = workflow_store
        self.account_id = account_id
        self.plugin_type = self.__class__.__name__.replace("Plugin", "").lower()
    
    @abstractmethod
    def execute(self, record_id: str, **kwargs) -> PluginResult:
        """执行插件任务"""
        pass
    
    def _create_task(self, record_id: str, params: dict) -> str:
        """创建任务记录"""
        task_id = str(uuid.uuid4())[:16]
        self.workflow.create_plugin_task(
            record_id=record_id,
            account_id=self.account_id,
            plugin_type=self.plugin_type,
            params=params
        )
        return task_id
    
    def _update_task(self, task_id: str, status: str, result: dict = None, error_msg: str = ""):
        """更新任务状态"""
        self.workflow.update_plugin_task(
            task_id=task_id,
            status=status,
            result=result,
            error_msg=error_msg
        )


class AIScorePlugin(BasePlugin):
    """AI评分插件 - 评估文章爆款潜力"""
    
    def __init__(self, workflow_store: WorkflowStore, account_id: str = "default"):
        super().__init__(workflow_store, account_id)
        self.ai = UnifiedAICaller()
    
    def execute(self, record_id: str, **kwargs) -> PluginResult:
        """执行AI评分"""
        task_id = self._create_task(record_id, kwargs)
        
        try:
            # 获取文章原始内容
            content = self.workflow.get_article_content(record_id, self.account_id)
            if not content:
                # 如果没有内容，先获取灵感记录
                inspiration = self.workflow.get_inspiration(record_id, self.account_id)
                if not inspiration:
                    return PluginResult(False, "Record not found")
                
                # 抓取文章内容
                url = inspiration.get("url", "")
                if not url:
                    return PluginResult(False, "URL not found")
                
                collector = ContentCollector()
                article = collector.collect(url)
                
                # 保存原始内容
                self.workflow.save_article_content(
                    record_id=record_id,
                    account_id=self.account_id,
                    original_html=article.get("content_html", ""),
                    original_text=article.get("content_text", ""),
                    original_json=article
                )
                
                content_text = article.get("content_text", "")
                title = article.get("title", "")
            else:
                content_text = content.get("original_text", "")
                original_data = content.get("original_data", {})
                title = original_data.get("title", "")
            
            if not content_text:
                return PluginResult(False, "Content is empty")
            
            # 调用AI进行评分
            prompt = f"""请对以下文章进行爆款潜力评分分析。

文章标题：{title}

文章内容：
{content_text[:3000]}

请从以下维度分析并给出评分（0-100分）：
1. 选题热度与时效性
2. 标题吸引力
3. 内容价值与深度
4. 传播潜力

输出格式：
- 评分：XX分
- 核心洞察：简要分析文章的亮点
- 所属领域：文章所属分类"""
            
            response = self.ai.analyze(prompt)
            if not response:
                return PluginResult(False, "AI analysis failed")
            
            # 解析评分结果
            score, insight, category = self._parse_analysis(response)
            
            # 更新灵感记录
            inspiration = self.workflow.get_inspiration(record_id, self.account_id)
            if inspiration:
                inspiration["ai_score"] = score
                inspiration["ai_insight"] = insight
                inspiration["category"] = category
                inspiration["status"] = "已评分"
                inspiration["updated_at"] = _now_str()
                self.workflow.upsert_inspiration(inspiration)
            
            result_data = {
                "score": score,
                "insight": insight,
                "category": category,
                "raw_response": response
            }
            
            self._update_task(task_id, "completed", result_data)
            
            return PluginResult(True, f"评分完成: {score}分", result_data)
            
        except Exception as e:
            error_msg = str(e)
            self._update_task(task_id, "failed", error_msg=error_msg)
            return PluginResult(False, f"评分失败: {error_msg}")
    
    def _parse_analysis(self, response: str) -> tuple:
        """解析AI分析结果"""
        score = 0
        insight = ""
        category = ""
        
        # 提取评分
        import re
        score_match = re.search(r'(?:评分|分数|打分)[:\s]*(\d+(?:\.\d+)?)', response)
        if score_match:
            score = float(score_match.group(1))
        
        # 提取核心洞察
        insight_match = re.search(r'(?:核心洞察|洞察|亮点)[:\s]*([^\n]+)', response)
        if insight_match:
            insight = insight_match.group(1).strip()
        
        # 提取分类
        category_match = re.search(r'(?:分类|领域|类别)[:\s]*([^\n]+)', response)
        if category_match:
            category = category_match.group(1).strip()
        
        return score, insight, category


class AIRewritePlugin(BasePlugin):
    """AI改写插件 - 改写文章内容"""
    
    def __init__(self, workflow_store: WorkflowStore, account_id: str = "default"):
        super().__init__(workflow_store, account_id)
        self.ai = UnifiedAICaller()
    
    def execute(self, record_id: str, **kwargs) -> PluginResult:
        """执行AI改写"""
        role = kwargs.get("role", "tech_expert")
        model = kwargs.get("model", "auto")
        
        task_id = self._create_task(record_id, kwargs)
        
        try:
            # 获取文章内容
            content = self.workflow.get_article_content(record_id, self.account_id)
            if not content:
                return PluginResult(False, "Article content not found")
            
            original_data = content.get("original_data", {})
            title = original_data.get("title", "")
            content_text = content.get("original_text", "")
            content_html = content.get("original_html", "")
            
            if not content_text:
                return PluginResult(False, "Content is empty")
            
            # 更新状态为改写中
            inspiration = self.workflow.get_inspiration(record_id, self.account_id)
            if inspiration:
                inspiration["status"] = "改写中"
                inspiration["updated_at"] = _now_str()
                self.workflow.upsert_inspiration(inspiration)
            
            # 调用AI进行改写
            article_data = {
                "title": title,
                "content_raw": content_text,
                "content_html": content_html,
                "images": original_data.get("images", [])
            }
            
            response = self.ai.rewrite(article_data, role_key=role, preferred_model=model if model != "auto" else None)
            if not response:
                # 更新状态为改写失败
                inspiration = self.workflow.get_inspiration(record_id, self.account_id)
                if inspiration:
                    inspiration["status"] = "改写失败"
                    inspiration["updated_at"] = _now_str()
                    self.workflow.upsert_inspiration(inspiration)
                return PluginResult(False, "AI模型全部调用失败，未能完成改写")
            
            # 解析改写结果
            rewritten_title, rewritten_text = self._parse_rewrite(response, title)
            
            # 转换HTML
            rewritten_html = self._text_to_html(rewritten_text)
            
            # 保存改写内容
            self.workflow.save_article_content(
                record_id=record_id,
                account_id=self.account_id,
                original_html=content_html,
                original_text=content_text,
                rewritten_html=rewritten_html,
                rewritten_text=rewritten_text,
                rewritten_data={"title": rewritten_title, "content": rewritten_text}
            )
            
            # 更新灵感记录
            inspiration = self.workflow.get_inspiration(record_id, self.account_id)
            if inspiration:
                inspiration["status"] = "已改写"
                inspiration["title"] = rewritten_title
                inspiration["updated_at"] = _now_str()
                self.workflow.upsert_inspiration(inspiration)
            
            result_data = {
                "title": rewritten_title,
                "content_preview": rewritten_text[:200] + "...",
                "model": model,
                "role": role
            }
            
            self._update_task(task_id, "completed", result_data)
            
            return PluginResult(True, f"改写完成: {rewritten_title}", result_data)
            
        except Exception as e:
            error_msg = str(e)
            self._update_task(task_id, "failed", error_msg=error_msg)
            # 更新状态为改写失败
            inspiration = self.workflow.get_inspiration(record_id, self.account_id)
            if inspiration:
                inspiration["status"] = "改写失败"
                inspiration["updated_at"] = _now_str()
                self.workflow.upsert_inspiration(inspiration)
            return PluginResult(False, f"改写失败: {error_msg}")
    
    def _parse_rewrite(self, response, default_title: str) -> tuple:
        """解析改写结果"""
        # response 可能是字典或字符串
        if isinstance(response, dict):
            title = response.get("title", default_title)
            content = response.get("content", "") or response.get("content_html", "")
            return title, content
        
        # 如果是字符串，提取标题（假设第一行是标题）
        lines = response.strip().split('\n')
        title = default_title
        content = response
        
        if len(lines) > 1:
            first_line = lines[0].strip()
            # 如果第一行较短且没有标点，认为是标题
            if len(first_line) < 50 and first_line and not first_line.endswith(('。', '，', '！', '？', '.', ',')):
                title = first_line.lstrip('#').strip()
                content = '\n'.join(lines[1:]).strip()
        
        return title, content
    
    def _text_to_html(self, text: str) -> str:
        """将文本转换为简单HTML"""
        # 处理标题
        html = text
        html = html.replace('\n\n', '</p><p>')
        html = html.replace('\n', '<br>')
        html = f'<p>{html}</p>'
        
        # 处理Markdown标题
        import re
        html = re.sub(r'<p>#{1,6}\s+(.+?)</p>', r'<h2>\1</h2>', html)
        
        return html


class PublishPlugin(BasePlugin):
    """发布插件 - 发布到微信公众号"""
    
    def __init__(self, workflow_store: WorkflowStore, account_id: str = "default"):
        super().__init__(workflow_store, account_id)
        self.publisher = WeChatPublisher(
            appid=Config.WECHAT_APPID,
            secret=Config.WECHAT_SECRET,
            author=Config.WECHAT_AUTHOR
        )
    
    def execute(self, record_id: str, **kwargs) -> PluginResult:
        """执行发布"""
        task_id = self._create_task(record_id, kwargs)
        
        try:
            # 获取灵感记录
            inspiration = self.workflow.get_inspiration(record_id, self.account_id)
            if not inspiration:
                return PluginResult(False, "Inspiration record not found")
            
            # 获取文章内容
            content = self.workflow.get_article_content(record_id, self.account_id)
            if not content:
                return PluginResult(False, "Article content not found")
            
            rewritten_data = content.get("rewritten_data", {})
            content_html = rewritten_data.get("content_html", "")
            content_text = rewritten_data.get("content_text", "")
            
            if not content_html:
                return PluginResult(False, "Rewritten content is empty, please rewrite first")
            
            # 更新状态为发布中
            if inspiration:
                inspiration["status"] = "发布中"
                inspiration["updated_at"] = _now_str()
                self.workflow.upsert_inspiration(inspiration)
            
            # 处理封面图
            thumb_media_id = None
            cover_url = inspiration.get("cover_url", "")
            if cover_url:
                thumb_media_id = self.publisher.upload_from_url(cover_url)
            
            # 处理正文图片
            processed_html = self._process_images(content_html)
            
            # 生成摘要
            digest = content_text[:100] + "..." if len(content_text) > 100 else content_text
            
            # 发布草稿
            title = rewritten_data.get("title") or inspiration.get("title", "未命名标题")
            media_id = self.publisher.publish_draft(title, processed_html, digest, thumb_media_id)
            
            if not media_id:
                raise Exception("Failed to create WeChat draft")
            
            # 记录发布日志
            publish_record = {
                "record_id": str(uuid.uuid4())[:16],
                "pipeline_record_id": record_id,
                "account_id": self.account_id,
                "title": title,
                "publish_status": "已发布",
                "result": "草稿创建成功",
                "url": inspiration.get("url", ""),
                "draft_id": media_id,
                "published_at": _now_str(),
            }
            self.workflow.add_publish_log(publish_record)
            
            # 更新灵感记录状态
            if inspiration:
                inspiration["status"] = "已发布"
                inspiration["updated_at"] = _now_str()
                self.workflow.upsert_inspiration(inspiration)
            
            result_data = {
                "media_id": media_id,
                "title": title,
                "thumb_media_id": thumb_media_id
            }
            
            self._update_task(task_id, "completed", result_data)
            
            return PluginResult(True, f"发布成功! Media ID: {media_id}", result_data)
            
        except Exception as e:
            error_msg = str(e)
            self._update_task(task_id, "failed", error_msg=error_msg)
            # 记录失败日志
            try:
                self.workflow.add_publish_log({
                    "record_id": str(uuid.uuid4())[:16],
                    "pipeline_record_id": record_id,
                    "account_id": self.account_id,
                    "title": inspiration.get("title", "未命名标题") if inspiration else "未知",
                    "publish_status": "发布失败",
                    "result": error_msg,
                    "url": inspiration.get("url", "") if inspiration else "",
                    "draft_id": "",
                    "published_at": _now_str(),
                })
            except Exception:
                pass
            
            # 更新状态为发布失败
            inspiration = self.workflow.get_inspiration(record_id, self.account_id)
            if inspiration:
                inspiration["status"] = "发布失败"
                inspiration["updated_at"] = _now_str()
                self.workflow.upsert_inspiration(inspiration)
            return PluginResult(False, f"发布失败: {error_msg}")
    
    def _process_images(self, html: str) -> str:
        """处理文章中的图片"""
        import re
        import requests
        
        img_pattern = r'<img[^>]+src=["\']([^"\']+)["\'][^>]*>'
        
        def replace_image(match):
            src = match.group(1)
            # 跳过已经是微信图片的
            if "mmbiz.qpic.cn" in src or "mmbizurl.cn" in src:
                return match.group(0)
            
            try:
                resp = requests.get(src, timeout=30)
                if resp.status_code == 200:
                    wx_url = self.publisher.upload_article_image(resp.content)
                    if wx_url:
                        return match.group(0).replace(src, wx_url)
            except Exception as e:
                print(f"⚠️ 图片处理失败 {src}: {e}")
            
            return match.group(0)
        
        return re.sub(img_pattern, replace_image, html)


# 插件注册表
PLUGIN_REGISTRY = {
    "ai_score": AIScorePlugin,
    "ai_rewrite": AIRewritePlugin,
    "publish": PublishPlugin,
}


def get_plugin(plugin_type: str, workflow_store: WorkflowStore, account_id: str = "default") -> Optional[BasePlugin]:
    """获取插件实例"""
    plugin_class = PLUGIN_REGISTRY.get(plugin_type)
    if plugin_class:
        return plugin_class(workflow_store, account_id)
    return None


def list_plugins() -> List[dict]:
    """列出所有可用插件"""
    return [
        {"type": key, "name": cls.__doc__.split("-")[0].strip()}
        for key, cls in PLUGIN_REGISTRY.items()
    ]
