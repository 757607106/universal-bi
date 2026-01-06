<script setup lang="ts">
import { reactive, ref } from "vue";
import { getRegister } from "@/api/user";
import { registerRules } from "../utils/rule";
import { User, Lock, Message } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";

const emit = defineEmits(["switch-to-login"]);

const formRef = ref();
const loading = ref(false);

const registerForm = reactive({
  email: "",
  full_name: "",
  password: "",
  repeatPassword: ""
});

const handleRegister = async () => {
  if (!formRef.value) return;
  
  // 验证两次密码是否一致
  if (registerForm.password !== registerForm.repeatPassword) {
    ElMessage.error("两次输入的密码不一致");
    return;
  }
  
  await formRef.value.validate(async (valid: boolean) => {
    if (valid) {
      loading.value = true;
      try {
        await getRegister({
          email: registerForm.email,
          password: registerForm.password,
          full_name: registerForm.full_name || undefined
        });
        
        ElMessage.success("注册成功");
        // 切换回登录视图
        emit("switch-to-login");
      } catch (error: any) {
        console.error(error);
        ElMessage.error(error.message || "注册失败");
      } finally {
        loading.value = false;
      }
    }
  });
};

const handleBackToLogin = () => {
  emit("switch-to-login");
};
</script>

<template>
  <div class="regist-form">
    <div class="text-center mb-8">
      <h2 class="text-2xl font-bold text-gray-800 dark:text-white mb-2">创建新账号</h2>
      <p class="text-gray-500 dark:text-gray-400">请填写以下信息完成注册</p>
    </div>

    <el-form
      ref="formRef"
      :model="registerForm"
      :rules="registerRules"
      class="register-form"
      @keyup.enter="handleRegister"
    >
      <el-form-item prop="email">
        <el-input
          v-model="registerForm.email"
          placeholder="邮箱"
          :prefix-icon="Message"
          size="large"
        />
      </el-form-item>

      <el-form-item prop="full_name">
        <el-input
          v-model="registerForm.full_name"
          placeholder="全名（可选）"
          :prefix-icon="User"
          size="large"
        />
      </el-form-item>

      <el-form-item prop="password">
        <el-input
          v-model="registerForm.password"
          type="password"
          placeholder="密码（至少6位）"
          :prefix-icon="Lock"
          show-password
          size="large"
        />
      </el-form-item>

      <el-form-item prop="repeatPassword">
        <el-input
          v-model="registerForm.repeatPassword"
          type="password"
          placeholder="确认密码"
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
          @click="handleRegister"
        >
          注册
        </el-button>
      </el-form-item>

      <el-form-item class="text-center">
        <el-button
          type="text"
          @click="handleBackToLogin"
        >
          返回登录
        </el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<style scoped>
.regist-form {
  width: 100%;
}
</style>
