<template>
  <div class="space-y-4">
    <!-- 筛选栏 -->
    <div class="bg-white rounded-lg shadow p-4 flex flex-wrap gap-3 items-center">
      <!-- 查看分类 Tab（任务③：未查看 / 已查看 / 已忽略 / 全部） -->
      <div class="flex items-center gap-1 bg-gray-100 rounded-lg p-1">
        <button
          v-for="t in statusTabs"
          :key="t.value"
          @click="selectTab(t.value)"
          class="px-3 py-1 text-sm rounded-md transition-colors whitespace-nowrap"
          :class="filterStatus === t.value
            ? 'bg-white shadow text-blue-600 font-medium'
            : 'text-gray-500 hover:text-gray-700'"
        >
          {{ t.label }}
        </button>
      </div>
      <select
        v-model="filterDirection"
        class="border rounded px-3 py-1.5 text-sm"
        @change="applyFilter"
      >
        <option value="">全部方向</option>
        <option value="frontend">前端匹配</option>
        <option value="ai">AI匹配</option>
        <option value="both">双匹配</option>
        <option value="none">不匹配</option>
      </select>
      <button
        @click="refresh"
        title="重新拉取列表（列表已做缓存，新采集的数据点这里刷新）"
        class="px-3 py-1.5 border border-gray-300 rounded text-sm hover:bg-gray-50"
      >
        刷新
      </button>
      <div class="ml-auto flex items-center gap-3">
        <div class="text-sm text-gray-500">共 {{ jobsStore.total }} 个岗位</div>
        <button
          @click="exportJobs('csv')"
          :disabled="exporting"
          class="px-3 py-1.5 border border-gray-300 rounded text-sm hover:bg-gray-50 disabled:opacity-50"
        >
          导出 CSV
        </button>
        <button
          @click="exportJobs('md')"
          :disabled="exporting"
          class="px-3 py-1.5 border border-gray-300 rounded text-sm hover:bg-gray-50 disabled:opacity-50"
        >
          导出 Markdown
        </button>
      </div>
    </div>

    <!-- 岗位卡片列表 -->
    <div v-if="jobsStore.loading" class="text-center py-12 text-gray-400">加载中...</div>
    <div
      v-else-if="jobsStore.listError"
      class="text-center py-12 text-red-400 text-sm"
    >
      岗位列表加载失败
      <button @click="fetchData" class="ml-2 px-3 py-1 border border-red-200 rounded hover:bg-red-50">
        重试
      </button>
    </div>
    <div v-else-if="jobsStore.jobs.length === 0" class="text-center py-12 text-gray-400">
      {{ emptyText }}
    </div>
    <div v-else class="space-y-3">
      <div
        v-for="job in jobsStore.jobs"
        :key="job.id"
        class="bg-white rounded-lg shadow p-4 hover:shadow-md transition-shadow cursor-pointer"
        @click="$router.push(`/jobs/${job.id}`)"
        @auxclick="onAuxClick(job, $event)"
      >
        <div class="flex items-start justify-between">
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 mb-1">
              <a
                :href="`/jobs/${job.id}`"
                target="_blank"
                rel="noopener"
                class="font-semibold text-gray-800 hover:text-blue-600 flex-1 min-w-0 truncate"
                title="左键打开详情；中键 / 右键可在此链接新标签打开"
                @click.prevent.stop="$router.push(`/jobs/${job.id}`)"
              >
                {{ job.job_name }}
              </a>
              <span class="text-sm text-red-500 font-medium flex-shrink-0">
                {{ formatSalary(job.salary_min, job.salary_max) }}
              </span>
            </div>
            <div class="text-sm text-gray-500 mb-2 flex flex-wrap items-center gap-x-2 gap-y-0.5">
              <span class="font-medium" :class="company.blacklistHit(job.company_name) ? 'text-red-600 line-through decoration-red-300' : ''">
                {{ job.company_name }}
              </span>
              <!-- 任务④：黑名单命中标 -->
              <span
                v-if="company.blacklistHit(job.company_name)"
                class="px-1.5 py-0.5 text-xs rounded bg-red-100 text-red-600 font-medium"
                title="该公司已被加入黑名单，注意避雷"
              >
                ⚠ 黑名单
              </span>
              <!-- 任务④：同公司多岗位提示（疑似批量刷帖） -->
              <span
                v-if="company.countOf(job.company_name) > 1"
                class="px-1.5 py-0.5 text-xs rounded bg-orange-100 text-orange-600"
                :title="`该公司在库 ${company.countOf(job.company_name)} 个岗位，留意是否为批量刷帖`"
              >
                同公司 ×{{ company.countOf(job.company_name) }}
              </span>
              <span v-if="job.company_size" class="ml-1">{{ job.company_size }}</span>
              <span v-if="job.city">· {{ job.city }}</span>
              <span v-if="job.experience">· {{ job.experience }}</span>
              <span v-if="job.education">· {{ job.education }}</span>
            </div>
            <div v-if="job.jd_text" class="text-sm text-gray-400 line-clamp-2">
              {{ job.jd_text }}
            </div>
          </div>
          <div class="ml-4 flex flex-col items-end gap-2 flex-shrink-0">
            <span
              v-if="job.match_direction"
              class="px-2 py-0.5 text-xs rounded-full"
              :class="matchClass(job.match_direction)"
            >
              {{ matchLabel(job.match_direction) }}
            </span>
            <span class="px-2 py-0.5 text-xs rounded-full" :class="statusClass(job.status)">
              {{ statusLabel(job.status) }}
            </span>
          </div>
        </div>

        <!-- 风险标签 -->
        <div v-if="riskOf(job).state === 'flags'" class="mt-2 flex flex-wrap gap-1.5">
          <span
            v-for="(f, i) in riskOf(job).flags.slice(0, 3)"
            :key="i"
            class="px-2 py-0.5 text-xs rounded-full"
            :class="severityClass(f.severity)"
            :title="f.reason"
          >
            {{ severityLabel(f.severity) }} · {{ f.reason }}
          </span>
          <span
            v-if="riskOf(job).flags.length > 3"
            class="px-2 py-0.5 text-xs rounded-full bg-gray-100 text-gray-600"
          >
            +{{ riskOf(job).flags.length - 3 }} 条
          </span>
        </div>
        <div
          v-else
          class="mt-2 px-2 py-0.5 inline-block text-xs rounded-full"
          :class="riskOf(job).state === 'clean' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'"
        >
          {{ riskOf(job).state === "clean" ? "无明显风险" : "未分析" }}
        </div>

        <!-- 公司信息包（问坑文本） -->
        <div v-if="job.company_profile" class="mt-3">
          <div class="text-xs text-gray-400 mb-1 flex items-center justify-between">
            <span>公司信息包（问坑文本）</span>
            <button
              @click.stop="toggleProfile(job)"
              class="text-blue-600 hover:text-blue-800"
            >
              {{ expandedIds.has(job.id) ? "收起" : "展开完整文本" }}
            </button>
          </div>
          <div
            class="text-xs bg-gray-50 rounded p-2 text-gray-600 whitespace-pre-wrap line-clamp-3"
            :class="{ 'line-clamp-none': expandedIds.has(job.id) }"
          >
            {{ job.company_profile }}
          </div>
        </div>

        <!-- 操作行 -->
        <div class="mt-3 pt-3 border-t border-gray-100 flex items-center gap-2">
          <button
            @click.stop="copyProfile(job)"
            class="px-3 py-1 text-xs rounded border border-blue-200 text-blue-600 hover:bg-blue-50"
          >
            {{ copiedId === job.id ? "已复制 ✓" : "复制问坑文本" }}
          </button>
          <a
            :href="`/jobs/${job.id}`"
            target="_blank"
            rel="noopener"
            @click.stop
            class="px-3 py-1 text-xs rounded border border-gray-200 text-gray-600 hover:bg-gray-50"
          >
            新标签打开
          </a>
          <button
            v-if="job.status !== 'applied'"
            @click.stop="quickStatus(job, 'applied')"
            class="px-3 py-1 text-xs rounded border border-green-200 text-green-600 hover:bg-green-50"
          >
            标记已投递
          </button>
          <button
            v-if="job.status !== 'ignored'"
            @click.stop="quickStatus(job, 'ignored')"
            class="px-3 py-1 text-xs rounded border border-gray-200 text-gray-500 hover:bg-gray-50"
          >
            不感兴趣
          </button>
          <!-- 任务④：公司避雷（加入黑名单后整批岗位带 ⚠ 标签） -->
          <button
            v-if="!company.blacklistHit(job.company_name)"
            @click.stop="addToBlacklist(job)"
            class="px-3 py-1 text-xs rounded border border-red-200 text-red-500 hover:bg-red-50"
          >
            加入黑名单
          </button>
          <button
            v-else
            disabled
            title="该公司已在黑名单"
            class="px-3 py-1 text-xs rounded border border-red-100 text-red-300 cursor-not-allowed"
          >
            已拉黑
          </button>
          <a
            :href="job.source_url"
            target="_blank"
            @click.stop
            class="px-3 py-1 text-xs rounded border border-gray-200 text-gray-500 hover:bg-gray-50 ml-auto"
          >
            打开原帖
          </a>
        </div>
      </div>
    </div>

    <!-- 分页 -->
    <div v-if="jobsStore.total > 20" class="flex justify-center gap-2 pt-4">
      <button
        v-for="p in totalPages"
        :key="p"
        @click="goPage(p)"
        class="px-3 py-1 border rounded text-sm"
        :class="p === page ? 'bg-blue-600 text-white border-blue-600' : 'hover:bg-gray-50'"
      >
        {{ p }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onActivated, onDeactivated, nextTick } from "vue";
