<script setup lang="ts">
import { onMounted, ref } from 'vue'
import axios from 'axios'

const health = ref('checking...')
const apiBase = import.meta.env.VITE_API_BASE || '/api'

onMounted(async () => {
  try {
    const { data } = await axios.get(`${apiBase}/v1/health`)
    health.value = JSON.stringify(data)
  } catch (e: unknown) {
    health.value = '后端不可达，请先启动 backend（uvicorn app.main:app --port 8000）'
  }
})
</script>

<template>
  <main class="page">
    <h1>OJ Web 在线测评系统（第 3 天基线页）</h1>
    <p>后端健康检查：{{ health }}</p>
    <p>当前基线：后端 7 表建库 + 注册/登录(JWT) + 题库 + 提交 + 假评测器（FAKE_JUDGE=true，第 4 天替换）。</p>
  </main>
</template>
