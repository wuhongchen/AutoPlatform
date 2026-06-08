"""
三方技术信息源采集器
统一封装 Discourse / HackerNews / Reddit / Dev.to / GitHub / RSS 等平台的采集能力。

所有采集结果统一输出为 Markdown 格式，走 AutoPlatform 的 Markdown 管道。
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import quote, urljoin

import feedparser
import requests
from bs4 import BeautifulSoup

from app.core.logger import get_logger

logger = get_logger("tech_sources")

# ──────────────────────────────────────────────
# 数据模型
# ──────────────────────────────────────────────

@dataclass
class TechArticle:
    """统一的技术文章模型"""
    title: str
    url: str
    author: str = ""
    summary: str = ""           # 摘要（纯文本）
    content_md: str = ""        # 正文（Markdown）
    content_html: str = ""      # 正文（原始 HTML）
    published_at: str = ""      # ISO 时间
    source_type: str = ""       # discourse / hackernews / reddit / devto / github / rss
    source_name: str = ""       # 来源名称（如 linux.do, HN, r/programming）
    tags: List[str] = field(default_factory=list)
    score: int = 0
    comment_count: int = 0
    metadata: Dict = field(default_factory=dict)


# ──────────────────────────────────────────────
# 基础 HTTP 客户端
# ──────────────────────────────────────────────

class BaseHttpCollector:
    """所有采集器的基类，提供通用 HTTP 能力"""

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "AutoPlatform/2.0 (Tech Source Collector; github.com/wuhongchen/AutoPlatform)",
            "Accept": "application/json, text/html",
        })

    def _get_json(self, url: str, **kwargs) -> dict:
        resp = self.session.get(url, timeout=self.timeout, **kwargs)
        resp.raise_for_status()
        return resp.json()

    def _get_html(self, url: str) -> str:
        resp = self.session.get(url, timeout=self.timeout)
        resp.raise_for_status()
        return resp.text

    @staticmethod
    def _html_to_markdown(html: str) -> str:
        """简单的 HTML → Markdown 降级转换"""
        if not html:
            return ""
        from app.services.markdown_utils import html_to_markdown
        return html_to_markdown(html)

    @staticmethod
    def _strip_html(html: str) -> str:
        if not html:
            return ""
        return BeautifulSoup(html, "html.parser").get_text("\n", strip=True)


# ──────────────────────────────────────────────
# 1. Discourse 论坛采集器
# ──────────────────────────────────────────────

class DiscourseCollector(BaseHttpCollector):
    """Discourse 论坛采集器（linux.do / meta.discourse.org 等）

    Discourse 提供公开 JSON API，无需认证：
    - /latest.json      最新主题
    - /top.json          热门主题
    - /t/{id}.json       主题详情 + 帖子
    - /search.json?q=    搜索
    """

    def fetch_latest(self, forum_url: str, limit: int = 30) -> List[TechArticle]:
        forum_url = forum_url.rstrip("/")
        try:
            data = self._get_json(f"{forum_url}/latest.json")
            topics = data.get("topic_list", {}).get("topics", [])[:limit]
            users = {u["id"]: u for u in data.get("users", [])}
            return [self._topic_to_article(forum_url, t, users) for t in topics]
        except Exception as e:
            logger.error(f"[discourse] fetch_latest failed for {forum_url}: {e}")
            return []

    def fetch_top(self, forum_url: str, period: str = "weekly", limit: int = 30) -> List[TechArticle]:
        forum_url = forum_url.rstrip("/")
        try:
            data = self._get_json(f"{forum_url}/top.json?period={period}")
            topics = data.get("topic_list", {}).get("topics", [])[:limit]
            users = {u["id"]: u for u in data.get("users", [])}
            return [self._topic_to_article(forum_url, t, users) for t in topics]
        except Exception as e:
            logger.error(f"[discourse] fetch_top failed: {e}")
            return []

    def get_topic(self, forum_url: str, topic_id: int) -> Optional[TechArticle]:
        forum_url = forum_url.rstrip("/")
        try:
            data = self._get_json(f"{forum_url}/t/{topic_id}.json")
            title = data.get("title", "")
            posts = data.get("post_stream", {}).get("posts", [])
            first_post = posts[0] if posts else {}
            cooked = first_post.get("cooked", "")
            return TechArticle(
                title=title,
                url=f"{forum_url}/t/{topic_id}",
                author=first_post.get("username", ""),
                content_html=cooked,
                content_md=self._html_to_markdown(cooked),
                summary=self._strip_html(cooked)[:300],
                published_at=first_post.get("created_at", ""),
                source_type="discourse",
                source_name=data.get("category_slug", forum_url.split("//")[-1]),
                tags=data.get("tags", []),
                comment_count=len(posts) - 1,
            )
        except Exception as e:
            logger.error(f"[discourse] get_topic failed: {e}")
            return None

    def search(self, forum_url: str, query: str, limit: int = 20) -> List[TechArticle]:
        forum_url = forum_url.rstrip("/")
        try:
            data = self._get_json(f"{forum_url}/search.json?q={quote(query)}")
            topics = data.get("topics", [])[:limit]
            return [self._topic_to_article(forum_url, t, {}) for t in topics]
        except Exception as e:
            logger.error(f"[discourse] search failed: {e}")
            return []

    def _topic_to_article(self, forum_url: str, topic: dict, users: dict) -> TechArticle:
        tid = topic["id"]
        author_id = topic.get("posters", [{}])[0].get("user_id", "")
        author = users.get(author_id, {}).get("username", "") if author_id else ""
        excerpt = topic.get("excerpt", "")
        return TechArticle(
            title=topic.get("title", ""),
            url=f"{forum_url}/t/{topic.get('slug', tid)}/{tid}",
            author=author,
            summary=self._strip_html(excerpt)[:300] if excerpt else "",
            content_html=excerpt or "",
            content_md=self._html_to_markdown(excerpt) if excerpt else "",
            published_at=topic.get("created_at", ""),
            source_type="discourse",
            source_name=forum_url.split("//")[-1].split(".")[0],
            tags=topic.get("tags", []),
            score=topic.get("like_count", 0),
            comment_count=topic.get("posts_count", 0) - 1,
        )


# ──────────────────────────────────────────────
# 2. Hacker News 采集器
# ──────────────────────────────────────────────

class HackerNewsCollector(BaseHttpCollector):
    """Hacker News 采集器

    使用官方 Firebase API，完全免费无需认证：
    - https://hacker-news.firebaseio.com/v0/
    """

    API_BASE = "https://hacker-news.firebaseio.com/v0"
    ITEM_URL = "https://news.ycombinator.com/item?id={}"

    def fetch_top(self, limit: int = 30) -> List[TechArticle]:
        return self._fetch_stories("topstories", limit)

    def fetch_new(self, limit: int = 30) -> List[TechArticle]:
        return self._fetch_stories("newstories", limit)

    def fetch_best(self, limit: int = 30) -> List[TechArticle]:
        return self._fetch_stories("beststories", limit)

    def _fetch_stories(self, endpoint: str, limit: int) -> List[TechArticle]:
        try:
            ids = self._get_json(f"{self.API_BASE}/{endpoint}.json")[:limit * 2]
            articles = []
            for item_id in ids[:limit * 2]:
                article = self._get_item(item_id)
                if article and article.url:
                    articles.append(article)
                if len(articles) >= limit:
                    break
            return articles
        except Exception as e:
            logger.error(f"[hn] fetch failed: {e}")
            return []

    def _get_item(self, item_id: int) -> Optional[TechArticle]:
        try:
            data = self._get_json(f"{self.API_BASE}/item/{item_id}.json")
            if not data:
                return None
            item_type = data.get("type", "")
            if item_type not in ("story", "job"):
                return None

            text = data.get("text", "")
            return TechArticle(
                title=data.get("title", ""),
                url=data.get("url") or self.ITEM_URL.format(item_id),
                author=data.get("by", ""),
                content_html=text,
                content_md=self._html_to_markdown(text) if text else "",
                summary=self._strip_html(text)[:300] if text else "",
                published_at=datetime.fromtimestamp(data.get("time", 0)).isoformat(),
                source_type="hackernews",
                source_name="Hacker News",
                score=data.get("score", 0),
                comment_count=data.get("descendants", 0),
            )
        except Exception:
            return None


# ──────────────────────────────────────────────
# 3. Reddit 采集器
# ──────────────────────────────────────────────

class RedditCollector(BaseHttpCollector):
    """Reddit 采集器

    使用 Reddit 公开 JSON API（`.json` 后缀），无需认证。
    限速：60 req/min，已内置延迟。
    """

    def __init__(self, timeout: int = 30):
        super().__init__(timeout)
        self.session.headers["User-Agent"] = "AutoPlatform/2.0 (by /u/autoplatform_bot)"

    def fetch_subreddit(self, subreddit: str, sort: str = "hot", limit: int = 25) -> List[TechArticle]:
        try:
            url = f"https://www.reddit.com/r/{subreddit}/{sort}.json?limit={limit}"
            data = self._get_json(url)
            posts = data.get("data", {}).get("children", [])
            articles = []
            for p in posts:
                d = p["data"]
                if d.get("stickied"):
                    continue
                selftext = d.get("selftext", "")
                articles.append(TechArticle(
                    title=d.get("title", ""),
                    url=d.get("url", f"https://reddit.com{d.get('permalink', '')}"),
                    author=d.get("author", ""),
                    content_html=d.get("selftext_html", "") or "",
                    content_md=self._html_to_markdown(d.get("selftext_html", "")) if selftext else "",
                    summary=self._strip_html(selftext)[:300] if selftext else d.get("title", ""),
                    published_at=datetime.fromtimestamp(d.get("created_utc", 0)).isoformat(),
                    source_type="reddit",
                    source_name=f"r/{subreddit}",
                    score=d.get("score", 0),
                    comment_count=d.get("num_comments", 0),
                    tags=[subreddit],
                ))
                time.sleep(0.1)  # 礼貌限速
            return articles
        except Exception as e:
            logger.error(f"[reddit] fetch failed for r/{subreddit}: {e}")
            return []

    def search(self, query: str, limit: int = 25) -> List[TechArticle]:
        try:
            url = f"https://www.reddit.com/search.json?q={quote(query)}&limit={limit}"
            data = self._get_json(url)
            posts = data.get("data", {}).get("children", [])
            articles = []
            for p in posts:
                d = p["data"]
                selftext = d.get("selftext", "")
                articles.append(TechArticle(
                    title=d.get("title", ""),
                    url=d.get("url", ""),
                    author=d.get("author", ""),
                    content_html=d.get("selftext_html", "") or "",
                    content_md=self._html_to_markdown(d.get("selftext_html", "")) if selftext else "",
                    summary=self._strip_html(selftext)[:300] if selftext else "",
                    published_at=datetime.fromtimestamp(d.get("created_utc", 0)).isoformat(),
                    source_type="reddit",
                    source_name="search",
                    score=d.get("score", 0),
                    comment_count=d.get("num_comments", 0),
                ))
            return articles
        except Exception as e:
            logger.error(f"[reddit] search failed: {e}")
            return []


# ──────────────────────────────────────────────
# 4. Dev.to 采集器
# ──────────────────────────────────────────────

class DevToCollector(BaseHttpCollector):
    """Dev.to 采集器

    使用 Dev.to 公开 REST API (Forem API)，无需认证：
    - https://dev.to/api/articles
    """

    API_BASE = "https://dev.to/api"

    def fetch_articles(self, tag: str = "", top: str = "", limit: int = 30) -> List[TechArticle]:
        try:
            params = {"per_page": limit}
            if tag:
                params["tag"] = tag
            if top:
                params["top"] = top
            qs = "&".join(f"{k}={quote(str(v))}" for k, v in params.items())
            data = self._get_json(f"{self.API_BASE}/articles?{qs}")
            articles = []
            for d in data:
                body_md = d.get("body_markdown", "") or d.get("description", "")
                articles.append(TechArticle(
                    title=d.get("title", ""),
                    url=d.get("url", ""),
                    author=d.get("user", {}).get("name", ""),
                    content_md=body_md,  # Dev.to 原生就是 Markdown！
                    content_html=d.get("body_html", ""),
                    summary=d.get("description", ""),
                    published_at=d.get("published_at", ""),
                    source_type="devto",
                    source_name="dev.to",
                    tags=d.get("tag_list", []),
                    score=d.get("positive_reactions_count", 0),
                    comment_count=d.get("comments_count", 0),
                ))
            return articles
        except Exception as e:
            logger.error(f"[devto] fetch failed: {e}")
            return []

    def get_article(self, article_id: int) -> Optional[TechArticle]:
        try:
            d = self._get_json(f"{self.API_BASE}/articles/{article_id}")
            return TechArticle(
                title=d.get("title", ""),
                url=d.get("url", ""),
                author=d.get("user", {}).get("name", ""),
                content_md=d.get("body_markdown", ""),
                content_html=d.get("body_html", ""),
                summary=d.get("description", ""),
                published_at=d.get("published_at", ""),
                source_type="devto",
                source_name="dev.to",
                tags=d.get("tag_list", []),
                score=d.get("positive_reactions_count", 0),
                comment_count=d.get("comments_count", 0),
            )
        except Exception as e:
            logger.error(f"[devto] get_article failed: {e}")
            return None


# ──────────────────────────────────────────────
# 5. GitHub Trending 采集器
# ──────────────────────────────────────────────

class GitHubTrendingCollector(BaseHttpCollector):
    """GitHub Trending / 搜索采集器

    - Trending 页面需要简易爬虫
    - 搜索使用 GitHub REST API (未认证限速 60 req/h)
    """

    def fetch_trending(self, language: str = "", since: str = "daily") -> List[TechArticle]:
        """从 GitHub Trending 页面抓取"""
        try:
            lang_path = f"/{language}" if language else ""
            url = f"https://github.com/trending{lang_path}?since={since}"
            html = self._get_html(url)
            soup = BeautifulSoup(html, "html.parser")
            articles = []
            for repo in soup.select("article.Box-row")[:30]:
                h2 = repo.select_one("h2 a")
                if not h2:
                    continue
                name = h2.get_text(strip=True).replace("\n", "").replace(" ", "")
                desc_el = repo.select_one("p")
                desc = desc_el.get_text(strip=True) if desc_el else ""
                lang_el = repo.select_one('[itemprop="programmingLanguage"]')
                lang = lang_el.get_text(strip=True) if lang_el else ""
                stars_el = repo.select_one(".Link--muted")
                stars = stars_el.get_text(strip=True).replace(",", "") if stars_el else "0"

                articles.append(TechArticle(
                    title=f"{name}: {desc}" if desc else name,
                    url=f"https://github.com/{name}",
                    author=name.split("/")[0] if "/" in name else "",
                    summary=desc,
                    content_md=f"# {name}\n\n{desc}\n\n- 语言: {lang}\n- Stars: {stars}\n- 链接: https://github.com/{name}",
                    content_html=f"<h1>{name}</h1><p>{desc}</p>",
                    published_at=datetime.now().isoformat(),
                    source_type="github",
                    source_name="GitHub Trending",
                    tags=[lang] if lang else [],
                    score=int(stars) if stars.isdigit() else 0,
                ))
            return articles
        except Exception as e:
            logger.error(f"[github] trending failed: {e}")
            return []

    def search_repos(self, query: str, sort: str = "stars", limit: int = 20) -> List[TechArticle]:
        try:
            url = f"https://api.github.com/search/repositories?q={quote(query)}&sort={sort}&per_page={limit}"
            data = self._get_json(url)
            articles = []
            for item in data.get("items", []):
                desc = item.get("description", "") or ""
                articles.append(TechArticle(
                    title=item.get("full_name", ""),
                    url=item.get("html_url", ""),
                    author=item.get("owner", {}).get("login", ""),
                    summary=desc,
                    content_md=f"# {item.get('full_name')}\n\n{desc}\n\n- Stars: {item.get('stargazers_count')}\n- Language: {item.get('language', '')}\n- {item.get('html_url')}",
                    content_html=f"<h1>{item.get('full_name')}</h1><p>{desc}</p>",
                    published_at=item.get("created_at", ""),
                    source_type="github",
                    source_name="GitHub Search",
                    tags=[item.get("language", "")] if item.get("language") else [],
                    score=item.get("stargazers_count", 0),
                ))
            return articles
        except Exception as e:
            logger.error(f"[github] search failed: {e}")
            return []


# ──────────────────────────────────────────────
# 6. 通用 RSS/Atom 采集器
# ──────────────────────────────────────────────

class RSSCollector(BaseHttpCollector):
    """通用 RSS/Atom Feed 采集器，使用 feedparser"""

    def fetch(self, feed_url: str, limit: int = 30) -> List[TechArticle]:
        try:
            feed = feedparser.parse(feed_url)
            if feed.bozo and not feed.entries:
                logger.warning(f"[rss] parse warning for {feed_url}: {feed.bozo_exception}")
            articles = []
            for entry in feed.entries[:limit]:
                content_html = ""
                if hasattr(entry, "content"):
                    content_html = entry.content[0].get("value", "") if entry.content else ""
                if not content_html:
                    content_html = entry.get("summary", "") or entry.get("description", "")
                articles.append(TechArticle(
                    title=entry.get("title", ""),
                    url=entry.get("link", ""),
                    author=entry.get("author", ""),
                    summary=entry.get("summary", "") or self._strip_html(content_html)[:300],
                    content_html=content_html,
                    content_md=self._html_to_markdown(content_html),
                    published_at=entry.get("published", "") or entry.get("updated", ""),
                    source_type="rss",
                    source_name=feed.feed.get("title", feed_url),
                    tags=[t.get("term", "") for t in entry.get("tags", [])] if hasattr(entry, "tags") else [],
                ))
            return articles
        except Exception as e:
            logger.error(f"[rss] fetch failed for {feed_url}: {e}")
            return []


# ──────────────────────────────────────────────
# 统一采集入口
# ──────────────────────────────────────────────

class TechSourceHub:
    """统一的技术信息源采集入口。

    用法:
        hub = TechSourceHub()
        articles = hub.fetch("discourse", forum_url="https://linux.do")
        articles = hub.fetch("hackernews", sort="top")
        articles = hub.fetch("reddit", subreddit="programming")
        articles = hub.fetch("devto", tag="python")
        articles = hub.fetch("github", language="python")
        articles = hub.fetch("rss", feed_url="https://example.com/feed.xml")
    """

    def __init__(self):
        self.discourse = DiscourseCollector()
        self.hn = HackerNewsCollector()
        self.reddit = RedditCollector()
        self.devto = DevToCollector()
        self.github = GitHubTrendingCollector()
        self.rss = RSSCollector()

    # 预置的优质技术信息源
    PRESET_SOURCES = {
        "discourse": [
            {"name": "linux.do", "forum_url": "https://linux.do",
             "desc": "中文技术社区，涵盖编程、AI、DevOps 等热门话题，Discourse 架构"},
            {"name": "Elixir Forum", "forum_url": "https://elixirforum.com",
             "desc": "Elixir / Phoenix / Erlang 技术讨论，社区活跃"},
        ],
        "hackernews": [
            {"name": "HN 热门", "sort": "top",
             "desc": "Hacker News 首页热门，全球技术动态风向标"},
            {"name": "HN 最新", "sort": "new",
             "desc": "Hacker News 实时最新提交，第一时间捕捉新技术话题"},
            {"name": "HN 最佳", "sort": "best",
             "desc": "Hacker News 近期高票最佳内容精选"},
        ],
        "reddit": [
            {"name": "r/programming", "subreddit": "programming",
             "desc": "Reddit 编程板块，泛技术话题讨论"},
            {"name": "r/MachineLearning", "subreddit": "MachineLearning",
             "desc": "机器学习论文解读、实战经验、最新进展"},
            {"name": "r/Python", "subreddit": "Python",
             "desc": "Python 语言生态、框架、工具讨论"},
            {"name": "r/rust", "subreddit": "rust",
             "desc": "Rust 语言开发、性能优化、社区动态"},
            {"name": "r/golang", "subreddit": "golang",
             "desc": "Go 语言实战技巧、标准库、并发编程"},
            {"name": "r/webdev", "subreddit": "webdev",
             "desc": "前端/后端/全栈 Web 开发技术与趋势"},
        ],
        "devto": [
            {"name": "dev.to Python", "tag": "python",
             "desc": "Dev.to 社区 Python 标签，教程、经验、工具推荐"},
            {"name": "dev.to Rust", "tag": "rust",
             "desc": "Dev.to 社区 Rust 标签，系统编程与性能优化"},
            {"name": "dev.to AI", "tag": "ai",
             "desc": "Dev.to 社区 AI/大模型标签，LLM 应用与实践"},
            {"name": "dev.to WebDev", "tag": "webdev",
             "desc": "Dev.to 社区前端/全栈开发标签"},
        ],
        "github": [
            {"name": "GitHub Python 趋势", "language": "python",
             "desc": "Python 开源项目每日 Trending，发现热门新库"},
            {"name": "GitHub Rust 趋势", "language": "rust",
             "desc": "Rust 开源项目每日 Trending"},
            {"name": "GitHub 全语言趋势", "language": "",
             "desc": "GitHub Trending 全语言每日热门项目"},
        ],
        "rss": [
            {"name": "Hacker News RSS", "feed_url": "https://hnrss.org/frontpage",
             "desc": "Hacker News 首页 RSS，含文章链接和摘要"},
            {"name": "TechCrunch", "feed_url": "https://techcrunch.com/feed/",
             "desc": "全球知名科技媒体，创业、融资、新产品"},
            {"name": "Ars Technica", "feed_url": "https://feeds.arstechnica.com/arstechnica/index",
             "desc": "深度技术分析，硬件、软件、科学、政策"},
        ],
    }

    def list_presets(self) -> Dict[str, List[Dict]]:
        """列出所有预置信息源"""
        return dict(self.PRESET_SOURCES)

    def fetch(self, source_type: str, **kwargs) -> List[TechArticle]:
        """统一采集入口

        Args:
            source_type: discourse | hackernews | reddit | devto | github | rss
            **kwargs: 各采集器的特定参数

        Returns:
            List[TechArticle] 统一的技术文章列表
        """
        limit = kwargs.pop("limit", 30)

        if source_type == "discourse":
            forum_url = kwargs.get("forum_url", "")
            sort = kwargs.get("sort", "latest")
            if sort == "top":
                return self.discourse.fetch_top(forum_url, kwargs.get("period", "weekly"), limit)
            return self.discourse.fetch_latest(forum_url, limit)

        elif source_type == "hackernews":
            sort = kwargs.get("sort", "top")
            if sort == "new":
                return self.hn.fetch_new(limit)
            if sort == "best":
                return self.hn.fetch_best(limit)
            return self.hn.fetch_top(limit)

        elif source_type == "reddit":
            subreddit = kwargs.get("subreddit", "programming")
            sort = kwargs.get("sort", "hot")
            return self.reddit.fetch_subreddit(subreddit, sort, limit)

        elif source_type == "devto":
            tag = kwargs.get("tag", "")
            top = kwargs.get("top", "")
            return self.devto.fetch_articles(tag, top, limit)

        elif source_type == "github":
            language = kwargs.get("language", "")
            since = kwargs.get("since", "daily")
            return self.github.fetch_trending(language, since)

        elif source_type == "rss":
            feed_url = kwargs.get("feed_url", "")
            return self.rss.fetch(feed_url, limit)

        else:
            logger.warning(f"[tech_sources] unknown source type: {source_type}")
            return []

    def collect_all_presets(self, limit_per_source: int = 15) -> List[TechArticle]:
        """一键采集所有预置信息源"""
        all_articles = []
        for source_type, presets in self.PRESET_SOURCES.items():
            for preset in presets[:2]:  # 每类最多取 2 个预设
                try:
                    kwargs = dict(preset)
                    kwargs.pop("name", None)
                    kwargs["limit"] = limit_per_source
                    articles = self.fetch(source_type, **kwargs)
                    all_articles.extend(articles)
                    logger.info(f"[tech_sources] {source_type}/{preset['name']}: {len(articles)} articles")
                except Exception as e:
                    logger.warning(f"[tech_sources] skip {source_type}/{preset.get('name')}: {e}")
        logger.info(f"[tech_sources] collected {len(all_articles)} articles total")
        return all_articles