import { useJobsStore } from "@/stores/jobs";
import { getJobs, exportJobs as apiExportJobs, updateJobStatus } from "@/api/jobs";
import { createRecord } from "@/api/records";
import { riskState, severityClass, severityLabel, copyText } from "@/utils/risk";
import { formatSalary, matchClass, matchLabel, jobStatusClass as statusClass, jobStatusLabel as statusLabel } from "@/utils/formatters";
import { useToastStore } from "@/stores/toast";
import { useCompanyStore } from "@/stores/company";
import type { Job } from "@/types";

// keep-alive include 匹配（App.vue 只缓存本组件，从详情返回保持状态与滚动）
defineOptions({ name: "JobList" });

const jobsStore = useJobsStore();
const toast = useToastStore();
const company = useCompanyStore();

// ---- 任务③：查看分类 Tab（默认「未查看」= 每天先处理新采集的）----
const statusTabs = [
  { label: "未查看", value: "new" },
  { label: "已查看", value: "viewed" },
  { label: "已忽略", value: "ignored" },
  { label: "全部", value: "" },
];
const filterStatus = ref("new");

// ---- 任务①：返回列表时恢复滚动位置（滚动容器在 AppLayout <main id="page-scroll">）----
let savedScrollTop = 0;
function scrollEl(): HTMLElement | null {
  return document.getElementById("page-scroll");
}
onDeactivated(() => {
  savedScrollTop = scrollEl()?.scrollTop || 0;
});
onActivated(async () => {
  reconcileLocal();
  company.loadMeta(); // 黑名单/公司计数可能被详情页或配置中心改动，返回时刷新
  await nextTick();
  const el = scrollEl();
  if (el && savedScrollTop > 0) el.scrollTop = savedScrollTop;
});

