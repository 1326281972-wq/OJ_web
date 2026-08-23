<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  getSubmission,
  getSubmissionStatus,
  listSubmissions,
  type SubmissionDetail,
  type SubmissionListItem,
} from '../api/submissions'
import { ACTIVE_STATUSES, statusMeta } from '../utils/status'

const route = useRoute()
const router = useRouter()

const rows = ref<SubmissionListItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)

const detailVisible = ref(false)
const detail = ref<SubmissionDetail | null>(null)
const detailLoading = ref(false)

let timer: ReturnType<typeof setInterval> | null = null
let pollTries = 0
const MAX_POLL_TRIES = 60 // 最长约 2 分钟

async function load() {
  loading.value = true
  try {
    const r = await listSubmissions(page.value, pageSize.value)
    rows.value = r.items
    total.value = r.total
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    loading.value = false
  }
}

/** 轮询：对仍在 pending/compiling/running 的行批量取状态 */
async function poll() {
  const active = rows.value.filter((r) => ACTIVE_STATUSES.includes(r.status))
  if (active.length === 0 || pollTries >= MAX_POLL_TRIES) return
  pollTries += 1
  try {
    const st = await getSubmissionStatus(active.map((r) => r.id))
    const map = new Map(st.map((s) => [s.id, s.status]))
    rows.value = rows.value.map((r) =>
      map.has(r.id) ? { ...r, status: map.get(r.id)! } : r,
    )
  } catch (e) {
    // 轮询失败不打断列表，下次再试
    console.warn('poll failed:', e)
  }
}

async function openDetail(id: number) {
  detailVisible.value = true
  detailLoading.value = true
  try {
    detail.value = await getSubmission(id)
  } catch (e) {
    ElMessage.error((e as Error).message)
    detailVisible.value = false
  } finally {
    detailLoading.value = false
  }
}

onMounted(() => {
  load()
  timer = setInterval(poll, 2000)
  // 从题目详情跳转过来时高亮刚提交的记录
  const focus = route.query.focus
  if (focus) {
    setTimeout(() => {
      document
        .querySelector(`tr[row-id="sub-${focus}"]`)
        ?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }, 600)
  }
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<template>
  <div>
    <div class="toolbar">
      <h2>我的提交</h2>
      <el-button size="small" @click="load">刷新</el-button>
    </div>

    <el-table :data="rows" v-loading="loading" :row-key="(r: SubmissionListItem) => r.id" :row-class-name="(r: SubmissionListItem) => route.query.focus === String(r.id) ? 'focus-row' : ''">
      <el-table-column prop="id" label="编号" width="90" />
      <el-table-column label="题目" min-width="120">
        <template #default="{ row }">
          <el-link type="primary" @click="router.push(`/problems/${row.problem_id}`)">
            P{{ row.problem_id }}
          </el-link>
        </template>
      </el-table-column>
      <el-table-column label="语言" width="90">
        <template #default="{ row }">{{ row.language === 'cpp' ? 'C++' : row.language }}</template>
      </el-table-column>
      <el-table-column label="状态" width="130">
        <template #default="{ row }">
          <el-tag :type="statusMeta(row.status).type" size="small">
            {{ statusMeta(row.status).label }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="耗时" width="90">
        <template #default="{ row }">{{ row.time_used ?? '—' }} ms</template>
      </el-table-column>
      <el-table-column label="内存" width="90">
        <template #default="{ row }">{{ row.memory_used ?? '—' }} MB</template>
      </el-table-column>
      <el-table-column prop="submitted_at" label="提交时间" min-width="170" />
      <el-table-column label="" width="90">
        <template #default="{ row }">
          <el-button size="small" @click="openDetail(row.id)">详情</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      class="pager"
      layout="total, prev, pager, next"
      :total="total"
      :page-size="pageSize"
      :current-page="page"
      @current-change="(p: number) => { page = p; load() }"
    />

    <el-dialog v-model="detailVisible" title="提交详情" width="720px" v-loading="detailLoading">
      <template v-if="detail">
        <p class="meta">
          编号 #{{ detail.id }} · 题目 P{{ detail.problem_id }} · 语言
          {{ detail.language === 'cpp' ? 'C++' : detail.language }} · 状态
          <el-tag :type="statusMeta(detail.status).type" size="small">
            {{ statusMeta(detail.status).label }}
          </el-tag>
        </p>
        <h4>代码</h4>
        <pre class="code">{{ detail.code }}</pre>
        <template v-if="detail.compile_info">
          <h4>编译信息</h4>
          <pre class="info">{{ detail.compile_info }}</pre>
        </template>
        <template v-if="detail.run_info">
          <h4>运行信息</h4>
          <pre class="info">{{ detail.run_info }}</pre>
        </template>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.pager {
  margin-top: 16px;
  justify-content: flex-end;
}
.code {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 12px;
  border-radius: 6px;
  font-family: 'Cascadia Code', Consolas, Menlo, monospace;
  font-size: 13px;
  max-height: 300px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
}
.info {
  background: #fff7e6;
  border: 1px solid #ffe58f;
  color: #614700;
  padding: 10px;
  border-radius: 6px;
  font-size: 13px;
  white-space: pre-wrap;
}
.meta {
  margin: 0 0 8px;
}
:deep(.focus-row) {
  --el-table-tr-bg-color: #ecf5ff;
  --el-table-row-hover-bg-color: #d9ecff;
}
</style>
