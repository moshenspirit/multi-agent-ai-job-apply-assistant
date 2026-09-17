import { defineStore } from "pinia";
import { ref } from "vue";

export type ToastType = "success" | "error" | "info";

export interface ToastItem {
  id: number;
  type: ToastType;
  message: string;
}

let seq = 0;

export const useToastStore = defineStore("toast", () => {
  const toasts = ref<ToastItem[]>([]);

  function remove(id: number) {
    toasts.value = toasts.value.filter((t) => t.id !== id);
  }

  function push(type: ToastType, message: string, duration = 3000) {
    const id = ++seq;
    toasts.value.push({ id, type, message });
    if (duration > 0) {
      setTimeout(() => remove(id), duration);
    }
    return id;
  }

  function success(message: string, duration?: number) {
    return push("success", message, duration);
  }

  function error(message: string, duration?: number) {
    return push("error", message, duration);
  }

  function info(message: string, duration?: number) {
    return push("info", message, duration);
  }

  return { toasts, remove, push, success, error, info };
});
