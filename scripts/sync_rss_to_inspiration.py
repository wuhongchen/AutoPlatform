import os
import sys
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from dotenv import load_dotenv

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from config import Config
from modules.feishu import FeishuBitable

# 加载配置
load_dotenv()

# RSS 源配置 (更精选，减少噪音)
RSS_FEEDS = [
    {"name": "OpenAI News", "url": "https://openai.com/news/rss.xml"},
    {"name": "DeepMind Blog", "url": "https://deepmind.google/blog/rss.xml"},
    {"name": "TechCrunch AI", "url": "https://techcrunch.com/category/artificial-intelligence/feed/"},
    {"name": "The Verge AI", "url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml"},
    {"name": "MIT Tech Review AI", "url": "https://www.technologyreview.com/topic/artificial-intelligence/feed/"}
]

# 单个源抓取上限
ITEMS_PER_FEED_LIMIT = 5

class RSSInspirationSync:
    def __init__(self):
        self.feishu = FeishuBitable(
            Config.FEISHU_APP_ID, 
            Config.FEISHU_APP_SECRET, 
            Config.FEISHU_APP_TOKEN
        )
        self.table_name = Config.FEISHU_INSPIRATION_TABLE
        self.table_id = self.feishu.get_table_id_by_name(self.table_name) or self.feishu.get_table_id_by_name("内容灵感库")

    def get_existing_urls(self):
        """获取灵感库中已有的链接，防止重复同步"""
        if not self.table_id:
            return set()
        
        print(f"🔍 正在检查灵感库已有记录...")
        records = self.feishu.list_records(self.table_id)
        urls = set()
        for item in records.get('items', []):
            url = item.get('fields', {}).get('文章 URL')
            if url:
                urls.add(url)
        return urls

    def parse_rss(self, feed_url):
        """解析 RSS 内容 (基础版实现，不依赖第三方库)"""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            resp = requests.get(feed_url, headers=headers, timeout=20)
            if resp.status_code != 200:
                print(f"❌ 抓取失败 {feed_url}: HTTP {resp.status_code}")
                return []
            
            # 兼容 Atom 和 RSS 2.0
            root = ET.fromstring(resp.content)
            items = []
            
            # 尝试 RSS 2.0 路径
            for item in root.findall(".//item"):
                title = item.findtext("title")
                link = item.findtext("link")
                items.append({"title": title, "link": link})
            
            # 尝试 Atom 路径 (如果上面没找到)
            if not items:
                # Atom 命名空间处理
                ns = {'atom': 'http://www.w3.org/2005/Atom'}
                for entry in root.findall(".//atom:entry", ns):
                    title = entry.findtext("atom:title", namespaces=ns)
                    link_node = entry.find("atom:link", namespaces=ns)
                    link = link_node.get('href') if link_node is not None else ""
                    items.append({"title": title, "link": link})
                    
            return items
        except Exception as e:
            print(f"❌ 解析 RSS 异常 {feed_url}: {e}")
            return []

    def sync(self):
        if not self.table_id:
            print(f"❌ 找不到名为 '{self.table_name}' 的表格")
            return

        existing_urls = self.get_existing_urls()
        all_new_records = []

        print(f"📡 开始扫描 {len(RSS_FEEDS)} 个精选 AI 资讯源 (每个源限取 {ITEMS_PER_FEED_LIMIT} 条)...")
        for feed in RSS_FEEDS:
            print(f"  ➜ 正在抓取: {feed['name']}")
            items = self.parse_rss(feed['url'])
            
            # 限制每个源的抓取数量
            for item in items[:ITEMS_PER_FEED_LIMIT]:
                if item['link'] and item['link'] not in existing_urls:
                    new_record = {
                        "标题": item['title'],
                        "文章 URL": item['link'],
                        "处理状态": "待分析",
                        "同步时间": int(datetime.now().timestamp() * 1000),
                        "AI 推荐理由": f"来源 RSS: {feed['name']} (同步于 {datetime.now().strftime('%Y-%m-%d %H:%M')})"
                    }
                    all_new_records.append(new_record)
                    # 添加到已存在集合，防止本次扫描中出现重复内容
                    existing_urls.add(item['link'])

        if all_new_records:
            total = len(all_new_records)
            print(f"🚀 发现 {total} 条新资讯，正在推送到飞书灵感库 (分批处理)...")
            
            # 飞书批量写入限制 100 条
            batch_size = 100
            success_count = 0
            
            for i in range(0, total, batch_size):
                batch = all_new_records[i : i + batch_size]

                if self.feishu.add_records(self.table_id, batch):
                    success_count += len(batch)
                    print(f"  ✅ 已同步 {success_count}/{total}...")
                else:
                    print(f"  ❌ 批次 {i//batch_size + 1} 同步失败")

            print(f"✅ 同步完成！共新增 {success_count} 条灵感。")
        else:
            print("😴 没有发现新内容。")

if __name__ == "__main__":
    syncer = RSSInspirationSync()
    syncer.sync()
