<template>
  <div class="space-y-6 max-w-3xl">
    <!-- 搜索关键词 -->
    <div class="bg-white rounded-lg shadow p-6">
      <h2 class="text-lg font-semibold text-gray-800 mb-4">搜索关键词</h2>
      <p class="text-sm text-gray-400 mb-4">每组关键词对应一份简历方向，采集时会用每组关键词分别搜索并合并结果</p>
      <div class="space-y-3">
        <div
          v-for="(group, gIdx) in searchKeywords"
          :key="gIdx"
          class="flex items-start gap-3 p-3 bg-gray-50 rounded-lg"
        >
          <select
            v-model="group.direction"
            class="border rounded px-2 py-1 text-sm w-28 flex-shrink-0"
          >
            <option value="frontend">前端</option>
            <option value="ai">AI</option>
          </select>
          <div class="flex-1 space-y-2">
            <div v-for="(kw, kIdx) in group.keywords" :key="kIdx" class="flex gap-2">
              <input
                v-model="group.keywords[kIdx]"
                class="flex-1 border rounded px-3 py-1.5 text-sm"
                :class="{ 'border-red-300': errors[`kw_${gIdx}_${kIdx}`] }"
                placeholder="输入关键词，如：前端开发"
                @input="clearError(`kw_${gIdx}_${kIdx}`)"
              />
              <button
                @click="removeKeyword(gIdx, kIdx)"
                class="text-red-400 hover:text-red-600 text-sm flex-shrink-0"
                :disabled="group.keywords.length <= 1"
              >
                删除
              </button>
            </div>
            <button
              @click="addKeyword(gIdx)"
              class="text-blue-600 text-sm hover:text-blue-800"
            >
              + 添加关键词
            </button>
          </div>
          <button
            @click="removeGroup(gIdx)"
            class="text-red-400 hover:text-red-600 text-sm mt-1 flex-shrink-0"
            :disabled="searchKeywords.length <= 1"
          >
            删除组
          </button>
        </div>
        <button
          @click="addGroup"
          class="text-blue-600 text-sm hover:text-blue-800"
        >
          + 添加关键词组
        </button>
      </div>
    </div>

    <!-- 筛选条件 -->
    <div class="bg-white rounded-lg shadow p-6">
      <h2 class="text-lg font-semibold text-gray-800 mb-4">筛选条件</h2>
      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block text-sm text-gray-600 mb-1">期望城市</label>
          <input
            v-model="filterConditions.city"
            class="w-full border rounded px-3 py-1.5 text-sm"
            placeholder="如：广州、深圳"
          />
        </div>
        <div>
          <label class="block text-sm text-gray-600 mb-1">最低薪资（元）</label>
          <input
            v-model.number="filterConditions.salary_min"
            type="number"
            class="w-full border rounded px-3 py-1.5 text-sm"
            :class="{ 'border-red-300': errors.salary }"
            placeholder="如：15000"
            @input="clearError('salary')"
          />
        </div>
        <div>
          <label class="block text-sm text-gray-600 mb-1">最高薪资（元）</label>
          <input
            v-model.number="filterConditions.salary_max"
            type="number"
            class="w-full border rounded px-3 py-1.5 text-sm"
            :class="{ 'border-red-300': errors.salary }"
            placeholder="如：25000"
            @input="clearError('salary')"
          />
        </div>
        <div>
          <label class="block text-sm text-gray-600 mb-1">学历要求</label>
          <select v-model="filterConditions.education" class="w-full border rounded px-3 py-1.5 text-sm">
            <option value="">不限</option>
            <option value="大专">大专</option>
            <option value="本科">本科</option>
            <option value="硕士">硕士</option>
            <option value="博士">博士</option>
          </select>
        </div>
        <div>
          <label class="block text-sm text-gray-600 mb-1">经验要求</label>
          <select v-model="filterConditions.experience" class="w-full border rounded px-3 py-1.5 text-sm">
            <option value="">不限</option>
            <option value="应届生">应届生</option>
            <option value="1-3年">1-3年</option>
            <option value="3-5年">3-5年</option>
            <option value="5-10年">5-10年</option>
          </select>
        </div>
        <div>
          <label class="block text-sm text-gray-600 mb-1">公司规模</label>
          <div class="space-y-1.5">
            <label v-for="size in companySizes" :key="size" class="flex items-center gap-2 text-sm cursor-pointer">
              <input
                type="checkbox"
                :value="size"
                v-model="filterConditions.company_size"
                class="rounded border-gray-300"
              />
              {{ size }}
            </label>
          </div>
        </div>
        <div>
          <label class="block text-sm text-gray-600 mb-1">行业偏好</label>
          <div class="space-y-1.5">
            <label v-for="ind in industries" :key="ind" class="flex items-center gap-2 text-sm cursor-pointer">
              <input
                type="checkbox"
                :value="ind"
                v-model="filterConditions.industry"
                class="rounded border-gray-300"
              />
              {{ ind }}
            </label>
          </div>
        </div>
      </div>
    </div>

    <!-- 公司黑名单（任务④ 避雷） -->
    <div class="bg-white rounded-lg shadow p-6">
      <h2 class="text-lg font-semibold text-gray-800 mb-1">公司黑名单（避雷）</h2>
      <p class="text-sm text-gray-400 mb-4">
        黑名单公司的岗位会在列表中带「⚠ 黑名单」红色标签提醒你避雷；也可直接在岗位卡片 / 详情页一键加入。
        保存后生效，重新采集时匹配 Agent 也会把黑名单公司标为不匹配。
      </p>
      <div v-if="!filterConditions.blacklist?.length" class="text-sm text-gray-400 mb-3">
        暂无黑名单公司
      </div>
      <div v-else class="flex flex-wrap gap-2 mb-3">
        <span
          v-for="(name, i) in filterConditions.blacklist"
          :key="`${name}-${i}`"
          class="inline-flex items-center gap-1.5 px-2.5 py-1 bg-red-50 text-red-600 text-sm rounded-lg border border-red-100"
        >
          {{ name }}
          <button @click="filterConditions.blacklist?.splice(i, 1)" class="text-red-400 hover:text-red-600 text-xs">✕</button>
        </span>
      </div>
      <div class="flex gap-2">
        <input
          v-model="newBlacklistItem"
          @keydown.enter.prevent="addBlacklistItem"
          placeholder="输入公司名关键词，回车添加（如：XX科技）"
          class="flex-1 border rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-red-500"
        />
        <button
          @click="addBlacklistItem"
          class="px-4 py-1.5 bg-red-600 text-white rounded text-sm hover:bg-red-700"
        >
          添加
        </button>
      </div>
    </div>

    <!-- 权重配置 -->
    <div class="bg-white rounded-lg shadow p-6">
      <h2 class="text-lg font-semibold text-gray-800 mb-4">排序权重</h2>
      <p class="text-sm text-gray-400 mb-4">调整各因素在岗位排序中的重要性（0=忽略，10=最重要）</p>
      <div class="space-y-4 max-w-lg">
        <div v-for="item in weightItems" :key="item.key" class="flex items-center gap-4">
          <span class="w-24 text-sm text-gray-600 flex-shrink-0">{{ item.label }}</span>
          <input
            type="range"
            min="0"
            max="10"
            v-model.number="weights[item.key]"
            class="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
          />
          <span class="w-6 text-sm font-medium text-gray-700 text-right">{{ weights[item.key] }}</span>
        </div>
      </div>
    </div>

    <!-- 采集参数 -->
    <div class="bg-white rounded-lg shadow p-6">
      <h2 class="text-lg font-semibold text-gray-800 mb-4">采集参数</h2>
      <div class="grid grid-cols-2 gap-4 max-w-lg">
        <div>
          <label class="block text-sm text-gray-600 mb-1">最大翻页数</label>
          <input
            v-model.number="maxPages"
            type="number"
            min="1"
            max="20"
            class="w-full border rounded px-3 py-1.5 text-sm"
            :class="{ 'border-red-300': errors.maxPages }"
            @input="clearError('maxPages')"
          />
          <span class="text-xs text-gray-400">建议 3-5 页</span>
        </div>
        <div>
          <label class="block text-sm text-gray-600 mb-1">最大采集时间（秒）</label>
          <input
            v-model.number="maxCollectTime"
            type="number"
            min="60"
            max="1800"
            class="w-full border rounded px-3 py-1.5 text-sm"
            :class="{ 'border-red-300': errors.maxCollectTime }"
            @input="clearError('maxCollectTime')"
          />
          <span class="text-xs text-gray-400">建议 300-600 秒</span>
        </div>
      </div>
    </div>

    <!-- 错误汇总 -->
    <div v-if="Object.keys(errors).length" class="bg-red-50 border border-red-200 rounded-lg p-4">
      <div class="text-sm text-red-700 font-medium mb-1">请修正以下问题：</div>
      <ul class="text-sm text-red-600 space-y-0.5">
        <li v-for="(msg, key) in errors" :key="key">{{ msg }}</li>
      </ul>
    </div>

    <!-- 保存 -->
    <div class="flex gap-3">
      <button
        @click="saveConfig"
        :disabled="saving"
        class="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 text-sm font-medium transition-colors"
      >
        {{ saving ? "保存中..." : "保存配置" }}
      </button>
      <span v-if="saveMsg" class="text-sm self-center" :class="saveOk ? 'text-green-600' : 'text-red-500'">
        {{ saveMsg }}
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { getConfig, updateConfig } from "@/api/config";
import type { SearchKeywordGroup, FilterConditions } from "@/types";

