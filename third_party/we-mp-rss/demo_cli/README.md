# WeChat Core Demo CLI

This is an independent CLI demo for core capabilities extracted from this project:

- QR login
- Add mp account (local demo state)
- Fetch article list
- Fetch article content
- Switch account

## Location

- CLI: `/Users/hongchen/Downloads/code/we-mp-rss/demo_cli/wechat_demo_cli.py`
- Local state: `/Users/hongchen/Downloads/code/we-mp-rss/demo_cli/data/state.json`

## Quick Start

Run from repo root:

```bash
pip install -r requirements.txt
# optional, if config.yaml does not exist:
cp config.example.yaml config.yaml

python3 demo_cli/wechat_demo_cli.py login
```

Generate QR only (do not wait):

```bash
python3 demo_cli/wechat_demo_cli.py login --no-wait
```

Print QR in terminal:

```bash
python3 demo_cli/wechat_demo_cli.py login --qr-display terminal
```

Open QR image with system viewer:

```bash
python3 demo_cli/wechat_demo_cli.py login --qr-display open
```

Print in terminal and open viewer (default):

```bash
python3 demo_cli/wechat_demo_cli.py login --qr-display both
```

If your environment is slow to persist token/cookie after scan, increase wait time:

```bash
python3 demo_cli/wechat_demo_cli.py login --qr-display both --token-wait-timeout 60 --thread-join-timeout 20
```

Check login status:

```bash
python3 demo_cli/wechat_demo_cli.py status
```

## MP Search and Add

Search mp:

```bash
python3 demo_cli/wechat_demo_cli.py search-mp "AI"
```

Add one from search result (pick index starts at 1):

```bash
python3 demo_cli/wechat_demo_cli.py add-mp --keyword "AI" --pick 1
```

List local mp records:

```bash
python3 demo_cli/wechat_demo_cli.py list-mp
```

## Article List

Fetch article list by saved mp id:

```bash
python3 demo_cli/wechat_demo_cli.py pull-articles --mp-id MP_WXS_xxx --pages 1 --mode api
```

Fetch with content at the same time:

```bash
python3 demo_cli/wechat_demo_cli.py pull-articles --mp-id MP_WXS_xxx --pages 1 --mode api --with-content
```

List fetched articles:

```bash
python3 demo_cli/wechat_demo_cli.py list-articles --mp-id MP_WXS_xxx
```

## Content Fetch

Fetch content by URL:

```bash
python3 demo_cli/wechat_demo_cli.py fetch-content --url "https://mp.weixin.qq.com/s/xxxx"
```

Fetch content by stored article id:

```bash
python3 demo_cli/wechat_demo_cli.py fetch-content --article-id ARTICLE_ID --mp-id MP_WXS_xxx
```

Save content HTML to file:

```bash
python3 demo_cli/wechat_demo_cli.py fetch-content --url "https://mp.weixin.qq.com/s/xxxx" --output ./demo_cli/data/article.html
```

Batch fetch content from fetched article list:

```bash
python3 demo_cli/wechat_demo_cli.py batch-fetch-content --mp-id MP_WXS_xxx --limit 10
```

Batch fetch all cached article lists:

```bash
python3 demo_cli/wechat_demo_cli.py batch-fetch-content
```

Skip existing html files and continue on errors:

```bash
python3 demo_cli/wechat_demo_cli.py batch-fetch-content --mp-id MP_WXS_xxx --skip-existing --continue-on-error
```

## Switch Account

```bash
python3 demo_cli/wechat_demo_cli.py switch-account
```

Or provide username if needed:

```bash
python3 demo_cli/wechat_demo_cli.py switch-account --username target_username
```

## Notes

- This demo is intentionally minimal and CLI-focused.
- It reuses existing project login/session/token behavior.
- If token/cookie is missing or expired, run `login` again.
- If login reports missing `PIL`, install it in current venv:

```bash
python3 -m pip install pillow
```
