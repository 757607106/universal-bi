<script setup lang="ts">
import { reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { useUserStore } from "@/store/modules/user";
import { User, Lock } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import Regist from "./components/regist.vue";

const router = useRouter();
const userStore = useUserStore();

const formRef = ref();
const loading = ref(false);
const currentPage = ref(0); // 0: login, 1: register

const loginForm = reactive({
  username: "",
  password: ""
});

const rules = {
  username: [
    { required: true, message: "请输入账号", trigger: "blur" },
    { min: 3, max: 50, message: "账号长度在3-50位之间", trigger: "blur" }
  ],
  password: [{ required: true, message: "请输入密码", trigger: "blur" }]
};

const handleLogin = async () => {
  if (!formRef.value) return;
  
  await formRef.value.validate(async (valid: boolean) => {
    if (valid) {
      loading.value = true;
      try {
        // Prepare form data for backend (which expects OAuth2PasswordRequestForm usually)
        // api/user.ts handles the transformation to form-data if implemented correctly.
        // The store action calls api/user.ts -> getLogin
        await userStore.loginByUsername({
          username: loginForm.username,
          password: loginForm.password
        });
        
        // 登录成功后立即获取用户信息
        await userStore.getUserInfo();
        
        ElMessage.success("登录成功");
        router.push("/");
      } catch (error: any) {
        console.error(error);
        ElMessage.error(error.message || "登录失败");
      } finally {
        loading.value = false;
      }
    }
  });
};

const switchToRegister = () => {
  currentPage.value = 1;
};

const switchToLogin = () => {
  currentPage.value = 0;
};
</script>

<template>
  <div class="login-container flex items-center justify-center min-h-screen bg-gray-100 dark:bg-gray-900">
    <div class="login-box w-full max-w-md p-8 bg-white dark:bg-gray-800 rounded-lg shadow-lg">
      <!-- 登录表单 -->
      <div v-if="currentPage === 0">
        <div class="text-center mb-8">
          <h1 class="text-3xl font-bold text-gray-800 dark:text-white mb-2">Universal BI</h1>
          <p class="text-gray-500 dark:text-gray-400">企业级智能数据分析平台</p>
        </div>

        <el-form
          ref="formRef"
          :model="loginForm"
          :rules="rules"
          class="login-form"
          @keyup.enter="handleLogin"
        >
          <el-form-item prop="username">
            <el-input
              v-model="loginForm.username"
              placeholder="账号"
              :prefix-icon="User"
              size="large"
            />
          </el-form-item>

          <el-form-item prop="password">
            <el-input
              v-model="loginForm.password"
              type="password"
              placeholder="密码"
              :prefix-icon="Lock"
              show-password
              size="large"
            />
          </el-form-item>

          <el-form-item>
            <el-button
              type="primary"
              :loading="loading"
              class="w-full"
              size="large"
              @click="handleLogin"
            >
              登录
            </el-button>
          </el-form-item>

          <el-form-item class="text-center">
            <el-button
              type="text"
              @click="switchToRegister"
            >
              没有账号？立即注册
            </el-button>
          </el-form-item>
        </el-form>
      </div>

      <!-- 注册表单 -->
      <Regist v-if="currentPage === 1" @switch-to-login="switchToLogin" />
    </div>
  </div>
</template>

<style scoped>
.login-container {
  background-image: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
}

.dark .login-container {
  background-image: linear-gradient(135deg, #1f2937 0%, #111827 100%);
}
</style>
