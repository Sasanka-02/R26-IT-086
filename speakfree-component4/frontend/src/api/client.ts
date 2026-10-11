import axios from "axios";

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL as string;
export const SESSION_KEY = "speakfree_c4_session";

/** One axios instance for the whole app: adds the login token to every
 *  request and signs the user out if the server says the session expired. */
export const api = axios.create({ baseURL: API_BASE_URL });

let onUnauthorized: (() => void) | null = null;

export function setUnauthorizedHandler(handler: () => void) {
  onUnauthorized = handler;
}

export function storedToken(): string | null {
  try {
    const raw = localStorage.getItem(SESSION_KEY);
    return raw ? JSON.parse(raw).token ?? null : null;
  } catch {
    return null;
  }
}

api.interceptors.request.use((config) => {
  const token = storedToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error?.response?.status === 401 && storedToken()) onUnauthorized?.();
    return Promise.reject(error);
  }
);

/** Human-readable message from an API error. */
export function errorMessage(error: unknown, fallback: string): string {
  const detail = (error as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail[0]?.msg) return String(detail[0].msg);
  return fallback;
}
