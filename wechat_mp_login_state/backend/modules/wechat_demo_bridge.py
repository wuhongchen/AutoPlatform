import json
import os
import re
import subprocess
import tempfile
from typing import Dict, Optional

from bs4 import BeautifulSoup


def _env_truthy(name: str, default: str = "0") -> bool:
    val = (os.getenv(name, default) or "").strip().lower()
    return val in {"1", "true", "yes", "on"}


class WechatDemoBridge:
    """
    可选接入 wechat-demo-cli 的桥接器。

    设计目标：
    1) 不改变现有抓取入口签名；
    2) demo 不可用时自动回退；
    3) 只返回与 ContentCollector 兼容的数据结构。
    """

    def __init__(self):
        self.enabled = _env_truthy("OPENCLAW_WECHAT_DEMO_ENABLED", "0")
        self.cli_path = (os.getenv("OPENCLAW_WECHAT_DEMO_CLI") or "").strip()
        self.python_bin = (os.getenv("OPENCLAW_WECHAT_DEMO_PYTHON") or "python3").strip()
        try:
            self.timeout = int((os.getenv("OPENCLAW_WECHAT_DEMO_TIMEOUT") or "180").strip())
        except Exception:
            self.timeout = 180

    def is_ready(self) -> bool:
        if not self.enabled:
            return False
        return bool(self.cli_path and os.path.isfile(self.cli_path))

    def fetch(self, url: str) -> Optional[Dict]:
        if not self.is_ready():
            return None
        if not url:
            return None

        tmp_path = ""
        try:
            with tempfile.NamedTemporaryFile(prefix="wechat_demo_", suffix=".html", delete=False) as f:
                tmp_path = f.name

            cmd = [
                self.python_bin,
                self.cli_path,
                "fetch-content",
                "--url",
                url,
                "--output",
                tmp_path,
            ]
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=max(30, self.timeout),
            )

            if proc.returncode != 0:
                print(f"⚠️ wechat-demo 抓取失败，自动回退默认抓取器: {proc.stderr.strip() or proc.stdout.strip()}")
                return None

            raw_stdout = proc.stdout or ""
            meta = self._extract_last_json(raw_stdout)

            content_html = ""
            if tmp_path and os.path.exists(tmp_path):
                try:
                    with open(tmp_path, "r", encoding="utf-8") as f:
                        content_html = f.read()
                except Exception:
                    content_html = ""

            if not content_html.strip():
                print("⚠️ wechat-demo 返回正文为空，自动回退默认抓取器。")
                return None

            parsed = self._normalize_content(content_html)
            if not parsed:
                return None

            parsed["title"] = (meta.get("title") or parsed.get("title") or "无标题").strip()
            parsed["author"] = (meta.get("author") or parsed.get("author") or "未知作者").strip()
            parsed["source"] = "wechat-demo-cli"
            return parsed
        except Exception as e:
            print(f"⚠️ wechat-demo 桥接异常，自动回退默认抓取器: {e}")
            return None
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

    def _extract_last_json(self, text: str) -> Dict:
        if not text:
            return {}
        matches = re.findall(r"\{[\s\S]*?\}", text)
        for raw in reversed(matches):
            try:
                obj = json.loads(raw)
                if isinstance(obj, dict):
                    return obj
            except Exception:
                continue
        return {}

    def _normalize_content(self, html: str) -> Optional[Dict]:
        soup = BeautifulSoup(html, "html.parser")

        for tag in soup.select("script,style,iframe,noscript"):
            tag.decompose()

        title = ""
        h1 = soup.find("h1")
        if h1:
            title = h1.get_text(strip=True)

        images = []
        for img in soup.find_all("img"):
            src = img.get("data-src") or img.get("src")
            if src:
                images.append(src)
                img["src"] = src

        content_html = str(soup)
        content_raw = soup.get_text(separator="\n", strip=True)
        if not content_raw.strip():
            return None

        return {
            "title": title or "无标题",
            "author": "未知作者",
            "content_raw": content_raw,
            "content_html": content_html,
            "images": images,
        }

