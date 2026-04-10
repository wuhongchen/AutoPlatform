# 实施路线图：移除流水线，实现插件化全流程

## 当前系统状态（基于诊断结果）

```
✅ 已完成:
  - PipelineBoard.vue 已移除
  - admin_server.py 重写为飞书无关版本
  - WorkflowStore 本地数据库实现
  - UnifiedAICaller 统一AI调用器
  - inspiration_records 表（94条记录）
  - publish_logs 表（59条记录）

⚠️ 待完成:
  - core/manager.py: 24处飞书引用
  - core/manager_inspiration.py: 31处飞书引用
  - pipeline_records 表（97条记录，需要废弃）
  - 插件化API实现
```

## Phase 1: 数据库Schema更新（1-2小时）

### 1.1 修改 modules/workflow_store.py

**新增方法:**
```python
def _ensure_schema_v2(self):
    """确保Schema v2结构存在"""
    # 新增 article_contents 表
    # 新增 plugin_tasks 表
    pass

def save_article_content(self, record_id, html_content, text_content, images=None):
    """保存文章内容到本地存储"""
    pass

def get_article_content(self, record_id):
    """获取文章内容"""
    pass

def create_plugin_task(self, record_id, plugin_type, params):
    """创建插件任务"""
    pass

def update_plugin_task(self, task_id, status, result=None, error=None):
    """更新插件任务状态"""
    pass

def get_plugin_tasks(self, record_id, plugin_type=None):
    """获取插件任务列表"""
    pass
```

### 1.2 SQL Schema变更

```sql
-- 新增文章内容表
CREATE TABLE IF NOT EXISTS article_contents (
    record_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    original_html TEXT NOT NULL DEFAULT '',
    original_text TEXT NOT NULL DEFAULT '',
    rewritten_html TEXT NOT NULL DEFAULT '',
    rewritten_text TEXT NOT NULL DEFAULT '',
    images_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- 新增插件任务表
CREATE TABLE IF NOT EXISTS plugin_tasks (
    task_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    record_id TEXT NOT NULL,
    plugin_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    params_json TEXT NOT NULL DEFAULT '{}',
    result_json TEXT NOT NULL DEFAULT '{}',
    error_msg TEXT NOT NULL DEFAULT '',
    started_at TEXT,
    ended_at TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_article_account ON article_contents(account_id);
CREATE INDEX IF NOT EXISTS idx_plugin_task_record ON plugin_tasks(record_id);
CREATE INDEX IF NOT EXISTS idx_plugin_task_status ON plugin_tasks(status);
```

## Phase 2: 实现插件架构（2-3小时）

### 2.1 创建 modules/plugins/base.py

```python
from abc import ABC, abstractmethod
from typing import Dict, Any

class BasePlugin(ABC):
    """插件基类"""
    
    plugin_type: str
    plugin_name: str
    plugin_description: str
    
    def __init__(self, workflow_store, ai_caller=None):
        self.store = workflow_store
        self.ai_caller = ai_caller
    
    @abstractmethod
    def execute(self, record_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行插件任务"""
        pass
    
    def _create_task(self, record_id: str, params: Dict) -> str:
        """创建任务记录"""
        return self.store.create_plugin_task(record_id, self.plugin_type, params)
    
    def _update_task(self, task_id: str, status: str, result=None, error=None):
        """更新任务状态"""
        self.store.update_plugin_task(task_id, status, result, error)
```

### 2.2 创建 modules/plugins/ai_score.py

```python
from .base import BasePlugin
from modules.ai_caller import get_unified_caller
import json

class AIScorePlugin(BasePlugin):
    """AI评分插件"""
    
    plugin_type = "ai_score"
    plugin_name = "AI评分"
    plugin_description = "分析文章质量并给出1-10分评分"
    
    def execute(self, record_id: str, params: dict) -> dict:
        """执行AI评分"""
        # 1. 获取文章内容
        # 2. 调用AI分析
        # 3. 更新inspiration记录
        # 4. 返回结果
        pass
```

