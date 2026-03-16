from modules.collector import ContentCollector

class InspirationCollector(ContentCollector):
    """
    专门为灵感库设计的采集器
    除了抓取正文，还会尝试分析内容的爆款特征
    """
    def __init__(self, timeout=30):
        super().__init__(timeout)

    def fetch_with_metrics(self, url):
        """
        抓取文章
        """
        print(f"🕵️ [灵感采集] 正在深度分析: {url}")
        return self.fetch(url)

if __name__ == "__main__":
    col = InspirationCollector()
    result = col.fetch_with_metrics("https://mp.weixin.qq.com/s/UhQSCacrzkyxrFp2uGgzjQ")
    if result:
        print(f"标题: {result['title']}")
        print(f"正文长度: {len(result.get('content_raw', ''))}")
