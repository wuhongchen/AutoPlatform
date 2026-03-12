import os
import sys

# 挂载模块路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from dotenv import load_dotenv
from modules.feishu import FeishuBitable
import json

load_dotenv()

def test_wiki_content():
    app_id = os.getenv("FEISHU_APP_ID")
    app_secret = os.getenv("FEISHU_APP_SECRET")
    app_token = os.getenv("FEISHU_APP_TOKEN")
    
    feishu = FeishuBitable(app_id, app_secret, app_token)
    
    # 目标 Wiki ID
    wiki_url = "https://my.feishu.cn/wiki/Tup4w6U3jieWmJkKeuncPMgsnFg"
    wiki_token = "Tup4w6U3jieWmJkKeuncPMgsnFg"
    
    print(f"🚀 开始测试 Wiki 抓取: {wiki_url}")
    print("-" * 50)
    
    article = feishu.get_docx_content(wiki_token)
    
    if article:
        print(f"✅ 抓取成功！")
        print(f"📌 标题: {article.get('title')}")
        print(f"👤 作者: {article.get('author')}")
        print("-" * 30)
        print("📝 内容预览 (前 500 字):")
        print(article.get('content_raw')[:500])
        print("-" * 30)
        print(f"📸 图片数量: {article.get('content_html').count('<img')}")
        
        # 模拟转换 Blocks
        print("\n🛠️ 正在模拟转换为飞书 Blocks...")
        blocks, _ = feishu.html_to_docx_blocks(article['content_html'])
        print(f"🧱 生成的 Blocks 总数: {len(blocks)}")
        
        # 调试第一个图片 Block
        img_blocks = [b for b in blocks if b['block_type'] == 27]
        if img_blocks:
            print(f"🖼️ 检测到首个图片源: {img_blocks[0].get('image', {}).get('_src_url')}")
    else:
        print("❌ 抓取失败，请检查 Token 或鉴权状态。")

if __name__ == "__main__":
    test_wiki_content()
