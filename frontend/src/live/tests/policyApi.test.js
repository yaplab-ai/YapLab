import test from 'node:test';
import assert from 'node:assert/strict';
import { createPolicyApi } from '../policyApi.js';

const response = (body, ok = true, status = 200) => ({ ok, status, json: async () => body });

test('requires an explicitly configured backend', async () => {
  const api = createPolicyApi('', () => { throw new Error('must not fetch'); });
  await assert.rejects(api.search('privacy'), /Set VITE_API_URL/);
});

test('sends structured review and role-scoped exercise requests', async () => {
  const calls = [];
  const api = createPolicyApi('http://localhost:8000/', async (...args) => { calls.push(args); return response({ ok: true }); });
  await api.review('Visible facts', ['privacy'], 'Classroom');
  await api.exercise('id/1', 'accessibility');
  assert.equal(calls[0][0], 'http://localhost:8000/policy/review');
  assert.deepEqual(JSON.parse(calls[0][1].body), { text: 'Visible facts', topics: ['privacy'], context: 'Classroom', institution: 'general' });
  assert.equal(calls[1][0], 'http://localhost:8000/policy/exercises/id%2F1?role=accessibility');
});


test('institution scopes the catalog, search, and review while defaulting to general', async () => {
  const calls = [];
  const api = createPolicyApi('https://api.example', async (...args) => { calls.push(args); return response({ ok: true }); });
  await api.sources();
  await api.sources('uaeu');
  await api.search('captions');
  await api.search('captions', 5, 'uaeu');
  await api.review('A question', [], '', 'uaeu');
  assert.match(calls[0][0], /institution=general$/);
  assert.match(calls[1][0], /institution=uaeu$/);
  assert.deepEqual(JSON.parse(calls[2][1].body), { query: 'captions', limit: 10, institution: 'general' });
  assert.deepEqual(JSON.parse(calls[3][1].body), { query: 'captions', limit: 5, institution: 'uaeu' });
  assert.equal(JSON.parse(calls[4][1].body).institution, 'uaeu');
});


test('scenario mutations carry the viewed stage and selected evidence', async () => {
  const calls = [];
  const api = createPolicyApi('https://api.example', async (...args) => { calls.push(args); return response({ ok: true }); });
  await api.advance('exercise/1', 'teacher', 2);
  await api.decide('exercise/1', 'privacy', 'Pause and review.', ['fact-1'], 3);
  assert.equal(calls[0][0], 'https://api.example/policy/exercises/exercise%2F1/advance?role=teacher');
  assert.deepEqual(JSON.parse(calls[0][1].body), { expected_stage: 2 });
  assert.deepEqual(JSON.parse(calls[1][1].body), { role: 'privacy', decision: 'Pause and review.', source_ids: ['fact-1'], expected_stage: 3 });
  assert.throws(() => api.advance('exercise/1', 'teacher'), /current stage/);
  assert.throws(() => api.advance('exercise/1', 'teacher', 0), /current stage/);
  assert.throws(() => api.decide('exercise/1', 'teacher', 'Pause', [], 1), /at least one released fact/);
  assert.equal(calls.length, 2, 'invalid mutations must not be sent');
});

test('a stale-stage response remains an explicit conflict for refresh without retry', async () => {
  let count = 0;
  const api = createPolicyApi('https://api.example', async () => { count += 1; return response({ detail: 'Stage changed' }, false, 409); });
  await assert.rejects(api.advance('exercise', 'teacher', 1), (error) => error.status === 409 && error.message === 'Stage changed');
  assert.equal(count, 1);
});


test('coordination uses explicit stage and collection, and reloads the named round', async () => {
  const calls = [];
  const api = createPolicyApi('https://api.example', async (...args) => { calls.push(args); return response({ enabled: true }); });
  await api.coordinationStatus();
  await api.coordinate('exercise/1', 2, 'uaeu');
  await api.coordinationRound('exercise/1', 'round/1');
  assert.equal(calls[0][0], 'https://api.example/policy/coordination/status');
  assert.equal(calls[1][0], 'https://api.example/policy/exercises/exercise%2F1/coordinate');
  assert.deepEqual(JSON.parse(calls[1][1].body), { expected_stage: 2, institution: 'uaeu' });
  assert.equal(calls[2][0], 'https://api.example/policy/exercises/exercise%2F1/coordination/round%2F1');
  assert.throws(() => api.coordinate('exercise/1'), /current stage/);
  assert.equal(calls.length, 3);
});

test('coordination conflicts are returned without retry', async () => {
  let calls = 0;
  const api = createPolicyApi('https://api.example', async () => { calls++; return response({ detail: 'Stage changed; refresh the exercise before retrying.' }, false, 409); });
  await assert.rejects(api.coordinate('exercise', 1), (error) => error.status === 409 && /refresh/.test(error.message));
  assert.equal(calls, 1);
});

test('surfaces backend and network errors without inventing results', async () => {
  const rejected = createPolicyApi('http://localhost:8000', async () => response({ detail: 'Stage is final' }, false, 409));
  await assert.rejects(rejected.advance('id', 'teacher', 1), /Stage is final/);
  const offline = createPolicyApi('http://localhost:8000', async () => { throw new Error('offline'); });
  await assert.rejects(offline.sources(), /Could not reach/);
  const malformed = createPolicyApi('http://localhost:8000', async () => response(null));
  await assert.rejects(malformed.sources(), /invalid response/);
});

