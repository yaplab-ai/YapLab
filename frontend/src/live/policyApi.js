import { API_URL } from '../lib/api.js';

// Policy Lab never falls back to the rehearsal demo engine.
export function createPolicyApi(baseUrl = API_URL, fetchImpl = globalThis.fetch) {
  const base = String(baseUrl || '').replace(/\/+$/, '');
  async function request(path, options = {}) {
    if (!base) throw new Error('Set VITE_API_URL to the running backend and restart the frontend to use Policy Lab.');
    let response;
    try {
      response = await fetchImpl(`${base}${path}`, options);
    } catch {
      throw new Error('Could not reach the policy backend. Check VITE_API_URL and that the backend is running.');
    }
    let data;
    try { data = await response.json(); } catch { throw new Error('The policy backend returned an invalid response.'); }
    if (!response.ok) {
      const detail = typeof data?.detail === 'string' ? data.detail : `Request failed (${response.status}).`;
      throw new Error(detail);
    }
    if (!data || typeof data !== 'object' || Array.isArray(data)) throw new Error('The policy backend returned an invalid response.');
    return data;
  }
  const post = (path, body) => request(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  const roleQuery = (role) => `?role=${encodeURIComponent(role)}`;
  return {
    sources: () => request('/policy/sources'),
    search: (query, limit = 10) => post('/policy/search', { query, limit }),
    review: (text, topics = [], context = '') => post('/policy/review', { text, topics, context }),
    scenarios: () => request('/policy/scenarios'),
    startExercise: (scenarioId, role) => post(`/policy/exercises${roleQuery(role)}`, { scenario_id: scenarioId }),
    exercise: (id, role) => request(`/policy/exercises/${encodeURIComponent(id)}${roleQuery(role)}`),
    advance: (id, role) => post(`/policy/exercises/${encodeURIComponent(id)}/advance${roleQuery(role)}`, {}),
    decide: (id, role, decision, sourceIds = []) => post(`/policy/exercises/${encodeURIComponent(id)}/decision`, { role, decision, source_ids: sourceIds }),
    audit: (id, role) => request(`/policy/exercises/${encodeURIComponent(id)}/audit${roleQuery(role)}`),
  };
}

export const policyApi = createPolicyApi();
