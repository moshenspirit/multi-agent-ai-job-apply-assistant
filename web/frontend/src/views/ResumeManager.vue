<template>
  <div class="space-y-6 max-w-3xl">
    <!-- 上传区域 -->
    <div class="bg-white rounded-lg shadow p-6">
      <h2 class="text-lg font-semibold text-gray-800 mb-4">上传简历</h2>
      <div
        class="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-blue-400 transition-colors cursor-pointer"
        :class="{ 'border-blue-400 bg-blue-50': dragging }"
        @dragover.prevent="dragging = true"
        @dragleave="dragging = false"
        @drop.prevent="handleDrop"
      >
        <input
          ref="fileInput"
          type="file"
          accept=".pdf,.jpg,.jpeg,.png,.bmp,.webp"
          class="hidden"
          @change="handleFileSelect"
        />
        <div @click="fileInput?.click()" class="cursor-pointer">
          <svg class="w-12 h-12 mx-auto text-gray-300 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
              d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
          </svg>
          <p class="text-gray-500 text-sm">拖拽 PDF 或图片到此处，或点击上传</p>
          <p class="text-gray-400 text-xs mt-1">支持 PDF、JPG、PNG 格式</p>
        </div>
      </div>

      <!-- 上传参数 -->
      <div v-if="selectedFile" class="mt-4 p-4 bg-gray-50 rounded-lg space-y-3">
        <div class="text-sm font-medium text-gray-700">
          已选择：{{ selectedFile.name }}
        </div>
        <div class="flex gap-4">
          <div class="flex-1">
            <label class="block text-xs text-gray-500 mb-1">简历名称</label>
            <input
              v-model="uploadName"
              class="w-full border rounded px-3 py-1.5 text-sm"
              placeholder="如：前端开发简历"
            />
          </div>
          <div class="flex-1">
            <label class="block text-xs text-gray-500 mb-1">简历方向</label>
            <select v-model="uploadDirection" class="w-full border rounded px-3 py-1.5 text-sm">
              <option value="frontend">前端开发</option>
              <option value="ai">AI 开发</option>
            </select>
          </div>
        </div>
        <div class="flex gap-3">
          <button
            @click="doUpload"
            :disabled="uploading"
            class="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 text-sm font-medium"
          >
            {{ uploading ? "解析中..." : "开始上传并解析" }}
          </button>
          <button
            @click="cancelUpload"
            class="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 text-sm"
          >
            取消
          </button>
        </div>
        <div v-if="uploadMsg" class="text-sm" :class="uploadOk ? 'text-green-600' : 'text-red-500'">
          {{ uploadMsg }}
        </div>
      </div>
    </div>

    <!-- 简历列表 -->
    <div class="bg-white rounded-lg shadow p-6">
      <h2 class="text-lg font-semibold text-gray-800 mb-4">
        简历列表
        <span v-if="resumes.length" class="text-sm font-normal text-gray-400 ml-2">共 {{ resumes.length }} 份</span>
      </h2>
      <div v-if="loading" class="text-gray-400 text-sm">加载中...</div>
      <div v-else-if="loadError" class="text-gray-400 text-sm">
        简历列表加载失败
        <button @click="fetchResumes" class="ml-2 px-3 py-1 border border-gray-200 rounded hover:bg-gray-50">
          重试
        </button>
      </div>
      <div v-else-if="resumes.length === 0" class="text-gray-400 text-sm">暂无简历，请上传</div>
      <div v-else class="space-y-3">
        <div
          v-for="r in resumes"
          :key="r.id"
          class="border border-gray-200 rounded-lg overflow-hidden"
        >
          <!-- 简历头部 -->
          <div
            class="flex items-center justify-between p-4 bg-gray-50 cursor-pointer hover:bg-gray-100"
            @click="toggleDetail(r.id)"
          >
            <div>
              <div class="font-medium text-gray-800">{{ r.name }}</div>
              <div class="text-sm text-gray-500">
                {{ r.direction === "frontend" ? "前端开发" : "AI 开发" }}
                <span class="ml-3">{{ formatDate(r.created_at) }}</span>
              </div>
            </div>
            <div class="flex items-center gap-2">
              <button
                @click.stop="handleReparse(r.id)"
                class="px-3 py-1 text-blue-600 text-xs border border-blue-200 rounded hover:bg-blue-50"
                :disabled="reparsingId === r.id"
              >
                {{ reparsingId === r.id ? "解析中..." : "重新解析" }}
              </button>
              <button
                @click.stop="handleDelete(r.id)"
                class="text-red-400 hover:text-red-600 text-sm"
              >
                删除
              </button>
              <svg
                class="w-4 h-4 text-gray-400 transition-transform"
                :class="{ 'rotate-90': expandedId === r.id }"
                fill="none" stroke="currentColor" viewBox="0 0 24 24"
              >
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
              </svg>
            </div>
          </div>

          <!-- 简历详情 -->
          <div v-if="expandedId === r.id" class="p-4 border-t">
            <div v-if="expandedData" class="space-y-4">
              <!-- 基本信息 -->
              <div class="grid grid-cols-2 gap-3 text-sm">
                <div v-if="expandedData.name">
                  <span class="text-gray-400">姓名：</span>
                  <span class="text-gray-700">{{ expandedData.name }}</span>
                </div>
                <div v-if="expandedData.years">
                  <span class="text-gray-400">工作年限：</span>
                  <span class="text-gray-700">{{ expandedData.years }} 年</span>
                </div>
                <div v-if="expandedData.education">
                  <span class="text-gray-400">学历：</span>
                  <span class="text-gray-700">{{ expandedData.education }}</span>
                </div>
                <div v-if="expandedData.school">
                  <span class="text-gray-400">毕业院校：</span>
                  <span class="text-gray-700">{{ expandedData.school }}</span>
                </div>
              </div>

              <!-- 技能 -->
              <div v-if="expandedData.skills?.length">
                <div class="text-sm text-gray-400 mb-1">技能标签</div>
                <div class="flex flex-wrap gap-1.5">
                  <span
                    v-for="s in expandedData.skills"
                    :key="s"
                    class="px-2 py-0.5 bg-blue-50 text-blue-700 text-xs rounded"
                  >{{ s }}</span>
                </div>
              </div>

              <!-- 项目 -->
              <div v-if="expandedData.projects?.length">
                <div class="text-sm text-gray-400 mb-2">项目经历</div>
                <div class="space-y-2">
                  <div
                    v-for="(p, idx) in expandedData.projects"
                    :key="idx"
                    class="p-3 bg-gray-50 rounded text-sm"
                  >
                    <div class="font-medium text-gray-700">{{ p.name }}</div>
                    <div class="text-gray-500 mt-1">
                      <span v-if="p.role">角色：{{ p.role }}</span>
                      <span v-if="p.tech?.length" class="ml-3">
                        技术：{{ p.tech.join("、") }}
                      </span>
                    </div>
                    <div v-if="p.desc" class="text-gray-500 mt-1">{{ p.desc }}</div>
                  </div>
                </div>
              </div>

              <!-- 摘要 -->
              <div v-if="expandedData.summary">
                <div class="text-sm text-gray-400 mb-1">简历摘要</div>
                <div class="text-sm text-gray-600 leading-relaxed">{{ expandedData.summary }}</div>
              </div>

              <!-- 解析错误提示 -->
              <div v-if="expandedData.parse_error" class="text-sm text-yellow-600">
                解析警告：{{ expandedData.parse_error }}
              </div>
            </div>

            <!-- 原始文本 -->
            <div v-if="r.raw_text" class="mt-4">
              <details>
                <summary class="text-sm text-gray-400 cursor-pointer hover:text-gray-600">
                  查看原始文本
                </summary>
                <pre class="mt-2 p-3 bg-gray-50 rounded text-xs text-gray-600 max-h-64 overflow-auto whitespace-pre-wrap">{{ r.raw_text }}</pre>
              </details>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { getResumes, deleteResume, uploadResume } from "@/api/resumes";
