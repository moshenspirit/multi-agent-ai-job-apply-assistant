/**
 * 格式化与状态映射工具（JobList / JobDetail / Dashboard / DeliveryHistory 共用）
 * 2026-09-03 从 4 个页面抽出的重复定义
 */

export function formatSalary(min: number | null | undefined, max: number | null | undefined): string {
  if (!min && !max) return "面议";
  const minStr = min ? `${(min / 1000).toFixed(0)}k` : "";
  const maxStr = max ? `${(max / 1000).toFixed(0)}k` : "";
  return `${minStr}-${maxStr}`;
}

export function formatDate(d: string | null | undefined): string {
  if (!d) return "-";
  return new Date(d).toLocaleDateString("zh-CN");
}

/** 匹配方向徽章 */
const MATCH_CLASS: Record<string, string> = {
  frontend: "bg-blue-100 text-blue-700",
  ai: "bg-purple-100 text-purple-700",
  both: "bg-green-100 text-green-700",
  none: "bg-gray-100 text-gray-600",
};
const MATCH_LABEL: Record<string, string> = {
  frontend: "前端",
  ai: "AI",
  both: "双匹配",
  none: "不匹配",
};

export function matchClass(dir: string | null | undefined): string {
  return MATCH_CLASS[dir || ""] || MATCH_CLASS.none;
}

export function matchLabel(dir: string | null | undefined): string {
  return MATCH_LABEL[dir || ""] || dir || "未匹配";
}

/** 岗位状态（jobs.status：new/viewed/applied/ignored）徽章 */
const JOB_STATUS_CLASS: Record<string, string> = {
  new: "bg-yellow-100 text-yellow-700",
  viewed: "bg-blue-100 text-blue-700",
  applied: "bg-green-100 text-green-700",
  ignored: "bg-gray-100 text-gray-600",
};
const JOB_STATUS_LABEL: Record<string, string> = {
  new: "新",
  viewed: "已查看",
  applied: "已投递",
  ignored: "忽略",
};

export function jobStatusClass(status: string | null | undefined): string {
  return JOB_STATUS_CLASS[status || ""] || JOB_STATUS_CLASS.ignored;
}

export function jobStatusLabel(status: string | null | undefined): string {
  return JOB_STATUS_LABEL[status || ""] || status || "-";
}

/** 投递进展（delivery_records.status：applied/interviewed/offer/rejected）徽章 */
const PROGRESS_CLASS: Record<string, string> = {
  applied: "bg-blue-100 text-blue-700",
  interviewed: "bg-yellow-100 text-yellow-700",
  offer: "bg-green-100 text-green-700",
  rejected: "bg-red-100 text-red-700",
};
const PROGRESS_LABEL: Record<string, string> = {
  applied: "已投递",
  interviewed: "面试中",
  offer: "已录用",
  rejected: "未通过",
};

export function progressClass(status: string | null | undefined): string {
  return PROGRESS_CLASS[status || ""] || "bg-gray-100 text-gray-600";
}

export function progressLabel(status: string | null | undefined): string {
  return PROGRESS_LABEL[status || ""] || status || "-";
}

/** 匹配度数字颜色 */
export function scoreColor(score: number | null | undefined): string {
  if (score == null) return "text-gray-300";
  if (score >= 80) return "text-green-600";
  if (score >= 60) return "text-yellow-600";
  return "text-red-500";
}
