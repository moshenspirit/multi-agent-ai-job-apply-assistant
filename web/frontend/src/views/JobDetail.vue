<template>
  <div v-if="job" class="space-y-6">
    <!-- 返回 -->
    <button @click="$router.back()" class="text-blue-600 hover:text-blue-800 text-sm flex items-center gap-1">
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
      </svg>
      返回列表
    </button>

    <!-- 岗位头 -->
    <div class="bg-white rounded-lg shadow p-6">
      <div class="flex items-start justify-between">
        <div>
          <h1 class="text-2xl font-bold text-gray-800">{{ job.job_name }}</h1>
          <div class="mt-1 text-lg text-gray-500 flex flex-wrap items-center gap-2">
            <span :class="blacklistHit ? 'text-red-600 line-through decoration-red-300' : ''">
              {{ job.company_name }}
            </span>
            <span
              v-if="blacklistHit"
              class="px-2 py-0.5 text-xs rounded bg-red-100 text-red-600 font-medium"
              title="该公司已被加入黑名单"
            >
              ⚠ 黑名单（{{ blacklistHit }}）
            </span>
            <span
              v-if="dupCount > 1"
              class="px-2 py-0.5 text-xs rounded bg-orange-100 text-orange-600"
              title="该公司在库多个岗位，留意是否为批量刷帖"
            >
              同公司 ×{{ dupCount }}
            </span>
          </div>
          <div class="mt-2 flex flex-wrap gap-2 text-sm text-gray-500">
            <span v-if="job.city" class="bg-gray-100 px-2 py-0.5 rounded">{{ job.city }}</span>
            <span v-if="job.district" class="bg-gray-100 px-2 py-0.5 rounded">{{ job.district }}</span>
            <span v-if="job.experience" class="bg-gray-100 px-2 py-0.5 rounded">{{ job.experience }}</span>
            <span v-if="job.education" class="bg-gray-100 px-2 py-0.5 rounded">{{ job.education }}</span>
            <span class="bg-red-50 text-red-600 px-2 py-0.5 rounded font-medium">
              {{ formatSalary(job.salary_min, job.salary_max) }}
            </span>
          </div>
        </div>
        <div class="flex flex-col items-end gap-2">
          <span
            v-if="job.match_direction"
            class="px-3 py-1 text-sm rounded-full font-medium"
            :class="matchClass(job.match_direction)"
          >
            {{ matchLabel(job.match_direction) }}
          </span>
          <a
            :href="job.source_url"
            target="_blank"
            class="px-4 py-1.5 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700"
          >
            打开原始链接
          </a>
        </div>
      </div>
    </div>

    <!-- 公司信息 + 匹配详情 -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- 公司信息 -->
      <div class="bg-white rounded-lg shadow p-6">
        <h2 class="text-lg font-semibold text-gray-800 mb-4">公司信息</h2>
        <div class="space-y-3 text-sm">
          <div v-if="job.company_size">
            <span class="text-gray-400">公司规模：</span>
            <span class="text-gray-700">{{ job.company_size }}</span>
          </div>
          <div v-if="job.company_industry">
            <span class="text-gray-400">所属行业：</span>
            <span class="text-gray-700">{{ job.company_industry }}</span>
          </div>
          <div v-if="job.company_finance">
            <span class="text-gray-400">融资阶段：</span>
            <span class="text-gray-700">{{ job.company_finance }}</span>
          </div>
          <div v-if="job.boss_active">
            <span class="text-gray-400">Boss 活跃度：</span>
            <span class="text-gray-700">{{ job.boss_active }}</span>
          </div>
        </div>
      </div>

      <!-- 匹配详情 -->
      <div class="lg:col-span-2 bg-white rounded-lg shadow p-6">
        <h2 class="text-lg font-semibold text-gray-800 mb-4">AI 匹配分析</h2>
        <div v-if="!job.match_reason" class="text-gray-400 text-sm">暂未匹配</div>
        <div v-else>
          <div class="flex gap-6 mb-4">
            <div class="text-center">
              <div class="text-3xl font-bold" :class="scoreColor(job.match_score_frontend)">
                {{ job.match_score_frontend ?? "-" }}
              </div>
              <div class="text-xs text-gray-400 mt-1">前端匹配度</div>
            </div>
            <div class="text-center">
              <div class="text-3xl font-bold" :class="scoreColor(job.match_score_ai)">
                {{ job.match_score_ai ?? "-" }}
              </div>
              <div class="text-xs text-gray-400 mt-1">AI 匹配度</div>
            </div>
          </div>
          <div class="p-4 bg-gray-50 rounded-lg text-sm text-gray-700 whitespace-pre-wrap">
            {{ job.match_reason }}
          </div>
        </div>
      </div>
    </div>

    <!-- 公司避坑（需求 6：信息包 + 主动分析参考） -->
    <div class="bg-white rounded-lg shadow p-6">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-lg font-semibold text-gray-800">公司避坑</h2>
        <button
          v-if="job.company_profile"
          @click="copyProfile"
          class="px-3 py-1.5 text-sm rounded-lg border border-blue-200 text-blue-600 hover:bg-blue-50"
        >
          {{ copied ? "已复制 ✓" : "复制问坑文本" }}
        </button>
      </div>

      <!-- 风险标签（主动形态：DeepSeek 分析，只做参考） -->
      <div v-if="risk.state === 'flags'" class="mb-4 space-y-2">
        <div
          v-for="(f, i) in risk.flags"
          :key="i"
          class="flex items-start gap-2 p-3 rounded-lg"
          :class="severityClass(f.severity)"
        >
          <span class="flex-shrink-0 text-xs font-medium">
            {{ severityLabel(f.severity) }}
          </span>
          <span class="text-sm">{{ f.reason }}</span>
        </div>
        <p class="text-xs text-gray-400 mt-1">以上为 AI 提示信号，仅供参考，以你的判断为准。</p>
      </div>
      <div v-else-if="risk.state === 'clean'" class="mb-4">
        <span class="px-2 py-0.5 text-xs rounded-full bg-green-100 text-green-700">无明显风险</span>
        <p class="text-xs text-gray-400 mt-2">AI 已分析过此岗位，未发现明显异常信号。</p>
      </div>
      <div v-else class="mb-4">
        <span class="px-2 py-0.5 text-xs rounded-full bg-gray-100 text-gray-500">未分析</span>
        <p class="text-xs text-gray-400 mt-2">
          尚未做主动风险分析。可复制下方问坑文本，贴给 DeepSeek 自行判读。
        </p>
      </div>

      <!-- 公司信息包（被动形态：复制 → 贴给 DeepSeek 问坑） -->
      <div v-if="job.company_profile">
        <div class="text-xs text-gray-400 mb-1">公司信息包（问坑文本）</div>
        <pre
          class="p-4 bg-gray-50 rounded-lg text-sm text-gray-700 whitespace-pre-wrap leading-relaxed font-sans"
        >{{ job.company_profile }}</pre>
      </div>
      <div v-else class="text-sm text-gray-400">暂无公司信息包</div>
    </div>

    <!-- JD -->
    <div class="bg-white rounded-lg shadow p-6">
      <h2 class="text-lg font-semibold text-gray-800 mb-4">职位描述</h2>
      <div v-if="!job.jd_text" class="text-gray-400 text-sm">暂无职位描述</div>
      <div v-else class="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">
        {{ job.jd_text }}
      </div>
    </div>

    <!-- 操作 -->
    <div class="bg-white rounded-lg shadow p-6">
      <!-- 已投递：显示进展 + 流转 -->
      <div v-if="deliveryRecord" class="flex flex-wrap items-center gap-3">
        <span class="px-3 py-1 text-sm rounded-full" :class="progressClass(deliveryRecord.status)">
          {{ progressLabel(deliveryRecord.status) }}
        </span>
        <span class="text-sm text-gray-400">已投递于 {{ formatDate(deliveryRecord.created_at) }}</span>
        <button
          v-if="deliveryRecord.status !== 'interviewed'"
          @click="updateProgress('interviewed')"
          class="px-4 py-1.5 border border-yellow-300 text-yellow-700 rounded-lg hover:bg-yellow-50 text-sm"
        >
          进入面试
        </button>
        <button
          v-if="deliveryRecord.status !== 'offer'"
          @click="updateProgress('offer')"
          class="px-4 py-1.5 bg-green-600 text-white rounded-lg hover:bg-green-700 text-sm"
        >
          已录用
        </button>
        <button
          v-if="deliveryRecord.status !== 'rejected'"
          @click="updateProgress('rejected')"
          class="px-4 py-1.5 border border-red-200 text-red-600 rounded-lg hover:bg-red-50 text-sm"
        >
          未通过
        </button>
      </div>
      <!-- 未投递：操作 -->
      <div v-else class="flex items-center gap-3">
        <button
          @click="markApplied"
          class="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 text-sm font-medium"
        >
          标记已投递
        </button>
        <button
          @click="updateStatus('viewed')"
          class="px-6 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 text-sm"
        >
          标记已查看
        </button>
        <button
          @click="updateStatus('ignored')"
          class="px-6 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 text-sm"
        >
          不感兴趣
        </button>
      </div>

      <!-- 任务④：公司避雷行 -->
      <div class="mt-4 pt-3 border-t border-gray-100 flex items-center gap-3">
        <span class="text-xs text-gray-400">公司避雷</span>
        <button
          v-if="!blacklistHit"
          @click="addBlacklist"
          class="px-3 py-1 text-xs rounded-lg border border-red-200 text-red-600 hover:bg-red-50"
        >
          ⚠ 加入黑名单
        </button>
        <span v-else class="text-xs text-red-500">
          该公司已在黑名单，后续岗位会带 ⚠ 标签提醒
        </span>
      </div>
    </div>
  </div>
  <div v-else-if="error" class="text-center py-12 text-gray-400">{{ error }}</div>
  <div v-else class="text-center py-12 text-gray-400">加载中...</div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRoute } from "vue-router";
