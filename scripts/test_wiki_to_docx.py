import os
import sys
import time

# 挂载模块路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from dotenv import load_dotenv
from modules.feishu import FeishuBitable

load_dotenv()

def extract_and_save_to_docx():
    app_id = os.getenv("FEISHU_APP_ID")
    app_secret = os.getenv("FEISHU_APP_SECRET")
    app_token = os.getenv("FEISHU_APP_TOKEN")
    
    feishu = FeishuBitable(app_id, app_secret, app_token)
    
    # 目标 Wiki
    wiki_url = "https://yunyinghui.feishu.cn/wiki/Ru7PwG82qiDGo1kGMFZcxqpGnnf"
    wiki_token = "Ru7PwG82qiDGo1kGMFZcxqpGnnf"
    
    print(f"🚀 开始处理 Wiki 原文提取...")
    print(f"🔗 目标链接: {wiki_url}")
    
    # 1. 获取内容
    article = feishu.get_docx_content(wiki_token)
    if not article:
        print("❌ 内容提取失败，请检查 Token 权限。")
        return
        
    print(f"✅ 内容抓取完成: {article['title']}")
    
    # 2. 创建新文档
    new_title = f"【内容提取测试】{article['title']}"
    doc_id, doc_url = feishu.create_docx(new_title)
    
    if doc_id:
        print(f"📄 新文档已创建: {doc_url}")
        print(f"🧱 正在转换并写入正文块（包含图片转存）...")
        
        # 3. 转换并追加内容
        blocks, _ = feishu.html_to_docx_blocks(article['content_html'], doc_id)
        if blocks:
            success = feishu.append_docx_blocks(doc_id, blocks)
            if success:
                print(f"✨ 写入成功！请点击上方链接查看详情。")
            else:
                print(f"⚠️ 部分内容写入可能受限。")
        else:
            print("⚠️ 未能识别到有效的 HTML 结构，尝试纯文本写入...")
            feishu.append_docx_blocks(doc_id, [{"block_type": 2, "text": {"elements": [{"text_run": {"content": article['content_raw']}}]}}])
    else:
        print("❌ 创建文档失败。")

if __name__ == "__main__":
    extract_and_save_to_docx()
