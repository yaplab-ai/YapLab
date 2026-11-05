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
      const error = new Error(detail);
      error.status = response.status;
      throw error;
    }
    if (!data || typeof data !== 'object' || Array.isArray(data)) throw new Error('The policy backend returned an invalid response.');
    return data;
  }
  const post = (path, body) => request(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  const roleQuery = (role) => `?role=${encodeURIComponent(role)}`;
  const requireStage = (stage) => {
    if (!Number.isInteger(stage) || stage < 1) throw new Error('Refresh the exercise to get its current stage.');
  };
  return {
    sources: (institution = 'general') => request(`/policy/sources?institution=${encodeURIComponent(institution)}`),
    search: (query, limit = 10, institution = 'general') => post('/policy/search', { query, limit, institution }),
    review: (text, topics = [], context = '', institution = 'general') => post('/policy/review', { text, topics, context, institution }),
    scenarios: () => request('/policy/scenarios'),
    replay: () => request('/policy/replay'),
    replayHtmlUrl: () => `${base}/policy/replay/timeline.html`,
    timeline: (id) => request(`/policy/exercises/${encodeURIComponent(id)}/timeline`),
    timelineHtmlUrl: (id) => `${base}/policy/exercises/${encodeURIComponent(id)}/timeline.html`,
    gaps: (scenarioId) => request(`/policy/gaps?scenario_id=${encodeURIComponent(scenarioId)}`),
    coordinationStatus: () => request('/policy/coordination/status'),
    coordinate: (id, expectedStage, institution = 'general') => {
      requireStage(expectedStage);
      return post(`/policy/exercises/${encodeURIComponent(id)}/coordinate`, { expected_stage: expectedStage, institution });
    },
    coordinationRound: (id, roundId) => request(`/policy/exercises/${encodeURIComponent(id)}/coordination/${encodeURIComponent(roundId)}`),
    startExercise: (scenarioId, role) => post(`/policy/exercises${roleQuery(role)}`, { scenario_id: scenarioId }),
    exercise: (id, role) => request(`/policy/exercises/${encodeURIComponent(id)}${roleQuery(role)}`),
    advance: (id, role, expectedStage) => {
      requireStage(expectedStage);
      return post(`/policy/exercises/${encodeURIComponent(id)}/advance${roleQuery(role)}`, { expected_stage: expectedStage });
    },
    decide: (id, role, decision, sourceIds, expectedStage) => {
      requireStage(expectedStage);
      if (!Array.isArray(sourceIds) || !sourceIds.length) throw new Error('Select at least one released fact before recording a decision.');
      return post(`/policy/exercises/${encodeURIComponent(id)}/decision`, { role, decision, source_ids: sourceIds, expected_stage: expectedStage });
    },
    audit: (id, role) => request(`/policy/exercises/${encodeURIComponent(id)}/audit${roleQuery(role)}`),
  };
}

export const policyApi = createPolicyApi();
