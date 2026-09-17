<template>
  <div class="space-y-4">
    <div class="bg-white rounded-lg shadow p-4 text-sm text-gray-500">
      管理采集 / 匹配 / 避坑三个 Agent：配置参数、触发运行、查看最近结果。
      运行在后台执行，采集可能需要 30-60 分钟（需手机热点 + 专用 Chrome）。
    </div>

    <div v-if="loading" class="text-center py-12 text-gray-400">加载中...</div>
    <div
      v-else-if="loadError"
      class="text-center py-12 text-red-400 text-sm"
    >
      Agent 信息加载失败
      <button @click="fetchAgents" class="ml-2 px-3 py-1 border border-red-200 rounded hover:bg-red-50">
        重试
      </button>
    </div>
    <div v-else-if="agents.length === 0" class="text-center py-12 text-gray-400">
      暂无 Agent
    </div>
    <div v-else class="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <div
        v-for="agent in agents"
        :key="agent.name"
        class="bg-white rounded-lg shadow p-5 flex flex-col"
      >
        <!-- 卡头 -->
        <div class="flex items-center justify-between mb-1">
          <h2 class="text-base font-semibold text-gray-800">{{ agent.label }}</h2>
          <span class="flex items-center gap-1.5 text-xs" :class="badgeClass(agent)">
            <span
              v-if="agent.running"
              class="w-2 h-2 rounded-full bg-blue-500 animate-pulse"
            ></span>
            <span
              v-else
              class="w-2 h-2 rounded-full"
              :class="badgeDot(agent)"
            ></span>
            {{ badgeText(agent) }}
          </span>
        </div>
        <p class="text-xs text-gray-400 mb-4">{{ agent.description }}</p>

        <!-- 配置表单（fields 驱动） -->
        <div v-if="agent.fields.length" class="space-y-3 mb-4">
          <div v-for="field in agent.fields" :key="field.key">
            <label v-if="field.type !== 'boolean'" class="block text-xs text-gray-500 mb-1">
              {{ field.label }}
            </label>
            <input
              v-if="field.type === 'text'"
              v-model="agent.config[field.key]"
              type="text"
              class="w-full border rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
            <input
              v-else-if="field.type === 'number'"
              v-model.number="agent.config[field.key]"
              type="number"
              :min="field.min"
              :max="field.max"
              class="w-full border rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
            <label
              v-else-if="field.type === 'boolean'"
              class="flex items-center gap-2 cursor-pointer text-sm text-gray-700"
            >
              <input v-model="agent.config[field.key]" type="checkbox" class="w-4 h-4" />
              {{ field.label }}
            </label>
          </div>
        </div>

        <!-- 按钮 -->
        <div class="flex items-center gap-2 mt-auto mb-3">
          <button
            v-if="agent.fields.length"
            @click="saveConfig(agent)"
            class="px-3 py-1.5 text-sm rounded-lg border border-gray-300 hover:bg-gray-50"
          >
            {{ savedName === agent.name ? "已保存 ✓" : "保存配置" }}
          </button>
          <button
            @click="run(agent)"
            :disabled="agent.running"
            class="px-4 py-1.5 text-sm rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {{ agent.running ? "运行中..." : "运行" }}
          </button>
          <button
            v-if="agent.log"
            @click="toggleLog(agent.name)"
            class="px-3 py-1.5 text-sm rounded-lg border border-gray-200 text-gray-500 hover:bg-gray-50 ml-auto"
          >
            {{ expandedLogs.has(agent.name) ? "收起日志" : "最近日志" }}
          </button>
        </div>

        <!-- 最近运行 + 日志 -->
        <div v-if="agent.last_run" class="text-xs text-gray-400 mb-2">
          上次运行：{{ formatTime(agent.last_run.finished_at) }}
          <span v-if="agent.last_run.exit_code === 0" class="text-green-600">成功</span>
          <span v-else-if="agent.last_run.exit_code != null" class="text-red-600">
            失败 (exit {{ agent.last_run.exit_code }})
          </span>
        </div>
        <pre
          v-if="agent.log && expandedLogs.has(agent.name)"
          class="text-xs bg-gray-50 rounded p-2 text-gray-600 whitespace-pre-wrap max-h-40 overflow-auto"
        >{{ agent.log.tail }}</pre>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from "vue";
