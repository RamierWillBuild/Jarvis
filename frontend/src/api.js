// API client. Base URL is configurable via VITE_API_URL (env var at build/dev time).
const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status}: ${detail}`);
  }
  return res.json();
}

export const api = {
  getLatestBriefing: () => request("/briefing/latest"),
  getArticles: (category) =>
    request(`/articles${category ? `?category=${encodeURIComponent(category)}` : ""}`),
  chat: (message, history = []) =>
    request("/chat", { method: "POST", body: JSON.stringify({ message, history }) }),
  runPipeline: () => request("/pipeline/run", { method: "POST" }),
  getSettings: () => request("/settings"),
  updateSettings: (payload) =>
    request("/settings", { method: "PUT", body: JSON.stringify(payload) }),
};
