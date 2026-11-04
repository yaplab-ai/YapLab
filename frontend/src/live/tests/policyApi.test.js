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

test('surfaces backend and network errors without inventing results', async () => {
  const rejected = createPolicyApi('http://localhost:8000', async () => response({ detail: 'Stage is final' }, false, 409));
  await assert.rejects(rejected.advance('id', 'teacher'), /Stage is final/);
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
