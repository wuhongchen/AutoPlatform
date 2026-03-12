import os
import json
from dotenv import load_dotenv
from modules.feishu import FeishuBitable

load_dotenv()

app_id = os.getenv("FEISHU_APP_ID")
app_secret = os.getenv("FEISHU_APP_SECRET")
app_token = os.getenv("FEISHU_APP_TOKEN")

print(f"App ID: {app_id}")
print(f"App Token: {app_token}")

feishu = FeishuBitable(app_id, app_secret, app_token)

tables = feishu.list_tables()
if tables:
    print("\n--- Tables List ---")
    for t in tables:
        print(f"Table Name: {t['name']} | Table ID: {t['table_id']}")
        # 顺便查一下第一个表的字段
        fields = feishu.list_fields(t['table_id'])
        if fields:
            print("  Fields:")
            for f in fields:
                print(f"    - {f['field_name']} ({f['type']})")
else:
    print("❌ Failed to list tables.")
