import Axios, {
  type AxiosInstance,
  type AxiosRequestConfig,
  type CustomParamsSerializer,
  type AxiosError
} from "axios";
import NProgress from "nprogress";
import "nprogress/nprogress.css";
import { getToken, removeToken } from "@/utils/auth";

// 默认配置
const defaultConfig: AxiosRequestConfig = {
  baseURL: "/api/v1",
  timeout: 60000,  // AI 查询可能需要更长时间，设置为 60 秒
  headers: {
    "Content-Type": "application/json",
    "X-Requested-With": "XMLHttpRequest"
  }
};

class PureHttp {
  constructor() {
    this.httpInterceptorsRequest();
    this.httpInterceptorsResponse();
  }

  /** 初始化配置对象 */
  private static initConfig: AxiosRequestConfig = {};

  /** 保存当前Axios实例对象 */
  private static axiosInstance: AxiosInstance = Axios.create(defaultConfig);

  /** 请求拦截 */
  private httpInterceptorsRequest(): void {
    PureHttp.axiosInstance.interceptors.request.use(
      async (config: any) => {
        // 开启进度条
        NProgress.start();
        // 可以在这里添加token
        const token = getToken();
        if (token) {
          config.headers["Authorization"] = `Bearer ${token}`;
        }
        return config;
      },
      error => {
        return Promise.reject(error);
      }
    );
  }

  /** 响应拦截 */
  private httpInterceptorsResponse(): void {
    PureHttp.axiosInstance.interceptors.response.use(
      (response: any) => {
        // 关闭进度条
        NProgress.done();
        // 这里可以根据后端返回的状态码做统一处理
        return response.data; // 直接返回data，适配原有的api调用习惯
      },
      (error: AxiosError) => {
        // 关闭进度条
        NProgress.done();
        // 处理 HTTP 网络错误
        let message = "";
        // HTTP 状态码
        const status = error.response?.status;
        switch (status) {
          case 400:
            message = "请求错误";
            break;
          case 401:
            message = "未授权，请登录";
            removeToken();
            window.location.href = "/login";
            break;
          case 403:
            message = "拒绝访问";
            break;
          case 404:
            message = `请求地址出错: ${error.response?.config?.url}`;
            break;
          case 408:
            message = "请求超时";
            break;
          case 500:
            message = "服务器内部错误";
            break;
          case 501:
            message = "服务未实现";
            break;
          case 502:
            message = "网关错误";
            break;
          case 503:
            message = "服务不可用";
            break;
          case 504:
            message = "网关超时";
            break;
          case 505:
            message = "HTTP版本不受支持";
            break;
          default:
            message = "网络连接故障";
        }
        console.error(message);
        return Promise.reject(error);
      }
    );
  }

  /** 通用请求工具函数 */
  public request<T>(
    method: string,
    url: string,
    param?: AxiosRequestConfig,
    axiosConfig?: AxiosRequestConfig
  ): Promise<T> {
    const config = {
      method,
      url,
      ...param,
      ...axiosConfig
    } as AxiosRequestConfig;

    return new Promise((resolve, reject) => {
      PureHttp.axiosInstance
        .request(config)
        .then((response: any) => {
          resolve(response);
        })
        .catch(error => {
          reject(error);
        });
    });
  }

  public post<T, P>(
    url: string,
    params?: P,
    config?: AxiosRequestConfig
  ): Promise<T> {
    return this.request<T>("post", url, { data: params, ...config });
  }

  public get<T, P>(
    url: string,
    params?: P,
    config?: AxiosRequestConfig
  ): Promise<T> {
    return this.request<T>("get", url, { params, ...config });
  }

  public delete<T, P>(
      url: string,
      params?: P,
      config?: AxiosRequestConfig
  ): Promise<T> {
    return this.request<T>("delete", url, { params, ...config });
  }

    public put<T, P>(
        url: string,
        params?: P,
        config?: AxiosRequestConfig
    ): Promise<T> {
        return this.request<T>("put", url, { data: params, ...config });
    }
}

export const http = new PureHttp();