### 2.3 创建 modules/plugins/ai_rewrite.py

```python
from .base import BasePlugin
from modules.ai_caller import get_unified_caller

class AIRewritePlugin(BasePlugin):
    """AI改写插件"""
    
    plugin_type = "ai_rewrite"
    plugin_name = "AI改写"
    plugin_description = "基于角色设定改写文章内容"
    
    def execute(self, record_id: str, params: dict) -> dict:
        """执行AI改写"""
        # 1. 获取原文
        # 2. 获取角色配置
        # 3. 调用AI改写
        # 4. 保存改写结果
        # 5. 更新状态
        pass
```

### 2.4 创建 modules/plugins/publisher.py

```python
from .base import BasePlugin
from modules.publisher import WeChatPublisher

class PublishPlugin(BasePlugin):
    """发布插件"""
    
    plugin_type = "publish"
    plugin_name = "发布到微信"
    plugin_description = "将改写后的文章发布到微信公众号草稿箱"
    
    def execute(self, record_id: str, params: dict) -> dict:
        """执行发布"""
        # 1. 获取改写后的内容
        # 2. 内容验证
        # 3. 上传封面图
        # 4. 处理正文图片
        # 5. 发布到微信
        # 6. 记录日志
        pass
```

### 2.5 创建 modules/plugins/__init__.py

```python
from .ai_score import AIScorePlugin
from .ai_rewrite import AIRewritePlugin
from .publisher import PublishPlugin

PLUGIN_REGISTRY = {
    'ai_score': AIScorePlugin,
    'ai_rewrite': AIRewritePlugin,
    'publish': PublishPlugin,
}

def get_plugin(plugin_type, workflow_store, ai_caller=None):
    """获取插件实例"""
    plugin_class = PLUGIN_REGISTRY.get(plugin_type)
    if plugin_class:
        return plugin_class(workflow_store, ai_caller)
    raise ValueError(f"Unknown plugin type: {plugin_type}")

def list_plugins():
    """列出所有可用插件"""
    return [
        {
            'type': p.plugin_type,
            'name': p.plugin_name,
            'description': p.plugin_description,
        }
        for p in PLUGIN_REGISTRY.values()
    ]
```

## Phase 3: 重构核心模块（3-4小时）

### 3.1 重构 core/manager_inspiration.py

**修改要点:**
1. 移除 FeishuBitable 初始化
2. 移除 `_ensure_fields` 方法
3. 修改 `_process_local_url` 方法:
   - 移除飞书文档创建
   - 内容保存到 article_contents 表
   - AI评分保存到 extra_json
4. 移除 `_process_new_url` 方法（飞书专用）
5. 移除同步到流水线逻辑

**新流程:**
```python
def _process_local_url(self, record_id, url, input_title):
    # 1. 采集内容
    article = self.collector.fetch(url)
    
    # 2. 保存原文到 article_contents
    self.workflow.save_article_content(
        record_id,
        html_content=article['content_html'],
        text_content=article['content_raw'],
        images=article.get('images', [])
    )
    
    # 3. AI评分
    analysis = self.analyzer.analyze(article)
    
    # 4. 更新灵感库状态
    self.workflow.upsert_inspiration({
        "record_id": record_id,
        "status": "待改写" if analysis['score'] >= 5 else "已跳过",
        "extra": {
            "ai_score": analysis['score'],
            "ai_reason": analysis['reason'],
            "title_zh": analysis.get('title_zh', ''),
            "insight": analysis.get('insight', ''),
            "domain": analysis.get('domain', ''),
        }
    })
```

### 3.2 重构 core/manager.py

**修改要点:**
1. 移除 `run_pipeline_once` 方法（流水线巡检）
2. 移除 `run_pipeline_step_1` 和 `run_pipeline_step_2` 方法
3. 修改 `run_with_params` 为直接调用插件:

