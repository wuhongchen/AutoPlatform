# Extraction Manifest

| Extracted path | Original path | Purpose |
| --- | --- | --- |
| `backend/modules/wechat_ingest_service.py` | `modules/wechat_ingest_service.py` | Main account-isolated WeChat ingest service. |
| `backend/modules/wechat_demo_bridge.py` | `modules/wechat_demo_bridge.py` | Optional login-state article fetch bridge. |
| `backend/modules/feishu.py` | `modules/feishu.py` | Dependency for syncing fetched WeChat articles into the inspiration table. |
| `backend/scripts/wechat_ingest_cli.py` | `scripts/wechat_ingest_cli.py` | CLI entrypoint for status/login/search/add/pull/sync/full-flow. |
| `backend/scripts/internal/wechat_demo_wrapper.py` | `scripts/internal/wechat_demo_wrapper.py` | Runtime wrapper that isolates QR/token state per account. |
| `backend/run_wechat_ingest.sh` | `run_wechat_ingest.sh` | Shell launcher for the CLI. |
| `backend/admin_accounts.py` | `admin_accounts.py` | Account selector used by the CLI and backend service. |
| `backend/config.py` | `config.py` | Environment config used by the service and bridge. |
| `backend/integration/admin_server.py` | `admin_server.py` | Flask API integration source containing the WeChat endpoints. |
| `backend/integration/collector.py` | `modules/collector.py` | Shows how `WechatDemoBridge` is used for WeChat article URLs. |
| `frontend/components/WechatRadarBoard.vue` | `frontend/admin/src/components/WechatRadarBoard.vue` | Main UI for QR login state and article ingest. |
| `frontend/lib/api.js` | `frontend/admin/src/lib/api.js` | Dashboard API methods used by the radar UI. |
| `frontend/lib/pipeline.js` | `frontend/admin/src/lib/pipeline.js` | Sidebar nav registration for the radar view. |
| `frontend/styles/main.css` | `frontend/admin/src/styles/main.css` | CSS classes used by the radar UI and QR preview. |
| `frontend/integration/App.vue` | `frontend/admin/src/App.vue` | Vue integration point for rendering `WechatRadarBoard`. |
| `frontend/integration/SettingsBoard.vue` | `frontend/admin/src/components/SettingsBoard.vue` | Secondary status-check integration. |
| `third_party/we-mp-rss-runtime/demo_cli/` | `third_party/we-mp-rss/demo_cli/` | Third-party CLI runtime used by the wrapper and ingest service. |
| `third_party/we-mp-rss-runtime/driver/` | `third_party/we-mp-rss/driver/` | QR login, token, cookie, browser driver, and WeChat API runtime code. |
| `third_party/we-mp-rss-runtime/core/` | `third_party/we-mp-rss/core/` | Supporting modules required by the third-party driver runtime. |
| `third_party/we-mp-rss-runtime/config.example.yaml` | `third_party/we-mp-rss/config.example.yaml` | Safe example config for the third-party runtime. |
| `third_party/we-mp-rss-runtime/requirements.txt` | `third_party/we-mp-rss/requirements.txt` | Python dependencies for the third-party runtime. |
| `third_party/we-mp-rss-runtime/ReadMe.md` | `third_party/we-mp-rss/ReadMe.md` | Upstream runtime documentation. |
| `docs/ENV_SETUP_GUIDE.md` | `docs/ENV_SETUP_GUIDE.md` | Setup notes for WeChat login-state ingest. |
| `docs/TESTING_GUIDE.md` | `docs/TESTING_GUIDE.md` | Test commands for login-state ingest. |
| `docs/ADMIN_DASHBOARD.md` | `docs/ADMIN_DASHBOARD.md` | Admin dashboard feature map and config fields. |
| `docs/Product-Spec.md` | `docs/Product-Spec.md` | Product requirements for the radar module. |
| `docs/Product-Spec-CHANGELOG.md` | `docs/Product-Spec-CHANGELOG.md` | Requirement-change notes for the radar module. |

## Omitted On Purpose

The following were not copied:

- `.env`
- `output/`
- account runtime folders
- QR images
- token/cookie state
- browser cache/profile state
- `frontend/admin/node_modules/`
- generated frontend `dist/`
- Python `__pycache__/` and `.pyc` files

These are runtime artifacts or secrets, not portable source code.
