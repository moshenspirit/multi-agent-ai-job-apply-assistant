import axios from "axios";

const client = axios.create({
  baseURL: "/api",
  timeout: 30000,
  headers: {
    "Content-Type": "application/json",
  },
});

// 响应拦截器：统一错误处理
client.interceptors.response.use(
  (res) => res,
  (error) => {
    const message = error.response?.data?.error || error.message || "请求失败";
    console.error("[API Error]", message);
    return Promise.reject(error);
  }
);

export default client;