import { formatDate } from "@/utils/formatters";
import { useToastStore } from "@/stores/toast";
import type { Resume } from "@/types";

const fileInput = ref<HTMLInputElement | null>(null);
const resumes = ref<Resume[]>([]);
const loading = ref(false);
const loadError = ref(false);
const expandedId = ref<number | null>(null);
const toast = useToastStore();

// 上传状态
const dragging = ref(false);
const selectedFile = ref<File | null>(null);
const uploadName = ref("");
const uploadDirection = ref("frontend");
const uploading = ref(false);
const uploadMsg = ref("");
const uploadOk = ref(true);

// 重新解析
const reparsingId = ref<number | null>(null);

onMounted(() => {
  fetchResumes();
});

async function fetchResumes() {
  loading.value = true;
  loadError.value = false;
  try {
    const res = await getResumes();
    resumes.value = res.data;
  } catch {
    loadError.value = true;
  } finally {
    loading.value = false;
  }
}

function handleFileSelect(e: Event) {
  const target = e.target as HTMLInputElement;
  if (target.files?.length) {
    selectFile(target.files[0]);
  }
}

function handleDrop(e: DragEvent) {
  dragging.value = false;
  const file = e.dataTransfer?.files?.[0];
  if (file) selectFile(file);
}

function selectFile(file: File) {
  selectedFile.value = file;
  uploadName.value = file.name.replace(/\.[^.]+$/, "");
  uploadMsg.value = "";
}

