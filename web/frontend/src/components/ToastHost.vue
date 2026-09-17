<template>
  <div class="fixed top-4 right-4 z-50 flex flex-col items-end gap-2 pointer-events-none">
    <transition-group name="toast">
      <div
        v-for="t in store.toasts"
        :key="t.id"
        class="pointer-events-auto flex items-center gap-2 px-4 py-2.5 rounded-lg shadow-lg text-sm text-white max-w-sm toast-item"
        :class="bgClass(t.type)"
      >
        <span class="flex-shrink-0">{{ icon(t.type) }}</span>
        <span class="break-all">{{ t.message }}</span>
        <button
          @click="store.remove(t.id)"
          class="ml-1 flex-shrink-0 opacity-70 hover:opacity-100 text-xs"
          aria-label="关闭"
        >
          ✕
        </button>
      </div>
    </transition-group>
  </div>
</template>

<script setup lang="ts">
import { useToastStore, type ToastType } from "@/stores/toast";

const store = useToastStore();

function bgClass(type: ToastType): string {
  return {
    success: "bg-green-600",
    error: "bg-red-600",
    info: "bg-blue-600",
  }[type];
}

function icon(type: ToastType): string {
  return { success: "✓", error: "✕", info: "ℹ" }[type];
}
</script>

<style scoped>
.toast-item {
  animation: toast-in 0.2s ease-out;
}
.toast-leave-active {
  transition: opacity 0.2s ease;
}
.toast-leave-to {
  opacity: 0;
}
@keyframes toast-in {
  from {
    opacity: 0;
    transform: translateX(16px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}
</style>
