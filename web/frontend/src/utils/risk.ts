/**
 * 风险标签解析 + 剪贴板工具（展示层共用）
 */

export interface RiskFlag {
  flag: string;
  severity: string; // high / mid / low
  reason: string;
}

export type RiskState = "unanalyzed" | "clean" | "flags";

export function parseRiskFlags(raw: string | null): RiskFlag[] {
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

/**
 * 区分三种状态：
 * - unanalyzed：risk_flags 为 null / 解析失败（未做主动分析）
 * - clean：解析成功但为空数组 []（已分析，无明显风险）
 * - flags：解析出非空标签数组
 */
export function riskState(raw: string | null): { state: RiskState; flags: RiskFlag[] } {
  if (!raw) return { state: "unanalyzed", flags: [] };
  try {
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed)) {
      return parsed.length
        ? { state: "flags", flags: parsed }
        : { state: "clean", flags: [] };
    }
    return { state: "unanalyzed", flags: [] };
  } catch {
    return { state: "unanalyzed", flags: [] };
  }
}

export function severityClass(severity: string): string {
  const map: Record<string, string> = {
    high: "bg-red-100 text-red-700",
    mid: "bg-amber-100 text-amber-700",
    low: "bg-blue-100 text-blue-700",
  };
  return map[severity] || "bg-gray-100 text-gray-600";
}

export function severityLabel(severity: string): string {
  const map: Record<string, string> = {
    high: "高风险",
    mid: "中风险",
    low: "低风险",
  };
  return map[severity] || severity || "风险";
}

/** 复制文本到剪贴板（优先 Clipboard API，降级 execCommand） */
export async function copyText(text: string): Promise<boolean> {
  if (!text) return false;
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    // 降级：隐藏 textarea + execCommand（兼容非安全上下文）
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.select();
    try {
      return document.execCommand("copy");
    } catch {
      return false;
    } finally {
      document.body.removeChild(ta);
    }
  }
}
