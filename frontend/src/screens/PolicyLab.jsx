import { useEffect, useRef, useState } from 'react';
import Icon from '../components/Icon.jsx';
import { policyApi } from '../live/policyApi.js';
import '../policyLab.css';

const TOPICS = [
  ['privacy', 'Privacy'], ['accessibility', 'Accessibility'], ['responsible_ai', 'Responsible AI'],
  ['education', 'Education'], ['human_oversight', 'Human oversight'],
];
const ROLES = [['teacher', 'Teacher / TA'], ['privacy', 'Privacy'], ['accessibility', 'Accessibility']];
const topicLabel = (topic) => TOPICS.find(([id]) => id === topic)?.[1] || topic;
const fallbackLabel = { timeout: 'The configured model timed out.', provider_error: 'The configured model could not be reached.', invalid_model_response: 'The configured model returned an invalid response.', model_abstained: 'The configured model abstained.', no_retrieved_candidates: 'No candidate references were retrieved.' };

function Source({ source }) {
  return <article className="policy-source">
    <div className="policy-source-meta"><span>{source.document_type}</span><span>{source.jurisdiction}</span></div>
    <h4><a href={source.url} target="_blank" rel="noreferrer">{source.title} <span aria-label="opens in a new tab">↗</span></a></h4>
    <p className="policy-source-author">{source.authority}{source.source_locator ? ` · ${source.source_locator}` : ''}</p>
    {source.summary && <p>{source.summary}</p>}
    {source.scope && <p><strong>Scope:</strong> {source.scope}</p>}
    {source.limitations && <p><strong>Limits:</strong> {Array.isArray(source.limitations) ? source.limitations.join(' ') : source.limitations}</p>}
    {(source.published || source.retrieved) && <p className="policy-source-date">{[source.published && `Published ${source.published}`, source.retrieved && `Retrieved ${source.retrieved}`].filter(Boolean).join(' · ')}</p>}
  </article>;
}

export function ReviewResult({ result }) {
  if (!result) return null;
  const references = [...new Map((result.considerations || []).flatMap((item) => item.citations || []).map((source) => [source.id, source])).values()];
  return <section className="policy-result" aria-live="polite">
    <div className="policy-result-head"><div><p className="eyebrow">Structured review</p><h3>Considerations to investigate</h3></div><span className="policy-tag">{result.review_mode === 'model_assisted' ? 'Model-assisted' : 'Deterministic'} review</span></div>
    <p>{result.summary}</p>
    {result.audit?.fallback_reason && <p className="policy-fallback" role="status">{fallbackLabel[result.audit.fallback_reason] || 'The configured model could not complete the review.'} The deterministic review is shown.</p>}
    {(result.considerations || []).map((item, index) => <div className="policy-consideration" key={`${item.topic}-${index}`}>
      <span className="policy-topic">{topicLabel(item.topic)}</span><p><strong>Observation.</strong> {item.observation}</p><p><strong>Next step.</strong> {item.recommendation}</p>
      {!!item.citations?.length && <ul className="policy-citations" aria-label={`${topicLabel(item.topic)} sources`}>{item.citations.map((source) => <li key={source.id}><a href={source.url} target="_blank" rel="noreferrer">{source.title} <span aria-label="opens in a new tab">↗</span></a><span>{source.jurisdiction} · {source.document_type}</span></li>)}</ul>}
    </div>)}
    {!!references.length && <div className="policy-references"><h4>References</h4><p>Check each source’s scope and limits before applying it.</p>{references.map((source) => <Source key={source.id} source={source} />)}</div>}
    {!!result.gaps?.length && <div className="policy-notes"><h4>Gaps to resolve</h4><ul>{result.gaps.map((gap, i) => <li key={i}>{gap}</li>)}</ul></div>}
    {!!result.limitations?.length && <div className="policy-notes"><h4>Review limits</h4><ul>{result.limitations.map((limit, i) => <li key={i}>{limit}</li>)}</ul></div>}
    {result.audit && <details className="policy-audit"><summary>Review details</summary><p>Corpus {result.audit.corpus_version} · {result.audit.retrieval} · {result.audit.selection_mode} · Sources: {(result.audit.source_ids || []).join(', ') || 'none'}</p></details>}
  </section>;
}

