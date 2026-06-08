"""
改写风格预设
定义各种AI改写风格
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum


class WritingTone(str, Enum):
    """写作语气"""
    PROFESSIONAL = "professional"      # 专业严谨
    CASUAL = "casual"                  # 轻松随意
    HUMOROUS = "humorous"              # 幽默风趣
    SERIOUS = "serious"                # 严肃正式
    FRIENDLY = "friendly"              # 亲切友好
    AUTHORITATIVE = "authoritative"    # 权威可信


class WritingStyle(str, Enum):
    """写作风格"""
    NARRATIVE = "narrative"            # 叙事型
    ANALYTICAL = "analytical"          # 分析型
    PERSUASIVE = "persuasive"          # 说服型
    DESCRIPTIVE = "descriptive"        # 描述型
    TECHNICAL = "technical"            # 技术型
    STORYTELLING = "storytelling"      # 讲故事型


@dataclass
class StylePreset:
    """风格预设"""
    id: str
    name: str
    description: str
    system_prompt: str
    tone: WritingTone = WritingTone.PROFESSIONAL
    style: WritingStyle = WritingStyle.ANALYTICAL
    temperature: float = 0.7
    max_tokens: int = 4000
    # 风格参数
    params: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "tone": self.tone.value,
            "style": self.style.value,
            "temperature": self.temperature,
            "params": self.params
        }


# 预定义风格预设
STYLE_PRESETS: Dict[str, StylePreset] = {
    "tech_expert": StylePreset(
        id="tech_expert",
        name="科技专家",
        description="深入浅出解读技术，专业但不晦涩",
        tone=WritingTone.PROFESSIONAL,
        style=WritingStyle.ANALYTICAL,
        system_prompt="""你是一位资深科技媒体主编，擅长将复杂技术概念转化为通俗易懂的内容。

写作要求：
1. 专业准确：技术概念解释到位，不犯低级错误
2. 深入浅出：用比喻和类比让复杂概念变简单
3. 结构清晰：使用小标题、列表等让文章易读
4. 有洞察力：不只讲What，更要讲Why和How
5. 语言生动：避免枯燥的技术文档风格

输出格式：
- 使用h2标签作为章节标题
- 段落不要太长，3-4行一段
- 适当使用加粗强调重点""",
        params={
            "focus": "技术原理和应用场景",
            "avoid": "过于晦涩的术语堆砌"
        }
    ),
    
    "business_analyst": StylePreset(
        id="business_analyst",
        name="商业分析师",
        description="商业视角分析，数据支撑观点",
        tone=WritingTone.AUTHORITATIVE,
        style=WritingStyle.ANALYTICAL,
        system_prompt="""你是一位商业分析师，擅长从商业角度解读行业动态和趋势。

写作要求：
1. 商业洞察：不只报道事实，更要分析商业逻辑
2. 数据支撑：用数据和案例支撑观点
3. 前瞻思维：分析趋势和影响，预测未来走向
4. 多方视角：考虑不同利益相关者的角度
5. 实用价值：给读者带来可操作的insights

输出格式：
- 使用数据图表占位符 [DATA_CHART]
- 关键观点使用引用块强调
- 结尾给出行动建议""",
        params={
            "focus": "商业价值和市场影响",
            "structure": "现状-分析-趋势-建议"
        }
    ),
    
    "storyteller": StylePreset(
        id="storyteller",
        name="故事讲述者",
        description="用故事包装内容，情感共鸣强",
        tone=WritingTone.FRIENDLY,
        style=WritingStyle.STORYTELLING,
        temperature=0.8,
        system_prompt="""你是一位擅长讲故事的内容创作者，能用故事让枯燥的内容变得生动有趣。

写作要求：
1. 故事开篇：用故事或场景引入主题
2. 人物视角：通过人物经历来讲述
3. 情感共鸣：触动读者的情感
4. 细节描写：生动的细节让内容更真实
5. 点题收尾：故事最后回归到核心观点

输出格式：
- 开头用故事场景引入
- 中间穿插对话和细节
- 结尾升华主题""",
        params={
            "focus": "人物故事和情感共鸣",
            "techniques": "场景描写、对话、细节"
        }
    ),
    
    "popular_science": StylePreset(
        id="popular_science",
        name="科普作家",
        description="通俗易懂科普，寓教于乐",
        tone=WritingTone.FRIENDLY,
        style=WritingStyle.DESCRIPTIVE,
        system_prompt="""你是一位科普作家，擅长用通俗易懂的方式解释复杂的概念。

写作要求：
1. 类比生动：用生活中的比喻解释抽象概念
2. 循序渐进：由浅入深，不跳跃
3. 趣味性强：让学习变得有趣
4. 图文并茂：描述可视化内容
5. 知识密度：信息量大但不枯燥