import { getAgents, saveAgentConfig, runAgent, getAgentStatus } from "@/api/agents";
import { useToastStore } from "@/stores/toast";
import type { AgentInfo } from "@/types";

const agents = ref<AgentInfo[]>([]);
const loading = ref(false);
const loadError = ref(false);
const savedName = ref<string | null>(null);
const expandedLogs = ref<Set<string>>(new Set());
const toast = useToastStore();
let timer: number | undefined;

onMounted(async () => {
  await fetchAgents();
  timer = window.setInterval(pollRunning, 5000);
});

onUnmounted(() => {
  if (timer) window.clearInterval(timer);
});

async function fetchAgents() {
  loading.value = true;
  loadError.value = false;
  try {
    const res = await getAgents();
    agents.value = res.data.agents;
  } catch {
    loadError.value = true;
  } finally {
    loading.value = false;
  }
}

async function saveConfig(agent: AgentInfo) {
  try {
    await saveAgentConfig(agent.name, agent.config);
    savedName.value = agent.name;
    toast.success(`「${agent.label}」配置已保存`);
    setTimeout(() => {
      if (savedName.value === agent.name) savedName.value = null;
    }, 2000);
  } catch (e: any) {
    toast.error(e?.response?.data?.error || "保存失败，请重试");
  }
}

const RUN_HINTS: Record<string, string> = {
  collector: "需手机热点 + 专用 Chrome 已登录，最长 30-60 分钟",
  matcher: "读取未匹配岗位做方向标记，通常 1-2 分钟",
  skirmish: "逐条分析公司风险（主动形态会调用 DeepSeek）",
};

async function run(agent: AgentInfo) {
  const hint = RUN_HINTS[agent.name] || "";
  const tip = hint ? `\n\n提示：${hint}` : "";
  if (!confirm(`确认运行「${agent.label}」？\n后台执行，期间可继续操作页面。${tip}`)) return;
  try {
    await runAgent(agent.name);
    agent.running = true;
    toast.success(`「${agent.label}」已在后台启动`);
    await pollRunning();
  } catch (e: any) {
    if ((e as any)?.response?.status === 409) {
      toast.info(e?.response?.data?.error || "该 Agent 正在运行中");
    } else {
      toast.error(e?.response?.data?.error || "启动失败，请重试");
    }
  }
}

async function pollRunning() {
  const runningAgents = agents.value.filter((a) => a.running);
  if (runningAgents.length === 0) return;
  for (const agent of runningAgents) {
    try {
      const res = await getAgentStatus(agent.name);
      agent.running = res.data.running;
      if (res.data.last_run) agent.last_run = res.data.last_run;
      if (res.data.log) agent.log = res.data.log;
    } catch {
      // 轮询失败静默（5s 后会自动重试；连续失败由「上次失败」徽章暴露）
    }
  }
}

function toggleLog(name: string) {
  const next = new Set(expandedLogs.value);
  if (next.has(name)) next.delete(name);
  else next.add(name);
  expandedLogs.value = next;
}

function badgeText(agent: AgentInfo): string {
  if (agent.running) return "运行中";
  if (agent.last_run?.exit_code === 0) return "上次正常";
  if (agent.last_run?.exit_code != null) return "上次失败";
  return "未运行";
}

function badgeDot(agent: AgentInfo): string {
  if (agent.last_run?.exit_code === 0) return "bg-green-500";
  if (agent.last_run?.exit_code != null) return "bg-red-500";
  return "bg-gray-300";
}

function badgeClass(agent: AgentInfo): string {
  if (agent.running) return "text-blue-600";
  if (agent.last_run?.exit_code === 0) return "text-green-600";
  if (agent.last_run?.exit_code != null) return "text-red-600";
  return "text-gray-400";
}

function formatTime(t: string | null): string {
  if (!t) return "-";
  const d = new Date(t);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getMonth() + 1}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}
</script>
