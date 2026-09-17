import { createRouter, createWebHistory } from "vue-router";
import type { RouteRecordRaw } from "vue-router";

const routes: RouteRecordRaw[] = [
  {
    path: "/",
    name: "dashboard",
    component: () => import("@/views/Dashboard.vue"),
  },
  {
    path: "/jobs",
    name: "jobs",
    component: () => import("@/views/JobList.vue"),
  },
  {
    path: "/jobs/:id",
    name: "job-detail",
    component: () => import("@/views/JobDetail.vue"),
  },
  {
    path: "/config",
    name: "config",
    component: () => import("@/views/ConfigCenter.vue"),
  },
  {
    path: "/resumes",
    name: "resumes",
    component: () => import("@/views/ResumeManager.vue"),
  },
  {
    path: "/history",
    name: "history",
    component: () => import("@/views/DeliveryHistory.vue"),
  },
  {
    path: "/agents",
    name: "agents",
    component: () => import("@/views/AgentManage.vue"),
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;