export default function PolicyLab({ onBack }) {
  const [tab, setTab] = useState('search');
  const [catalog, setCatalog] = useState(null);
  const [scenarios, setScenarios] = useState(null);
  const [initialError, setInitialError] = useState('');
  const [query, setQuery] = useState('');
  const [search, setSearch] = useState(null);
  const [text, setText] = useState('');
  const [context, setContext] = useState('');
  const [topics, setTopics] = useState([]);
  const [review, setReview] = useState(null);
  const [role, setRole] = useState('teacher');
  const [exercise, setExercise] = useState(null);
  const [selectedFacts, setSelectedFacts] = useState([]);
  const [scenarioReview, setScenarioReview] = useState(null);
  const [decision, setDecision] = useState('');
  const [audit, setAudit] = useState(null);
  const [decisionSaved, setDecisionSaved] = useState(false);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const epoch = useRef(0);

  useEffect(() => {
    let active = true;
    Promise.all([policyApi.sources(), policyApi.scenarios()]).then(([sources, cases]) => {
      if (active) { setCatalog(sources); setScenarios(cases); }
    }).catch((err) => { if (active) setInitialError(err.message); });
    return () => { active = false; };
  }, []);

  async function run(key, fn, success) {
    setBusy(key); setError('');
    try { const data = await fn(); success(data); } catch (err) { setError(err.message); } finally { setBusy(''); }
  }
  function invalidateScenario() {
    epoch.current += 1; setSelectedFacts([]); setScenarioReview(null); setDecision(''); setAudit(null); setDecisionSaved(false);
  }
  function changeRole(next) {
    invalidateScenario(); setRole(next); setError('');
    if (exercise) { setExercise(null); run('exercise', () => policyApi.exercise(exercise.exercise_id, next), setExercise); }
  }
  const facts = exercise?.released_stages.flatMap((stage) => stage.facts) || [];
  const selectedText = facts.filter((fact) => selectedFacts.includes(fact.id)).map((fact) => fact.text).join('\n');
  const toggle = (values, setValues, id) => setValues(values.includes(id) ? values.filter((value) => value !== id) : [...values, id]);

  return <main className="wrap policy-lab">
    <button className="link-back" onClick={onBack}><Icon name="prev" size={16} /> Modes</button>
    <header className="policy-intro"><div><p className="eyebrow">A sandbox for teachers &amp; TAs</p><h1>Policy Lab<span>.</span></h1><p>Find relevant sources, review a classroom question, and practice a decision as new information unfolds.</p></div><div className="policy-intro-note"><Icon name="book" size={20} /><p>Use this as a starting point for human review. Sources have different jurisdictions and scopes; the output is not a compliance determination.</p></div></header>
    {initialError ? <div className="policy-alert" role="alert"><strong>Policy Lab is unavailable.</strong> {initialError}</div> : !catalog || !scenarios ? <div className="policy-loading" role="status">Loading policy sources and scenarios…</div> : <>
      <nav className="policy-tabs" aria-label="Policy Lab tools">
        {[['search', '01', 'Find sources'], ['review', '02', 'Review a question'], ['scenario', '03', 'Practice a scenario']].map(([id, number, label]) => <button key={id} aria-pressed={tab === id} className={tab === id ? 'active' : ''} onClick={() => { setTab(id); setError(''); }}><span>{number}</span>{label}</button>)}
      </nav>
      {error && <div className="policy-alert" role="alert">{error}</div>}
      {tab === 'search' && <section className="policy-panel" aria-label="Find sources">
        <div className="policy-panel-heading"><div><p className="eyebrow">Source library · {catalog.version}</p><h2>Start with the source.</h2><p>Search the curated reference set by topic or phrase. Read each source in its own context.</p></div><span className="policy-count">{catalog.entries?.length || 0} references</span></div>
        <form className="policy-search-form" onSubmit={(event) => { event.preventDefault(); run('search', () => policyApi.search(query), setSearch); }}>
          <label htmlFor="policy-search">Search sources</label><div><input id="policy-search" value={query} onChange={(e) => setQuery(e.target.value)} maxLength={500} placeholder="e.g. student data, captions, AI feedback" required /><button className="btn btn-primary" disabled={!!busy}>{busy === 'search' ? 'Searching…' : 'Search sources'} <Icon name="arrow" size={16} /></button></div>
        </form>
        <div className="policy-reference-head"><h3>{search ? `Results for “${search.query}”` : 'Reference library'}</h3>{search && <button className="link" onClick={() => setSearch(null)}>Show all sources</button>}</div>
        {(search ? search.results : catalog.entries)?.length ? (search ? search.results : catalog.entries).map((source) => <Source key={source.id} source={source} />) : <p className="policy-empty">No matching sources. Try a broader term or browse the reference library.</p>}
        {catalog.limitations && <p className="policy-audit">Library limits: {Array.isArray(catalog.limitations) ? catalog.limitations.join(' ') : catalog.limitations}</p>}
      </section>}
      {tab === 'review' && <section className="policy-panel" aria-label="Review a question">
        <div className="policy-panel-heading"><div><p className="eyebrow">Structured review</p><h2>Put a question on the table.</h2><p>Describe a policy or classroom practice. The review surfaces topical considerations and related references. If a model provider is configured, your submitted text may be sent to it.</p></div></div>
        <form className="policy-form" onSubmit={(event) => { event.preventDefault(); setReview(null); run('review', () => policyApi.review(text, topics, context), setReview); }}>
          <label htmlFor="policy-text">What would you like to review?</label><textarea id="policy-text" value={text} onChange={(e) => setText(e.target.value)} maxLength={8000} required rows={6} placeholder="Describe the practice or question, without personal student information." />
          <label htmlFor="policy-context">Context <span>optional</span></label><input id="policy-context" value={context} onChange={(e) => setContext(e.target.value)} maxLength={1000} placeholder="e.g. a university teaching assistant" />
          <fieldset><legend>Focus areas <span>optional · leave empty to identify topics from the text</span></legend><div className="policy-checks">{TOPICS.map(([id, label]) => <label key={id}><input type="checkbox" checked={topics.includes(id)} onChange={() => toggle(topics, setTopics, id)} /> {label}</label>)}</div></fieldset>
          <button className="btn btn-primary" disabled={!!busy}>{busy === 'review' ? 'Reviewing…' : 'Review question'} <Icon name="arrow" size={16} /></button>
        </form><ReviewResult result={review} />
      </section>}
      {tab === 'scenario' && <section className="policy-panel" aria-label="Practice a scenario">
        <div className="policy-panel-heading"><div><p className="eyebrow">Staged exercise</p><h2>Practice with a changing picture.</h2><p>Choose a role, reveal one stage at a time, and record your judgment. Only facts visible to that role are sent for review.</p></div></div>
        <div className="policy-alert policy-alert-subtle">{scenarios.disclaimer} Exercises and decisions are temporary and stored in server memory.</div>
        <div className="policy-role"><label htmlFor="policy-role">View as</label><select id="policy-role" value={role} disabled={!!busy} onChange={(e) => changeRole(e.target.value)}>{ROLES.map(([id, label]) => <option value={id} key={id}>{label}</option>)}</select></div>
        {!exercise ? <div className="policy-scenarios">{(scenarios.scenarios || []).map((scenario) => <article key={scenario.id}><div><p className="policy-topic">{scenario.stage_count} stages</p><h3>{scenario.title}</h3><p>{scenario.summary}</p></div><button className="btn btn-ghost" disabled={!!busy} onClick={() => { invalidateScenario(); run('exercise', () => policyApi.startExercise(scenario.id, role), setExercise); }}>{busy === 'exercise' ? 'Starting…' : 'Start scenario'} <Icon name="arrow" size={16} /></button></article>)}</div> : <>
          <div className="policy-stage-head"><div><p className="eyebrow">Stage {exercise.current_stage} of {exercise.stage_count}</p><h3>{scenarios.scenarios.find((s) => s.id === exercise.scenario_id)?.title || 'Scenario'}</h3></div><button className="link" disabled={!!busy} onClick={() => { invalidateScenario(); setExercise(null); }}>Choose another scenario</button></div>
          <p className="policy-fact-hint">Select released facts to review or cite in your decision.</p>
          {exercise.released_stages.map((stage) => <div className="policy-stage" key={stage.stage}><h4><span>{String(stage.stage).padStart(2, '0')}</span> {stage.title}</h4>{stage.facts.map((fact) => <label className="policy-fact" key={fact.id}><input type="checkbox" checked={selectedFacts.includes(fact.id)} onChange={() => { epoch.current += 1; setScenarioReview(null); toggle(selectedFacts, setSelectedFacts, fact.id); }} /><span>{fact.text}</span></label>)}</div>)}
          <div className="policy-actions"><button className="btn btn-ghost" disabled={!!busy || !selectedFacts.length} onClick={() => { const current = epoch.current; setScenarioReview(null); run('scenario-review', () => policyApi.review(selectedText), (data) => { if (current === epoch.current) setScenarioReview(data); }); }}>{busy === 'scenario-review' ? 'Reviewing…' : 'Review selected facts'}</button><button className="btn btn-primary" disabled={!!busy || exercise.current_stage >= exercise.stage_count} onClick={() => { invalidateScenario(); run('advance', () => policyApi.advance(exercise.exercise_id, role), setExercise); }}>{busy === 'advance' ? 'Revealing…' : exercise.current_stage >= exercise.stage_count ? 'Final stage reached' : 'Reveal next stage'} <Icon name="arrow" size={16} /></button></div>
          <ReviewResult result={scenarioReview} />
          <form className="policy-form policy-decision" onSubmit={(event) => { event.preventDefault(); run('decision', () => policyApi.decide(exercise.exercise_id, role, decision, selectedFacts), () => { setDecision(''); setAudit(null); setDecisionSaved(true); }); }}><label htmlFor="policy-decision">Record your decision</label><textarea id="policy-decision" rows={3} maxLength={500} value={decision} onChange={(e) => setDecision(e.target.value)} required placeholder="What would you do next, and why?" /><p className="policy-fact-hint">Selected facts are attached as references. Your decision is recorded for this exercise.</p><button className="btn btn-ghost" disabled={!!busy}>{busy === 'decision' ? 'Recording…' : 'Record decision'}</button>{decisionSaved && <p role="status">Decision recorded.</p>}</form>
          <div className="policy-audit-block"><button className="link" disabled={!!busy} onClick={() => run('audit', () => policyApi.audit(exercise.exercise_id, role), setAudit)}>View role activity</button>{audit && <div aria-live="polite"><h4>Role activity</h4>{audit.events?.length ? audit.events.map((event, i) => <p key={i}><strong>{event.type === 'decision' ? 'Decision' : event.type}</strong> · Stage {event.stage}{event.decision && ` — ${event.decision}`}{event.source_ids?.length ? ` (facts: ${event.source_ids.join(', ')})` : ''}</p>) : <p>No activity recorded yet.</p>}</div>}</div>
        </>}
      </section>}
    </>}
  </main>;
}
