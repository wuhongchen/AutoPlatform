#!/bin/bash
# AutoInfo Platform - 自动化测试脚本
# 测试重构后的插件化系统

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TEST_DB="$PROJECT_ROOT/output/test_workflow.db"

echo "============================================================"
echo "  AutoInfo Platform - 自动化测试"
echo "============================================================"
echo "项目目录: $PROJECT_ROOT"
echo "测试时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "------------------------------------------------------------"

# 清理旧的测试数据库
echo "[1/6] 清理测试环境..."
rm -f "$TEST_DB"

# 运行Python单元测试
echo ""
echo "[2/6] 运行Python单元测试..."
cd "$PROJECT_ROOT"
if python3 tests/test_full_system.py; then
    echo "✅ Python单元测试通过"
else
    echo "❌ Python单元测试失败"
    exit 1
fi

# 检查数据库状态
echo ""
echo "[3/6] 检查数据库状态..."
if [ -f "$PROJECT_ROOT/output/workflow.db" ]; then
    sqlite3 "$PROJECT_ROOT/output/workflow.db" "SELECT COUNT(*) FROM inspiration_records;" 2>/dev/null || echo "无法查询灵感库表"
    sqlite3 "$PROJECT_ROOT/output/workflow.db" "SELECT COUNT(*) FROM publish_logs;" 2>/dev/null || echo "无法查询发布日志表"
else
    echo "数据库文件不存在"
fi

# 检查API服务状态
echo ""
echo "[4/6] 检查API服务状态..."
if curl -s http://localhost:8701/api/health > /dev/null 2>&1; then
    echo "✅ API服务运行中"
    curl -s http://localhost:8701/api/health | python3 -m json.tool 2>/dev/null || true
else
    echo "⚠️ API服务未运行 (这是正常的，如果服务没有启动)"
fi

# 测试前端构建
echo ""
echo "[5/6] 检查前端构建状态..."
FRONTEND_DIR="$PROJECT_ROOT/frontend/admin"
if [ -d "$FRONTEND_DIR/dist" ]; then
    echo "✅ 前端已构建"
    echo "   构建文件数: $(find "$FRONTEND_DIR/dist" -type f | wc -l)"
else
    echo "⚠️ 前端未构建 (运行 cd frontend/admin && npm run build)"
fi

# 生成测试报告
echo ""
echo "[6/6] 生成测试报告..."
REPORT_FILE="$PROJECT_ROOT/output/test_report_$(date +%Y%m%d_%H%M%S).txt"
{
    echo "AutoInfo Platform 测试报告"
    echo "=========================="
    echo "测试时间: $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""
    echo "数据库状态:"
    sqlite3 "$PROJECT_ROOT/output/workflow.db" ".tables" 2>/dev/null || echo "无法连接数据库"
    echo ""
    echo "Git状态:"
    git -C "$PROJECT_ROOT" status --short 2>/dev/null || echo "非Git仓库"
    echo ""
    echo "最近提交:"
    git -C "$PROJECT_ROOT" log --oneline -5 2>/dev/null || echo "无Git历史"
} > "$REPORT_FILE"

echo "测试报告已保存: $REPORT_FILE"

echo ""
echo "============================================================"
echo "  测试完成！"
echo "============================================================"
