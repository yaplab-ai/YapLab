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
        { role: 'teacher', status: 'partial', reason: 'invalid_response', proposals: [{ action_id: 'continue', text: 'Consider continuing.', fact_ids: ['f1'], source_ids: ['s1'] }, { action_id: 'pause', text: 'Pause for a review.', fact_ids: ['f2'], source_ids: ['s2'] }], questions: [{ question_id: 'q1', text: 'Who decides?' }], evidence: [{ id: 's1', title: 'Official source', url: 'https://example.org/policy', authority: 'Authority', jurisdiction: 'UAE', document_type: 'Guidance', scope: 'University context', source_locator: 'Section 3', verification: 'Check current version.', summary: 'Source overview.', limitations: ['Limited to context.'] }], prompt_sha256: 'digest-1' },
        { role: 'privacy', status: 'unavailable', reason: 'timeout', proposals: [], questions: [] },
      ], plan: [{ action_id: 'continue', owner: 'teacher', text: 'Consider continuing.', depends_on: ['check_terms'], handoffs: [{ action_id: 'check_terms', owner: 'privacy' }], status: 'missing_prerequisites' }],
      unresolved: ['Privacy review is needed.'], limitations: ['No action was executed.'],
    } }));
    assert.match(html, /Offline test/);
    assert.match(html, /Some items could not be used; the remaining items are shown/);
    assert.match(html, /Consider continuing/);
    assert.doesNotMatch(html, /invalid.response/);
    assert.match(html, /<p><strong>Consider continuing\.<\/strong><br\/>Facts: f1 · Sources: s1<\/p>/);
    assert.match(html, /<p><strong>Pause for a review\.<\/strong><br\/>Facts: f2 · Sources: s2<\/p>/);
    assert.match(html, /Check whether each selected source supports the proposal in this context/);
    assert.match(html, /Who decides\?/);
    assert.match(html, /Reason: timeout/);
    assert.match(html, /Depends on: check terms/);
    assert.match(html, /Privacy — check terms/);
    assert.match(html, /Privacy review is needed/);
    assert.match(html, /No action was executed/);
    assert.match(html, /fake \/ local · Corpus corpus-1 · Protocol v1/);
    assert.match(html, /href="https:\/\/example.org\/policy"/);
    assert.match(html, /Scope: University context/);
    assert.match(html, /Section 3/);
    assert.match(html, /Summary: Source overview/);
    assert.match(html, /Verification: Check current version/);
    assert.match(html, /Limits: Limited to context/);
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

test('gap, timeline and configured replay use read-only endpoints', async () => {
  const calls = [];
  const api = createPolicyApi('https://api.example/', async (...args) => { calls.push(args); return response({ ok: true }); });
  await api.gaps('scenario/1');
  await api.timeline('exercise/1');
  await api.replay();
  assert.deepEqual(calls.map(([url]) => url), ['https://api.example/policy/gaps?scenario_id=scenario%2F1', 'https://api.example/policy/exercises/exercise%2F1/timeline', 'https://api.example/policy/replay']);
  assert.ok(calls.every(([, options]) => !options.method || options.method === 'GET'));
  assert.equal(api.timelineHtmlUrl('exercise/1'), 'https://api.example/policy/exercises/exercise%2F1/timeline.html');
  assert.equal(api.replayHtmlUrl(), 'https://api.example/policy/replay/timeline.html');
});

