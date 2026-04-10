<template>
  <div class="pipeline-page">
    <el-card shadow="never">
      <template #header>
        <div class="flex justify-between items-center">
          <span>流水线任务</span>
          <el-button type="primary" @click="runPipeline">
            <el-icon><VideoPlay /></el-icon>运行流水线
          </el-button>
        </div>
      </template>

      <el-empty description="流水线功能开发中...">
        <template #description>
          <p>一键批量处理：采集 → 改写 → 发布</p>
          <p class="text-gray-400 text-sm mt-2">自动处理待改写的文章</p>
        </template>
      </el-empty>
    </el-card>
  </div>
</template>

<script setup>
import { VideoPlay } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import api from '../api'

async function runPipeline() {
  try {
    await api.pipeline.process({ account_id: 'default', batch_size: 3 })
    ElMessage.success('流水线已启动')
  } catch (error) {
    ElMessage.error(error.message || '启动失败')
  }
}
</script>