// ---- 任务③：从详情页操作返回后，把不再匹配当前 Tab 的岗位从本地列表移除 ----
function reconcileLocal() {
  if (filterStatus.value === "") return; // 「全部」不过滤
  const before = jobsStore.jobs.length;
  jobsStore.jobs = jobsStore.jobs.filter((j) => statusInGroup(j.status, filterStatus.value));
  const removed = before - jobsStore.jobs.length;
  if (removed > 0) jobsStore.total = Math.max(0, jobsStore.total - removed);
  // 整页都被移走（如当前页岗位全部在详情里被转状态）→ 回退上一页并重新拉取
  if (removed > 0 && jobsStore.jobs.length === 0 && page.value > 1) {
    page.value -= 1;
    fetchData();
  }
}

/** status 是否属于某个 Tab 分组（''=全部） */
function statusInGroup(status: string, group: string): boolean {
  if (!group) return true;
  if (group === "new") return status === "new";
  if (group === "viewed") return status === "viewed" || status === "applied";
  if (group === "ignored") return status === "ignored";
  return true;
}
const filterDirection = ref("");
const page = ref(1);
const exporting = ref(false);
const copiedId = ref<number | null>(null);
const expandedIds = ref<Set<number>>(new Set());

const totalPages = computed(() => Math.ceil(jobsStore.total / 20));

/** 当前 Tab 的空态文案 */
const emptyText = computed(() => {
  const label = statusTabs.find((t) => t.value === filterStatus.value)?.label || "全部";
  return label === "全部" ? "暂无岗位数据" : `暂无${label}的岗位`;
});