function cancelUpload() {
  selectedFile.value = null;
  uploadName.value = "";
  uploadMsg.value = "";
}

async function doUpload() {
  if (!selectedFile.value) return;

  uploading.value = true;
  uploadMsg.value = "";
  try {
    const formData = new FormData();
    formData.append("file", selectedFile.value);
    formData.append("name", uploadName.value || selectedFile.value.name);
    formData.append("direction", uploadDirection.value);

    await uploadResume(formData);
    uploadOk.value = true;
    uploadMsg.value = "上传并解析成功！";
    selectedFile.value = null;
    uploadName.value = "";
    await fetchResumes();
  } catch (err: any) {
    uploadOk.value = false;
    uploadMsg.value = err?.response?.data?.error || "上传失败";
  } finally {
    uploading.value = false;
    setTimeout(() => (uploadMsg.value = ""), 5000);
  }
}

function toggleDetail(id: number) {
  expandedId.value = expandedId.value === id ? null : id;
}

// 展开项的解析结果（computed 跟随 expandedId + resumes，重解析后自动刷新）
const expandedData = computed<Record<string, any> | null>(() => {
  if (expandedId.value === null) return null;
  const r = resumes.value.find((x) => x.id === expandedId.value);
  if (!r?.structured) return null;
  try {
    return JSON.parse(r.structured);
  } catch {
    return null;
  }
});

async function handleReparse(id: number) {
  reparsingId.value = id;
  try {
    const { default: client } = await import("@/api/client");
    await client.post(`/resumes/${id}/parse`);
    await fetchResumes();
    toast.success("重新解析完成");
  } catch (e: any) {
    toast.error(e?.response?.data?.error || "重新解析失败，请重试");
  } finally {
    reparsingId.value = null;
  }
}

async function handleDelete(id: number) {
  if (!confirm("确定删除这份简历吗？")) return;
  try {
    await deleteResume(id);
    resumes.value = resumes.value.filter((r) => r.id !== id);
    if (expandedId.value === id) expandedId.value = null;
    toast.success("已删除简历");
  } catch (e: any) {
    toast.error(e?.response?.data?.error || "删除失败，请重试");
  }
}
</script>
