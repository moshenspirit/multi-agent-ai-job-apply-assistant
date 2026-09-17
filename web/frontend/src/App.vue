<template>
  <div id="app" class="min-h-screen flex flex-col">
    <AppLayout>
      <!-- keep-alive 缓存 JobList：从详情返回时保留筛选/分页/滚动位置（任务① 2026-09-03） -->
      <router-view v-slot="{ Component }">
        <keep-alive include="JobList">
          <component :is="Component" />
        </keep-alive>
      </router-view>
    </AppLayout>
    <ToastHost />
  </div>
</template>

<script setup lang="ts">
import AppLayout from "@/components/AppLayout.vue";
import ToastHost from "@/components/ToastHost.vue";
</script>
