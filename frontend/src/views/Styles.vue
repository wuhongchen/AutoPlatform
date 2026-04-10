<template>
  <div class="styles-page">
    <!-- 操作栏 -->
    <div class="toolbar">
      <el-radio-group v-model="filterType" size="large">
        <el-radio-button label="all">全部</el-radio-button>
        <el-radio-button label="builtin">内置</el-radio-button>
        <el-radio-button label="custom">自定义</el-radio-button>
      </el-radio-group>
      <el-button type="primary" size="large" @click="openCreateDialog">
        <el-icon><Plus /></el-icon>新建风格
      </el-button>
    </div>

    <!-- 风格列表 -->
    <el-table :data="filteredStyles" v-loading="loading" stripe>
      <el-table-column label="风格名称" min-width="180">
        <template #default="{ row }">
          <div class="style-name">
            <span class="name">{{ row.name }}</span>
            <span class="id">{{ row.id }}</span>
          </div>
        </template>
      </el-table-column>
      
      <el-table-column label="描述" prop="description" min-width="200" />
      
      <el-table-column label="语气" width="100">
        <template #default="{ row }">
          <el-tag size="small">{{ row.tone }}</el-tag>
        </template>
      </el-table-column>
      
      <el-table-column label="类型" width="100">
        <template #default="{ row }">
          <el-tag :type="row.is_builtin ? 'info' : 'success'" size="small">
            {{ row.is_builtin ? '内置' : '自定义' }}
          </el-tag>
        </template>
      </el-table-column>
      
      <el-table-column label="温度" width="80">
        <template #default="{ row }">
          {{ row.temperature }}
        </template>
      </el-table-column>
      
      <el-table-column label="使用次数" width="100">
        <template #default="{ row }">
          {{ row.usage_count || 0 }}
        </template>
      </el-table-column>
      
      <el-table-column label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.is_active !== false ? 'success' : 'warning'" size="small">
            {{ row.is_active !== false ? '启用' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="{ row }">
          <el-button-group>
            <el-button 
              size="small" 
              @click="openEditDialog(row)"
              :disabled="row.is_builtin"
            >
              编辑
            </el-button>
            <el-button 
              size="small" 
              @click="handleToggle(row)"
            >
              {{ row.is_active !== false ? '禁用' : '启用' }}
            </el-button>
            <el-button 
              size="small" 
              type="danger" 
              @click="handleDelete(row)"
              :disabled="row.is_builtin"
            >
              删除
            </el-button>
          </el-button-group>
        </template>
      </el-table-column>
    </el-table>

    <!-- 创建/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑风格' : '新建风格'"
      width="700px"
      destroy-on-close
    >
      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="风格名称" prop="name">
          <el-input v-model="form.name" placeholder="例如：科技专家" />
        </el-form-item>
        
        <el-form-item label="标识ID" prop="id" v-if="!isEdit">
          <el-input v-model="form.id" placeholder="例如：tech_expert" />
          <span class="form-tip">唯一标识，创建后不可修改</span>
        </el-form-item>
        
        <el-form-item label="描述">
          <el-input v-model="form.description" placeholder="简短描述风格特点" />
        </el-form-item>
        
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="写作语气">
              <el-select v-model="form.tone" style="width: 100%">
                <el-option label="专业严谨" value="professional" />
                <el-option label="轻松随意" value="casual" />
                <el-option label="幽默风趣" value="humorous" />
                <el-option label="严肃正式" value="serious" />
                <el-option label="亲切友好" value="friendly" />
                <el-option label="权威可信" value="authoritative" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="写作风格">
              <el-select v-model="form.style" style="width: 100%">
                <el-option label="叙事型" value="narrative" />
                <el-option label="分析型" value="analytical" />
                <el-option label="说服型" value="persuasive" />
                <el-option label="描述型" value="descriptive" />
                <el-option label="技术型" value="technical" />
                <el-option label="讲故事型" value="storytelling" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="Temperature">
              <el-slider v-model="form.temperature" :min="0" :max="2" :step="0.1" show-input />
              <span class="form-tip">越高越有创意，越低越稳定</span>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="最大 Tokens">
              <el-input-number v-model="form.max_tokens" :min="100" :max="8000" :step="100" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-form-item label="系统提示词" prop="system_prompt">
          <el-input 
            v-model="form.system_prompt" 
            type="textarea" 
            :rows="8"
            placeholder="输入系统提示词，定义AI的写作角色和要求..."
          />
          <span class="form-tip">这是核心配置，告诉AI如何改写文章</span>
        </el-form-item>
        
        <el-form-item label="额外参数">
          <el-input 
            v-model="form.params" 
            type="textarea" 
            :rows="3"
            placeholder='{"focus": "技术深度", "avoid": "过于简单"}'
          />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">
          保存
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { useStyleStore } from '../stores'

const styleStore = useStyleStore()

const loading = ref(false)
const filterType = ref('all')
const dialogVisible = ref(false)
const isEdit = ref(false)
const submitting = ref(false)
const formRef = ref(null)

const form = ref({
  id: '',
  name: '',
  description: '',
  system_prompt: '',
  tone: 'professional',
  style: 'analytical',
  temperature: 0.7,
  max_tokens: 4000,
  params: ''
})

const rules = {
  name: [{ required: true, message: '请输入风格名称', trigger: 'blur' }],
  id: [{ required: true, message: '请输入标识ID', trigger: 'blur' }],
  system_prompt: [{ required: true, message: '请输入系统提示词', trigger: 'blur' }]
}

const filteredStyles = computed(() => {
  if (filterType.value === 'all') return styleStore.styles
  if (filterType.value === 'builtin') return styleStore.styles.filter(s => s.is_builtin)
  return styleStore.styles.filter(s => !s.is_builtin)
})

function openCreateDialog() {
  isEdit.value = false
  form.value = {
    id: '',
    name: '',
    description: '',
    system_prompt: '',
    tone: 'professional',
    style: 'analytical',
    temperature: 0.7,
    max_tokens: 4000,
    params: ''
  }
  dialogVisible.value = true
}

function openEditDialog(row) {
  isEdit.value = true
  form.value = {
    ...row,
    params: JSON.stringify(row.params || {}, null, 2)
  }
  dialogVisible.value = true
}

async function handleSubmit() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    const data = {
      ...form.value,
      params: form.value.params ? JSON.parse(form.value.params) : {}
    }
    
    if (isEdit.value) {
      await styleStore.updateStyle(form.value.id, data)
      ElMessage.success('更新成功')
    } else {
      await styleStore.createStyle(data)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
  } catch (error) {
    ElMessage.error(error.message || '操作失败')
  } finally {
    submitting.value = false
  }
}

async function handleToggle(row) {
  try {
    await styleStore.toggleStyle(row.id)
    ElMessage.success('状态更新成功')
  } catch (error) {
    ElMessage.error(error.message || '操作失败')
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm('确定要删除这个风格预设吗？', '确认删除', {
      type: 'warning'
    })
    await styleStore.deleteStyle(row.id)
    ElMessage.success('删除成功')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '删除失败')
    }
  }
}

onMounted(() => {
  loading.value = true
  styleStore.fetchStyles(true).finally(() => {
    loading.value = false
  })
})
</script>

<style scoped>
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.style-name {
  display: flex;
  flex-direction: column;
}

.style-name .name {
  font-weight: 500;
}

.style-name .id {
  font-size: 12px;
  color: #64748b;
}

.form-tip {
  font-size: 12px;
  color: #64748b;
  margin-top: 4px;
}
</style>