const searchKeywords = ref<SearchKeywordGroup[]>([{ direction: "frontend", keywords: [""] }]);

const filterConditions = reactive<FilterConditions>({
  city: "",
  salary_min: undefined,
  salary_max: undefined,
  company_size: [],
  industry: [],
  education: "",
  experience: "",
  blacklist: [],
});

const weights = reactive<Record<string, number>>({
  salary: 8,
  location: 10,
  company_size: 5,
  industry: 4,
  experience: 6,
  education: 5,
});

const weightItems = [
  { key: "salary", label: "薪资" },
  { key: "location", label: "地点" },
  { key: "company_size", label: "公司规模" },
  { key: "industry", label: "行业" },
  { key: "experience", label: "经验匹配" },
  { key: "education", label: "学历匹配" },
];

const companySizes = ["少于15人", "15-50人", "50-99人", "100-499人", "500-999人", "1000-9999人", "10000人以上"];
const industries = ["互联网", "游戏", "人工智能", "金融", "教育", "医疗", "电商", "社交", "企业服务", "硬件"];

const maxPages = ref(5);
const maxCollectTime = ref(600);

const saving = ref(false);
const saveMsg = ref("");
const saveOk = ref(true);
const newBlacklistItem = ref("");

/** 任务④：添加黑名单公司（本地追加，随整体「保存配置」提交） */
function addBlacklistItem() {
  const v = newBlacklistItem.value.trim();
  if (!v) return;
  if (!filterConditions.blacklist) filterConditions.blacklist = [];
  const list = filterConditions.blacklist;
  if (!list.includes(v)) list.push(v);
  newBlacklistItem.value = "";
}

