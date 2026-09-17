import client from "./client";
import type { Resume } from "@/types";

export function getResumes() {
  return client.get<Resume[]>("/resumes");
}

export function getResume(id: number) {
  return client.get<Resume>(`/resumes/${id}`);
}

export function uploadResume(formData: FormData) {
  return client.post("/resumes/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
}

export function updateResume(id: number, data: Partial<Resume>) {
  return client.put(`/resumes/${id}`, data);
}

export function deleteResume(id: number) {
  return client.delete(`/resumes/${id}`);
}
