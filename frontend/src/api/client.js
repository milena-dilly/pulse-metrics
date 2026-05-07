/**
 * api/client.js — Base API client
 * ─────────────────────────────────
 * Single fetch wrapper used by all API modules.
 * Base URL comes from Vite env var → defaults to localhost:8000.
 */

const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

/**
 * Core fetch wrapper.
 * - Appends query params automatically
 * - Parses JSON
 * - Throws structured ApiError on non-2xx
 */
export async function apiFetch(path, params = {}) {
  const url = new URL(path, BASE_URL);

  // Append only defined params (skip null/undefined)
  Object.entries(params).forEach(([k, v]) => {
    if (v !== null && v !== undefined) url.searchParams.set(k, v);
  });

  const res = await fetch(url.toString(), {
    method: "GET",
    headers: { Accept: "application/json" },
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body.detail ?? "Unknown error", path);
  }

  return res.json();
}

export class ApiError extends Error {
  constructor(status, detail, path) {
    super(`API ${status} on ${path}: ${detail}`);
    this.status = status;
    this.detail = detail;
    this.path = path;
  }
}
