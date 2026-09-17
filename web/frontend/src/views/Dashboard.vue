<template>
  <div class="space-y-6">
    <!-- 统计卡片 -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
      <div class="bg-white rounded-lg shadow p-4">
        <div class="text-sm text-gray-500">总岗位数</div>
        <div class="text-2xl font-bold text-gray-800">{{ stats.total }}</div>
      </div>
      <div class="bg-white rounded-lg shadow p-4">
        <div class="text-sm text-gray-500">新采集</div>
        <div class="text-2xl font-bold text-blue-600">{{ stats.new }}</div>
      </div>
      <div class="bg-white rounded-lg shadow p-4">
        <div class="text-sm text-gray-500">已投递</div>
        <div class="text-2xl font-bold text-green-600">{{ stats.applied }}</div>
      </div>
      <div class="bg-white rounded-lg shadow p-4">
        <div class="text-sm text-gray-500">前端匹配</div>
        <div class="text-2xl font-bold text-indigo-600">{{ stats.frontend_match }}</div>
      </div>
      <div class="bg-white rounded-lg shadow p-4">
        <div class="text-sm text-gray-500">AI 匹配</div>
        <div class="text-2xl font-bold text-purple-600">{{ stats.ai_match }}</div>
      </div>
    </div>
    <div
      v-if="jobsStore.statsError"
      class="bg-red-50 text-red-500 text-sm px-4 py-2 rounded-lg flex items-center gap-3"
    >
      统计数据加载失败
      <button
        @click="jobsStore.fetchStats()"
        class="px-3 py-1 border border-red-200 rounded hover:bg-red-100"
      >
        重试
      </button>
    </div>

    <!-- 最近岗位 -->
    <div class="bg-white rounded-lg shadow p-6">
      <h2 class="text-lg font-semibold text-gray-800 mb-4">最近岗位</h2>
      <div v-if="jobsStore.loading" class="text-gray-400 text-sm">加载中...</div>
      <div v-else-if="jobsStore.listError" class="text-gray-400 text-sm">
        岗位加载失败
        <button
          @click="reload"
          class="ml-2 px-3 py-1 border border-gray-200 rounded hover:bg-gray-50 text-xs"
        >
          重试
        </button>
      </div>
      <div v-else-if="jobsStore.jobs.length === 0" class="text-gray-400 text-sm">
        暂无数据，请先配置搜索关键词并开始采集
      </div>
      <div v-else class="space-y-3">
        <div
          v-for="job in jobsStore.jobs.slice(0, 5)"
          :key="job.id"
          class="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 cursor-pointer"
          @click="$router.push(`/jobs/${job.id}`)"
        >
          <div class="flex-1 min-w-0">
            <div class="font-medium text-gray-800 truncate">{{ job.job_name }}</div>
            <div class="text-sm text-gray-500">{{ job.company_name }}</div>
          </div>
          <div class="flex items-center gap-3 ml-4">
            <span class="text-sm text-red-500 font-medium">
              {{ formatSalary(job.salary_min, job.salary_max) }}
            </span>
            <span
              v-if="job.match_direction"
              class="px-2 py-0.5 text-xs rounded-full"
              :class="matchClass(job.match_direction)"
            >
              {{ matchLabel(job.match_direction) }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from "vue";
import { useJobsStore } from "@/stores/jobs";
import { formatSalary, matchClass, matchLabel } from "@/utils/formatters";

const jobsStore = useJobsStore();
const stats = jobsStore.stats;

onMounted(() => {
  jobsStore.fetchJobs({ per_page: 5 });
  jobsStore.fetchStats();
});

function reload() {
  jobsStore.fetchJobs({ per_page: 5 });
  jobsStore.fetchStats();
}
</script>