test('test fixture replay renders saved output, audit and scoped gaps without mutation controls', async () => {
  const { createServer } = await import('vite');
  const { fileURLToPath } = await import('node:url');
  const { createElement } = await import('react');
  const { renderToStaticMarkup } = await import('react-dom/server');
  const server = await createServer({ root: fileURLToPath(new URL('../../../', import.meta.url)), server: { middlewareMode: true, hmr: false }, appType: 'custom', logLevel: 'error' });
  try {
    const { ReplayContent } = await server.ssrLoadModule('/src/screens/PolicyLab.jsx');
    // Synthetic fixture for rendering only; this is not a recorded live output.
    const html = renderToStaticMarkup(createElement(ReplayContent, { replay: { banner: 'TEST FIXTURE · no new model calls', recording: { exercise_id: 'test', scenario_id: 'test-scenario', sha256: 'test-digest', rounds: [{ stage: 3, review_mode: 'model_assisted', roles: [{ role: 'teacher', status: 'partial', proposals: [{ action_id: 'a', text: 'Saved proposal', rationale: 'Saved rationale', fact_ids: [], source_ids: [] }] }], plan: [{ action_id: 'a', text: 'Saved plan', owner: 'teacher', status: 'missing_prerequisites' }] }], events: [{ type: 'stage_release', stage: 1, fact_ids_by_role: { teacher: ['f1'] } }, { type: 'model_request', stage: 1, role: 'teacher', model: 'test-model', prompt_sha256: 'test-prompt', usage: { total_tokens: 5 }, latency_ms: 10, status: 'partial', prompt_attempted: true }, { type: 'validation', status: 'partial', rationale_issues: ['rationale_rejected'] }, { type: 'decision', role: 'teacher', decision: 'Test decision', source_ids: ['f1'], review_mode: 'human' }] } }, gaps: { label: 'test', gaps: [{ id: 'gap-1', title: 'Test gap', gap_type: 'standards_gap', operational_gap: 'Test question', verification_status: 'candidate', uae_sources: [{ source_id: 'u1', title: 'UAE source', url: 'https://example.org/uae', locator: 'Article 1', says: 'Test says', does_not_say: 'Test does not say' }], global_examples: [{ source_id: 'g1', title: 'Global source', url: 'https://example.org/global', locator: 'Section 2', addresses: 'Test example', scope: 'Universities', binding_status: 'Guidance' }], evidence_needed: ['Test evidence'] }] } }));
    for (const text of ['TEST FIXTURE', 'Saved proposal', 'Saved rationale', 'Stated rationale · model-written, not verified', 'partial', 'Saved plan', 'test-prompt', 'rationale_rejected', 'Test decision', 'Candidate gaps', 'Article 1', 'Universities', 'Guidance', 'Test evidence']) assert.ok(html.includes(text), text);
    assert.doesNotMatch(html, /Reveal next stage|Record decision|View role proposals/);
    assert.match(html, /href="https:\/\/example.org\/uae"/);
  } finally { await server.close(); }
});

test('proposal details identify rejected rationales without altering accepted proposals', async () => {
  const { createServer } = await import('vite');
  const { fileURLToPath } = await import('node:url');
  const { createElement } = await import('react');
  const { renderToStaticMarkup } = await import('react-dom/server');
  const server = await createServer({ root: fileURLToPath(new URL('../../../', import.meta.url)), server: { middlewareMode: true, hmr: false }, appType: 'custom', logLevel: 'error' });
  try {
    const { CoordinationResult } = await server.ssrLoadModule('/src/screens/PolicyLab.jsx');
    const result = { stage: 1, review_mode: 'model_assisted', roles: [{ role: 'teacher', status: 'completed', proposals: [
      { action_id: 'one', text: 'First action', fact_ids: ['f1'], source_ids: ['s1'], rationale_rejected: true, rationale_issue: 'rationale_legal_conclusion' },
      { action_id: 'two', text: 'Second action', fact_ids: ['f2'], source_ids: ['s2'], rationale: 'The facts support review.' },
    ] }], plan: [] };
    const before = JSON.stringify(result);
    const html = renderToStaticMarkup(createElement(CoordinationResult, { result }));
    assert.match(html, /Rationale omitted · rationale_rejected · rationale_legal_conclusion/);
    assert.match(html, /Stated rationale · model-written, not verified/);
    assert.match(html, /The facts support review/);
    assert.equal((html.match(/Rationale omitted/g) || []).length, 1);
    assert.equal(JSON.stringify(result), before);
  } finally { await server.close(); }
});
