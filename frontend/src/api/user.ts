import { http } from "@/utils/http";

export type UserResult = {
  success: boolean;
  data: {
    /** 头像 */
    avatar: string;
    /** 用户名 */
    username: string;
    /** 昵称 */
    nickname: string;
    /** 当前登录用户的角色 */
    roles: Array<string>;
    /** 按钮级别权限 */
    permissions: Array<string>;
    /** `token` */
    accessToken: string;
    /** 用于调用刷新`accessToken`的接口时所需的`token` */
    refreshToken: string;
    /** `accessToken`的过期时间（格式'xxxx/xx/xx xx:xx:xx'） */
    expires: Date;
  };
};

export type RefreshTokenResult = {
  success: boolean;
  data: {
    accessToken: string;
    refreshToken: string;
    expires: Date;
  };
};

/** 登录 */
export const getLogin = (data?: object) => {
  // Use URLSearchParams for application/x-www-form-urlencoded
  const params = new URLSearchParams();
  for (const key in data) {
    params.append(key, (data as any)[key]);
  }

  return http.request<any>("post", "/auth/login", {
    data: params,
    headers: {
      "Content-Type": "application/x-www-form-urlencoded"
    }
  });
};

/** 刷新token */
export const getRefreshToken = (data?: object) => {
  return http.request<RefreshTokenResult>("post", "/auth/refresh-token", { data });
};

/** 注册 */
export const getRegister = (data?: object) => {
  return http.request<any>("post", "/auth/register", { data });
};

/** 退出登录 */
export const logout = () => {
  return http.request<any>("post", "/auth/logout");
};

/** 获取当前用户信息 */
export const getCurrentUser = () => {
  return http.request<any>("get", "/auth/me");
};
