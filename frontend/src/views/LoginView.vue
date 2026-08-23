<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const mode = ref<'login' | 'register'>('login')
const loading = ref(false)
const form = reactive({ user_id: '', password: '', nickname: '', email: '' })

async function submit() {
  if (!form.user_id || !form.password) {
    ElMessage.warning('请填写用户名与密码')
    return
  }
  if (mode.value === 'register') {
    if (!form.nickname) {
      ElMessage.warning('注册需填写昵称')
      return
    }
    if (form.password.length < 6) {
      ElMessage.warning('密码至少 6 位')
      return
    }
  }
  loading.value = true
  try {
    if (mode.value === 'login') {
      await auth.login(form.user_id, form.password)
    } else {
      await auth.register(form.user_id, form.password, form.nickname, form.email || undefined)
    }
    ElMessage.success(mode.value === 'login' ? '登录成功' : '注册成功，已自动登录')
    router.push((route.query.redirect as string) || '/problems')
  } catch (e) {
    ElMessage.error((e as Error).message || '请求失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <el-card class="login-card">
      <h2 class="title">OJ Web · 在线评测系统</h2>
      <el-tabs v-model="mode" stretch>
        <el-tab-pane label="登录" name="login">
          <el-form label-position="top" @submit.prevent="submit">
            <el-form-item label="用户名">
              <el-input v-model="form.user_id" placeholder="如 demo_user" autocomplete="username" />
            </el-form-item>
            <el-form-item label="密码">
              <el-input
                v-model="form.password"
                type="password"
                show-password
                placeholder="如 demo123"
                autocomplete="current-password"
                @keyup.enter="submit"
              />
            </el-form-item>
            <el-button type="primary" class="w-full" :loading="loading" @click="submit">
              登 录
            </el-button>
          </el-form>
        </el-tab-pane>
        <el-tab-pane label="注册" name="register">
          <el-form label-position="top" @submit.prevent="submit">
            <el-form-item label="用户名">
              <el-input v-model="form.user_id" placeholder="不超过 64 字符" autocomplete="username" />
            </el-form-item>
            <el-form-item label="昵称">
              <el-input v-model="form.nickname" placeholder="必填" />
            </el-form-item>
            <el-form-item label="密码">
              <el-input
                v-model="form.password"
                type="password"
                show-password
                placeholder="至少 6 位"
                autocomplete="new-password"
              />
            </el-form-item>
            <el-form-item label="邮箱（可选）">
              <el-input v-model="form.email" placeholder="如 a@x.com" />
            </el-form-item>
            <el-button type="primary" class="w-full" :loading="loading" @click="submit">
              注册并登录
            </el-button>
          </el-form>
        </el-tab-pane>
      </el-tabs>
      <p class="hint">演示账号：admin / admin123（管理员），demo_user / demo123（选手）</p>
    </el-card>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #eef4ff 0%, #f5f7fa 100%);
}
.login-card {
  width: 420px;
}
.title {
  text-align: center;
  margin: 0 0 12px;
  color: #303133;
}
.hint {
  margin-top: 14px;
  font-size: 12px;
  color: #909399;
  text-align: center;
}
.w-full {
  width: 100%;
}
</style>
