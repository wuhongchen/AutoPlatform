import os
from dotenv import load_dotenv
from modules.feishu import FeishuBitable

load_dotenv()

def sync():
    app_id = os.getenv("FEISHU_APP_ID")
    app_secret = os.getenv("FEISHU_APP_SECRET")
    app_token = os.getenv("FEISHU_APP_TOKEN")
    
    feishu = FeishuBitable(app_id, app_secret, app_token)
    
    # 1. 获取第一个表格 ID
    tables = feishu.list_tables()
    if not tables:
        print("❌ 无法获取表格列表")
        return
    
    table_id = tables[0]['table_id']
    print(f"📡 目标表格: {tables[0]['name']} ({table_id})")
    
    # 2. 创建流水线所需字段
    fields_to_create = [
        ("阶段", 1),
        ("流水线任务", 1),
        ("实现逻辑", 1),
        ("核心模块", 1),
        ("执行状态", 1)
    ]
    
    for name, ftype in fields_to_create:
        feishu.create_field(table_id, name, ftype)
        
    # 3. 准备流水线数据
    pipeline_data = [
        {
            "阶段": "I. 采集",
            "流水线任务": "1. 网页全文解析",
            "实现逻辑": "BeautifulSoup4 抓取微信正文、图片路径及作者元数据",
            "核心模块": "modules/collector.py",
            "执行状态": "✅ 已通过"
        },
        {
            "阶段": "II. 改写",
            "流水线任务": "2. 角色化 AI 创作",
            "实现逻辑": "调用 Doubao-Seed-2.0-Pro 进行专业文风重塑",
            "核心模块": "modules/models.py",
            "执行状态": "✅ 已通过"
        },
        {
            "阶段": "III. 生图",
            "流水线任务": "3. AI 封面生成",
            "实现逻辑": "Python 原生实现火山引擎签名算法，调用即梦生图",
            "核心模块": "modules/processor.py",
            "执行状态": "✅ 已通过"
        },
        {
            "阶段": "IV. 发布",
            "流水线任务": "4. 微信素材同步",
            "实现逻辑": "自动将生成的 AI 图片上传至微信后台素材库",
            "核心模块": "modules/publisher.py",
            "执行状态": "✅ 已通过"
        },
        {
            "阶段": "IV. 发布",
            "流水线任务": "5. 云端草稿箱同步",
            "实现逻辑": "构建微信 Drafts 报文，完成 0 错误在线发布",
            "核心模块": "modules/publisher.py",
            "执行状态": "✅ 已通过"
        }
    ]
    
    # 4. 批量同步数据
    print(f"🚀 正在同步 {len(pipeline_data)} 个步骤到飞书流水线...")
    res = feishu.add_records(table_id, pipeline_data)
    if res:
        print("✨ 飞书流水线同步成功！")
    else:
        print("❌ 同步失败")

if __name__ == "__main__":
    sync()