test('review keeps per-topic citations compact and deduplicates full references', async () => {
  const { createServer } = await import('vite');
  const { fileURLToPath } = await import('node:url');
  const { createElement } = await import('react');
  const { renderToStaticMarkup } = await import('react-dom/server');
  const server = await createServer({ root: fileURLToPath(new URL('../../../', import.meta.url)), server: { middlewareMode: true, hmr: false }, appType: 'custom', logLevel: 'error' });
  try {
    const { ReviewResult } = await server.ssrLoadModule('/src/screens/PolicyLab.jsx');
    const source = { id: 'england-source', title: 'Education guidance', url: 'https://example.org/guidance', authority: 'Education authority', jurisdiction: 'England', document_type: 'Guidance', scope: 'Applies within its stated scope.', limitations: ['Check local context.'], institution: 'uaeu', reuse_note: 'Link to the source.', verification: 'Check current institutional policy.' };
    const html = renderToStaticMarkup(createElement(ReviewResult, { result: {
      review_mode: 'deterministic', summary: 'Review summary', considerations: [
        { topic: 'privacy', observation: 'First observation', recommendation: 'First step', citations: [source] },
        { topic: 'education', observation: 'Second observation', recommendation: 'Second step', citations: [source] },
      ], gaps: [], limitations: [], audit: { corpus_version: 'v1', retrieval: 'weighted_lexical', selection_mode: 'explicit', source_ids: ['england-source'] },
    } }));
    assert.equal((html.match(/class="policy-citations"/g) || []).length, 2);
    assert.equal((html.match(/class="policy-source"/g) || []).length, 1);
    assert.equal((html.match(/Applies within its stated scope\./g) || []).length, 1);
    assert.equal((html.match(/Check local context\./g) || []).length, 1);
    assert.match(html, /Deterministic review/);
    assert.match(html, /<details class="policy-audit"><summary>Review details<\/summary>/);
    assert.match(html, /England · Guidance · UAEU example/);
    assert.match(html, /Use and reuse:<\/strong> Link to the source/);
    assert.match(html, /Verification:<\/strong> Check current institutional policy/);
  } finally { await server.close(); }
});


test('facilitator result exposes role gaps, evidence and conditional handoffs', async () => {
  const { createServer } = await import('vite');
  const { fileURLToPath } = await import('node:url');
  const { createElement } = await import('react');
  const { renderToStaticMarkup } = await import('react-dom/server');
  const server = await createServer({ root: fileURLToPath(new URL('../../../', import.meta.url)), server: { middlewareMode: true, hmr: false }, appType: 'custom', logLevel: 'error' });
  try {
    const { CoordinationResult } = await server.ssrLoadModule('/src/screens/PolicyLab.jsx');
    const html = renderToStaticMarkup(createElement(CoordinationResult, { result: {
      stage: 2, institution: 'general', review_mode: 'offline_test', protocol_version: 'v1', corpus_version: 'corpus-1', model: { provider: 'fake', model: 'local' }, roles: [
        { role: 'teacher', status: 'completed', proposals: [{ action_id: 'continue', text: 'Consider continuing.', fact_ids: ['f1'], source_ids: ['s1'] }], questions: [{ question_id: 'q1', text: 'Who decides?' }], evidence: [{ id: 's1', title: 'Official source', url: 'https://example.org/policy', authority: 'Authority', jurisdiction: 'UAE', document_type: 'Guidance', scope: 'University context' }], prompt_sha256: 'digest-1' },
        { role: 'privacy', status: 'unavailable', reason: 'timeout', proposals: [], questions: [] },
      ], plan: [{ action_id: 'continue', owner: 'teacher', text: 'Consider continuing.', depends_on: ['check_terms'], handoffs: [{ action_id: 'check_terms', owner: 'privacy' }], status: 'missing_prerequisites' }],
      unresolved: ['Privacy review is needed.'], limitations: ['No action was executed.'],
    } }));
    assert.match(html, /Offline test/);
    assert.match(html, /Facts: f1 · Sources: s1/);
    assert.match(html, /Who decides\?/);
    assert.match(html, /Reason: timeout/);
    assert.match(html, /Depends on: check terms/);
    assert.match(html, /Privacy — check terms/);
    assert.match(html, /Privacy review is needed/);
    assert.match(html, /No action was executed/);
    assert.match(html, /fake \/ local · Corpus corpus-1 · Protocol v1/);
    assert.match(html, /href="https:\/\/example.org\/policy"/);
    assert.match(html, /Scope: University context/);
    assert.match(html, /Prompt digest/);
    assert.match(html, /<details class="policy-audit"><summary>Sources and details<\/summary>/);
    assert.match(html, /<details class="policy-audit"><summary>Model and reference details<\/summary>/);
  } finally { await server.close(); }
});



test('a manual retry can load the stored partial round without client auto-retry', async () => {
  let requests = 0;
  let modelCalls = 0;
  let stored;
  const api = createPolicyApi('https://api.example', async () => {
    requests += 1;
    if (!stored) {
      modelCalls += 1;
      stored = { round_id: 'round-1', review_mode: 'offline_test', roles: [{ role: 'privacy', status: 'unavailable', reason: 'timeout', proposals: [], questions: [] }] };
      throw new Error('connection dropped after commit');
    }
    return response(stored);
  });
  await assert.rejects(api.coordinate('exercise-1', 1, 'general'), /Could not reach/);
  assert.equal(requests, 1, 'the client must not retry automatically');
  const recovered = await api.coordinate('exercise-1', 1, 'general');
  assert.equal(requests, 2);
  assert.equal(modelCalls, 1);
  assert.equal(recovered.round_id, 'round-1');
  assert.equal(recovered.roles[0].status, 'unavailable');
  assert.equal(recovered.roles[0].reason, 'timeout');
});
