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
    
    # 1. 创建新表: 小龙虾智能内容库
    url = f"{feishu.base_url}/bitable/v1/apps/{feishu.app_token}/tables"
    headers = {
        "Authorization": f"Bearer {feishu.token}",
        "Content-Type": "application/json; charset=utf-8"
    }
    payload = {"table": {"name": "小龙虾智能内容库"}}
    
    resp = requests.post(url, headers=headers, json=payload).json()
    if resp.get("code") in [1254302, 1254013]: # 已存在
        print("💡 表格 [小龙虾智能内容库] 已存在，正在查找其 ID...")
        tables = feishu.list_tables()
        table_id = next((t['table_id'] for t in tables if t['name'] == "小龙虾智能内容库"), None)
    elif resp.get("code") == 0:
        table_id = resp["data"]["table_id"]
        print(f"✅ 成功创建新表: {table_id}")
    else:
        print(f"❌ 创建表格失败: {resp}")
        return

    if not table_id:
        print("未能获取目标表格 ID")
        return

    # 2. 检查并纠正字段类型
    existing_fields = feishu.list_fields(table_id) or []
    for f in existing_fields:
        # 如果“数据流程状态”已经是单选了, 就跳过
        if f['field_name'] == "数据流程状态":
            if f['type'] != 3:
                print(f"🗑️ 发现旧的文本类型字段 [数据流程状态], 正在删除并重建为单选类型...")
                feishu.delete_field(table_id, f['field_id'])
            else:
                print("✅ 字段 [数据流程状态] 已经是单选类型，跳过更新。")

    # 定义单选选项
    status_options = [
        {"name": "✅ 采集完成"},
        {"name": "✅ 改写完成"},
        {"name": "✅ 生图完成"},
        {"name": "✅ 发布完成"},
        {"name": "✨ 流程全通"},
        {"name": "❌ 失败"},
    ]
    
    fields = [
        ("编号", 1, None),
        ("文章 URL", 1, None),
        ("标题", 1, None),
        ("原创度", 2, None),
        ("草稿 ID", 1, None),
        ("备注", 1, None),
        ("数据流程状态", 3, {"options": status_options}), # 重新创建为单选
        ("负责人", 1, None)
    ]
    
    for name, ftype, fprop in fields:
        feishu.create_field(table_id, name, ftype, fprop)

    # 3. 导入演示历史记录 (取自 Excel)
    demo_data = [
        {
            "编号": "1",
            "文章 URL": "https://mp.weixin.qq.com/s/...",
            "标题": "2026 年 AI 副业精细化运营趋势",
            "原创度": 92,
            "草稿 ID": "f98nLrQV...35J4BDr",
            "备注": "已使用 Prompt 3 改写。引入 KANO 模型。",
            "数据流程状态": "✅ 采集 -> ✅ 改写 -> ✅ 生图 -> ✅ 发布",
            "负责人": "CEO"
        }
    ]
    feishu.add_records(table_id, demo_data)
    print("✨ 已按 Excel 格式同步历史记录至内容库中。")

if __name__ == "__main__":
    setup()
