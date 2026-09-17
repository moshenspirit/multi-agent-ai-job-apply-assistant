import client from "./client";
import type { AgentInfo } from "@/types";

export function getAgents() {
  return client.get<{ agents: AgentInfo[] }>("/agents");
}

export function saveAgentConfig(name: string, config: Record<string, string | number | boolean>) {
  return client.put(`/agents/${name}/config`, { config });
}

export function runAgent(name: string) {
  return client.post(`/agents/${name}/run`);
}

export function getAgentStatus(name: string) {
  return client.get<{
    running: boolean;
    last_run: AgentInfo["last_run"];
    log: AgentInfo["log"];
  }>(`/agents/${name}/status`);
}
