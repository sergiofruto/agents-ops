// lib/api.ts — server-side fetch helpers

const BASE = process.env.API_BASE ?? "http://localhost:5003";

export async function fetchStatus() {
  const r = await fetch(`${BASE}/api/status`, { next: { revalidate: 30 } });
  if (!r.ok) return null;
  return r.json();
}

export async function fetchSky() {
  const r = await fetch(`${BASE}/api/sky`, { next: { revalidate: 60 } });
  if (!r.ok) return null;
  return r.json();
}

export async function fetchSolar() {
  const r = await fetch(`${BASE}/api/solar`, { next: { revalidate: 120 } });
  if (!r.ok) return null;
  return r.json();
}

export async function fetchBriefs(limit = 10) {
  const r = await fetch(`${BASE}/api/briefs?limit=${limit}`, { next: { revalidate: 60 } });
  if (!r.ok) return [];
  return r.json();
}

export async function fetchBrief(id: number) {
  const r = await fetch(`${BASE}/api/briefs/${id}`, { next: { revalidate: 60 } });
  if (!r.ok) return null;
  return r.json();
}
