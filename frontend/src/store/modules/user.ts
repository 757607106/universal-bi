import { defineStore } from "pinia";

export const useUserStore = defineStore("user", {
  state: () => ({
    username: "Admin User",
    email: "admin@universal-bi.com",
    avatar: "UA",
    roles: ["admin"]
  }),
  actions: {
    setUserInfo(username: string, email: string) {
      this.username = username;
      this.email = email;
    }
  }
});
