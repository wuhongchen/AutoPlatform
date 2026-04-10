"""
统一 AI 调用器 (Unified AI Caller)
封装 LLM 调用逻辑，提供自动故障转移，确保改写和评分稳定运行
"""
import os
import requests
import json
import time
import logging
from typing import List, Dict, Optional, Callable
from datetime import datetime

# 配置日志
logger = logging.getLogger("ai_caller")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '[%(asctime)s] [AI] %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def _log_ai_event(event_type: str, details: dict):
    """记录 AI 调用事件"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    details_str = " | ".join([f"{k}={v}" for k, v in details.items()])
    logger.info(f"[{event_type}] {details_str}")


class UnifiedAICaller:
    """
    统一的 AI 调用器，支持多模型自动故障转移
    """

    # 模型优先级列表（按可靠性排序）
    # 注意：ark-code-latest 暂时移除，因该模型/端点配置有问题（返回404）
    DEFAULT_MODEL_PRIORITY = [
        "volcengine",           # 火山方舟通用（豆包 Seed 2.0 Pro）
        "doubao-seed-2-0-pro",  # 豆包 Seed 2.0 Pro（Coding Play）
        "kimi-k2.5",            # Moonshot Kimi K2.5（通过火山方舟）
        "kimi",                 # Moonshot KIMI
        "qwen3.5-plus",         # 阿里百炼
        "bailian",              # 阿里云百炼
    ]

    def __init__(self, model_priority: Optional[List[str]] = None):
        """
        初始化统一 AI 调用器
        :param model_priority: 模型优先级列表，None 使用默认优先级
        """
        from modules.models import MODEL_POOL
        self.model_pool = MODEL_POOL
        self.model_priority = model_priority or self.DEFAULT_MODEL_PRIORITY

    def _get_available_models(self) -> List[str]:
        """获取当前可用的模型列表（有配置 API Key 的）"""
        available = []
        for model_key in self.model_priority:
            cfg = self.model_pool.get(model_key, {})
            api_key = cfg.get("api_key", "")
            endpoint = cfg.get("endpoint", "")
            if api_key and endpoint:
                available.append(model_key)
        return available

    def _call_model(self, model_key: str, messages: List[Dict], temperature: float = 0.7,
                    response_format: Optional[str] = None) -> Optional[str]:
        """
        调用指定模型
        :param model_key: 模型标识
        :param messages: OpenAI 格式的消息列表
        :param temperature: 温度参数
        :param response_format: 响应格式（如 "json_object"）
        :return: 模型返回的文本内容，失败返回 None
        """
        cfg = self.model_pool.get(model_key)
        if not cfg:
            _log_ai_event("MODEL_NOT_FOUND", {"model": model_key})
            print(f"   ⚠️ 模型 {model_key} 未配置")
            return None

        api_key = cfg.get("api_key", "").strip()
        endpoint = cfg.get("endpoint", "").strip()
        model_name = cfg.get("model", "").strip()

        if not api_key or not endpoint:
            _log_ai_event("MODEL_CONFIG_INVALID", {"model": model_key, "has_key": bool(api_key), "has_endpoint": bool(endpoint)})
            print(f"   ⚠️ 模型 {model_key} 缺少 API Key 或 Endpoint")
            return None

        # 记录调用开始
        start_time = time.time()
        prompt_tokens = sum(len(m.get("content", "")) for m in messages) // 4  # 粗略估算
        _log_ai_event("API_CALL_START", {
            "model_key": model_key,
            "model_name": model_name,
            "temperature": temperature,
            "prompt_tokens_est": prompt_tokens
        })

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature
        }

        # 仅对支持的模型添加 response_format
        if response_format and response_format == "json_object":
            # 火山方舟/豆包系列不支持 response_format
            if not any(x in model_name for x in ["doubao", "ark-code"]):
                payload["response_format"] = {"type": "json_object"}

        try:
            print(f"   🔄 尝试模型: {cfg.get('name', model_key)} ({model_name[:30]}...)")
            resp = requests.post(endpoint, headers=headers, json=payload, timeout=300)
            elapsed = time.time() - start_time

            if resp.status_code != 200:
                _log_ai_event("API_CALL_FAILED", {
                    "model": model_key,
                    "status_code": resp.status_code,
                    "elapsed_sec": f"{elapsed:.2f}",
                    "error": resp.text[:100]
                })
                print(f"   ⚠️ 模型 {model_key} HTTP {resp.status_code}: {resp.text[:200]}")
                return None

            result = resp.json()

            if 'choices' not in result or not result['choices']:
                _log_ai_event("API_RESPONSE_INVALID", {
                    "model": model_key,
                    "error": result.get('error', 'no choices')
                })
                print(f"   ⚠️ 模型 {model_key} 响应异常: {result.get('error', '未知错误')}")
                return None

            content = result['choices'][0]['message']['content']
            content_length = len(content)

            # 记录成功
            _log_ai_event("API_CALL_SUCCESS", {
                "model": model_key,
                "elapsed_sec": f"{elapsed:.2f}",
                "response_length": content_length
            })
            print(f"   ✅ 模型 {model_key} 调用成功 ({elapsed:.1f}s, {content_length} chars)")
            return content

        except requests.exceptions.Timeout:
            elapsed = time.time() - start_time
            _log_ai_event("API_CALL_TIMEOUT", {"model": model_key, "elapsed_sec": f"{elapsed:.2f}"})
            print(f"   ⚠️ 模型 {model_key} 请求超时 ({elapsed:.1f}s)")
        except Exception as e:
            elapsed = time.time() - start_time
            _log_ai_event("API_CALL_EXCEPTION", {"model": model_key, "error": str(e)[:100], "elapsed_sec": f"{elapsed:.2f}"})
            print(f"   ⚠️ 模型 {model_key} 异常: {str(e)[:100]}")

        return None

    def call_with_fallback(self, messages: List[Dict], temperature: float = 0.7,
                          response_format: Optional[str] = None,
                          preferred_model: Optional[str] = None,
                          task_type: str = "unknown") -> Optional[str]:
        """
        调用 AI，自动故障转移到可用模型
        :param messages: OpenAI 格式的消息列表
        :param temperature: 温度参数
        :param response_format: 响应格式
        :param preferred_model: 优先使用的模型（会首先尝试）
        :param task_type: 任务类型（用于日志）
        :return: 模型返回的文本内容，全部失败返回 None
        """
        start_time = time.time()
        available_models = self._get_available_models()

        if not available_models:
            _log_ai_event("NO_MODELS_AVAILABLE", {"task_type": task_type})
            print("❌ 没有可用的 AI 模型，请检查 API Key 配置")
            return None

        # 构建尝试列表：优先模型 + 可用模型（去重）
        try_models = []
        if preferred_model and preferred_model in available_models:
            try_models.append(preferred_model)
        for m in available_models:
            if m not in try_models:
                try_models.append(m)

        _log_ai_event("FALLBACK_START", {
            "task_type": task_type,
            "preferred_model": preferred_model,
            "available_models": len(try_models),
            "model_list": ",".join(try_models[:3]) + ("..." if len(try_models) > 3 else "")
        })
        print(f"🤖 AI 调用（任务: {task_type}, 可用模型: {len(try_models)} 个）")

        for idx, model_key in enumerate(try_models):
            result = self._call_model(model_key, messages, temperature, response_format)
            if result is not None:
                elapsed = time.time() - start_time
                _log_ai_event("FALLBACK_SUCCESS", {
                    "task_type": task_type,
                    "success_model": model_key,
                    "attempts": idx + 1,
                    "elapsed_sec": f"{elapsed:.2f}"
                })
                return result

        elapsed = time.time() - start_time
        _log_ai_event("FALLBACK_FAILED", {
            "task_type": task_type,
            "attempts": len(try_models),
            "elapsed_sec": f"{elapsed:.2f}"
        })
        print(f"❌ 所有模型均调用失败 ({elapsed:.1f}s)")
        return None

    def rewrite(self, article_data: Dict, role_key: str = "tech_expert",
                preferred_model: Optional[str] = None) -> Dict:
        """
        统一改写接口
        :param article_data: 文章数据，包含 title, author, content_raw, content_html, images
        :param role_key: 角色标识
        :param preferred_model: 优先使用的模型
        :return: 改写结果字典
        """
        from modules.prompts import ROLES, DEFAULT_ROLE
        import re

        start_time = time.time()
        title = article_data.get('title', '未命名标题')
        content_raw = article_data.get('content_raw', '')
        content_html = article_data.get('content_html', '')
        images = article_data.get('images', [])
        
        # 优先使用 HTML 内容（包含图片）
        content_to_rewrite = content_html if content_html else content_raw
        content_length = len(content_to_rewrite)

        _log_ai_event("REWRITE_START", {
            "title": title[:50],
            "role": role_key,
            "preferred_model": preferred_model,
            "content_length": content_length,
            "has_images": len(images) > 0
        })
        print(f"🤖 [改写] 文章: {title[:50]}... (角色: {role_key}, 字数: {content_length}, 图片: {len(images)}张)")

        role = ROLES.get(role_key, ROLES[DEFAULT_ROLE])

        content_direction = os.getenv("OPENCLAW_CONTENT_DIRECTION", "").strip()
        prompt_direction = os.getenv("OPENCLAW_PROMPT_DIRECTION", "").strip()

        system_prompt = role["system_prompt"]
        
        # 添加图片保留的提示（检查images列表或HTML内容中的img标签）
        has_images = images or '<img' in content_html.lower()
        if has_images:
            system_prompt += (
                "\n\n【图片保留要求】\n"
                "原文中包含图片，改写时请：\n"
                "1. 保留原文中的所有图片引用（<img>标签）\n"
                "2. 根据上下文适当调整图片位置\n"
                "3. 图片说明文字可以优化，但保留图片本身\n"
                "4. 图片路径保持原样，不要修改src属性\n"
            )
        
        if prompt_direction:
            system_prompt += (
                "\n\n【账户提示词方向】\n"
                f"{prompt_direction}\n"
                "请在不偏离事实的前提下优先遵循该方向。"
            )

        user_prompt = (
            f"请改写以下文章：\n"
            f"标题：{title}\n"
            f"作者：{article_data.get('author', '未知作者')}\n"
            f"内容：{content_to_rewrite[:12000]}"
        )
        if content_direction:
            user_prompt += (
                "\n\n【本篇内容方向】\n"
                f"{content_direction}\n"
                "请按该方向调整选题角度、论证重点与表达风格。"
            )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        result = self.call_with_fallback(messages, temperature=0.7, preferred_model=preferred_model, task_type="rewrite")

        elapsed = time.time() - start_time

        if result:
            result_length = len(result)
            _log_ai_event("REWRITE_SUCCESS", {
                "title": title[:50],
                "elapsed_sec": f"{elapsed:.2f}",
                "result_length": result_length
            })
            print(f"✅ [改写成功] {title[:50]}... ({elapsed:.1f}s, 输出: {result_length} chars)")
            return {
                'title': title,
                'content': result,
                'digest': content_raw[:100] + "...",
                'originality': 85,
                'model_used': 'ai_fallback',
                'elapsed_sec': elapsed
            }

        # 全部失败，返回 None 表示失败
        _log_ai_event("REWRITE_FAILED", {
            "title": title[:50],
            "elapsed_sec": f"{elapsed:.2f}"
        })
        print(f"❌ [改写失败] {title[:50]}... 所有模型均调用失败 ({elapsed:.1f}s)")
        return None

    def analyze(self, article_data: Dict, preferred_model: Optional[str] = None) -> Dict:
        """
        统一评分/分析接口
        :param article_data: 文章数据
        :param preferred_model: 优先使用的模型
        :return: 分析结果字典
        """
        start_time = time.time()
        title = article_data.get('title', '未命名标题')
        content_raw = article_data.get('content_raw', '')
        content_length = len(content_raw)

        _log_ai_event("ANALYZE_START", {
            "title": title[:50],
            "preferred_model": preferred_model,
            "content_length": content_length
        })
        print(f"🧠 [评分] 文章: {title[:50]}... (字数: {content_length})")

        prompt = f"""
