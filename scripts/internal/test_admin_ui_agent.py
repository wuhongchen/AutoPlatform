#!/usr/bin/env python3
import argparse
import json
import os
import re
import socket
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List, Optional

import requests
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_HOST = "127.0.0.1"
REPORT_DIR = ROOT / "output"


@dataclass
class CheckResult:
    category: str
    name: str
    ok: bool
    detail: str


class AdminUITestAgent:
    def __init__(self, host: str, port: int, keep_server: bool = False):
        self.host = host
        self.port = port
        self.keep_server = keep_server
        self.base_url = f"http://{host}:{port}"
        self.process: Optional[subprocess.Popen] = None
        self.results: List[CheckResult] = []
        self.original_active_account_id = ""
        self.server_log_lines: List[str] = []

    def record(self, category: str, name: str, ok: bool, detail: str):
        self.results.append(CheckResult(category=category, name=name, ok=ok, detail=detail))

    def wait_for_server(self, timeout: float = 20.0):
        deadline = time.time() + timeout
        last_error = ""
        while time.time() < deadline:
            try:
                resp = requests.get(f"{self.base_url}/api/health", timeout=2)
                if resp.ok:
                    return
                last_error = f"HTTP {resp.status_code}"
            except Exception as exc:  # pragma: no cover - runtime smoke
                last_error = str(exc)
            time.sleep(0.5)
        raise RuntimeError(f"管理后台未在 {timeout:.0f}s 内启动成功: {last_error}")

    def start_server(self):
        env = dict(os.environ)
        env.setdefault("OPENCLAW_AUTO_INSTALL", "0")
        env.setdefault("ADMIN_HOST", self.host)
        env.setdefault("ADMIN_PORT", str(self.port))
        cmd = [sys.executable, "admin_server.py"]
        self.process = subprocess.Popen(
            cmd,
            cwd=str(ROOT),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        self.wait_for_server()

    def stop_server(self):
        if not self.process or self.keep_server:
            return
        self.process.terminate()
        try:
            stdout, _ = self.process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
            stdout, _ = self.process.communicate(timeout=5)
        self.server_log_lines = [line for line in (stdout or "").splitlines() if line][-80:]

    def fetch_json(self, path: str):
        resp = requests.get(f"{self.base_url}{path}", timeout=10)
        resp.raise_for_status()
        return resp.json()

    def post_json(self, path: str, payload: dict):
        resp = requests.post(f"{self.base_url}{path}", json=payload, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def test_api_smoke(self):
        health = self.fetch_json("/api/health")
        self.record("api", "health endpoint", bool(health.get("ok")), json.dumps(health, ensure_ascii=False))

        accounts = self.fetch_json("/api/accounts")
        self.original_active_account_id = str(accounts.get("active_account_id") or "")
        self.record(
            "api",
            "accounts endpoint",
            bool(accounts.get("ok")) and isinstance(accounts.get("items"), list) and len(accounts.get("items", [])) >= 1,
            f"active_account_id={self.original_active_account_id}, accounts={len(accounts.get('items', []))}",
        )

        overview = self.fetch_json(f"/api/overview?account_id={self.original_active_account_id}")
        self.record(
            "api",
            "overview endpoint",
            bool(overview.get("account")) and "meta" in overview,
            f"overview_ok={overview.get('ok')}, inspiration_total={overview.get('meta', {}).get('inspiration_total')}",
        )

        jobs = self.fetch_json("/api/jobs")
        self.record("api", "jobs endpoint", bool(jobs.get("ok")) and isinstance(jobs.get("items"), list), f"jobs={len(jobs.get('items', []))}")

        scheduler = self.fetch_json("/api/scheduler")
        self.record(
            "api",
            "scheduler endpoint",
            bool(scheduler.get("ok")) and isinstance(scheduler.get("scheduler"), dict),
            json.dumps(scheduler.get("scheduler", {}), ensure_ascii=False),
        )

    def test_page_shell(self):
        root_resp = requests.get(f"{self.base_url}/", timeout=10)
        root_resp.raise_for_status()
        root_html = root_resp.text
        self.record("page", "root vue route", "/admin-assets/" in root_html and '<div id="app"></div>' in root_html, "selector=/")

        vue_resp = requests.get(f"{self.base_url}/vue", timeout=10)
        vue_resp.raise_for_status()
        vue_html = vue_resp.text
        self.record("page", "vue preview route", "/admin-assets/" in vue_html and '<div id="app"></div>' in vue_html, "selector=/vue")

        legacy_resp = requests.get(f"{self.base_url}/legacy", timeout=10)
        self.record("page", "legacy removed", legacy_resp.status_code == 404, f"status={legacy_resp.status_code}")

        vue_soup = BeautifulSoup(vue_html, "html.parser")
        vue_js = ""
        vue_css = ""
        for script in vue_soup.select("script[src]"):
            src = script.get("src") or ""
            if src.startswith("/admin-assets/") and src.endswith(".js"):
                js_resp = requests.get(f"{self.base_url}{src}", timeout=10)
                js_resp.raise_for_status()
                vue_js = js_resp.text
                break
        for link in vue_soup.select("link[href]"):
            href = link.get("href") or ""
            if href.startswith("/admin-assets/") and href.endswith(".css"):
                css_resp = requests.get(f"{self.base_url}{href}", timeout=10)
                css_resp.raise_for_status()
                vue_css = css_resp.text
                break

        self.record("page", "vue bundle loaded", bool(vue_js), f"js_loaded={bool(vue_js)}")
        self.record("page", "vue styles loaded", bool(vue_css), f"css_loaded={bool(vue_css)}")
        self.record(
            "page",
            "vue shell classes",
            all(token in vue_css for token in [".admin-shell", ".sidebar-shell", ".topbar-shell"]),
            "required=.admin-shell/.sidebar-shell/.topbar-shell",
        )
        self.record(
            "page",
            "vue nav labels",
            all(token in vue_js for token in ["概览", "账户号", "灵感库", "写作管理链", "发布日志", "追踪中心", "设置"]),
            "required nav labels in bundle",
        )
        self.record(
            "page",
            "vue narrow screen guards",
            bool(re.search(r"@media\s*\(\s*max-width\s*:\s*980px\s*\)", vue_css))
            and bool(re.search(r"@media\s*\(\s*max-width\s*:\s*720px\s*\)", vue_css)),
            "required media queries for responsive shell (980/720)",
        )
        vue_css_compact = re.sub(r"\s+", "", vue_css or "")
        self.record(
            "page",
            "vue narrow toolbar overflow guard",
            ".topbar-shell,.toolbar-left,.toolbar-right,.page-actions{flex-wrap:wrap}" in vue_css_compact
            and ".account-select-shell{min-width:0;width:100%}" in vue_css_compact,
            "required flex-wrap + account selector width guard in narrow screens",
        )

    def test_account_mutation(self):
        temp_id = f"ui-test-{int(time.time())}"
        payload = {
            "id": temp_id,
            "name": "UI 测试账户",
            "enabled": True,
            "pipeline_role": "tech_expert",
            "pipeline_model": "auto",
            "pipeline_batch_size": 2,
            "content_direction": "测试内容方向",
            "prompt_direction": "测试改写方向",
            "wechat_prompt_direction": "测试公众号成稿方向",
        }
        created = self.post_json("/api/accounts/upsert", payload)
        self.record("action", "create temp account", bool(created.get("item", {}).get("id") == temp_id), json.dumps(created.get("item", {}), ensure_ascii=False))

        activated = self.post_json(f"/api/accounts/{temp_id}/activate", {})
        self.record("action", "activate temp account", activated.get("active_account_id") == temp_id, json.dumps(activated, ensure_ascii=False))

        accounts_after = self.fetch_json("/api/accounts")
        self.record("action", "verify temp account active", accounts_after.get("active_account_id") == temp_id, f"active={accounts_after.get('active_account_id')}")

        if self.original_active_account_id:
            restored = self.post_json(f"/api/accounts/{self.original_active_account_id}/activate", {})
            self.record("action", "restore original active account", restored.get("active_account_id") == self.original_active_account_id, json.dumps(restored, ensure_ascii=False))

        deleted = self.post_json(f"/api/accounts/{temp_id}/delete", {})
        self.record("action", "delete temp account", bool(deleted.get("ok")), json.dumps(deleted, ensure_ascii=False))

    def test_scheduler_mutation(self):
        original = self.fetch_json("/api/scheduler").get("scheduler", {})
        original_running = bool(original.get("running"))
        original_minutes = int(original.get("minutes") or 30)

        started = self.post_json("/api/scheduler/start", {"minutes": 59})
        started_scheduler = started.get("scheduler", {})
        self.record(
            "action",
            "scheduler start",
            bool(started_scheduler.get("running")) and int(started_scheduler.get("minutes") or 0) == 59,
            json.dumps(started_scheduler, ensure_ascii=False),
        )

        if original_running:
            restored = self.post_json("/api/scheduler/start", {"minutes": original_minutes})
            restored_scheduler = restored.get("scheduler", {})
            ok = bool(restored_scheduler.get("running")) and int(restored_scheduler.get("minutes") or 0) == original_minutes
            self.record("action", "scheduler restore running state", ok, json.dumps(restored_scheduler, ensure_ascii=False))
        else:
            stopped = self.post_json("/api/scheduler/stop", {})
            stopped_scheduler = stopped.get("scheduler", {})
            self.record("action", "scheduler restore stopped state", not stopped_scheduler.get("running"), json.dumps(stopped_scheduler, ensure_ascii=False))

    def write_reports(self):
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        json_path = REPORT_DIR / f"admin-ui-agent-report-{timestamp}.json"
        md_path = REPORT_DIR / f"admin-ui-agent-report-{timestamp}.md"

        passed = sum(1 for item in self.results if item.ok)
        failed = len(self.results) - passed
        payload = {
            "ok": failed == 0,
            "base_url": self.base_url,
            "checked_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "summary": {"passed": passed, "failed": failed, "total": len(self.results)},
            "results": [asdict(item) for item in self.results],
        }
        json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

        lines = [
            "# 管理后台测试 Agent 报告",
            "",
            f"- 地址：`{self.base_url}`",
            f"- 检查时间：`{payload['checked_at']}`",
            f"- 总计：`{len(self.results)}`",
            f"- 通过：`{passed}`",
            f"- 失败：`{failed}`",
            "",
            "## 明细",
            "",
        ]
        for item in self.results:
            mark = "✅" if item.ok else "❌"
            lines.append(f"- {mark} [{item.category}] {item.name}：{item.detail}")
        md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return json_path, md_path, failed == 0

    def run(self):
        try:
            self.start_server()
            self.test_api_smoke()
            self.test_page_shell()
            self.test_account_mutation()
            self.test_scheduler_mutation()
        finally:
            self.stop_server()
        return self.write_reports()


def pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((DEFAULT_HOST, 0))
        return int(sock.getsockname()[1])


def main():
    parser = argparse.ArgumentParser(description="管理后台测试 agent：验证页面结构、关键展示和安全可回滚动作。")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=pick_free_port())
    parser.add_argument("--keep-server", action="store_true", help="测试结束后不自动关闭后台服务")
    args = parser.parse_args()

    agent = AdminUITestAgent(host=args.host, port=args.port, keep_server=args.keep_server)
    json_path, md_path, ok = agent.run()

    print(f"管理后台测试 agent 已完成: {'PASS' if ok else 'FAIL'}")
    print(f"JSON 报告: {json_path}")
    print(f"Markdown 报告: {md_path}")
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