const errors = reactive<Record<string, string>>({});

onMounted(async () => {
  try {
    const res = await getConfig();
    const cfg = res.data;
    if (cfg.search_keywords?.length) {
      searchKeywords.value = cfg.search_keywords;
    }
    if (cfg.filter_conditions) {
      // 确保数组字段有默认值，防止 v-for 遍历 null 报错
      const fc = cfg.filter_conditions;
      filterConditions.city = fc.city || "";
      filterConditions.salary_min = fc.salary_min ?? undefined;
      filterConditions.salary_max = fc.salary_max ?? undefined;
      filterConditions.company_size = Array.isArray(fc.company_size) ? fc.company_size : [];
      filterConditions.industry = Array.isArray(fc.industry) ? fc.industry : [];
      filterConditions.education = fc.education || "";
      filterConditions.experience = fc.experience || "";
      filterConditions.blacklist = Array.isArray(fc.blacklist) ? fc.blacklist : [];
    }
    if (cfg.weights && Object.keys(cfg.weights).length) {
      Object.assign(weights, cfg.weights);
    }
    maxPages.value = cfg.max_pages || 5;
    maxCollectTime.value = cfg.max_collect_time || 600;
  } catch (e) {
    console.warn("加载配置失败，使用默认值:", e);
  }
});

function validate(): boolean {
  // 清空之前的错误
  Object.keys(errors).forEach((k) => delete errors[k]);

  // 校验关键词非空
  let hasKeyword = false;
  searchKeywords.value.forEach((group, gIdx) => {
    group.keywords.forEach((kw, kIdx) => {
      if (kw.trim()) hasKeyword = true;
      if (!kw.trim() && group.keywords.length === 1 && searchKeywords.value.length === 1) {
        errors[`kw_${gIdx}_${kIdx}`] = "请至少填写一个搜索关键词";
      }
    });
  });
  if (!hasKeyword) {
    errors.keywords = "请至少填写一个搜索关键词";
  }

  // 校验薪资范围
  const smin = filterConditions.salary_min;
  const smax = filterConditions.salary_max;
  if (smin != null && smax != null && smin > smax) {
    errors.salary = "最低薪资不能高于最高薪资";
  }

  // 校验采集参数
  if (maxPages.value < 1 || maxPages.value > 20) {
    errors.maxPages = "翻页数应在 1-20 之间";
  }
  if (maxCollectTime.value < 60 || maxCollectTime.value > 1800) {
    errors.maxCollectTime = "采集时间应在 60-1800 秒之间";
  }

  return Object.keys(errors).length === 0;
}

function clearError(key: string) {
  delete errors[key];
}

async function saveConfig() {
  if (!validate()) return;

  saving.value = true;
  saveMsg.value = "";
  try {
    // 过滤空关键词组和空关键词
    const cleanKeywords = searchKeywords.value
      .map((g) => ({
        direction: g.direction,
        keywords: g.keywords.filter((k) => k.trim()),
      }))
      .filter((g) => g.keywords.length > 0);

    await updateConfig({
      search_keywords: cleanKeywords,
      filter_conditions: filterConditions,
      weights: weights,
      max_pages: maxPages.value,
      max_collect_time: maxCollectTime.value,
    });
    saveOk.value = true;
    saveMsg.value = "保存成功！";
  } catch (err: any) {
    saveOk.value = false;
    saveMsg.value = err?.response?.data?.error || "保存失败";
  } finally {
    saving.value = false;
    setTimeout(() => (saveMsg.value = ""), 3000);
  }
}

function addGroup() {
  searchKeywords.value.push({ direction: "frontend", keywords: [""] });
}

function removeGroup(idx: number) {
  searchKeywords.value.splice(idx, 1);
}

function addKeyword(gIdx: number) {
  searchKeywords.value[gIdx].keywords.push("");
}

function removeKeyword(gIdx: number, kIdx: number) {
  searchKeywords.value[gIdx].keywords.splice(kIdx, 1);
}
</script>
