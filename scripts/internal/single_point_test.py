import os
import time
from dotenv import load_dotenv
from modules.feishu import FeishuBitable
from modules.inspiration.collector import InspirationCollector

# 加载配置
load_dotenv()

def run_single_point_test():
    print("🎯 [单点测试] 启动核心链路验证: 抓取 -> 转化 -> 物理存储")
    
    # 1. 初始化飞书
    app_id = os.getenv("FEISHU_APP_ID")
    app_secret = os.getenv("FEISHU_APP_SECRET")
    app_token = os.getenv("FEISHU_APP_TOKEN")
    feishu = FeishuBitable(app_id, app_secret, app_token)
    
    table_id = feishu.get_table_id_by_name("内容灵感库")
    if not table_id:
        print("❌ 无法找到表格，请确认表格名称为 [内容灵感库]")
        return

    # 2. 抓取微信内容
    url = "https://mp.weixin.qq.com/s/le4l9QzeYQwJaC_nxiD28w"
    collector = InspirationCollector()
    article = collector.fetch_with_metrics(url)
    
    if not article:
        print("❌ 网页抓取失败")
        return
    
    print(f"✅ 内容抓取成功: {article['title']}")
    print(f"📸 抓取到图片数量: {len(article['images'])}")

    # 3. 物理存储 A：创建飞书文档并存入内容 + 图片
    doc_id, doc_url = feishu.create_docx(title=f"【单点测试-文字图片备份】{article['title']}")
    if doc_id:
        print(f"📄 飞书文档已创建: {doc_url}")
        blocks, docx_tokens = feishu.html_to_docx_blocks(article['content_html'], doc_id)
        if blocks:
            feishu.append_docx_blocks(doc_id, blocks)
            print(f"✨ 文档内容及图片已物理存储完成。")

    # 4. 物理存储 B：在多维表格中创建新记录并存入图片附件
    print(f"📸 正在物理转存图片至多维表格附件库...")
    bitable_img_tokens = []
    # 转存前 3 张图片作为示例
    for img_url in article['images'][:3]:
        token = feishu.upload_image(img_url, parent_node=None, force_docx=False)
        if token:
            bitable_img_tokens.append({"file_token": token})
            print(f"   - 图片已转化存储，Token: {token[:10]}...")

    # 5. 回写多维表格
    test_fields = {
        "标题": article['title'],
        "文章 URL": url,
        "原文文档": doc_url if doc_url else "创建失败",
        "处理状态": "待审",
        # 写入我们刚刚创建的'图片'附件字段
        "图片": bitable_img_tokens
    }
    
    success = feishu.add_record(table_id, test_fields)
    if success:
        print(f"✅ 多维表格记录已新增，文字与图片均已成功存储！")
    else:
        print(f"❌ 多维表格记录新增失败，请确认 [图片] 字段名及类型(附件)是否正确。")

    print("\n🏁 [测试结束] 您可以刷新飞书查看结果。")

if __name__ == "__main__":
    run_single_point_test()
