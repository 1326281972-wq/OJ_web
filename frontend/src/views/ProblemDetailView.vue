<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getProblem, type ProblemDetail } from '../api/problems'
import { createSubmission } from '../api/submissions'
import { runCode, type RunResult } from '../wasm/runtime'

const route = useRoute()
const router = useRouter()

const problem = ref<ProblemDetail | null>(null)
const loading = ref(false)
const language = ref('cpp')
const code = ref('')
const submitting = ref(false)
const running = ref(false)
const runResult = ref<RunResult | null>(null)

async function load() {
  loading.value = true
  try {
    problem.value = await getProblem(Number(route.params.id))
  } catch (e) {
    ElMessage.error((e as Error).message)
    router.push('/problems')
  } finally {
    loading.value = false
  }
}

async function onRun() {
  running.value = true
  runResult.value = null
  try {
    runResult.value = await runCode(code.value, language.value, problem.value?.sample_input || '')
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    running.value = false
  }
}

async function onSubmit() {
  if (!code.value.trim()) {
    ElMessage.warning('请先编写代码')
    return
  }
  submitting.value = true
  try {
    const s = await createSubmission(problem.value!.id, language.value, code.value)
    ElMessage.success(`已提交 #${s.id}，等待评测`)
    router.push({ path: '/submissions', query: { focus: String(s.id) } })
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    submitting.value = false
  }
}

onMounted(load)
</script>

<template>
  <div v-loading="loading">
    <template v-if="problem">
      <div class="head">
        <h2>
          <span class="pid">P{{ problem.id }}</span>
          {{ problem.title }}
        </h2>
        <div class="limits">
          <el-tag size="small">时间 {{ problem.time_limit }} ms</el-tag>
          <el-tag size="small" type="success">内存 {{ problem.memory_limit }} MB</el-tag>
        </div>
      </div>

      <div class="layout">
        <div class="statement">
          <section>
            <h3>题目描述</h3>
            <pre class="block">{{ problem.description }}</pre>
          </section>
          <section>
            <h3>输入格式</h3>
            <pre class="block">{{ problem.input }}</pre>
          </section>
          <section>
            <h3>输出格式</h3>
            <pre class="block">{{ problem.output }}</pre>
          </section>
          <section>
            <h3>样例输入</h3>
            <pre class="block sample">{{ problem.sample_input }}</pre>
          </section>
          <section>
            <h3>样例输出</h3>
            <pre class="block sample">{{ problem.sample_output }}</pre>
          </section>
        </div>

        <div class="editor-panel">
          <div class="editor-toolbar">
            <el-select v-model="language" size="small" style="width: 110px">
              <el-option label="C++ (GCC17)" value="cpp" />
            </el-select>
            <div class="spacer" />
            <el-button size="small" :loading="running" @click="onRun">运行（WASM 演示）</el-button>
            <el-button size="small" type="primary" :loading="submitting" @click="onSubmit">
              提交评测
            </el-button>
          </div>
          <el-input
            v-model="code"
            type="textarea"
            class="code-editor"
            :rows="18"
            placeholder="#include <bits/stdc++.h> ..."
            spellcheck="false"
          />
          <div v-if="runResult" class="run-result">
            <div class="run-head">
              <span>运行结果</span>
              <el-tag v-if="runResult.demo" size="small" type="warning">演示模式</el-tag>
            </div>
            <pre class="block">{{ runResult.stdout }}{{ runResult.stderr }}</pre>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.pid {
  color: #409eff;
}
.limits :deep(.el-tag) {
  margin-left: 6px;
}
.layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 20px;
}
.statement h3 {
  margin: 12px 0 6px;
  color: #303133;
  font-size: 15px;
}
.block {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 14px;
  line-height: 1.7;
  color: #303133;
}
.sample {
  background: #f5f7fa;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  padding: 10px 12px;
  font-family: 'Cascadia Code', Consolas, Menlo, monospace;
}
.editor-toolbar {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
}
.spacer {
  flex: 1;
}
.code-editor :deep(textarea) {
  font-family: 'Cascadia Code', Consolas, Menlo, monospace;
  font-size: 14px;
  line-height: 1.6;
}
.run-result {
  margin-top: 10px;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  padding: 10px 12px;
  background: #fafafa;
}
.run-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
  font-weight: 600;
  font-size: 13px;
  color: #606266;
}
@media (max-width: 900px) {
  .layout {
    grid-template-columns: 1fr;
  }
}
</style>
