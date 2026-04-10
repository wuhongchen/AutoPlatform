#!/usr/bin/env python3
"""
文章改写脚本 - 后台异步执行
用法: python3 core/rewrite_article.py <record_id> <account_id> <role> <model>
"""
import os
import sys
import signal

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from config import Config
from modules.workflow_store import WorkflowStore
from modules.plugins import AIRewritePlugin


def _now_str():
    return __import__('time').strftime("%Y-%m-%d %H:%M:%S")


def main():
    if len(sys.argv) < 5:
        print("[ERROR] Usage: python3 rewrite_article.py <record_id> <account_id> <role> <model>")
        sys.exit(1)
    
    record_id = sys.argv[1]
    account_id = sys.argv[2]
    role = sys.argv[3]
    model = sys.argv[4]
    
    print(f"[{_now_str()}] [INFO] 开始AI改写任务")
    print(f"[{_now_str()}] [INFO] 记录ID: {record_id}")
    print(f"[{_now_str()}] [INFO] 账户: {account_id}")
    print(f"[{_now_str()}] [INFO] 角色: {role}")
    print(f"[{_now_str()}] [INFO] 模型: {model}")
    
    workflow = WorkflowStore(Config.WORKFLOW_DB)
    
    # 检查文章内容是否存在
    content = workflow.get_article_content(record_id, account_id)
    if not content:
        print(f"[{_now_str()}] [ERROR] 文章内容不存在，请先采集")
        # 更新状态为改写失败
        inspiration = workflow.get_inspiration(record_id, account_id)
        if inspiration:
            inspiration["status"] = "改写失败"
            inspiration["updated_at"] = _now_str()
            workflow.upsert_inspiration(inspiration)
        sys.exit(1)
    
    original_text = content.get("original_text") or content.get("original_data", {}).get("content_text", "")
    if not original_text:
        print(f"[{_now_str()}] [ERROR] 文章内容为空，无法改写")
        inspiration = workflow.get_inspiration(record_id, account_id)
        if inspiration:
            inspiration["status"] = "改写失败"
            inspiration["updated_at"] = _now_str()
            workflow.upsert_inspiration(inspiration)
        sys.exit(1)
    
    print(f"[{_now_str()}] [INFO] 内容长度: {len(original_text)} 字符")
    
    plugin = AIRewritePlugin(workflow, account_id)
    
    # 设置超时（5分钟）
    def timeout_handler(signum, frame):
        print(f"[{_now_str()}] [ERROR] 改写超时（5分钟）")
        # 更新状态为改写失败
        inspiration = workflow.get_inspiration(record_id, account_id)
        if inspiration:
            inspiration["status"] = "改写失败"
            inspiration["updated_at"] = _now_str()
            workflow.upsert_inspiration(inspiration)
        sys.exit(1)
    
    try:
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(300)  # 5分钟超时
    except Exception:
        pass  # Windows不支持signal
    
    try:
        result = plugin.execute(record_id, role=role, model=model)
        
        # 取消超时
        try:
            signal.alarm(0)
        except Exception:
            pass
        
        if result.success:
            print(f"[{_now_str()}] [INFO] ✅ 改写完成: {result.message}")
            if result.data:
                print(f"[{_now_str()}] [INFO] 标题: {result.data.get('title', '-')}")
            sys.exit(0)
        else:
            print(f"[{_now_str()}] [ERROR] ❌ 改写失败: {result.message}")
            sys.exit(1)
    except Exception as e:
        # 取消超时
        try:
            signal.alarm(0)
        except Exception:
            pass
        
        print(f"[{_now_str()}] [ERROR] ❌ 执行异常: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # 更新状态为改写失败
        try:
            inspiration = workflow.get_inspiration(record_id, account_id)
            if inspiration:
                inspiration["status"] = "改写失败"
                inspiration["updated_at"] = _now_str()
                workflow.upsert_inspiration(inspiration)
        except Exception as update_err:
            print(f"[{_now_str()}] [ERROR] 更新状态失败: {update_err}")
        
        sys.exit(1)


if __name__ == "__main__":
    main()
