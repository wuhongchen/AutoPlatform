"""
正式运行：
  1. 采集微信文章（含图片）
  2. 在飞书创建文档
  3. 用三步走方式写入内容和图片
  4. 输出可查看的飞书文档链接
"""
import os, sys, time
from dotenv import load_dotenv
from modules.feishu import FeishuBitable
from modules.collector import ContentCollector

load_dotenv()

# ── 默认测试 URL（可通过命令行参数传入）──────────────────────────────────────
DEFAULT_URL = "https://mp.weixin.qq.com/s/SqB9llfkT2o8x4v_LX-Ang"

def run(url=None):
    url = url or DEFAULT_URL
    
    # ── 初始化 ───────────────────────────────────────────────────────────────
    feishu = FeishuBitable(
        os.getenv("FEISHU_APP_ID"),
        os.getenv("FEISHU_APP_SECRET"),
        os.getenv("FEISHU_APP_TOKEN")
    )
    collector = ContentCollector()
    
    # ── 步骤 1: 采集文章 ──────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"📥 步骤 1: 采集文章")
    print(f"{'='*60}")
    article = collector.fetch(url)
    if not article:
        print("❌ 采集失败，退出")
        return
    
    title = article['title']
    content_html = article['content_html']
    images = article.get('images', [])
    
    print(f"   标题: {title}")
    print(f"   图片数: {len(images)} 张")
    print(f"   HTML 长度: {len(content_html)} chars")
    
    # ── 步骤 2: 创建飞书文档 ──────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"📄 步骤 2: 创建飞书文档")
    print(f"{'='*60}")
    doc_id, doc_url = feishu.create_docx(title)
    if not doc_id:
        print("❌ 创建文档失败，退出")
        return
    print(f"   ✅ 文档已创建: {doc_url}")
    time.sleep(2)
    
    # ── 步骤 3: 解析 HTML → blocks ───────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"🔧 步骤 3: 解析内容块")
    print(f"{'='*60}")
    blocks, _ = feishu.html_to_docx_blocks(content_html, document_id=doc_id)
    
    img_blocks = [b for b in blocks if b.get("block_type") == 27]
    txt_blocks = [b for b in blocks if b.get("block_type") != 27]
    print(f"   📝 文本块: {len(txt_blocks)} 个")
    print(f"   🖼️  图片块: {len(img_blocks)} 个")
    print(f"   📦 总 blocks: {len(blocks)} 个")
    
    # ── 步骤 4: 写入飞书文档（三步走图片 + 文本批写）────────────────────────
    print(f"\n{'='*60}")
    print(f"🚀 步骤 4: 写入飞书文档（含图片三步走）")
    print(f"{'='*60}")
    ok = feishu.append_docx_blocks(doc_id, blocks)
    
    # ── 完成 ──────────────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    if ok:
        print(f"✅ 全部完成！")
        print(f"   标题: {title}")
        print(f"   图片: {len(img_blocks)} 张")
        print(f"   👉 查看文档: {doc_url}")
    else:
        print(f"❌ 写入出错，请查看上方日志")
    print(f"{'='*60}")
    return doc_url

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else None
    run(url)
