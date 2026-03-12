import os
from dotenv import load_dotenv
from modules.feishu import FeishuBitable

load_dotenv()

def create_fields():
    print("🚀 [灵感库助手] 正在检查并创建缺失字段...")
    app_id = os.getenv("FEISHU_APP_ID")
    app_secret = os.getenv("FEISHU_APP_SECRET")
    app_token = os.getenv("FEISHU_APP_TOKEN")
    
    feishu = FeishuBitable(app_id, app_secret, app_token)
    table_id = feishu.get_table_id_by_name("内容灵感库")
    
    if not table_id:
        print("❌ 找不到 [内容灵感库] 表格")
        return

    # 创建 [图片] 字段 (17 代表附件类型)
    feishu.create_field(table_id, "图片", field_type=17)
    
    # 顺便创建 [原文文档] 字段 (15 代表链接类型)，如果缺失也可以补全
    feishu.create_field(table_id, "原文文档", field_type=15)
    
    print("\n✅ 字段补全工作已完成。")

if __name__ == "__main__":
    create_fields()
