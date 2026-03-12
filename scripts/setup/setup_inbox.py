import os
from dotenv import load_dotenv
from modules.feishu import FeishuBitable

load_dotenv()

def setup_inbox():
    app_id = os.getenv("FEISHU_APP_ID")
    app_secret = os.getenv("FEISHU_APP_SECRET")
    app_token = os.getenv("FEISHU_APP_TOKEN")
    
    feishu = FeishuBitable(app_id, app_secret, app_token)
    
    # 1. 创建“内容库 (待采集)”表格
    table_id = feishu.create_table("内容库")
    if not table_id:
        return

    # 2. 设置字段
    # 状态选项
    status_options = [
        {"name": "待处理", "color": 0},
        {"name": "处理中", "color": 1},
        {"name": "AI 改写", "color": 5},
        {"name": "已发布", "color": 2},
        {"name": "已跳过", "color": 3},
        {"name": "采集失败", "color": 4},
    ]
    
    # 优先级选项
    priority_options = [
        {"name": "🔥 高", "color": 0},
        {"name": "📅 中", "color": 1},
        {"name": "☕ 低", "color": 2},
    ]

    fields = [
        ("标题", 1, None),
        ("文章链接", 1, None),
        ("当前状态", 3, {"options": status_options}),
        ("优先级", 3, {"options": priority_options}),
        ("来源渠道", 1, None),
        ("备注说明", 1, None)
    ]
    
    print(f"📡 正在配置表格 [{table_id}] 的字段结构...")
    for name, ftype, fprop in fields:
        feishu.create_field(table_id, name, ftype, fprop)

    # 3. 初始演示数据
    initial_data = [
        {
            "标题": "示例：2026 AI 行业深度报告",
            "文章链接": "https://mp.weixin.qq.com/s/example1",
            "当前状态": "待处理",
            "优先级": "🔥 高",
            "来源渠道": "微信公众号",
            "备注说明": "这是一条待采集的示例数据"
        }
    ]
    feishu.add_records(table_id, initial_data)
    print("✨ “内容库”已初始化完成，可开始维护待采集信息。")

if __name__ == "__main__":
    setup_inbox()
