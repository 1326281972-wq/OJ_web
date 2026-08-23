<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { listProblems, type ProblemListItem } from '../api/problems'

const router = useRouter()
const loading = ref(false)
const items = ref<ProblemListItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const keyword = ref('')

async function load() {
  loading.value = true
  try {
    const r = await listProblems(page.value, pageSize.value, keyword.value || undefined)
    items.value = r.items
    total.value = r.total
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    loading.value = false
  }
}

function onSearch() {
  page.value = 1
  load()
}

onMounted(load)
</script>

<template>
  <div>
    <div class="toolbar">
      <h2>题库</h2>
      <el-input
        v-model="keyword"
        placeholder="按标题搜索"
        clearable
        class="search"
        @keyup.enter="onSearch"
        @clear="onSearch"
      >
        <template #append>
          <el-button @click="onSearch">搜索</el-button>
        </template>
      </el-input>
    </div>

    <el-table :data="items" v-loading="loading" row-class-name="clickable" @row-click="(row: ProblemListItem) => router.push(`/problems/${row.id}`)">
      <el-table-column prop="id" label="编号" width="90" />
      <el-table-column prop="title" label="标题" min-width="220" />
      <el-table-column label="时间限制" width="120">
        <template #default="{ row }">{{ row.time_limit }} ms</template>
      </el-table-column>
      <el-table-column label="内存限制" width="120">
        <template #default="{ row }">{{ row.memory_limit }} MB</template>
      </el-table-column>
      <el-table-column label="类型" width="100">
        <template #default="{ row }">
          <el-tag :type="row.spj === 2 ? 'warning' : 'info'" size="small">
            {{ row.spj === 2 ? '交互题' : '普通题' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="" width="90">
        <template #default="{ row }">
          <el-button size="small" type="primary" plain @click.stop="router.push(`/problems/${row.id}`)">
            做题
          </el-button>
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
  </div>
</template>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.search {
  width: 280px;
}
.pager {
  margin-top: 16px;
  justify-content: flex-end;
}
:deep(.clickable) {
  cursor: pointer;
}
</style>
