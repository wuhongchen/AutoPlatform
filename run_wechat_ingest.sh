#!/bin/bash

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

if [ "$#" -eq 0 ]; then
  cat <<'EOF'
用法: ./run_wechat_ingest.sh [--account-id <id>] <command> [args]

常用示例:
1) 查看状态:
   ./run_wechat_ingest.sh status

2) 扫码登录 (仅生成二维码并返回):
   ./run_wechat_ingest.sh --account-id default login --no-wait --qr-display both

3) 检索并关注公众号:
   ./run_wechat_ingest.sh --account-id default search-mp "机器之心" --limit 8
   ./run_wechat_ingest.sh --account-id default add-mp --keyword "机器之心" --pick 1

4) 拉取文章并同步灵感库:
   ./run_wechat_ingest.sh --account-id default pull-articles --mp-id MP_WXS_xxx --pages 1 --mode api
   ./run_wechat_ingest.sh --account-id default sync-inspiration --mp-id MP_WXS_xxx --limit 20

5) 全流程:
   ./run_wechat_ingest.sh --account-id default full-flow --keyword "机器之心" --pick 1 --pages 1 --sync-limit 20
EOF
  exit 0
fi

exec python3 scripts/wechat_ingest_cli.py "$@"