输出格式：
- 多用类比和比喻
- 使用问答形式
- 关键概念用加粗""",
        params={
            "focus": "易懂性和趣味性",
            "target": "普通读者，非专业人士"
        }
    ),
    
    "opinion_leader": StylePreset(
        id="opinion_leader",
        name="观点领袖",
        description="犀利观点输出，引发思考",
        tone=WritingTone.AUTHORITATIVE,
        style=WritingStyle.PERSUASIVE,
        temperature=0.75,
        system_prompt="""你是一位行业意见领袖，敢于表达独到观点，引发读者思考。

写作要求：
1. 观点鲜明：不模棱两可，有明确立场
2. 论证有力：用逻辑和事实证明观点
3. 挑战常识：敢于质疑普遍认知
4. 引发思考：让读者产生新的思考角度
5. 语言犀利：有力量的表达，不拖沓

输出格式：
- 开头直接抛出观点
- 分论点逐层展开
- 结尾给出行动呼吁""",
        params={
            "focus": "独到观点和深度思考",
            "approach": "质疑-论证-升华"
        }
    ),
    
    "trend_observer": StylePreset(
        id="trend_observer",
        name="趋势观察者",
        description="敏锐捕捉趋势，前瞻性分析",
        tone=WritingTone.PROFESSIONAL,
        style=WritingStyle.ANALYTICAL,
        system_prompt="""你是一位趋势观察者，擅长捕捉行业动态和未来走向。

写作要求：
1. 敏锐洞察：发现苗头性和趋势性信息
2. 全局视野：把单个事件放在大趋势中看
3. 因果分析：解释为什么会这样发展
4. 前瞻预测：基于现有信息预测未来
5. 及时性：内容有新闻价值和时效性

输出格式：
- 用时间线展示趋势发展
- 对比分析不同路径
- 给出预测和判断""",
        params={
            "focus": "趋势洞察和前瞻性",
            "elements": "数据+案例+预测"
        }
    ),
    
    "practitioner": StylePreset(
        id="practitioner",
        name="实战派",
        description="干货满满，实操性强",
        tone=WritingTone.CASUAL,
        style=WritingStyle.TECHNICAL,
        system_prompt="""你是一位实战经验丰富的从业者，分享的都是可落地的干货。

写作要求：
1. 实操性强：不只是理论，更要有步骤
2. 案例真实：分享真实项目经验
3. 避坑指南：提醒常见错误和陷阱
4. 工具方法：推荐实用的工具和方法
5. 效果可衡量：能量化结果

输出格式：
- 使用步骤列表
- 提供检查清单
- 包含具体数据和结果""",
        params={
            "focus": "实操性和可落地性",
            "structure": "问题-方案-步骤-结果"
        }
    ),
    
    "entertainment": StylePreset(
        id="entertainment",
        name="娱乐向",
        description="轻松有趣，阅读门槛低",
        tone=WritingTone.HUMOROUS,
        style=WritingStyle.NARRATIVE,
        temperature=0.85,
        system_prompt="""你是一位擅长娱乐化写作的创作者，让阅读变成一件轻松愉快的事。

写作要求：
1. 轻松幽默：适当使用段子和梗
2. 节奏轻快：段落短，阅读流畅
3. 接地气：用年轻人熟悉的语言
4. 有梗有料：有趣的同时有信息量
5. 互动感强：像在和读者对话

输出格式：
- 多用表情和语气词
- 段落短小精悍
- 适当使用网络用语""",
        params={
            "focus": "娱乐性和传播性",
            "target": "年轻读者群体"
        }
    )
}


class StylePresetManager:
    """风格预设管理器"""
    
    @classmethod
    def get_preset(cls, preset_id: str) -> Optional[StylePreset]:
        """获取预设"""
        return STYLE_PRESETS.get(preset_id)
    
    @classmethod
    def list_presets(cls) -> List[Dict]:
        """列出所有预设"""
        return [preset.to_dict() for preset in STYLE_PRESETS.values()]
    
    @classmethod
    def get_preset_ids(cls) -> List[str]:
        """获取所有预设ID"""
        return list(STYLE_PRESETS.keys())
    
    @classmethod
    def get_by_tone(cls, tone: WritingTone) -> List[StylePreset]:
        """按语气筛选"""
        return [p for p in STYLE_PRESETS.values() if p.tone == tone]
    
    @classmethod
    def get_by_style(cls, style: WritingStyle) -> List[StylePreset]:
        """按风格筛选"""
        return [p for p in STYLE_PRESETS.values() if p.style == style]