```python
def run_full_flow(self, url, role_key="tech_expert", model_key="auto"):
    """直接执行全流程"""
    from modules.plugins import get_plugin
    
    # 1. 创建灵感记录
    inspiration = self.workflow.upsert_inspiration({
        "url": url,
        "status": "处理中",
    })
    
    # 2. 采集
    article = self.collector.fetch(url)
    self.workflow.save_article_content(inspiration['record_id'], ...)
    
    # 3. AI评分插件
    score_plugin = get_plugin('ai_score', self.workflow)
    score_result = score_plugin.execute(inspiration['record_id'], {})
    
    # 4. AI改写插件
    rewrite_plugin = get_plugin('ai_rewrite', self.workflow)
    rewrite_result = rewrite_plugin.execute(inspiration['record_id'], {
        'role': role_key,
        'model': model_key,
    })
    
    # 5. 发布插件
    publish_plugin = get_plugin('publish', self.workflow)
    publish_result = publish_plugin.execute(inspiration['record_id'], {})
    
    return {
        'inspiration_id': inspiration['record_id'],
        'score': score_result,
        'rewrite': rewrite_result,
        'publish': publish_result,
    }
```

## Phase 4: 更新API服务（1-2小时）

### 4.1 修改 admin_server.py

**新增API端点:**

```python
# 插件API
@app.post("/api/plugins/ai-score")
def api_plugin_ai_score():
    """执行AI评分"""
    payload = request.get_json() or {}
    record_id = payload.get('record_id')
    
    from modules.plugins import get_plugin
    plugin = get_plugin('ai_score', workflow_store)
    result = plugin.execute(record_id, {})
    
    return {"ok": True, "result": result}

@app.post("/api/plugins/ai-rewrite")
def api_plugin_ai_rewrite():
    """执行AI改写"""
    payload = request.get_json() or {}
    record_id = payload.get('record_id')
    role = payload.get('role', 'tech_expert')
    model = payload.get('model', 'auto')
    
    from modules.plugins import get_plugin
    plugin = get_plugin('ai_rewrite', workflow_store)
    result = plugin.execute(record_id, {'role': role, 'model': model})
    
    return {"ok": True, "result": result}

@app.post("/api/plugins/publish")
def api_plugin_publish():
    """执行发布"""
    payload = request.get_json() or {}
    record_id = payload.get('record_id')
    
    from modules.plugins import get_plugin
    plugin = get_plugin('publish', workflow_store)
    result = plugin.execute(record_id, {})
    
    return {"ok": True, "result": result}

# 文章内容API
@app.get("/api/article-content/<record_id>")
def api_get_article_content(record_id):
    """获取文章内容"""
    content = workflow_store.get_article_content(record_id)
    if not content:
        return {"ok": False, "error": "Content not found"}, 404
    return {"ok": True, "content": content}

# 插件列表API
@app.get("/api/plugins")
def api_list_plugins():
    """获取可用插件列表"""
    from modules.plugins import list_plugins
    return {"ok": True, "plugins": list_plugins()}

# 插件任务API
@app.get("/api/plugin-tasks")
def api_list_plugin_tasks():
    """获取插件任务列表"""
    record_id = request.args.get('record_id')
    tasks = workflow_store.get_plugin_tasks(record_id)
    return {"ok": True, "tasks": tasks}
```

## Phase 5: 前端更新（1-2小时）

### 5.1 修改 frontend/admin/src/lib/api.js

```javascript
export const dashboardApi = {
  // ... 现有API ...
  
  // 新增插件API
  runAIScore: ({ recordId }) => 
    api('/api/plugins/ai-score', { 
      method: 'POST', 
      body: JSON.stringify({ record_id: recordId }) 
    }),
  
  runAIRewrite: ({ recordId, role, model }) => 
    api('/api/plugins/ai-rewrite', { 
      method: 'POST', 
      body: JSON.stringify({ record_id: recordId, role, model }) 
    }),
  
  runPublish: ({ recordId }) => 
    api('/api/plugins/publish', { 
      method: 'POST', 
      body: JSON.stringify({ record_id: recordId }) 
    }),
  
  getArticleContent: (recordId) => 
    api(`/api/article-content/${encodeURIComponent(recordId)}`),
  
  listPlugins: () => 
    api('/api/plugins'),
  
  listPluginTasks: (recordId) => 
    api(`/api/plugin-tasks?record_id=${encodeURIComponent(recordId)}`),
}
```

