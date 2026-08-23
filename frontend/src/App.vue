<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useAuthStore } from './stores/auth'

const auth = useAuthStore()
const router = useRouter()

function onLogout() {
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <div class="app-shell">
    <header v-if="auth.isLoggedIn" class="topbar">
      <div class="brand">OJ Web · 在线评测系统</div>
      <nav class="nav">
        <router-link to="/problems" class="nav-link">题库</router-link>
        <router-link to="/submissions" class="nav-link">我的提交</router-link>
      </nav>
      <div class="user">
        <el-tag size="small" :type="auth.user?.role === 'admin' ? 'danger' : 'primary'">
          {{ auth.user?.role === 'admin' ? '管理员' : '选手' }}
        </el-tag>
        <span class="nick">{{ auth.user?.nickname || auth.user?.user_id }}</span>
        <el-button size="small" @click="onLogout">退出</el-button>
      </div>
    </header>
    <main class="content">
      <router-view />
    </main>
  </div>
</template>

<style scoped>
.app-shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
.topbar {
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 0 24px;
  height: 56px;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  position: sticky;
  top: 0;
  z-index: 10;
}
.brand {
  font-weight: 700;
  color: #303133;
}
.nav {
  display: flex;
  gap: 18px;
  flex: 1;
}
.nav-link {
  color: #606266;
  text-decoration: none;
  font-size: 14px;
}
.nav-link.router-link-active {
  color: #409eff;
  font-weight: 600;
}
.user {
  display: flex;
  align-items: center;
  gap: 8px;
}
.nick {
  font-size: 14px;
  color: #303133;
}
.content {
  flex: 1;
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px 24px 40px;
}
</style>