你是一位顶尖的内容运营专家和爆款选题师。请对以下采集到的文章进行"爆款潜力"评估。

**文章信息:**
标题: {title}
作者: {article_data.get('author', '未知作者')}
内容片段: {content_raw[:2000]}

**分析要求:**
1. **内容评价**: 基于内容的实用性、趣味性、观点独特性、受众共鸣度进行综合评估。
2. **潜力评分 (1-10)**:
   - 9-10分：行业重磅事件、现象级爆款内容
   - 7-8分：优质内容，有明确的受众群体和价值
   - 5-6分：中等质量内容，适合垂直领域受众
   - 1-4分：低质量无价值内容
3. **中文译名**: 如果是英文标题，请提供吸引人的中文标题。
4. **核心洞察**: 简述文章中最有价值的1个观点（100字以内）。
5. **所属领域**: 标记该文章属于哪个领域。

**输出要求**:
必须返回 JSON 格式，包含以下字段:
- score: 数字 (1-10)
- title_zh: 字符串 (中文标题)
- insight: 字符串 (核心洞察)
- domain: 字符串 (所属领域)
- reason: 字符串 (推荐理由)
- rewrite_direction: 字符串 (改写建议)
"""

        messages = [
            {"role": "system", "content": "你是一个专业的内容分析助手，必须只输出严格的JSON格式，不要任何其他文本、解释、markdown包裹。直接输出JSON对象。"},
            {"role": "user", "content": prompt}
        ]

        result = self.call_with_fallback(messages, temperature=0.4,
                                        response_format="json_object",
                                        preferred_model=preferred_model,
                                        task_type="analyze")

        elapsed = time.time() - start_time

        if result:
            try:
                # 清理 Markdown 代码块
                if result.startswith("```"):
                    result = result.split("```json")[-1].split("```")[0].strip()

                analysis = json.loads(result)

                # 容错处理 score
                score = analysis.get("score", 5)
                try:
                    score = int(float(score))
                    score = max(1, min(10, score))
                except:
                    score = 5

                _log_ai_event("ANALYZE_SUCCESS", {
                    "title": title[:50],
                    "score": score,
                    "domain": analysis.get("domain", "杂项"),
                    "elapsed_sec": f"{elapsed:.2f}"
                })
                print(f"✅ [评分成功] {title[:50]}... 评分: {score}/10 ({elapsed:.1f}s)")

                return {
                    "score": score,
                    "title_zh": analysis.get("title_zh", title),
                    "insight": analysis.get("insight", "暂无洞察"),
                    "domain": analysis.get("domain", "杂项"),
                    "reason": analysis.get("reason", "无特殊说明"),
                    "rewrite_direction": analysis.get("rewrite_direction", "暂无建议"),
                    "model_used": "ai_fallback",
                    "elapsed_sec": elapsed
                }
            except json.JSONDecodeError as e:
                _log_ai_event("ANALYZE_JSON_ERROR", {"title": title[:50], "error": str(e)})
                print(f"   ⚠️ JSON 解析失败: {e}")

        # 分析失败，返回默认值
        _log_ai_event("ANALYZE_FAILED", {"title": title[:50], "elapsed_sec": f"{elapsed:.2f}"})
        print(f"❌ [评分失败] {title[:50]}... 返回默认值 ({elapsed:.1f}s)")
        return {
            "score": 5,
            "title_zh": title,
            "insight": "AI 分析失败，使用默认值",
            "domain": "杂项",
            "reason": "AI 服务暂时不可用",
            "rewrite_direction": "建议人工评估",
            "model_used": "fallback_failed",
            "elapsed_sec": elapsed
        }


# 全局单例实例
_unified_caller = None


def get_unified_caller() -> UnifiedAICaller:
    """获取统一 AI 调用器单例"""
    global _unified_caller
    if _unified_caller is None:
        _unified_caller = UnifiedAICaller()
    return _unified_caller
