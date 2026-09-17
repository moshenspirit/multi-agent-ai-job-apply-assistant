<template>
  <div class="flex h-screen bg-gray-100">
    <!-- 侧边栏 -->
    <aside
      :class="[
        'bg-slate-800 text-white transition-all duration-300 flex flex-col',
        store.sideMenuCollapsed ? 'w-16' : 'w-56',
      ]"
    >
      <div class="flex items-center h-16 px-4 border-b border-slate-700">
        <span v-if="!store.sideMenuCollapsed" class="text-lg font-bold whitespace-nowrap">
          岗位匹配助手
        </span>
        <button
          @click="store.toggleMenu()"
          class="ml-auto p-1 rounded hover:bg-slate-700 text-slate-300"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>
      </div>
      <nav class="flex-1 py-4 space-y-1">
        <router-link
          v-for="item in menuItems"
          :key="item.path"
          :to="item.path"
          class="flex items-center px-4 py-2.5 text-sm transition-colors hover:bg-slate-700"
          :class="$route.path === item.path ? 'bg-slate-700 text-white' : 'text-slate-300'"
        >
          <span class="w-5 h-5 mr-3 flex-shrink-0" v-html="item.icon"></span>
          <span v-if="!store.sideMenuCollapsed" class="whitespace-nowrap">{{ item.label }}</span>
        </router-link>
      </nav>
    </aside>

    <!-- 主内容区 -->
    <div class="flex-1 flex flex-col overflow-hidden">
      <header class="bg-white shadow-sm h-16 flex items-center px-6 border-b">
        <h1 class="text-lg font-medium text-gray-800">{{ currentTitle }}</h1>
      </header>
      <main id="page-scroll" class="flex-1 overflow-auto p-6">
        <slot />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";
import { useAppStore } from "@/stores/app";

const store = useAppStore();
const route = useRoute();

const menuItems = [
  {
    path: "/",
    label: "仪表盘",
    icon: '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"/></svg>',
  },
  {
    path: "/jobs",
    label: "岗位列表",
    icon: '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/></svg>',
  },
  {
    path: "/config",
    label: "配置中心",
    icon: '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/></svg>',
  },
  {
    path: "/resumes",
    label: "简历管理",
    icon: '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>',
  },
  {
    path: "/history",
    label: "投递历史",
    icon: '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>',
  },
  {
    path: "/agents",
    label: "Agent 管理",
    icon: '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/></svg>',
  },
];

const titles: Record<string, string> = {
  "/": "仪表盘",
  "/jobs": "岗位列表",
  "/config": "配置中心",
  "/resumes": "简历管理",
  "/history": "投递历史",
  "/agents": "Agent 管理",
};

const currentTitle = computed(() => {
  // 对 /jobs/:id 特殊处理
  if (route.path.startsWith("/jobs/") && route.params.id) {
    return "岗位详情";
  }
  return titles[route.path] || "岗位匹配助手";
});
</script>
