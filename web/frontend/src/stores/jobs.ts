import { defineStore } from "pinia";
import { ref } from "vue";
import type { Job } from "@/types";
import { getJobs, getJobStats } from "@/api/jobs";

export const useJobsStore = defineStore("jobs", () => {
  const jobs = ref<Job[]>([]);
  const total = ref(0);
  const loading = ref(false);
  // 加载失败标记（区分"失败"与"空数据"，2026-09-03 加）
  const listError = ref(false);
  const statsError = ref(false);
  const stats = ref({
    total: 0,
    new: 0,
    applied: 0,
    frontend_match: 0,
    ai_match: 0,
  });

  async function fetchJobs(params?: Record<string, unknown>) {
    loading.value = true;
    listError.value = false;
    try {
      const res = await getJobs(params);
      jobs.value = res.data.data;
      total.value = res.data.total;
    } catch {
      listError.value = true;
    } finally {
      loading.value = false;
    }
  }

  async function fetchStats() {
    statsError.value = false;
    try {
      const res = await getJobStats();
      stats.value = res.data;
    } catch {
      statsError.value = true;
    }
  }

  /** 同步本地岗位状态（详情页操作后回写列表缓存，2026-09-03） */
  function setLocalStatus(id: number, status: string) {
    const j = jobs.value.find((x) => x.id === id);
    if (j) j.status = status;
  }

  return { jobs, total, loading, listError, statsError, stats, fetchJobs, fetchStats, setLocalStatus };
});
