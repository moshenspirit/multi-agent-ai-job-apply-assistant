<template>
  <div class="space-y-4">
    <div class="bg-white rounded-lg shadow p-6">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-lg font-semibold text-gray-800">投递历史</h2>
        <div class="text-sm text-gray-400">共 {{ records.length }} 条</div>
      </div>
      <div v-if="loading" class="text-gray-400 text-sm">加载中...</div>
      <div v-else-if="loadError" class="text-gray-400 text-sm py-8 text-center">
        投递记录加载失败
        <button @click="fetchRecords" class="ml-2 px-3 py-1 border border-gray-200 rounded hover:bg-gray-50">
          重试
        </button>
      </div>
      <div v-else-if="records.length === 0" class="text-gray-400 text-sm py-8 text-center">
        暂无投递记录。在岗位列表或详情页点「标记已投递」即可记录。
      </div>
      <div v-else>
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b text-left text-gray-500">
              <th class="pb-3 font-medium">岗位</th>
              <th class="pb-3 font-medium">公司</th>
              <th class="pb-3 font-medium">薪资</th>
              <th class="pb-3 font-medium">进展</th>
              <th class="pb-3 font-medium">投递时间</th>
              <th class="pb-3 font-medium">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in records" :key="r.id" class="border-b last:border-0">
              <td class="py-3 text-gray-800 max-w-[240px] truncate">
                <router-link :to="`/jobs/${r.job_id}`" class="text-blue-600 hover:text-blue-800">
                  {{ r.job_name || `岗位 #${r.job_id}` }}
                </router-link>
              </td>
              <td class="py-3 text-gray-600">{{ r.company_name || "-" }}</td>
              <td class="py-3 text-red-500 font-medium">{{ formatSalary(r.salary_min, r.salary_max) }}</td>
              <td class="py-3">
                <div class="flex items-center gap-2">
                  <span class="px-2 py-0.5 text-xs rounded-full" :class="statusClass(r.status)">
                    {{ statusLabel(r.status) }}
                  </span>
                  <select
                    :value="r.status"
                    @change="changeStatus(r, ($event.target as HTMLSelectElement).value)"
                    class="border rounded px-1.5 py-0.5 text-xs text-gray-600 focus:outline-none"
                  >
                    <option value="applied">已投递</option>
                    <option value="interviewed">面试中</option>
                    <option value="offer">已录用</option>
                    <option value="rejected">未通过</option>
                  </select>
                </div>
              </td>
              <td class="py-3 text-gray-500">{{ formatDate(r.created_at) }}</td>
              <td class="py-3">
                <button
                  @click="remove(r)"
                  class="px-2 py-0.5 text-xs rounded border border-gray-200 text-gray-400 hover:text-red-600 hover:border-red-200"
                >
                  删除
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { getRecords, updateRecordStatus, deleteRecord } from "@/api/records";
import { formatSalary, formatDate, progressClass as statusClass, progressLabel as statusLabel } from "@/utils/formatters";
import { useToastStore } from "@/stores/toast";
import type { DeliveryRecord } from "@/types";

const records = ref<DeliveryRecord[]>([]);
const loading = ref(false);
const loadError = ref(false);
const toast = useToastStore();

onMounted(fetchRecords);

async function fetchRecords() {
  loading.value = true;
  loadError.value = false;
  try {
    const res = await getRecords();
    records.value = res.data;
  } catch {
    loadError.value = true;
  } finally {
    loading.value = false;
  }
}

async function changeStatus(r: DeliveryRecord, status: string) {
  try {
    const res = await updateRecordStatus(r.id, status);
    r.status = res.data.status;
    toast.success("进展已更新");
  } catch (e: any) {
    toast.error(e?.response?.data?.error || "更新失败，请重试");
  }
}

async function remove(r: DeliveryRecord) {
  if (!confirm(`删除「${r.job_name || r.job_id}」的投递记录？`)) return;
  try {
    await deleteRecord(r.id);
    records.value = records.value.filter((x) => x.id !== r.id);
    toast.success("已删除投递记录");
  } catch (e: any) {
    toast.error(e?.response?.data?.error || "删除失败，请重试");
  }
}
</script>
