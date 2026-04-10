"""
采集服务
提供内容采集功能
"""

import re
import time
from typing import Dict, List, Optional
import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS


class CollectorService:
    """内容采集服务"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
    
    def fetch_url(self, url: str, timeout: int = 30) -> Dict:
        """获取URL内容"""
        try:
            response = self.session.get(url, timeout=timeout)
            response.encoding = response.apparent_encoding or "utf-8"
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # 提取标题
            title = self._extract_title(soup)
            
            # 提取作者
            author = self._extract_author(soup)
            
            # 提取正文
            content, content_html = self._extract_content(soup)
            
            # 提取图片
            images = self._extract_images(soup, url)
            
            return {
                "success": True,
                "title": title,
                "author": author,
                "content": content,
                "content_html": content_html,
                "images": images,
                "url": url
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "url": url
            }
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """提取标题"""
        # 尝试各种标题选择器
        selectors = [
            "h1.article-title",
            "h1#activity-name",
            "h1.title",
            "h1",
            "#js_content h2",
            "meta[property='og:title']",
            "title"
        ]
        
        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                if elem.name == "meta":
                    return elem.get("content", "").strip()
                return elem.get_text(strip=True)
        
        return "无标题"
    
    def _extract_author(self, soup: BeautifulSoup) -> str:
        """提取作者"""
        selectors = [
            "#js_name",
            ".profile_nickname",
            "#profileBt a",
            "meta[name='author']",
            ".author",
            ".post-author"
        ]
        
        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                if elem.name == "meta":
                    return elem.get("content", "").strip()
                return elem.get_text(strip=True)
        
        return "未知作者"
    
    def _extract_content(self, soup: BeautifulSoup) -> tuple:
        """提取正文"""
        # 移除干扰元素
        for elem in soup.find_all(["script", "style", "nav", "header", "footer", "aside"]):
            elem.decompose()
        
        # 尝试内容选择器
        selectors = [
            "#js_content",
            "article",
            ".post-content",
            ".article-content",
            ".entry-content",
            "#content",
            ".content"
        ]
        
        for selector in selectors:
            elem = soup.select_one(selector)
            if elem and len(elem.get_text(strip=True)) > 100:
                # 清理样式
                for tag in elem.find_all(True):
                    tag.attrs = {k: v for k, v in tag.attrs.items() 
                                if k in ["src", "href", "alt"]}
                
                html = str(elem)
                text = elem.get_text(separator="\n", strip=True)
                return text, html
        
        #  fallback：提取body
        body = soup.find("body")
        if body:
            text = body.get_text(separator="\n", strip=True)
            html = str(body)
            return text, html
        
        return "", ""
    
    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """提取图片"""
        images = []
        
        for img in soup.find_all("img"):
            src = img.get("data-src") or img.get("src", "")
            if src:
                # 处理相对路径
                if src.startswith("//"):
                    src = "https:" + src
                elif src.startswith("/"):
                    src = base_url.rstrip("/") + src
                
                # 过滤二维码和广告图
                if not self._is_qr_or_ad(src, img):
                    images.append(src)
        
        return images
    
    def _is_qr_or_ad(self, src: str, img_tag) -> bool:
        """判断是否是二维码或广告图片"""
        # 根据URL特征判断
        ad_patterns = ["qr", "qrcode", "二维码", "关注", "扫码", "广告", "ad_", "banner"]
        src_lower = src.lower()
        
        for pattern in ad_patterns:
            if pattern in src_lower:
                return True
        
        # 根据尺寸判断（二维码通常是正方形小图）
        width = img_tag.get("width", "")
        height = img_tag.get("height", "")
        
        if width and height:
            try:
                w, h = int(width), int(height)
                # 小正方形图片可能是二维码
                if w < 200 and h < 200 and abs(w - h) < 10:
                    return True
            except ValueError:
                pass
        
        return False
    
    def search_content(self, keyword: str, max_results: int = 5) -> List[Dict]:
        """搜索内容"""
        results = []
        
        try:
            with DDGS() as ddgs:
                for result in ddgs.text(keyword, max_results=max_results):
                    results.append({
                        "title": result.get("title", ""),
                        "url": result.get("href", ""),
                        "snippet": result.get("body", "")
                    })
        except Exception as e:
            print(f"搜索失败: {e}")
        
        return results
