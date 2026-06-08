from curl_cffi import requests
from bs4 import BeautifulSoup
import re
import os
import time
import hashlib
from pathlib import Path
from urllib.parse import urlparse
from modules.wechat_demo_bridge import WechatDemoBridge

import random

class ContentCollector:
    # 浏览器UA池，随机模拟不同设备
    USER_AGENTS = [
        # 桌面端 Chrome
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        # 桌面端 Safari
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
        # 移动端
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (Linux; Android 14; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 14; MI 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Mobile Safari/537.36"
    ]

    # 随机接受语言
    ACCEPT_LANGUAGES = [
        "zh-CN,zh;q=0.9,en;q=0.8,ja;q=0.7",
        "zh-CN,zh;q=0.9,en-GB;q=0.8,en;q=0.7",
        "zh-CN,zh-TW;q=0.9,zh;q=0.8,en;q=0.7",
        "zh-Hans-CN,zh-Hans;q=0.9,en;q=0.8"
    ]

    def __init__(self, timeout=30, output_dir=None):
        self.timeout = timeout
        self.wechat_demo_bridge = WechatDemoBridge()
        # 图片存储目录
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = Path(__file__).parent.parent / "output"
        self.images_dir = self.output_dir / "article_images"
        self.images_dir.mkdir(parents=True, exist_ok=True)

    def _download_image(self, img_url, article_dir, img_index, max_retries=3):
        """下载单张图片到本地，支持重试"""
        # 生成本地文件名
        parsed = urlparse(img_url)
        ext = os.path.splitext(parsed.path)[1] or '.jpg'
        if ext.lower() not in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']:
            ext = '.jpg'
        local_name = f"img_{img_index:03d}{ext}"
        local_path = article_dir / local_name

        # 微信图片需要特殊的 headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
            'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'https://mp.weixin.qq.com/',
            'Sec-Fetch-Dest': 'image',
            'Sec-Fetch-Mode': 'no-cors',
            'Sec-Fetch-Site': 'cross-site',
        }

        for attempt in range(max_retries):
            try:
                response = requests.get(
                    img_url,
                    headers=headers,
                    timeout=self.timeout,
                    impersonate="chrome123"
                )
                response.raise_for_status()

                # 验证内容是图片
                content_type = response.headers.get('Content-Type', '')
                if 'image' not in content_type and len(response.content) > 100:
                    # 可能是图片，尝试保存
                    pass

                # 保存图片
                with open(local_path, 'wb') as f:
                    f.write(response.content)

                print(f"   ✅ 图片下载成功 [{img_index}]: {local_name}")
                return f"/local_images/{article_dir.name}/{local_name}"

            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2
                    print(f"   ⚠️ 图片下载失败 (尝试 {attempt + 1}/{max_retries}): {img_url[:50]}... - {e}")
                    time.sleep(wait_time)
                else:
                    print(f"   ❌ 图片下载失败 (最终): {img_url[:50]}... - {e}")
                    return None

    def _download_images_for_article(self, images, article_id):
        """下载文章的所有图片到本地"""
        if not images:
            return {}

        # 创建文章专属图片目录
        article_dir = self.images_dir / article_id
        article_dir.mkdir(parents=True, exist_ok=True)

        url_mapping = {}
        for i, img_url in enumerate(images, 1):
            local_url = self._download_image(img_url, article_dir, i)
            if local_url:
                url_mapping[img_url] = local_url
            else:
                # 下载失败时保留原URL
                url_mapping[img_url] = img_url

        return url_mapping, str(article_dir)

    def _replace_image_urls_in_html(self, html, url_mapping):
        """替换HTML中的图片URL为本地URL"""
        if not url_mapping:
            return html

        for original_url, local_url in url_mapping.items():
            # HTML 中的 & 可能被转义为 &amp;，需要同时处理两种形式
            urls_to_replace = [original_url, original_url.replace('&', '&amp;')]
            for url in urls_to_replace:
                # 转义特殊字符用于正则
                escaped = re.escape(url)
                # 替换 src="url" 和 data-src="url"
                html = re.sub(rf'(src=["\']?){escaped}(["\']?)', rf'\1{local_url}\2', html, flags=re.IGNORECASE)
                html = re.sub(rf'(data-src=["\']?){escaped}(["\']?)', rf'\1{local_url}\2', html, flags=re.IGNORECASE)

        return html

    def _get_random_headers(self, referer=None):
        """生成随机浏览器指纹请求头"""
        headers = {
            'User-Agent': random.choice(self.USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': random.choice(self.ACCEPT_LANGUAGES),
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',  # Do Not Track
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'sec-ch-ua': '"Chromium";v="123", "Not:A-Brand";v="8", "Google Chrome";v="123"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"'
        }
        if referer:
            headers['Referer'] = referer
        return headers

    def fetch(self, url, article_id=None):
        """抓取并提取文章内容
        Args:
            url: 文章URL
            article_id: 文章ID，用于创建本地图片目录，不传则自动生成
        """
        print(f"📥 正在抓取: {url}")
        max_retries = 3  # 最多重试3次
        last_error = None

        # 生成文章ID（基于URL的hash）
        if not article_id:
            article_id = hashlib.md5(url.encode()).hexdigest()[:12]

        try:
            if 'mp.weixin.qq.com' in url:
                bridge_data = self.wechat_demo_bridge.fetch(url)
                if bridge_data:
                    # 为bridge数据也下载图片
                    images = bridge_data.get('images', [])
                    if images:
                        print(f"   🖼️  发现 {len(images)} 张图片，开始下载...")
                        url_mapping, files_dir = self._download_images_for_article(images, article_id)
                        bridge_data['content_html'] = self._replace_image_urls_in_html(
                            bridge_data.get('content_html', ''), url_mapping
                        )
                        bridge_data['files_dir'] = files_dir
                        print(f"   ✅ 图片下载完成")
                    char_count = len(bridge_data.get('content_raw', ''))
                    img_count = len(bridge_data.get('images', []))
                    print(f"✅ 微信 demo 抓取成功: {bridge_data.get('title', '无标题')} ({char_count}字, {img_count}图)")
                    return bridge_data

            # 每个请求完全独立，模拟全新浏览器
            for retry in range(max_retries):
                try:
                    headers = self._get_random_headers()
                    # 使用 curl_cffi 完美模拟 Chrome 浏览器 TLS 指纹，绕过90%反爬
                    response = requests.get(
                        url,
                        headers=headers,
                        timeout=self.timeout,
                        allow_redirects=True,
                        impersonate="chrome123"  # 模拟真实Chrome 123的TLS指纹
                    )

                    # 如果 403/404/5xx/连接错误，重试
                    if response.status_code in [403, 404, 500, 502, 503, 504]:
                        print(f"⚠️  第 {retry+1} 次抓取失败，状态码 {response.status_code}，重试中...")
                        time.sleep(random.uniform(1, 3))  # 延长等待时间
                        continue

                    response.raise_for_status()
                    break
                except Exception as e:
                    # 捕获所有网络异常（包括curl错误、连接断开等）都重试
                    if "curl" in str(e).lower() or "connection" in str(e).lower() or "broken pipe" in str(e).lower():
                        print(f"⚠️  第 {retry+1} 次网络异常: {str(e)[:50]}，重试中...")
                        time.sleep(random.uniform(1, 3))
                        continue
                    raise
                except Exception as e:
                    last_error = e
                    print(f"⚠️  第 {retry+1} 次抓取异常: {e}")
                    time.sleep(1)
            else:
                # 所有重试都失败
                raise last_error or Exception("所有重试都失败")
            # 多轮编码检测，彻底解决中文乱码问题
            html = ""
            # 按优先级尝试编码：utf-8 → gbk → gb2312 → 自动检测
            encodings_to_try = ['utf-8', 'gbk', 'gb2312', 'gb18030', 'big5']
            min_error_count = float('inf')
            best_html = ""

            for encoding in encodings_to_try:
                try:
                    # 直接从content解码，避免response.text的自动编码干扰
                    decoded = response.content.decode(encoding)
                    error_count = decoded.count('\ufffd')
                    if error_count < min_error_count:
                        min_error_count = error_count
                        best_html = decoded
                        # 如果没有错误，直接用这个编码
                        if error_count == 0:
                            break
                except:
                    continue

            # 最后兜底：如果所有编码都失败，用response.text自动处理
            if not best_html or min_error_count > len(best_html) * 0.05:
                try:
                    html = response.text
                except:
                    html = best_html
            else:
                html = best_html
            
            # 针对微信公众号的简单处理
            if 'mp.weixin.qq.com' in url:
                return self._parse_wechat(html, article_id)
            else:
                return self._parse_generic(html, article_id)
        except Exception as e:
            print(f"❌ 抓取失败: {e}")
            return None

    def _parse_wechat(self, html, article_id=None):
        """解析微信公众号文章"""
        soup = BeautifulSoup(html, 'html.parser')

        # 提取标题 - 移除前后空白
        title_tag = soup.find('h1', class_='rich_media_title')
        title = title_tag.get_text(strip=True) if title_tag else "无标题"

        # 提取作者
        author_tag = soup.find('span', class_='rich_media_meta_text')
        author = author_tag.get_text(strip=True) if author_tag else "未知作者"

        # 提取正文
        content_div = soup.find('div', class_='rich_media_content')
        if not content_div:
            return None

        # 处理图片懒加载: 将 data-src 移动到 src
        images = []
        for img in content_div.find_all('img'):
            src = img.get('data-src') or img.get('src')
            if src:
                images.append(src)
                img['src'] = src
                # 移除可能导致不显示的样式
                if img.get('style'):
                    img['style'] = img['style'].replace('visibility: hidden', '').replace('opacity: 0', '')

        # 移除正文容器可能存在的隐藏样式
        if content_div.get('style'):
            content_div['style'] = content_div['style'].replace('visibility: hidden', '').replace('opacity: 0', '')

        # 提取 HTML 结构 (Inner HTML)
        content_html = "".join([str(item) for item in content_div.contents])

        # 下载图片到本地并替换URL
        files_dir = ""
        if article_id and images:
            print(f"   🖼️  发现 {len(images)} 张图片，开始下载...")
            url_mapping, files_dir = self._download_images_for_article(images, article_id)
            content_html = self._replace_image_urls_in_html(content_html, url_mapping)
            print(f"   ✅ 图片下载完成，保存在: {files_dir}")

        # 提取纯文本
        content_text = content_div.get_text(separator='\n', strip=True)

        return {
            'title': title,
            'author': author,
            'content_raw': content_text,
            'content_html': content_html,
            'images': images,
            'files_dir': files_dir
        }

    def _parse_generic(self, html, article_id=None):
        """解析通用网页文章 (基础实现)"""
        soup = BeautifulSoup(html, 'html.parser')
        title = soup.title.string if soup.title else "无标题"

        # 寻找可能的正文容器
        body = soup.find('body')
        if not body:
            return None

        # A. 预先提取图片（优先保全）
        img_list = []
        for img in body.find_all('img'):
            src = img.get('src') or img.get('data-src') or img.get('data-original-src') or img.get('srcset')
            if not src: continue
            if ',' in src: src = src.split(',')[0].strip().split(' ')[0]

            # 跳过 Base64 和 极短地址
            if src.startswith('data:') or len(src) < 20: continue

            # 过滤明显的图标类（通过文件名后缀和关键词）
            low_src = src.lower()
            if '.svg' in low_src or '.ico' in low_src: continue

            # 排除常见的 UI 占位符关键词，但要谨慎
            essential_noises = ['/avatar/', '/icon/', 'placeholder', 'pixel.gif', 'loading.gif']
            if any(k in low_src for k in essential_noises): continue

            if src not in img_list:
                img_list.append(src)

        # B. 降噪处理
        noise_selectors = [
            'script', 'style', 'nav', 'footer', 'iframe', 'aside',
            '.nav', '.footer', '.sidebar', '.menu', '.ad', '.ads',
            '#footer', '#sidebar', '.comment', '.comments'
        ]
        # 注意：此处不再轻易删除 'header'，因为很多文章的标题和首图在 header 里
        for selector in noise_selectors:
            for tag in body.select(selector):
                tag.decompose()

        # C. 提取内容 HTML
        content_html = ""
        main_content = body.find('main') or body.find('article') or body.find('div', id='content') or body.find('div', class_='content')
        if main_content:
            content_html = str(main_content)
        else:
            content_html = "".join([str(item) for item in body.contents[:100]]) # 限制一下长度

        # D. 下载图片到本地
        files_dir = ""
        if article_id and img_list:
            print(f"   🖼️  发现 {len(img_list)} 张图片，开始下载...")
            url_mapping, files_dir = self._download_images_for_article(img_list, article_id)
            content_html = self._replace_image_urls_in_html(content_html, url_mapping)
            print(f"   ✅ 图片下载完成")

        return {
            'title': title,
            'author': "未知",
            'content_raw': body.get_text(separator='\n', strip=True),
            'content_html': content_html,
            'images': img_list[:10], # 最多保留10张
            'files_dir': files_dir
        }

if __name__ == "__main__":
    # 测试代码
    collector = ContentCollector()
    res = collector.fetch("https://mp.weixin.qq.com/s/UhQSCacrzkyxrFp2uGgzjQ")
    if res:
        print(f"成功抓取: {res['title']}")
        print(f"作者: {res['author']}")
        print(f"图片数: {len(res['images'])}")
