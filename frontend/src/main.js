import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

import App from './App.vue'
import router from './router'

const app = createApp(App)

// 注册所有图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

// 全局错误处理
app.config.errorHandler = (err, vm, info) => {
  console.error('[Vue Error]', err, info)
}

// 路由错误处理
router.onError((error) => {
  console.error('[Router Error]', error)
})

app.use(createPinia())
app.use(router)
app.use(ElementPlus)

app.mount('#app')
