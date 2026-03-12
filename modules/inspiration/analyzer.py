from modules.models import MODEL_POOL, DEFAULT_MODEL
import requests
import json

class InspirationAnalyzer:
    """
    灵感评估引擎 (Inspiration Analyzer)
    核心任务：对采集到的内容进行爆款评估，生成评分和理由
    """
    def __init__(self, model_key=None):
        from modules.models import MODEL_POOL, DEFAULT_MODEL
        key = model_key or DEFAULT_MODEL
        self.model_cfg = MODEL_POOL.get(key, MODEL_POOL[DEFAULT_MODEL])
        self.api_key = str(self.model_cfg.get("api_key")).strip()
        self.endpoint = self.model_cfg.get("endpoint")
        self.model_name = self.model_cfg.get("model")

    def analyze(self, article_data):
        """对单篇文章进行深度爆款潜力分析"""
        print(f"🧠 [AI 分析] 正在评估选题潜力: {article_data['title']}")
        
        if not self.api_key:
            return {
                "score": 5,
                "reason": "未配置 AI 密钥，默认中等推荐",
                "rewrite_direction": "待定"
            }

        prompt = f"""
你是一位顶尖的内容运营专家和爆款选题师。请对以下采集到的文章进行“爆款潜力”评估。

**文章信息:**
标题: {article_data['title']}
作者: {article_data['author']}
内容片段: {article_data['content_raw'][:2000]}

**分析要求:**
1. **内容评价**: 基于内容的稀缺性、技术突破性、大众共鸣度进行评估。
2. **潜力评分 (1-10)**: 请非常苛刻，只有真正的重大突破或极具爆款潜质的内容（如 Sora 发布级别）才能给 9-10 分。普通科技新闻给 4-6 分。
3. **中文译名**: 如果是英文标题，请提供一个由您深度重构的、具有吸引力的中文文章标题。
4. **核心洞察**: 简述文章中最重要的 1 个技术突破点或观点。
5. **所属领域**: 标记该文章属于哪个领域 (如：大模型、通用机器人、AI 终端、AI 政策、开源项目)。

**输出要求**:
必须返回 JSON 格式，包含以下字段:
- score: 数字 (1-10)
- title_zh: 字符串 (中文标题)
- insight: 字符串 (100字以内的核心洞察)
- domain: 字符串 (所属领域)
- reason: 字符串 (推荐或不推荐的理由)
- rewrite_direction: 字符串 (改写建议)
"""
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": "你是一个专业的内容分析助手，只输出 JSON 格式。"},
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"} if "doubao" not in self.model_name else None,
            "temperature": 0.4
        }

        try:
            resp = requests.post(self.endpoint, headers=headers, json=payload, timeout=60)
            res_json = resp.json()
            
            if 'choices' not in res_json:
                print(f"❌ AI 响应异常，未找到 'choices' 字段: {res_json}")
                return {
                    "score": 0,
                    "reason": f"AI 响应格式错误: {res_json.get('error', '未知错误')}",
                    "rewrite_direction": "无法生成建议"
                }
                
            content = res_json['choices'][0]['message']['content']
            
            # 清理 Markdown 代码块包裹
            if content.startswith("```"):
                content = content.split("```json")[-1].split("```")[0].strip()
            
            analysis = json.loads(content)
            return {
                "score": int(analysis.get("score", 5)),
                "title_zh": analysis.get("title_zh", article_data['title']),
                "insight": analysis.get("insight", "暂无洞察"),
                "domain": analysis.get("domain", "杂项"),
                "reason": analysis.get("reason", "无特殊说明"),
                "rewrite_direction": analysis.get("rewrite_direction", "暂无建议")
            }
        except Exception as e:
            print(f"❌ AI 分析异常: {e}")
            return {
                "score": 0,
                "reason": f"评估失败: {str(e)}",
                "rewrite_direction": "无法生成建议"
            }

if __name__ == "__main__":
    analyzer = InspirationAnalyzer()
    dummy_article = {
        "title": "2026 年公众号运营的新趋势",
        "author": "运营专家",
        "content_raw": "这是一篇关于公众号运营深度思考的文章..."
    }
    res = analyzer.analyze(dummy_article)
    print(json.dumps(res, indent=4, ensure_ascii=False))