import { getJob, updateJobStatus } from "@/api/jobs";
import { getRecords, createRecord, updateRecordStatus } from "@/api/records";
import { riskState, severityClass, severityLabel, copyText } from "@/utils/risk";
import { formatSalary, formatDate, matchClass, matchLabel, scoreColor, progressClass, progressLabel } from "@/utils/formatters";
import { useToastStore } from "@/stores/toast";
import { useJobsStore } from "@/stores/jobs";
import { useCompanyStore } from "@/stores/company";
import type { Job, DeliveryRecord } from "@/types";

const route = useRoute();
const toast = useToastStore();
const jobsStore = useJobsStore();
const company = useCompanyStore();
const job = ref<Job | null>(null);
const error = ref("");
const copied = ref(false);
const deliveryRecord = ref<DeliveryRecord | null>(null);

/** 任务④：黑名单命中词（无则 null）与同公司岗位数 */
const blacklistHit = computed(() => (job.value ? company.blacklistHit(job.value.company_name) : null));
const dupCount = computed(() => (job.value ? company.countOf(job.value.company_name) : 0));

const risk = computed(() => (job.value ? riskState(job.value.risk_flags) : { state: "unanalyzed" as const, flags: [] }));

onMounted(async () => {
  const id = Number(route.params.id);
  try {
    const res = await getJob(id);
    job.value = res.data;
    // 查该岗位的投递记录
    const rec = await getRecords({ job_id: id });
    deliveryRecord.value = rec.data.length ? rec.data[0] : null;
    company.loadMeta();
    // 任务③：打开详情自动把 new → viewed（配合列表「未查看/已查看」分类）；
    // 静默失败不影响浏览，且同步回列表缓存（keep-alive）
    if (job.value.status === "new") {
      try {
        await updateJobStatus(id, "viewed");
        job.value.status = "viewed";
        jobsStore.setLocalStatus(id, "viewed");
      } catch {
        // 自动标记失败不打扰浏览
      }
    }
  } catch {
    error.value = "加载失败";
  }
});

