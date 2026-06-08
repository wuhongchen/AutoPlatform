#!/usr/bin/env python3
"""
批量下载已有灵感记录的图片到本地
"""
import json
import os
import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

# 项目根目录
PROJECT_DIR = Path(__file__).parent.parent
DB_PATH = PROJECT_DIR / "data" / "db" / "autoplatform.db"
IMAGE_DIR = PROJECT_DIR / "data" / "images"

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://mp.weixin.qq.com/",
})


def guess_ext(content_type: str, url: str) -> str:
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
    if "." in url.split("?")[0].split("/")[-1]:
        ext_part = url.split("?")[0].split("/")[-1].split(".")[-1].lower()
        if ext_part in ("jpg", "jpeg", "png", "gif", "webp", "svg", "bmp"):
            return f".{ext_part}"
    return ".jpg"


def download_one_image(url: str, filepath: str) -> bool:
    """下载单张图片"""
    try:
        resp = session.get(url, timeout=20, stream=True)
        resp.raise_for_status()
        with open(filepath, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"  ✗ failed: {url[:60]}... -> {e}")
        return False


def process_record(record_id: str, image_urls: list, content_html: str):
    """处理单条记录：下载图片并更新路径"""
    save_dir = IMAGE_DIR / record_id
    save_dir.mkdir(parents=True, exist_ok=True)

    local_paths = []
    url_map = {}

    for idx, url in enumerate(image_urls):
        # 跳过已本地化的路径
        if url.startswith("/local_images/"):
            local_paths.append(url)
            continue

        ext = guess_ext("", url)
        filename = f"img_{idx:03d}{ext}"
        filepath = str(save_dir / filename)
        local_path = f"/local_images/{record_id}/{filename}"

        if download_one_image(url, filepath):
            local_paths.append(local_path)
            url_map[url] = local_path
        else:
            # 下载失败保留原 URL
            local_paths.append(url)

    # 替换 content_html 中的图片 URL
    if url_map and content_html:
        for orig_url, local_path in url_map.items():
            content_html = content_html.replace(f'src="{orig_url}"', f'src="{local_path}"')
            content_html = content_html.replace(f'data-src="{orig_url}"', f'data-src="{local_path}"')

    return local_paths, content_html, len(url_map)


def main():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 获取所有需要处理的记录
    cursor.execute(
        "SELECT id, images, content_html FROM inspiration_records WHERE images != '[]'"
    )
    rows = cursor.fetchall()

    print(f"总共 {len(rows)} 条记录需要处理")

    total_downloaded = 0
    total_failed = 0

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {}
        for row in rows:
            record_id = row["id"]
            image_urls = json.loads(row["images"])
            content_html = row["content_html"] or ""

            future = executor.submit(process_record, record_id, image_urls, content_html)
            futures[future] = record_id

        for future in as_completed(futures):
            record_id = futures[future]
            try:
                local_paths, new_html, downloaded = future.result()
                total_downloaded += downloaded

                # 更新数据库
                cursor.execute(
                    "UPDATE inspiration_records SET images = ?, content_html = ? WHERE id = ?",
                    (json.dumps(local_paths), new_html, record_id),
                )
                print(f"✓ {record_id[:20]}... : {len(local_paths)} images, {downloaded} downloaded")
            except Exception as e:
                total_failed += 1
                print(f"✗ {record_id[:20]}... : ERROR {e}")

    conn.commit()
    conn.close()

    print(f"\n完成！成功下载 {total_downloaded} 张图片")
    if total_failed:
        print(f"失败记录: {total_failed}")


if __name__ == "__main__":
    main()
