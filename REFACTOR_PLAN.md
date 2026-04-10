# 项目重构计划：移除流水线，实现插件化全流程

## 1. 当前状态分析

### 1.1 已完成的工作
- ✅ 前端移除 PipelineBoard 组件
- ✅ InspirationBoard 添加独立操作按钮 (AI改写、发布)
- ✅ admin_server.py 重写为"飞书无关版本"
- ✅ WorkflowStore 本地数据库实现
- ✅ UnifiedAICaller 统一AI调用器

### 1.2 待重构的核心模块

| 模块 | 当前状态 | 目标状态 |
|------|---------|---------|
| core/manager.py | 强依赖飞书文档 | 本地存储+可选飞书 |
| core/manager_inspiration.py | 强依赖飞书Bitable | 仅本地SQLite |
| modules/publisher.py | 依赖飞书图片下载 | 独立微信发布 |
| modules/processor.py | 依赖飞书创建文档 | 本地Markdown存储 |
| admin_server.py | 部分API缺失 | 完整插件化API |

### 1.3 数据库表结构现状

```sql
-- 灵感库表 (已存在)
inspiration_records:
  - record_id, account_id, title, url, doc_url, status
  - captured_at, updated_at, remark
  - cover_token, cover_name, cover_type
  - extra_json (存储ai_score, ai_reason等)

-- 流水线表 (待移除/重构)
pipeline_records:
  - record_id, account_id, source_record_id
  - title, url, source_doc_url, rewritten_doc
  - status, model, role, remark, draft_id

-- 发布日志表 (保留)
publish_logs:
  - record_id, pipeline_record_id, account_id
  - title, publish_status, result, draft_id
```

## 2. 重构详细计划

### 2.1 数据库Schema变更

#### 2.1.1 新增文章存储表
```sql
CREATE TABLE article_contents (
    record_id TEXT PRIMARY KEY,  -- 关联inspiration_records
    account_id TEXT NOT NULL,
    original_html TEXT NOT NULL DEFAULT '',  -- 原始内容HTML
    original_text TEXT NOT NULL DEFAULT '',  -- 原始纯文本
    rewritten_html TEXT NOT NULL DEFAULT '', -- AI改写后HTML
    rewritten_text TEXT NOT NULL DEFAULT '', -- AI改写后纯文本
    images_json TEXT NOT NULL DEFAULT '{}',  -- 图片列表JSON
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

#### 2.1.2 新增插件任务表
```sql
CREATE TABLE plugin_tasks (
    task_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    record_id TEXT NOT NULL,     -- 关联的灵感记录ID
    plugin_type TEXT NOT NULL,   -- 'ai_score', 'ai_rewrite', 'publish'
    status TEXT NOT NULL,        -- 'pending', 'running', 'success', 'failed'
    params_json TEXT NOT NULL DEFAULT '{}',
    result_json TEXT NOT NULL DEFAULT '{}',
    error_msg TEXT NOT NULL DEFAULT '',
    started_at TEXT,
    ended_at TEXT,
    created_at TEXT NOT NULL
);
```

### 2.2 插件架构设计

#### 2.2.1 插件接口标准
```python
class BasePlugin:
    """插件基类"""
    plugin_type: str
    plugin_name: str

    def execute(self, record_id: str, params: dict) -> dict:
        """执行插件任务，返回结果字典"""
        raise NotImplementedError

class AIScorePlugin(BasePlugin):
    """AI评分插件"""
    plugin_type = "ai_score"
    plugin_name = "AI评分"

    def execute(self, record_id: str, params: dict) -> dict:
        # 1. 读取原文
        # 2. 调用AI分析
        # 3. 更新inspiration_records.extra_json.ai_score
        # 4. 返回结果
        pass

class AIRewritePlugin(BasePlugin):
    """AI改写插件"""
    plugin_type = "ai_rewrite"
    plugin_name = "AI改写"

    def execute(self, record_id: str, params: dict) -> dict:
        # 1. 读取原文
        # 2. 调用AI改写
        # 3. 保存改写内容到article_contents
        # 4. 更新inspiration_records状态
        # 5. 返回结果
        pass

class PublishPlugin(BasePlugin):
    """发布插件"""
    plugin_type = "publish"
    plugin_name = "发布到微信"

    def execute(self, record_id: str, params: dict) -> dict:
        # 1. 读取改写后的内容
        # 2. 内容完整性检查
        # 3. 上传封面图
        # 4. 处理正文图片
        # 5. 发布到微信草稿箱
        # 6. 记录发布日志
        # 7. 返回结果
        pass
```

### 2.3 核心模块重构清单

#### 2.3.1 core/manager_inspiration.py
- [ ] 移除FeishuBitable依赖
- [ ] 移除飞书文档创建和写入逻辑
- [ ] 原文内容保存到article_contents表
- [ ] AI评分直接保存到extra_json
- [ ] 移除"同步到流水线"逻辑

#### 2.3.2 core/manager.py
- [ ] 移除pipeline_records相关操作
- [ ] 重构run_with_params为独立插件调用
- [ ] 移除飞书文档读取/写入
- [ ] 从article_contents读取改写内容

#### 2.3.3 modules/processor.py
- [ ] 移除飞书文档创建逻辑
- [ ] 改写结果直接返回，不创建文档
- [ ] 内容保存由调用方处理

#### 2.3.4 admin_server.py 新增API
- [ ] `POST /api/plugins/ai-score` - AI评分
- [ ] `POST /api/plugins/ai-rewrite` - AI改写
- [ ] `POST /api/plugins/publish` - 发布
- [ ] `GET /api/article-content/:id` - 获取文章内容
- [ ] `POST /api/article-content/:id` - 保存文章内容

### 2.4 前端修改清单

#### 2.4.1 InspirationBoard.vue
- [ ] 添加"AI评分"按钮
- [ ] 修改"AI改写"调用新API
- [ ] 修改"发布"调用新API
- [ ] 添加文章内容预览弹窗

#### 2.4.2 新增 ArticlePreviewModal.vue
- [ ] 展示原文内容
- [ ] 展示改写后内容对比
- [ ] 支持重新改写

### 2.5 内容存储策略

#### 2.5.1 本地Markdown存储（可选）
```
output/articles/
  ├── {account_id}/
  │   ├── {record_id}_original.md   # 原文
  │   ├── {record_id}_rewritten.md  # 改写后
  │   └── images/
  │       └── {record_id}_/
  │           ├── img_001.jpg
  │           └── img_002.jpg
