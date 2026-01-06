import { defineStore } from "pinia";
import { getLogin, logout as apiLogout, getCurrentUser } from "@/api/user";
import { setToken, getToken, removeToken } from "@/utils/auth";
import { ElMessage } from "element-plus";

export const useUserStore = defineStore("user", {
  state: () => ({
    username: "Admin User",
    email: "admin@universal-bi.com",
    avatar: "UA",
    roles: ["admin"],
    token: getToken(),
    is_superuser: false,
    userId: null as number | null
  }),
  actions: {
    setUserInfo(userInfo: any) {
      this.username = userInfo.full_name || userInfo.email;
      this.email = userInfo.email;
      this.is_superuser = userInfo.is_superuser || false;
      this.userId = userInfo.id;
      // 根据用户权限设置角色
      this.roles = userInfo.is_superuser ? ["admin", "superuser"] : ["user"];
      // 生成头像缩写
      if (userInfo.full_name) {
        this.avatar = userInfo.full_name.substring(0, 2).toUpperCase();
      } else {
        this.avatar = userInfo.email.substring(0, 2).toUpperCase();
      }
    },
    /** 获取用户信息 */
    async getUserInfo() {
      try {
        const res = await getCurrentUser();
        this.setUserInfo(res);
        return res;
      } catch (error) {
        console.error("获取用户信息失败:", error);
        throw error;
      }
    },
    /** 登录 */
    async loginByUsername(data: any) {
      return new Promise<any>((resolve, reject) => {
        getLogin(data)
          .then(res => {
            if (res.access_token) {
              const token = res.access_token;
              this.token = token;
              setToken(token);
              // Mock roles for now as requested
              this.roles = ["admin"];
              resolve(res);
            } else {
              reject(new Error("Token not found in response"));
            }
          })
          .catch(error => {
            reject(error);
          });
      });
    },
    /** 登出 */
    async logOut() {
      try {
        // 调用后端退出接口，将 Token 加入黑名单
        await apiLogout();
      } catch (error) {
        console.error("退出登录失败:", error);
        // 即使后端调用失败，也要清除本地 token
      } finally {
        this.token = "";
        this.roles = [];
        this.is_superuser = false;
        this.userId = null;
        removeToken();
      }
    }
  }
});
