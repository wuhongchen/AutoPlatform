#!/usr/bin/env python3
"""
单篇文章采集脚本 - 只采集内容，不进行AI改写
用法: python3 core/capture_article.py <url> [--account-id=<id>]
"""
import os
import sys
import argparse

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from config import Config
from modules.workflow_store import WorkflowStore
from modules.collector import ContentCollector


def _now_str():
    return __import__('time').strftime("%Y-%m-%d %H:%M:%S")


def capture_article(url: str, account_id: str = "default"):
    """采集单篇文章内容"""
    print(f"🔍 开始采集文章: {url}")
    print(f"📁 账户: {account_id}")
    
    workflow = WorkflowStore(Config.WORKFLOW_DB)
    collector = ContentCollector()
    
    try:
        # 1. 检查是否已存在
        existing = workflow.list_inspiration(account_id, limit=1000)
        for item in existing:
            if item.get("url") == url:
                record_id = item.get("record_id")
                print(f"⚠️ 文章已存在: {record_id}")
                
                # 检查是否已有内容
                content = workflow.get_article_content(record_id, account_id)
                if content and content.get("original_html"):
                    print(f"✅ 文章内容已采集，跳过")
                    return {"record_id": record_id, "status": "exists"}
                
                # 已有记录但无内容，继续采集内容
                print(f"📝 记录存在但无内容，开始采集...")
                break
        else:
            record_id = None
        
        # 2. 抓取文章
        print(f"📥 正在抓取文章内容...")
        article = collector.fetch(url)
        
        if not article or not (article.get("content_text") or article.get("content_raw")):
            print(f"❌ 抓取失败: 内容为空")
            return {"error": "抓取失败，内容为空"}
        
        title = article.get("title", "未命名")
        content_text = article.get("content_text") or article.get("content_raw", "")
        print(f"✅ 抓取成功: {title[:50]}...")
        print(f"   内容长度: {len(content_text)} 字符")
        print(f"   图片数量: {len(article.get('images', []))} 张")
        
        # 3. 保存到灵感库
        if record_id:
            # 更新现有记录 - 使用upsert
            existing = workflow.get_inspiration(record_id, account_id)
            if existing:
                existing["title"] = title
                existing["status"] = "采集完成"
                existing["updated_at"] = _now_str()
                workflow.upsert_inspiration(existing)
        else:
            # 创建新记录
            record_id = f"ins_{__import__('uuid').uuid4().hex[:16]}"
            inspiration = {
                "record_id": record_id,
                "account_id": account_id,
                "title": title,
                "url": url,
                "source_name": "手动采集",
                "status": "采集完成",
                "captured_at": _now_str(),
                "updated_at": _now_str(),
            }
            workflow.upsert_inspiration(inspiration)
        
        # 4. 保存文章内容
        content_html = article.get("content_html", "")
        content_text = article.get("content_text") or article.get("content_raw", "")
        # 确保original_data包含正确的字段
        original_data = dict(article)
        if "content_text" not in original_data and "content_raw" in original_data:
            original_data["content_text"] = original_data["content_raw"]
        
        workflow.save_article_content(
            record_id=record_id,
            account_id=account_id,
            original_html=content_html,
            original_text=content_text,
            original_data=original_data
        )
        
        print(f"✅ 采集完成: {record_id}")
        print(f"   状态: 采集完成")
        
        return {
            "record_id": record_id,
            "title": title,
            "status": "采集完成"
        }
        
    except Exception as e:
        print(f"❌ 采集失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="采集单篇文章")
    parser.add_argument("url", help="文章URL")
    parser.add_argument("--account-id", default="default", help="账户ID")
    
    args = parser.parse_args()
    
    result = capture_article(args.url, args.account_id)
    
    if result.get("error"):
        print(f"\n❌ 失败: {result['error']}")
        sys.exit(1)
    else:
        print(f"\n✅ 成功: {result.get('record_id')}")
        sys.exit(0)


if __name__ == "__main__":
    main()
