import client from "./client";
import type { Job } from "@/types";

export function getJobs(params?: Record<string, unknown>) {
  return client.get<{ data: Job[]; total: number; page: number; per_page: number }>("/jobs", { params });
}

export function getJob(id: number) {
  return client.get<Job>(`/jobs/${id}`);
}

export function updateJobStatus(id: number, status: string) {
  return client.put<Job>(`/jobs/${id}/status`, { status });
}

export function getJobStats() {
  return client.get("/jobs/stats");
}

/** 按公司聚合岗位数（任务④：识别刷屏/批量发帖公司） */
export function getCompanyCounts() {
  return client.get<{ company_name: string; count: number }[]>("/jobs/company-counts");
}

/** 导出岗位列表（CSV / Markdown），返回 Blob */
export function exportJobs(format: "csv" | "md", params?: Record<string, unknown>) {
  return client.get<Blob>(`/jobs/export`, {
    params: { ...params, format },
    responseType: "blob",
  });
}
