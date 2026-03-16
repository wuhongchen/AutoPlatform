import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from config import Config
from modules.feishu import FeishuBitable
from modules.state_machine import PipelineState, canonical_pipeline_status

def auto_publish():
    feishu = FeishuBitable(
        Config.FEISHU_APP_ID, 
        Config.FEISHU_APP_SECRET, 
        Config.FEISHU_APP_TOKEN
    )
    table_id = feishu.get_table_id_by_name(Config.FEISHU_PIPELINE_TABLE) or feishu.get_table_id_by_name("小龙虾智能内容库")
    
    records = feishu.list_records(table_id)
    items = records.get('items', [])
    updated = 0
    
    for item in items:
        fields = item.get('fields', {})
        record_id = item.get('record_id')
        status = canonical_pipeline_status(fields.get('数据流程状态'))
        title = fields.get('标题')
        
        # 只要最新的一篇 "待审" 的 Tabbit 文章
        if status == PipelineState.REVIEW_READY and "Tabbit" in title:
            print(f"🚀 将 [{title}] 设为 待发布.")
            feishu.update_record(table_id, record_id, {'数据流程状态': PipelineState.PUBLISH_READY})
            updated += 1
            break # 仅处理一篇以供测试
            
    if updated == 0:
        print("📭 没有找到可以发布的内容。")

if __name__ == '__main__':
    auto_publish()