async function copyProfile() {
  if (!job.value?.company_profile) return;
  const ok = await copyText(job.value.company_profile);
  if (ok) {
    copied.value = true;
    setTimeout(() => (copied.value = false), 2000);
  }
}

async function markApplied() {
  if (!job.value) return;
  try {
    const res = await createRecord({ job_id: job.value.id });
    deliveryRecord.value = res.data;
    job.value.status = "applied";
    jobsStore.setLocalStatus(job.value.id, "applied"); // 同步列表缓存
    toast.success("已记录投递");
  } catch (e: any) {
    toast.error(e?.response?.data?.error || "操作失败，请重试");
  }
}

const PROGRESS_TEXT: Record<string, string> = {
  interviewed: "已进入面试",
  offer: "已标记录用",
  rejected: "已标记未通过",
};

async function updateProgress(status: string) {
  if (!deliveryRecord.value) return;
  try {
    const res = await updateRecordStatus(deliveryRecord.value.id, status);
    deliveryRecord.value = res.data;
    toast.success(PROGRESS_TEXT[status] || "状态已更新");
  } catch (e: any) {
    toast.error(e?.response?.data?.error || "操作失败，请重试");
  }
}

const STATUS_TEXT: Record<string, string> = {
  viewed: "已标记查看",
  ignored: "已标记不感兴趣",
};

async function updateStatus(status: string) {
  if (!job.value) return;
  try {
    await updateJobStatus(job.value.id, status);
    job.value.status = status;
    jobsStore.setLocalStatus(job.value.id, status); // 同步列表缓存
    toast.success(STATUS_TEXT[status] || "状态已更新");
  } catch (e: any) {
    toast.error(e?.response?.data?.error || "操作失败，请重试");
  }
}

/** 任务④：加入公司黑名单 */
async function addBlacklist() {
  if (!job.value) return;
  const name = (job.value.company_name || "").trim();
  if (!name) return;
  if (!confirm(`把「${name}」加入黑名单？\n\n该公司的所有岗位将带「⚠ 黑名单」标签提醒你避雷。`)) return;
  const ok = await company.addBlacklist(name);
  if (ok) {
    toast.success(`已将「${name}」加入黑名单`);
  } else {
    toast.error("加入黑名单失败，请重试");
  }
}

</script>
