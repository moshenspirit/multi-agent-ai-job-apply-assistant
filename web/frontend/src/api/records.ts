import client from "./client";
import type { DeliveryRecord } from "@/types";

export function getRecords(params?: { job_id?: number }) {
  return client.get<DeliveryRecord[]>("/records", { params });
}

export function createRecord(data: { job_id: number; status?: string; note?: string }) {
  return client.post<DeliveryRecord>("/records", data);
}

export function deleteRecord(id: number) {
  return client.delete(`/records/${id}`);
}

export function updateRecordStatus(id: number, status: string) {
  return client.put<DeliveryRecord>(`/records/${id}/status`, { status });
}
