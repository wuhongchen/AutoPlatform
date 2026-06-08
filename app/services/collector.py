"""
采集服务
提供内容采集功能
"""

import hashlib
import os
import re
import time
from typing import Dict, List, Optional, Tuple
import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from app.core.logger import get_logger

logger = get_logger("collector")


class CollectorService:
    """内容采集服务"""

    ALLOWED_CONTENT_ATTRS = {"src", "data-src", "href", "alt"}
    
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

    def extract_content_from_html(self, html: str) -> tuple:
        """从已有 HTML 字符串中提取正文文本和正文 HTML。"""
        if not html:
            return "", ""
        soup = BeautifulSoup(html, "html.parser")
        return self._extract_content(soup)
    
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
                html = self.sanitize_content_html(str(elem))
                text = BeautifulSoup(html, "html.parser").get_text(separator="\n", strip=True)
                return text, html
        
        #  fallback：提取body
        body = soup.find("body")
        if body:
            html = self.sanitize_content_html(str(body))
            text = BeautifulSoup(html, "html.parser").get_text(separator="\n", strip=True)
            return text, html
        
        return "", ""

    def sanitize_content_html(self, html: str) -> str:
        """清理采集正文中的隐藏样式，仅保留关键内容属性。"""
        if not html:
            return ""

        fragment = BeautifulSoup(html, "html.parser")
        for tag in fragment.find_all(True):
            tag.attrs = {
                key: value
                for key, value in tag.attrs.items()
                if key in self.ALLOWED_CONTENT_ATTRS
            }
        return str(fragment)
    
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
    
    def download_images(self, image_urls: List[str], record_id: str, 
                        base_dir: str = "data/images") -> Tuple[List[str], Dict[str, str]]:
        """下载图片到本地，返回本地路径列表和URL映射
        
        Returns:
            (local_paths, url_map): local_paths 是本地访问路径列表，
                                    url_map 是 {原URL: 本地路径} 映射
        """
        if not image_urls:
            return [], {}
        
        save_dir = os.path.join(base_dir, record_id)
        os.makedirs(save_dir, exist_ok=True)
        
        local_paths = []
        url_map = {}
        
        for idx, url in enumerate(image_urls):
            try:
                # 跳过本地路径（已下载的）
                if url.startswith("/local_images/"):
                    local_paths.append(url)
                    continue
                
                # 下载图片
                resp = self.session.get(url, timeout=15, stream=True)
                resp.raise_for_status()
                
                # 判断扩展名
                content_type = resp.headers.get("Content-Type", "")
                ext = self._guess_ext(content_type, url)
                
                # 生成文件名
                filename = f"img_{idx:03d}{ext}"
                filepath = os.path.join(save_dir, filename)
                
                with open(filepath, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                local_path = f"/local_images/{record_id}/{filename}"
                local_paths.append(local_path)
                url_map[url] = local_path
                logger.info(f"[download] {url} -> {filepath}")
                
            except Exception as e:
                logger.warning(f"[download] failed {url}: {e}")
                # 下载失败时保留原始URL
                local_paths.append(url)
        
        return local_paths, url_map
    
    def _guess_ext(self, content_type: str, url: str) -> str:
        """根据Content-Type和URL猜测文件扩展名"""
        type_map = {
            "image/jpeg": ".jpg",
            "image/jpg": ".jpg",
            "image/png": ".png",
            "image/gif": ".gif",
            "image/webp": ".webp",
            "image/svg+xml": ".svg",
            "image/bmp": ".bmp",
        }
        for mime, ext in type_map.items():
            if mime in content_type.lower():
                return ext
        # 从URL提取
        if "." in url.split("?")[0].split("/")[-1]:
            ext_part = url.split("?")[0].split("/")[-1].split(".")[-1].lower()
            if ext_part in ("jpg", "jpeg", "png", "gif", "webp", "svg", "bmp"):
                return f".{ext_part}"
        return ".jpg"
    
    def rewrite_image_urls(self, html: str, url_map: Dict[str, str]) -> str:
        """将HTML中的图片URL替换为本地路径"""
        if not url_map:
            return html

        soup = BeautifulSoup(html or "", "html.parser")
        for img in soup.find_all("img"):
            source = img.get("data-src") or img.get("src", "")
            if not source:
                continue
            local_path = url_map.get(source)
            if not local_path:
                continue
            img["src"] = local_path
            img["data-src"] = local_path

        return str(soup)

    def relink_local_images(self, html: str, local_images: List[str]) -> str:
        """按顺序将正文图片重定向到本地路径，用于修复历史数据。"""
        if not html or not local_images:
            return html

        soup = BeautifulSoup(html, "html.parser")
        image_iter = iter(local_images)
        changed = False
        for img in soup.find_all("img"):
            try:
                local_path = next(image_iter)
            except StopIteration:
                break
            if not local_path.startswith("/local_images/"):
                continue
            current_src = img.get("src") or ""
            current_data_src = img.get("data-src") or ""
            if current_src == local_path and current_data_src == local_path:
                continue
            img["src"] = local_path
            img["data-src"] = local_path
            changed = True

        return str(soup) if changed else html
    
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
            logger.warning(f"搜索失败: {e}")

        return results
