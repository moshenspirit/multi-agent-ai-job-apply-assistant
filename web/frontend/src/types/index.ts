/** 岗位 */
export interface Job {
  id: number;
  job_name: string;
  company_name: string;
  salary_min: number | null;
  salary_max: number | null;
  city: string | null;
  district: string | null;
  experience: string | null;
  education: string | null;
  jd_text: string | null;
  company_size: string | null;
  company_industry: string | null;
  company_finance: string | null;
  boss_active: string | null;
  source_url: string;
  source_keyword: string | null;
  match_direction: string | null;
  match_score_frontend: number | null;
  match_score_ai: number | null;
  match_reason: string | null;
  status: string;
  collect_batch: string | null;
  company_profile: string | null;
  risk_flags: string | null;
  risk_analyzed_at: string | null;
  created_at: string | null;
  updated_at: string | null;
}

/** 简历 */
export interface Resume {
  id: number;
  name: string;
  direction: string;
  file_path: string | null;
  raw_text: string | null;
  structured: string | null;
  created_at: string | null;
  updated_at: string | null;
}

/** 搜索关键词组 */
export interface SearchKeywordGroup {
  direction: string;
  keywords: string[];
}

/** 筛选条件 */
export interface FilterConditions {
  city?: string;
  salary_min?: number;
  salary_max?: number;
  company_size?: string[];
  industry?: string[];
  education?: string;
  experience?: string;
  blacklist?: string[];
}

/** 应用配置 */
export interface AppConfig {
  id: number;
  search_keywords: SearchKeywordGroup[];
  filter_conditions: FilterConditions;
  weights: Record<string, number>;
  max_pages: number;
  max_collect_time: number;
  updated_at: string | null;
}

/** 投递记录 */
export interface DeliveryRecord {
  id: number;
  job_id: number;
  status: string;
  note: string | null;
  created_at: string | null;
  job_name?: string | null;
  company_name?: string | null;
  salary_min?: number | null;
  salary_max?: number | null;
}

/** Agent 配置字段（注册表驱动表单渲染） */
export interface AgentField {
  key: string;
  label: string;
  type: "text" | "number" | "boolean";
  default?: string | number | boolean;
  min?: number;
  max?: number;
}

/** Agent 管理信息 */
export interface AgentInfo {
  name: string;
  label: string;
  description: string;
  fields: AgentField[];
  config: Record<string, string | number | boolean>;
  running: boolean;
  last_run: {
    started_at: string;
    finished_at: string;
    exit_code: number | null;
    log_path: string | null;
  } | null;
  log: {
    path: string;
    mtime: string;
    tail: string;
  } | null;
}
