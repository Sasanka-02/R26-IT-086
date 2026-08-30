import axios from "axios";
import { AgeCategory, ExtractFeaturesResponse, TaskType } from "../types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL as string;

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120_000, // model inference can be slow on CPU
});

/**
 * Determines a sensible filename/extension from the recorded blob's mime type.
 */
function inferFilename(blob: Blob): string {
  if (blob.type.includes("mp4")) return "recording.mp4";
  if (blob.type.includes("ogg")) return "recording.ogg";
  return "recording.webm";
}

export async function extractFeatures(params: {
  audioBlob: Blob;
  taskType: TaskType;
  sessionId: string;
  ageCategory: AgeCategory;
}): Promise<ExtractFeaturesResponse> {
  const { audioBlob, taskType, sessionId, ageCategory } = params;

  const formData = new FormData();
  formData.append("audio_file", audioBlob, inferFilename(audioBlob));
  formData.append("task_type", taskType);
  formData.append("session_id", sessionId);
  formData.append("age_category", ageCategory);

  const response = await apiClient.post<ExtractFeaturesResponse>(
    "/api/v1/extract-features",
    formData,
    {
      headers: { "Content-Type": "multipart/form-data" },
    }
  );

  return response.data;
}

export async function checkHealth(): Promise<boolean> {
  try {
    const response = await apiClient.get("/api/v1/health");
    return response.status === 200;
  } catch {
    return false;
  }
}