onMounted(() => {
  fetchData();
  company.loadMeta();
});

function fetchData() {
  const params: Record<string, unknown> = { page: page.value };
  const st = tabStatusParam();
  if (st) params.status = st;
  if (filterDirection.value) params.match_direction = filterDirection.value;
  jobsStore.fetchJobs(params);
}

/** Tab 值 → 后端 status 参数（「已查看」= viewed,applied 组合） */
function tabStatusParam(): string | undefined {
  if (!filterStatus.value) return undefined;
  if (filterStatus.value === "viewed") return "viewed,applied";
  return filterStatus.value;
}

function applyFilter() {
  page.value = 1;
  fetchData();
}

/** 切换查看分类 Tab（未查看/已查看/已忽略/全部） */
function selectTab(value: string) {
  if (filterStatus.value === value) return;
  filterStatus.value = value;
  applyFilter();
}

/** 手动刷新（keep-alive 缓存下列表不自动重拉，新采集的数据点这里） */
function refresh() {
  page.value = 1;
  fetchData();
  company.loadMeta();
}

/** 任务④：加入公司黑名单（持久化到 config.filter_conditions.blacklist） */
async function addToBlacklist(job: Job) {
  const name = (job.company_name || "").trim();
  if (!name) return;
  if (!confirm(`把「${name}」加入黑名单？\n\n该公司的所有岗位将带「⚠ 黑名单」标签提醒你避雷。\n（可随时在配置中心 → 公司黑名单 移除）`)) return;
  const ok = await company.addBlacklist(name);
  if (ok) {
    toast.success(`已将「${name}」加入黑名单`);
  } else {
    toast.error("加入黑名单失败，请重试");
  }
}

function goPage(p: number) {
  page.value = p;
  fetchData();
}

function riskOf(job: Job) {
  return riskState(job.risk_flags);
}

function toggleProfile(job: Job) {
  const next = new Set(expandedIds.value);
  if (next.has(job.id)) next.delete(job.id);
  else next.add(job.id);
  expandedIds.value = next;
}

/** 中键点击卡片 → 新标签打开详情（auxclick，不影响左键 click 导航） */
function onAuxClick(job: Job, e: MouseEvent) {
  if (e.button === 1) {
    e.preventDefault();
    window.open(`/jobs/${job.id}`, "_blank", "noopener");
  }
}

async function copyProfile(job: Job) {
  if (!job.company_profile) return;
  const ok = await copyText(job.company_profile);
  if (ok) {
    copiedId.value = job.id;
    setTimeout(() => {
      if (copiedId.value === job.id) copiedId.value = null;
    }, 2000);
  } else {
    toast.error("复制失败，请手动选择文本复制");
  }
}

async function quickStatus(job: Job, status: string) {
  try {
    if (status === "applied") {
      // 投递 → 写投递记录（幂等去重，返回已有记录也算成功）
      await createRecord({ job_id: job.id });
    } else {
      await updateJobStatus(job.id, status);
    }
    // 任务③：新状态若不再属于当前 Tab → 即时从列表移除（忽略/投递后"消失"）
    if (!statusInGroup(status, filterStatus.value)) {
      jobsStore.jobs = jobsStore.jobs.filter((x) => x.id !== job.id);
      jobsStore.total = Math.max(0, jobsStore.total - 1);
    } else {
      job.status = status;
    }
    if (status === "applied") {
      toast.success("已记录投递");
    } else if (status === "ignored") {
      toast.success("已忽略，从当前列表移除");
    }
  } catch (e: any) {
    toast.error(e?.response?.data?.error || "操作失败，请重试");
  }
}

async function exportJobs(format: "csv" | "md") {
  exporting.value = true;
  try {
    const params: Record<string, unknown> = {};
    const st = tabStatusParam();
    if (st) params.status = st;
    if (filterDirection.value) params.match_direction = filterDirection.value;
    const res = await apiExportJobs(format, params);
    const blob = res.data as Blob;
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    const now = new Date();
    const pad = (n: number) => String(n).padStart(2, "0");
    a.href = url;
    a.download = `jobs_${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}_${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}.${format}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  } catch (e: any) {
    console.error("[导出失败]", e);
    toast.error("导出失败，请重试");
  } finally {
    exporting.value = false;
  }
}

</script>

<style scoped>
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.line-clamp-3 {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.line-clamp-none {
  display: block;
  -webkit-line-clamp: unset;
}
</style>
