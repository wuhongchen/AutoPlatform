import os
import requests
import json
from dotenv import load_dotenv
from modules.feishu import FeishuBitable

load_dotenv()

def setup():
    app_id = os.getenv("FEISHU_APP_ID")
    app_secret = os.getenv("FEISHU_APP_SECRET")
    app_token = os.getenv("FEISHU_APP_TOKEN")
    
    feishu = FeishuBitable(app_id, app_secret, app_token)
    if not feishu._get_token():
        return
    
    # 1. 创建新表: 内容灵感库
    url = f"{feishu.base_url}/bitable/v1/apps/{feishu.app_token}/tables"
    headers = {
        "Authorization": f"Bearer {feishu.token}",
        "Content-Type": "application/json; charset=utf-8"
    }
    payload = {"table": {"name": "内容灵感库"}}
    
    resp = requests.post(url, headers=headers, json=payload).json()
    if resp.get("code") in [1254302, 1254013]: # 已存在
        print("💡 表格 [内容灵感库] 已存在，正在查找其 ID...")
        tables = feishu.list_tables()
        table_id = next((t['table_id'] for t in tables if t['name'] == "内容灵感库"), None)
    elif resp.get("code") == 0:
        table_id = resp["data"]["table_id"]
        print(f"✅ 成功创建新表 [内容灵感库]: {table_id}")
    else:
        print(f"❌ 创建表格失败: {resp}")
        return

    if not table_id:
        print("未能获取目标表格 ID")
        return

    # 2. 定义字段
    status_options = [
        {"name": "待审"},
        {"name": "已弃用"},
        {"name": "已同步"},
    ]
    
    fields = [
        ("文章 URL", 1, None),
        ("标题", 1, None),
        ("阅读量 / 点赞量", 1, None),
        ("AI 爆款潜力评分", 2, None), # 数字类型
        ("AI 推荐理由", 1, None),
        ("建议改写方向", 1, None),
        ("原文文档", 1, None), # 新增：飞书文档链接
        ("处理状态", 3, {"options": status_options}), # 单选
        ("同步时间", 5, None), # 日期
    ]
    
    existing_fields = feishu.list_fields(table_id) or []
    existing_names = [f['field_name'] for f in existing_fields]

    for name, ftype, fprop in fields:
        if name in existing_names:
            print(f"⏩ 字段 [{name}] 已存在，跳过。")
            continue
        feishu.create_field(table_id, name, ftype, fprop)

    print(f"\n✨ [内容灵感库] 初始化完成！")
    print(f"🔗 表 ID: {table_id}")

if __name__ == "__main__":
    setup()
