import os
import sys
from dotenv import load_dotenv

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from config import Config
from modules.feishu import FeishuBitable

load_dotenv()

def create_fields():
    print("🚀 [灵感库助手] 正在检查并创建缺失字段...")
    app_id = Config.FEISHU_APP_ID
    app_secret = Config.FEISHU_APP_SECRET
    app_token = Config.FEISHU_APP_TOKEN
    
    feishu = FeishuBitable(app_id, app_secret, app_token)
    table_id = feishu.get_table_id_by_name(Config.FEISHU_INSPIRATION_TABLE) or feishu.get_table_id_by_name("内容灵感库")
    
    if not table_id:
        print(f"❌ 找不到 [{Config.FEISHU_INSPIRATION_TABLE}] 表格")
        return

    # 创建 [图片] 字段 (17 代表附件类型)
    feishu.create_field(table_id, "图片", field_type=17)
    
    # 顺便创建 [原文文档] 字段 (15 代表链接类型)，如果缺失也可以补全
    feishu.create_field(table_id, "原文文档", field_type=15)
    
    print("\n✅ 字段补全工作已完成。")

if __name__ == "__main__":
    create_fields()
