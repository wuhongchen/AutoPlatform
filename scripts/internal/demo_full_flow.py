import argparse
import os
import sys
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from config import Config
from core.manager import AutoPlatformManager
from core.manager_inspiration import InspirationManager
from modules.feishu import FeishuBitable
from modules.state_machine import PipelineState


def find_record_ids_by_url(feishu, table_id, url):
    ids = set()
    data = feishu.list_records(table_id)
    for item in data.get("items", []):
        fields = item.get("fields", {})
        if str(fields.get("文章 URL", "")).strip() == url:
            rid = item.get("record_id")
            if rid:
                ids.add(rid)
    return ids


def list_record_ids(feishu, table_id):
    ids = set()
    data = feishu.list_records(table_id)
    for item in data.get("items", []):
        rid = item.get("record_id")
        if rid:
            ids.add(rid)
    return ids


def get_record_fields(feishu, table_id, record_id):
    record = feishu.get_record(table_id, record_id) or {}
    return record.get("fields", {})


def main():
    parser = argparse.ArgumentParser(description="全流程 Demo：灵感库 -> 流水线改写 -> 发布")
    parser.add_argument(
        "--url",
        default="https://mp.weixin.qq.com/s/wrsaOwVYDKd2lEDmRs65Jg",
        help="要跑全流程的公众号链接",
    )
    parser.add_argument(
        "--skip-publish",
        action="store_true",
        help="只跑到待审核，不执行发布",
    )
    args = parser.parse_args()

    url = args.url.strip()
    if not url:
        raise SystemExit("❌ URL 不能为空")

    print("=== Demo 全流程启动 ===")
    print(f"目标 URL: {url}")

    feishu = FeishuBitable(Config.FEISHU_APP_ID, Config.FEISHU_APP_SECRET, Config.FEISHU_APP_TOKEN)
    if not feishu._get_token():
        raise SystemExit("❌ 飞书鉴权失败，请检查 FEISHU_* 配置")

    inspiration_mgr = InspirationManager()
    pipeline_mgr = AutoPlatformManager()

    inspiration_table_id = inspiration_mgr.inspiration_table_id
    pipeline_table_id = pipeline_mgr.smart_table_id or pipeline_mgr.table_ids.get("pipeline")

    if not inspiration_table_id:
        raise SystemExit("❌ 未找到灵感库表")
    if not pipeline_table_id:
        raise SystemExit("❌ 未找到流水线表")

    print(f"灵感库表: {inspiration_table_id}")
    print(f"流水线表: {pipeline_table_id}")

    create_result = feishu.add_record_with_result(inspiration_table_id, {"文章 URL": url})
    if not create_result.get("ok"):
        raise SystemExit(f"❌ 写入灵感库失败: {create_result.get('raw')}")

    inspiration_record_id = create_result.get("record_id", "").strip()
    if not inspiration_record_id:
        # 兼容极端场景：接口未返回 records，退回 URL 查找
        time.sleep(1)
        matched_ids = sorted(list(find_record_ids_by_url(feishu, inspiration_table_id, url)))
        if not matched_ids:
            raise SystemExit("❌ 已提交写入，但未定位到新建灵感记录")
        inspiration_record_id = matched_ids[-1]
    print(f"✅ 新建灵感记录: {inspiration_record_id}")

    print("\n--- 阶段 1：灵感分析与原文文档生成 ---")
    inspiration_mgr._process_new_url(inspiration_record_id, url)

    print("\n--- 阶段 2：同步到流水线 ---")
    fields = get_record_fields(feishu, inspiration_table_id, inspiration_record_id)
    feishu.update_record(inspiration_table_id, inspiration_record_id, {"处理状态": "已同步"})
    fields["处理状态"] = "已同步"

    synced = inspiration_mgr.sync_engine.sync_to_pipeline(inspiration_record_id, fields)
    if not synced:
        raise SystemExit("❌ 灵感同步到流水线失败")

    pipeline_record_id = synced if isinstance(synced, str) else ""
    if not pipeline_record_id:
        # 兼容旧逻辑返回布尔值时的兜底查找
        time.sleep(1)
        after_pipeline_ids = list_record_ids(feishu, pipeline_table_id)
        if not after_pipeline_ids:
            raise SystemExit("❌ 同步成功，但未获取到流水线记录列表")
        pipeline_record_id = sorted(list(after_pipeline_ids))[-1]
    print(f"✅ 新建流水线记录: {pipeline_record_id}")

    print("\n--- 阶段 3：执行改写 ---")
    pipeline_fields = get_record_fields(feishu, pipeline_table_id, pipeline_record_id)
    pipeline_fields["_table_id"] = pipeline_table_id
    feishu.update_record(pipeline_table_id, pipeline_record_id, {"数据流程状态": PipelineState.REWRITE_RUNNING})
    pipeline_mgr.run_pipeline_step_1(pipeline_record_id, pipeline_fields)
    print("✅ 改写完成")

    if args.skip_publish:
        print("\n--- 跳过发布（--skip-publish）---")
        print("🏁 Demo 已完成（停在待审核/待发布前）")
        return

    print("\n--- 阶段 4：自动设为待发布并执行发布 ---")
    feishu.update_record(pipeline_table_id, pipeline_record_id, {"数据流程状态": PipelineState.PUBLISH_READY})
    publish_fields = get_record_fields(feishu, pipeline_table_id, pipeline_record_id)
    publish_fields["_table_id"] = pipeline_table_id
    feishu.update_record(pipeline_table_id, pipeline_record_id, {"数据流程状态": PipelineState.PUBLISH_RUNNING})
    try:
        pipeline_mgr.run_pipeline_step_2(pipeline_record_id, publish_fields)
        print("✅ 发布完成")
    except Exception as e:
        reason = str(e)
        feishu.update_record(pipeline_table_id, pipeline_record_id, {
            "数据流程状态": PipelineState.PUBLISH_FAILED,
            "备注": f"[Demo] 发布失败: {reason}"
        })
        print(f"❌ 发布失败: {reason}")
        print("排查建议：")
        print("1) 检查公众号后台是否放行当前服务器 IP（常见是白名单拦截）")
        print("2) 校验 WECHAT_APPID / WECHAT_SECRET 是否为当前公众号有效凭据")
        print("3) 若仅验证前半链路可用，可改用 --skip-publish")
        return

    latest_fields = get_record_fields(feishu, pipeline_table_id, pipeline_record_id)
    print("\n=== Demo 结果 ===")
    print(f"状态: {latest_fields.get('数据流程状态')}")
    print(f"标题: {latest_fields.get('标题')}")
    print(f"草稿 ID: {latest_fields.get('草稿 ID')}")
    print("🏁 全流程 Demo 执行结束")


if __name__ == "__main__":
    main()
