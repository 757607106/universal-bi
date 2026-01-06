import { useStorage } from "@vueuse/core";

const TokenKey = "authorized-token";

export interface TokenInfo {
  accessToken: string;
  expires?: number;
}

// Using localStorage via simple wrapper or @vueuse/core if complex reactivity needed.
// For simple token storage, native localStorage is fine, but let's be consistent.
// We'll use a simple object for now to match "Vue Pure Admin" style setToken/getToken

export function getToken(): string | null {
  return localStorage.getItem(TokenKey);
}

export function setToken(token: string) {
  localStorage.setItem(TokenKey, token);
}

export function removeToken() {
  localStorage.removeItem(TokenKey);
}
