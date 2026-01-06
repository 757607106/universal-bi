import { http } from "@/utils/http";

/** 用户列表项 */
export interface SystemUser {
  id: number;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_superuser: boolean;
  is_deleted: boolean;
  role: string;
}

/** 用户列表响应 */
export interface UsersListResponse {
  total: number;
  page: number;
  page_size: number;
  users: SystemUser[];
}

/** 更新用户状态请求 */
export interface UserStatusUpdate {
  is_active: boolean;
}

/** 管理员修改用户信息请求 */
export interface UserUpdateByAdmin {
  full_name?: string;
  password?: string;
  role?: string;
}

/**
 * 获取用户列表
 * @param page 页码
 * @param page_size 每页数量
 * @param search 搜索关键词
 */
export const getUserList = (params: {
  page?: number;
  page_size?: number;
  search?: string;
}) => {
  return http.get<UsersListResponse, typeof params>("/admin/users", params);
};

/**
 * 更新用户状态（封禁/解封）
 * @param userId 用户ID
 * @param data 状态数据
 */
export const updateUserStatus = (userId: number, data: UserStatusUpdate) => {
  return http.request<SystemUser>("patch", `/admin/users/${userId}/status`, {
    data
  });
};

/**
 * 软删除用户
 * @param userId 用户ID
 */
export const deleteUser = (userId: number) => {
  return http.delete<SystemUser, undefined>(`/admin/users/${userId}`);
};

/**
 * 管理员修改用户信息
 * @param userId 用户ID
 * @param data 用户信息
 */
export const updateUser = (userId: number, data: UserUpdateByAdmin) => {
  return http.request<SystemUser>("patch", `/admin/users/${userId}`, {
    data
  });
};
