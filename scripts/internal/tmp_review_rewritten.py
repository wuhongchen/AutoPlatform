import os
from modules.collector import ContentCollector
from modules.mp_processor import DeepMPProcessor
from config import Config

def dry_run_review(url):
    collector = ContentCollector()
    processor = DeepMPProcessor()
    
    print(f"📥 重新抓取供预览: {url}")
    article_data = collector.fetch(url)
    if not article_data: return
    
    print(f"🖋️ 再次进行 AI 改写预览...")
    # 模拟 manager.py 中的逻辑
    result = processor.process(url, article_data)
    
    output_path = "output/rewritten_review.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result['full_content'])
    
    print(f"\n✅ 改写内容已生成并保存至: {output_path}")
    print(f"   预览标题: {result['title']}")
    print(f"   内容分析 JSON: {result['analysis']}")
    print(f"\n--- 正文开头预览 ---")
    print(result['full_content'][:1000] + "...")

if __name__ == "__main__":
    dry_run_review("https://mp.weixin.qq.com/s/UhQSCacrzkyxrFp2uGgzjQ")
