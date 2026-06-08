# WeChat MP Login State Extraction

This folder is a non-destructive extraction of the WeChat Official Account QR-login-state feature from the main project.

The original project files were copied here so the feature can be reviewed, moved, or refactored without changing the currently running app.

## Scope

This extraction covers the login-state based WeChat MP ingest flow:

1. Generate and display a WeChat Official Account Platform QR code.
2. Wait for scan confirmation and persist token/cookie through the demo runtime.
3. Check login status and QR image readiness.
4. Search and add public accounts.
5. Pull article lists from followed public accounts.
6. Optionally fetch article content through the login-state bridge.
7. Sync cached articles into the inspiration table.
8. Expose the flow through CLI, Flask API routes, and the Vue "雷达舱" UI.

It does not include normal WeChat publishing by `WECHAT_APPID` / `WECHAT_SECRET`, except where config is needed by the surrounding project.

## Directory Map

```text
wechat_mp_login_state/
  backend/
    config.py
    admin_accounts.py
    run_wechat_ingest.sh
    modules/
      wechat_ingest_service.py
      wechat_demo_bridge.py
      feishu.py
    scripts/
      wechat_ingest_cli.py
      internal/wechat_demo_wrapper.py
    integration/
      admin_server.py
      collector.py
  frontend/
    components/
      WechatRadarBoard.vue
    lib/
      api.js
      pipeline.js
    styles/
      main.css
    integration/
      App.vue
      SettingsBoard.vue
  third_party/
    we-mp-rss-runtime/
      demo_cli/
      driver/
      core/
      config.example.yaml
      requirements.txt
      ReadMe.md
  docs/
    ENV_SETUP_GUIDE.md
    TESTING_GUIDE.md
    ADMIN_DASHBOARD.md
    Product-Spec.md
    Product-Spec-CHANGELOG.md
```

## Core Backend Files

`backend/modules/wechat_ingest_service.py`

The main service layer. It owns account-isolated workspace paths, QR image persistence, daemon login mode, login status, public-account search/add, article list pulling, article cache listing, batch content fetch, and sync to the inspiration table.

Important methods:

- `status()`
- `login()`
- `search_mp()`
- `add_mp()`
- `list_mps()`
- `pull_articles()`
- `list_articles()`
- `batch_fetch_content()`
- `sync_articles_to_inspiration()`
- `full_flow()`

`backend/scripts/wechat_ingest_cli.py`

Standalone CLI wrapper around `WechatIngestService`.

Common commands:

```bash
python3 scripts/wechat_ingest_cli.py status
python3 scripts/wechat_ingest_cli.py --account-id default login --no-wait --qr-display both
python3 scripts/wechat_ingest_cli.py --account-id default search-mp "机器之心" --limit 8
python3 scripts/wechat_ingest_cli.py --account-id default add-mp --keyword "机器之心" --pick 1
python3 scripts/wechat_ingest_cli.py --account-id default pull-articles --mp-id MP_WXS_xxx --pages 1 --mode api
python3 scripts/wechat_ingest_cli.py --account-id default sync-inspiration --mp-id MP_WXS_xxx --limit 20
```

`backend/scripts/internal/wechat_demo_wrapper.py`

Account-isolation wrapper for the third-party `wechat_demo_cli.py`. It patches the runtime QR behavior so each account keeps its own fixed QR image under the account state directory.

`backend/modules/wechat_demo_bridge.py`

Optional bridge used by the normal article collector. When `OPENCLAW_WECHAT_DEMO_ENABLED=1`, WeChat article URLs can be fetched through the login-state runtime instead of the default direct HTTP path.

`backend/integration/admin_server.py`

Full Flask admin server snapshot. The WeChat-related routes are embedded here:

- `GET /api/wechat/status`
- `GET /api/wechat/qr-image`
- `GET /api/wechat/list-mp`
- `GET /api/wechat/list-articles`
- `POST /api/wechat/search-mp`
- `POST /api/wechat/add-mp`
- `POST /api/actions/wechat-login`
- `POST /api/actions/wechat-pull-articles`
- `POST /api/actions/wechat-sync-inspiration`
- `POST /api/actions/wechat-full-flow`

## Frontend Files

`frontend/components/WechatRadarBoard.vue`

The primary Vue UI for the feature. It handles QR login dialog state, polling login status, public-account search/add, article list pull, inspiration sync, and full-flow triggering.

`frontend/lib/api.js`

Contains the dashboard API client methods used by `WechatRadarBoard.vue`, including:

- `wechatStatus`
- `wechatSearchMp`
- `wechatAddMp`
- `wechatListMp`
- `wechatListArticles`
- `wechatLogin`
- `wechatPullArticles`
- `wechatSyncInspiration`
- `wechatFullFlow`

`frontend/lib/pipeline.js`

Contains the sidebar nav item for `radar`.

`frontend/integration/App.vue`

Shows how `WechatRadarBoard` is mounted under `activeView === 'radar'`.

`frontend/integration/SettingsBoard.vue`

Contains the secondary "check WeChat ingest status" shortcut.

## Third-Party Runtime

`third_party/we-mp-rss-runtime/`

This is the copied runtime subset that actually talks to `mp.weixin.qq.com` using QR login and persisted token/cookie state.

Key files:

- `demo_cli/wechat_demo_cli.py`: CLI for login/status/search/add/pull/fetch.
- `driver/wx.py`: Playwright-based QR login path.
- `driver/wx_api.py`: API-mode login/status helpers.
- `driver/token.py`: token/cookie persistence helpers.
- `driver/store.py`: cookie store helper.
- `driver/playwright_driver.py`: browser automation controller.
- `core/`: supporting runtime modules required by the driver layer.

No runtime state, QR images, `.env`, or token/cookie files were copied into this extraction.

## Runtime State

In the main project, account-isolated state defaults to:

```text
output/wechat_accounts/<account_id>/
  runtime/
  state/
    state.json
    qr_login.png
    login_daemon.pid
    login_daemon.log
```

This extraction intentionally does not include that `output/` state.

## Environment Variables

Relevant variables:

```bash
OPENCLAW_WECHAT_DEMO_ENABLED=1
OPENCLAW_WECHAT_DEMO_CLI=/absolute/path/to/wechat_demo_cli.py
OPENCLAW_WECHAT_DEMO_PYTHON=python3
OPENCLAW_WECHAT_DEMO_TIMEOUT=180
OPENCLAW_WECHAT_ACCOUNTS_ROOT=
```

The service can also auto-discover the bundled demo CLI at:

```text
third_party/we-mp-rss/demo_cli/wechat_demo_cli.py
```

If you run the copied CLI directly from this extraction folder, set the demo path explicitly because the extracted third-party runtime is stored beside `backend/`:

```bash
export OPENCLAW_WECHAT_DEMO_CLI="$(pwd)/wechat_mp_login_state/third_party/we-mp-rss-runtime/demo_cli/wechat_demo_cli.py"
python3 wechat_mp_login_state/backend/scripts/wechat_ingest_cli.py --help
```

## Notes

- This folder is a copied extraction, not a wired refactor.
- The current application still imports and runs the original files in their original paths.
- If this feature is later turned into a true standalone package, imports such as `from config import Config`, `from admin_accounts import AccountStore`, and `from modules.feishu import FeishuBitable` should be replaced with package-local adapters.
