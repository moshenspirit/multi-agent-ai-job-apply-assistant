import { defineStore } from "pinia";
import { ref } from "vue";
import { getConfig, updateConfig } from "@/api/config";
import { getCompanyCounts } from "@/api/jobs";

/**
 * 公司元数据（任务④ 2026-09-03）：黑名单 + 公司岗位数（识别批量刷屏公司）
 * JobList / JobDetail / ConfigCenter 共用；JobList 在 activated 时刷新
 */
export const useCompanyStore = defineStore("company", () => {
  const blacklist = ref<string[]>([]);
  const companyCounts = ref<Record<string, number>>({});

  /** 拉取黑名单（来自 config.filter_conditions.blacklist）+ 公司岗位计数 */
  async function loadMeta() {
    try {
      const [cfgRes, cntRes] = await Promise.all([getConfig(), getCompanyCounts()]);
      blacklist.value = cfgRes.data.filter_conditions?.blacklist ?? [];
      const m: Record<string, number> = {};
      for (const item of cntRes.data) {
        m[item.company_name] = item.count;
      }
      companyCounts.value = m;
    } catch {
      // 元数据加载失败不阻塞列表浏览（列表本身有自己的 error 态）
    }
  }

  /** 公司名命中的黑名单词条（未命中返回 null） */
  function blacklistHit(company: string | null | undefined): string | null {
    const c = (company || "").trim();
    if (!c) return null;
    for (const kw of blacklist.value) {
      const k = (kw || "").trim();
      if (k && c.includes(k)) return k;
    }
    return null;
  }

  /** 该公司在库岗位数（0 = 仅当前 1 条或未统计到） */
  function countOf(company: string | null | undefined): number {
    return companyCounts.value[(company || "").trim()] || 0;
  }

  /** 把公司加入黑名单（先 GET 全量 config 再合并保存，避免覆盖其他筛选条件）。返回是否成功 */
  async function addBlacklist(company: string): Promise<boolean> {
    const c = (company || "").trim();
    if (!c) return false;
    if (blacklistHit(c)) return true; // 已在黑名单

    try {
      const cfg = await getConfig();
      const fc = { ...(cfg.data.filter_conditions || {}) };
      const next = [...(fc.blacklist || [])];
      if (!next.includes(c)) next.push(c);
      await updateConfig({ filter_conditions: { ...fc, blacklist: next } });
      blacklist.value = next;
      return true;
    } catch {
      return false;
    }
  }

  return { blacklist, companyCounts, loadMeta, blacklistHit, countOf, addBlacklist };
});
