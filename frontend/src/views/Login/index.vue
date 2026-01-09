<script setup lang="ts">
import { reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { useUserStore } from "@/store/modules/user";
import { User, Lock, DataAnalysis } from "@element-plus/icons-vue";
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
  <div class="login-container relative flex items-center justify-center min-h-screen overflow-hidden bg-gray-900 font-sans">
    <!-- 动态背景 -->
    <div class="absolute inset-0 z-0">
      <div class="absolute top-[-20%] left-[-10%] w-[60%] h-[60%] rounded-full bg-primary/20 blur-[150px] animate-float"></div>
      <div class="absolute bottom-[-20%] right-[-10%] w-[60%] h-[60%] rounded-full bg-cyber-purple/20 blur-[150px] animate-float" style="animation-delay: -4s"></div>
      <div class="absolute top-[40%] left-[40%] w-[30%] h-[30%] rounded-full bg-cyber-cyan/20 blur-[120px] animate-float" style="animation-delay: -2s"></div>
      <div class="absolute inset-0" 
           style="background-image: linear-gradient(#ffffff 1px, transparent 1px), linear-gradient(90deg, #ffffff 1px, transparent 1px); background-size: 20px 20px; opacity: 0.03;">
      </div>
    </div>

    <!-- 登录卡片 -->
    <div class="relative z-10 w-full max-w-md p-1">
      <div class="absolute -inset-1 bg-gradient-to-r from-primary via-cyber-purple to-cyber-cyan rounded-2xl blur opacity-70 animate-pulse-glow"></div>
      <div class="relative bg-white/10 dark:bg-dark-glass backdrop-blur-xl rounded-2xl p-8 shadow-glass border border-white/10">
        
        <!-- Logo & Title -->
        <div class="text-center mb-10">
          <div class="w-16 h-16 mx-auto mb-4 bg-gradient-to-br from-primary to-cyber-cyan rounded-2xl flex items-center justify-center shadow-lg shadow-primary/30 transform rotate-3 hover:rotate-0 transition-transform duration-500">
            <el-icon class="text-3xl text-white"><DataAnalysis /></el-icon>
          </div>
          <h1 class="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-slate-300 mb-2">Universal BI</h1>
          <p class="text-slate-400 text-sm tracking-wide">企业级智能数据分析平台</p>
        </div>

        <!-- 登录表单 -->
        <div v-if="currentPage === 0" class="space-y-6">
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
                class="custom-input"
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
                class="custom-input"
              />
            </el-form-item>

            <el-form-item>
              <el-button
                :loading="loading"
                class="w-full !h-12 !text-lg !font-medium !rounded-xl !bg-gradient-to-r !from-primary !to-cyber-cyan !border-none hover:!shadow-neon hover:!scale-[1.02] transition-all duration-300"
                type="primary"
                @click="handleLogin"
              >
                登 录
              </el-button>
            </el-form-item>

            <div class="flex items-center justify-between mt-6">
              <el-checkbox label="记住我" class="!text-slate-400" />
              <el-button type="text" class="!text-primary hover:!text-primary-glow" @click="switchToRegister">
                注册新账号
              </el-button>
            </div>
          </el-form>
        </div>

        <!-- 注册表单 -->
        <div v-if="currentPage === 1">
          <Regist @switch-to-login="switchToLogin" />
        </div>
      </div>
    </div>
    
    <!-- 底部版权 -->
    <div class="absolute bottom-6 text-center text-slate-500 text-xs">
      &copy; 2024 Universal BI. All rights reserved.
    </div>
  </div>
</template>

<style scoped>
/* 自定义输入框样式 */
:deep(.custom-input .el-input__wrapper) {
  background-color: rgba(255, 255, 255, 0.05) !important;
  box-shadow: none !important;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  padding: 4px 12px;
  transition: all 0.3s;
}

:deep(.custom-input .el-input__wrapper:hover) {
  background-color: rgba(255, 255, 255, 0.1) !important;
  border-color: rgba(255, 255, 255, 0.2);
}

:deep(.custom-input .el-input__wrapper.is-focus) {
  background-color: rgba(255, 255, 255, 0.1) !important;
  border-color: #3b82f6 !important;
  box-shadow: 0 0 0 1px #3b82f6 !important;
}

:deep(.custom-input .el-input__inner) {
  color: white !important;
  height: 44px;
}

:deep(.custom-input .el-input__icon) {
  color: #94a3b8;
}
</style>
