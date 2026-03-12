import os
import requests
import json
from dotenv import load_dotenv
from modules.feishu import FeishuBitable

load_dotenv()

def setup_publish_log():
    app_id = os.getenv("FEISHU_APP_ID")
    app_secret = os.getenv("FEISHU_APP_SECRET")
    app_token = os.getenv("FEISHU_APP_TOKEN")
    
    feishu = FeishuBitable(app_id, app_secret, app_token)
    
    # 1. 创建“发布记录表”
    table_id = feishu.create_table("发布记录表")
    if not table_id:
        return

    # 2. 设置字段 (发布结果回溯)
    fields = [
        ("发布标题", 1, None),
        ("发布时间", 5, None), # 日期类型
        ("发布平台", 1, None),
        ("草稿/文章 ID", 1, None),
        ("原创度", 2, None), # 数字
        ("关联原文链接", 1, None),
        ("负责人", 1, None),
        ("备注", 1, None)
    ]
    
    print(f"📡 正在配置 [发布记录表] 的字段结构...")
    for name, ftype, fprop in fields:
        feishu.create_field(table_id, name, ftype, fprop)

    print("✨ “发布记录表”已就绪。")

if __name__ == "__main__":
    setup_publish_log()