```

#### 2.5.2 SQLite存储（默认）
- 使用article_contents表存储
- 图片存储为base64或本地路径

## 3. 测试列表

### 3.1 单元测试

#### 3.1.1 AI调用模块测试
```python
# tests/test_ai_caller.py
def test_unified_caller_with_fallback():
    """测试AI调用自动故障转移"""
    # 模拟第一个模型失败，第二个成功
    pass

def test_analyze_plugin():
    """测试AI评分插件"""
    # 输入测试文章，验证返回包含score字段
    pass

def test_rewrite_plugin():
    """测试AI改写插件"""
    # 输入测试文章，验证返回改写后内容
    pass
```

#### 3.1.2 数据库操作测试
```python
# tests/test_workflow_store.py
def test_inspiration_crud():
    """测试灵感库增删改查"""
    pass

def test_article_content_storage():
    """测试文章内容存储"""
    pass

def test_plugin_task_tracking():
    """测试插件任务追踪"""
    pass
```

### 3.2 集成测试

#### 3.2.1 全流程测试
```python
# tests/test_full_workflow.py
def test_full_flow_inspiration_to_publish():
    """
    全流程测试：
    1. 添加灵感到库
    2. 执行AI评分
    3. 执行AI改写
    4. 执行发布
    5. 验证发布日志
    """
    pass

def test_concurrent_plugin_execution():
    """测试并发插件执行"""
    pass
```

### 3.3 API测试

#### 3.3.1 后端API测试
```bash
# tests/api/test_inspiration.sh
# 测试灵感库API
curl -X GET "http://localhost:8701/api/inspiration/list?account_id=test"
curl -X POST "http://localhost:8701/api/inspiration/add" \
  -H "Content-Type: application/json" \
  -d '{"urls": "https://example.com/article"}'

# 测试插件API
curl -X POST "http://localhost:8701/api/plugins/ai-score" \
  -H "Content-Type: application/json" \
  -d '{"record_id": "ins_xxx"}'

curl -X POST "http://localhost:8701/api/plugins/ai-rewrite" \
  -H "Content-Type: application/json" \
  -d '{"record_id": "ins_xxx", "role": "tech_expert"}'

curl -X POST "http://localhost:8701/api/plugins/publish" \
  -H "Content-Type: application/json" \
  -d '{"record_id": "ins_xxx"}'
```

### 3.4 前端测试

#### 3.4.1 E2E测试
```javascript
// tests/e2e/inspiration.spec.js
describe('灵感库全流程', () => {
  it('添加文章到灵感库', async () => {
    // 1. 点击添加按钮
    // 2. 输入URL
    // 3. 确认添加
    // 4. 验证列表出现新记录
  });

  it('执行AI评分', async () => {
    // 1. 选择文章
    // 2. 点击AI评分
    // 3. 等待完成
    // 4. 验证评分显示
  });

  it('执行AI改写', async () => {
    // 1. 选择文章
    // 2. 点击AI改写
    // 3. 等待完成
    // 4. 验证状态更新
  });

  it('发布到微信', async () => {
    // 1. 选择已改写文章
    // 2. 点击发布
    // 3. 等待完成
    // 4. 验证发布日志
  });
});
```

### 3.5 性能测试

```python
# tests/performance/test_concurrent.py
def test_100_concurrent_rewrites():
    """测试100个并发改写任务"""
    pass

def test_database_query_performance():
    """测试大数据量查询性能"""
    # 插入10000条记录，测试查询时间
    pass
```

## 4. 迁移策略

### 4.1 数据迁移
1. 保留现有pipeline_records表（只读）
2. 新数据写入article_contents表
3. 提供数据导出工具

### 4.2 配置迁移
```bash
# 旧配置
FEISHU_APP_ID=xxx
FEISHU_APP_SECRET=xxx
FEISHU_APP_TOKEN=xxx

# 新配置
STORAGE_MODE=sqlite  # sqlite | markdown
ARTICLES_DIR=./output/articles
```

## 5. 风险与应对

| 风险 | 影响 | 应对措施 |
|------|------|---------|
| 改写内容不保存到飞书 | 高 | 提供Markdown导出功能 |
| 图片存储问题 | 中 | 本地存储+URL引用 |
| 历史数据兼容性 | 中 | 保留旧表，提供迁移脚本 |
| AI调用超时 | 中 | 保持现有超时保护机制 |

## 6. 实施优先级

1. **P0** - 数据库Schema更新 (article_contents, plugin_tasks表)
2. **P0** - 移除飞书依赖的灵感库管理器
3. **P0** - 实现插件化API
4. **P1** - 前端调用新API
5. **P1** - 发布流程重构
6. **P2** - Markdown导出功能
7. **P2** - 完整测试覆盖
