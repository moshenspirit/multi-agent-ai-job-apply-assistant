import client from "./client";
import type { AppConfig } from "@/types";

export function getConfig() {
  return client.get<AppConfig>("/config");
}

export function updateConfig(data: Partial<AppConfig>) {
  return client.put<AppConfig>("/config", data);
}
