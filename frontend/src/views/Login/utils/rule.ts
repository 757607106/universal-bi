import type { FormItemRule } from "element-plus";

/** 登录表单验证规则 */
export const loginRules = {
  username: [{ required: true, message: "请输入用户名", trigger: "blur" }],
  password: [{ required: true, message: "请输入密码", trigger: "blur" }]
};

/** 注册表单验证规则 */
export const registerRules = {
  email: [
    { required: true, message: "请输入邮箱", trigger: "blur" },
    { type: "email" as const, message: "请输入有效的邮箱地址", trigger: "blur" }
  ] as FormItemRule[],
  password: [
    { required: true, message: "请输入密码", trigger: "blur" },
    { min: 6, message: "密码长度至少为6位", trigger: "blur" }
  ] as FormItemRule[],
  repeatPassword: [
    { required: true, message: "请再次输入密码", trigger: "blur" }
  ] as FormItemRule[]
};