### 5.2 修改 InspirationBoard.vue

**更新executeRewrite方法:**
```javascript
async function executeRewrite() {
  if (!actionItem.value) return
  actionLoading.value = true
  errorMessage.value = ''
  try {
    // 使用新的插件API
    const data = await dashboardApi.runAIRewrite({
      recordId: actionItem.value.record_id,
      role: 'tech_expert',
      model: 'auto',
    })
    actionResult.value = { 
      ok: true, 
      message: 'AI改写任务已提交',
      taskId: data?.result?.task_id 
    }
    setInfo(`AI改写任务已提交: ${actionItem.value.title}`)
    emit('refresh')
  } catch (err) {
    setError(err)
    actionResult.value = { ok: false, message: err?.message || '改写失败' }
  } finally {
    actionLoading.value = false
  }
}
```

**更新executePublish方法:**
```javascript
async function executePublish() {
  if (!actionItem.value) return
  actionLoading.value = true
  errorMessage.value = ''
  try {
    const data = await dashboardApi.runPublish({
      recordId: actionItem.value.record_id,
    })
    actionResult.value = { 
      ok: true, 
      message: '发布任务已提交',
      draftId: data?.result?.draft_id 
    }
    setInfo(`发布任务已提交: ${actionItem.value.title}`)
    emit('refresh')
  } catch (err) {
    setError(err)
    actionResult.value = { ok: false, message: err?.message || '发布失败' }
  } finally {
    actionLoading.value = false
  }
}
```

## Phase 6: 测试验证（1-2小时）

### 6.1 单元测试

```bash
# 运行测试
python3 tests/test_full_system.py

# 运行诊断
python3 tests/scripts/diagnose_system.py
```

### 6.2 集成测试

```bash
# 启动服务
python3 admin_server.py &

# 测试API
curl -X POST http://localhost:8701/api/plugins/ai-score \
  -H "Content-Type: application/json" \
  -d '{"record_id": "test_001"}'

curl -X POST http://localhost:8701/api/plugins/ai-rewrite \
  -H "Content-Type: application/json" \
  -d '{"record_id": "test_001", "role": "tech_expert"}'
```

## Phase 7: 废弃流水线（可选，后期执行）

### 7.1 数据归档

```python
# 将pipeline_records数据导出为只读归档
def archive_pipeline_records():
    # 导出到JSON文件
    # 保留表结构但不再写入
    pass
```

### 7.2 清理代码

```bash
# 删除流水线相关文件（确认不再需要后）
# - core/manager.py 中的流水线方法
# - modules/state_machine.py
# - 前端 PipelineBoard 相关代码（已移除）
```

## 实施时间表

| Phase | 任务 | 预估时间 | 优先级 |
|-------|------|---------|--------|
| 1 | 数据库Schema更新 | 1-2h | P0 |
| 2 | 插件架构实现 | 2-3h | P0 |
| 3 | 核心模块重构 | 3-4h | P0 |
| 4 | API服务更新 | 1-2h | P0 |
| 5 | 前端更新 | 1-2h | P1 |
| 6 | 测试验证 | 1-2h | P1 |
| 7 | 废弃流水线 | 1h | P2 |

**总计: 10-16小时工作量**

## 风险控制

1. **数据安全**: 所有变更前先备份数据库
2. **回滚计划**: 保留旧代码分支，必要时可回滚
3. **渐进式**: 先实现新功能，稳定后再移除旧功能
4. **监控**: 添加详细的日志记录，便于问题排查
