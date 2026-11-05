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
    <div className="policy-source-meta"><span>{source.document_type}</span><span>{source.jurisdiction}</span>{source.institution === 'uaeu' && <span className="policy-institution-badge">UAEU example</span>}</div>
    <h4><a href={source.url} target="_blank" rel="noreferrer">{source.title} <span aria-label="opens in a new tab">↗</span></a></h4>
    <p className="policy-source-author">{source.authority}{source.source_locator ? ` · ${source.source_locator}` : ''}</p>
    {source.summary && <p>{source.summary}</p>}
    {source.scope && <p><strong>Scope:</strong> {source.scope}</p>}
    {source.limitations && <p><strong>Limits:</strong> {Array.isArray(source.limitations) ? source.limitations.join(' ') : source.limitations}</p>}
    {source.reuse_note && <p><strong>Use and reuse:</strong> {source.reuse_note}</p>}
    {source.verification && <p><strong>Verification:</strong> {source.verification}</p>}
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
      {!!item.citations?.length && <ul className="policy-citations" aria-label={`${topicLabel(item.topic)} sources`}>{item.citations.map((source) => <li key={source.id}><a href={source.url} target="_blank" rel="noreferrer">{source.title} <span aria-label="opens in a new tab">↗</span></a><span>{source.jurisdiction} · {source.document_type}{source.institution === 'uaeu' && ' · UAEU example'}</span></li>)}</ul>}
    </div>)}
    {!!references.length && <div className="policy-references"><h4>References</h4><p>Check each source’s scope and limits before applying it.</p>{references.map((source) => <Source key={source.id} source={source} />)}</div>}
    {!!result.gaps?.length && <div className="policy-notes"><h4>Gaps to resolve</h4><ul>{result.gaps.map((gap, i) => <li key={i}>{gap}</li>)}</ul></div>}
    {!!result.limitations?.length && <div className="policy-notes"><h4>Review limits</h4><ul>{result.limitations.map((limit, i) => <li key={i}>{limit}</li>)}</ul></div>}
    {result.audit && <details className="policy-audit"><summary>Review details</summary><p>Corpus {result.audit.corpus_version} · {result.audit.retrieval} · {result.audit.selection_mode} · Sources: {(result.audit.source_ids || []).join(', ') || 'none'}</p></details>}
  </section>;
}

const humanLabel = (value) => (value || '').replaceAll('_', ' ');
const roleName = (role) => ROLES.find(([id]) => id === role)?.[1] || role;

export function CoordinationResult({ result }) {
  if (!result) return null;
  const actions = new Map((result.plan || []).map((item) => [item.action_id, item.text]));
  return <section className="policy-coordination-result" aria-label="Facilitator coordination result" aria-live="polite">
    <div className="policy-result-head"><div><p className="eyebrow">Facilitator view · stage {result.stage}</p><h3>Proposals and handoffs</h3></div><span className="policy-tag">{result.review_mode === 'model_assisted' ? 'Model-assisted' : result.review_mode === 'offline_test' ? 'Offline test' : humanLabel(result.review_mode) || 'Mode unavailable'}</span></div>
    <p>Reference collection: {result.institution === 'uaeu' ? 'UAEU example + general references' : 'General university context'}. These are proposals for human review.</p>
    {(result.model || result.corpus_version || result.protocol_version) && <details className="policy-audit"><summary>Model and reference details</summary><p>{[result.model && [result.model.provider, result.model.model].filter(Boolean).join(' / '), result.corpus_version && `Corpus ${result.corpus_version}`, result.protocol_version && `Protocol ${result.protocol_version}`].filter(Boolean).join(' · ')}</p></details>}
    <div className="policy-coordination-roles">{(result.roles || []).map((item) => <article className="policy-coordination-role" key={item.role}><h4>{roleName(item.role)} <span className="policy-topic">{humanLabel(item.status)}</span></h4>
      {item.status === 'partial' ? <p>Some items could not be used; the remaining items are shown.</p> : item.reason && <p>Reason: {humanLabel(item.reason)}</p>}
      {!!item.proposals?.length && <><h5>Proposals</h5><ul>{item.proposals.map((proposal) => <li key={proposal.action_id}>{proposal.text}{proposal.rationale && <p className="policy-rationale"><strong>{result.review_mode === 'model_assisted' ? 'Stated rationale · model-written, not verified' : 'Stated rationale · scripted offline example'}</strong><br />{proposal.rationale}</p>}</li>)}</ul></>}
      {!!item.questions?.length && <><h5>Questions</h5><ul>{item.questions.map((question, index) => <li key={question.question_id || index}>{question.text}</li>)}</ul></>}
      {(item.proposals?.length > 0 || item.evidence?.length > 0 || item.prompt_sha256) && <details className="policy-audit"><summary>Sources and details</summary>
        {!!item.proposals?.length && <p>Check whether each selected source supports the proposal in this context.</p>}
        {(item.proposals || []).map((proposal) => <p key={proposal.action_id}><strong>{proposal.text}</strong><br />Facts: {(proposal.fact_ids || []).join(', ')} · Sources: {(proposal.source_ids || []).join(', ')}</p>)}
        <ul>{(item.evidence || []).filter((source) => (item.proposals || []).some((proposal) => (proposal.source_ids || []).includes(source.id))).map((source) => <li key={source.id}><a href={source.url} target="_blank" rel="noreferrer">{source.title} <span aria-label="opens in a new tab">↗</span></a><span className="policy-evidence">{[source.authority, source.jurisdiction, source.document_type, source.source_locator].filter(Boolean).join(' · ')}{source.summary && ` · Summary: ${source.summary}`}{source.scope && ` · Scope: ${source.scope}`}{source.verification && ` · Verification: ${source.verification}`}{source.limitations && ` · Limits: ${Array.isArray(source.limitations) ? source.limitations.join(' ') : source.limitations}`}</span></li>)}</ul>
        {item.prompt_sha256 && <p>Prompt digest: {item.prompt_sha256}</p>}
      </details>}
      {item.status === 'completed' && !item.proposals?.length && <p>No action proposed.</p>}
    </article>)}</div>
    <div className="policy-coordination-plan"><h4>Conditional plan</h4>{result.plan?.length ? <ol>{result.plan.map((item) => <li key={item.action_id}><strong>{item.text}</strong><p>Owner: {roleName(item.owner)} · {humanLabel(item.status)}</p>{!!item.depends_on?.length && <p>Depends on: {item.depends_on.map((id) => actions.get(id) || humanLabel(id)).join('; ')}</p>}{!!item.handoffs?.length && <p>Handoffs: {item.handoffs.map((handoff) => `${roleName(handoff.owner)} — ${actions.get(handoff.action_id) || humanLabel(handoff.action_id)}`).join('; ')}</p>}</li>)}</ol> : <p>No plan was proposed.</p>}</div>
    {!!result.unresolved?.length && <div className="policy-notes"><h4>Unresolved</h4><ul>{result.unresolved.map((item, index) => <li key={index}>{item}</li>)}</ul></div>}
    {!!result.limitations?.length && <details className="policy-audit"><summary>Review limits</summary><ul>{result.limitations.map((item, index) => <li key={index}>{item}</li>)}</ul></details>}
  </section>;
}

function GapReference({ source, global = false }) {
  return <li><strong>{source.url ? <a href={source.url} target="_blank" rel="noreferrer">{source.title || source.source_id} ↗</a> : (source.title || source.source_id)}</strong>{source.locator && ` · ${source.locator}`}
    {global ? <><p>{source.addresses}</p><p>Scope: {source.scope} · {source.binding_status}</p></> : <><p><strong>Says:</strong> {source.says}</p><p><strong>Does not say:</strong> {source.does_not_say}</p></>}
  </li>;
}

export function CandidateGaps({ result }) {
  if (!result) return null;
  return <section className="policy-gaps" aria-label="Candidate gaps"><p className="eyebrow">Debrief · {result.label}</p><h3>Candidate gaps</h3><p>These are education-domain questions for further review, not country recommendations.</p>
    {(result.gaps || []).map((gap) => <article className="policy-gap" key={gap.id}><h4>{gap.title}</h4><p className="policy-topic">{humanLabel(gap.gap_type)} · {gap.verification_status}</p><p>{gap.operational_gap}</p>
      <h5>Reviewed UAE sources</h5><ul>{(gap.uae_sources || []).map((source, i) => <GapReference key={`${source.source_id}-${i}`} source={source} />)}</ul>
      <h5>Global examples and scope</h5><ul>{(gap.global_examples || []).map((source, i) => <GapReference key={`${source.source_id}-${i}`} source={source} global />)}</ul>
      <h5>Evidence needed</h5><ul>{(gap.evidence_needed || []).map((item, i) => <li key={i}>{item}</li>)}</ul>
    </article>)}
    {!result.gaps?.length && <p>No candidate gaps are available for this scenario.</p>}
  </section>;
}

function saveJson(value, filename) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(value, null, 2)], { type: 'application/json' }));
  const link = document.createElement('a'); link.href = url; link.download = filename; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function AuditTimeline({ timeline, htmlUrl }) {
  if (!timeline) return null;
  return <section className="policy-timeline" aria-label="Exercise audit timeline"><p className="eyebrow">Exercise record</p><h3>Audit timeline</h3>
    <p>Ordered events · Exercise {timeline.exercise_id} · SHA-256: {timeline.sha256 || 'unavailable'}</p>
    <div className="policy-actions"><button className="btn btn-ghost" onClick={() => saveJson(timeline, `policy-timeline-${timeline.exercise_id}.json`)}>Export JSON</button>{htmlUrl && <a className="btn btn-ghost" href={htmlUrl} download>Export HTML</a>}</div>
    <ol>{(timeline.events || []).map((event, i) => <li className="policy-timeline-event" key={i}><strong>{humanLabel(event.type)}</strong>{event.stage != null && ` · Stage ${event.stage}`}{event.role && ` · ${roleName(event.role)}`}{event.at && ` · ${event.at}`}
      {event.type === 'stage_release' && <p>Released fact IDs by role: {Object.entries(event.fact_ids_by_role || {}).map(([role, ids]) => `${roleName(role)}: ${ids.join(', ') || 'none'}`).join(' · ')}</p>}
      {event.type === 'model_request' && <><p>Provider / model: {[event.provider, event.model].filter(Boolean).join(' / ') || 'unavailable'} · Status: {humanLabel(event.status)} · Latency: {event.latency_ms == null ? 'unavailable' : `${event.latency_ms} ms`}</p><p>Prompt digest: {event.prompt_sha256 || 'unavailable'} · Usage: {event.usage ? JSON.stringify(event.usage) : 'unavailable'} · Prompt attempted: {String(event.prompt_attempted)}</p></>}
      {event.type === 'validation' && <p>Status: {humanLabel(event.status)}{event.issue && ` · Issue: ${humanLabel(event.issue)}`}{event.rationale_issues?.length ? ` · Rationale issues: ${event.rationale_issues.join(', ')}` : ''}</p>}
      {event.type === 'coordinator_plan' && <><ul>{(event.plan || []).map((item, index) => <li key={index}>{item.text || item.action_id} · Owner: {roleName(item.owner)} · {humanLabel(item.status)}{item.handoffs?.length ? ` · Handoffs: ${item.handoffs.map((h) => `${roleName(h.owner)}: ${h.action_id}`).join(', ')}` : ''}</li>)}</ul>{!!event.unresolved?.length && <p>Unresolved: {event.unresolved.join('; ')}</p>}</>}
      {event.type === 'decision' && <p>{event.decision} · Evidence: {(event.source_ids || []).join(', ') || 'none'} · Mode: {humanLabel(event.review_mode)}</p>}
    </li>)}</ol>
  </section>;
}

export function ReplayContent({ replay, gaps }) {
  return <><div className="policy-replay-banner" role="status">{replay.banner}</div><p className="policy-fact-hint">Read-only exercise record · {replay.recording.scenario_id}</p>
    {(replay.recording.rounds || []).map((round, i) => <CoordinationResult key={round.round_id || i} result={round} />)}
    <AuditTimeline timeline={replay.recording} htmlUrl={policyApi.replayHtmlUrl()} /><CandidateGaps result={gaps} />
  </>;
}

function ReplayLab({ onBack }) {
  const [replay, setReplay] = useState(null);
  const [gaps, setGaps] = useState(null);
  const [error, setError] = useState('');
  useEffect(() => {
    let active = true;
    policyApi.replay().then(async (data) => {
      if (!active) return;
      setReplay(data);
      try { const result = await policyApi.gaps(data.recording.scenario_id); if (active) setGaps(result); }
      catch (err) { if (active) setError(`Candidate gaps unavailable: ${err.message}`); }
    }).catch((err) => { if (active) setError(`Recorded run unavailable: ${err.message}`); });
    return () => { active = false; };
  }, []);
  return <main className="wrap policy-lab"><button className="link-back" onClick={onBack}><Icon name="prev" size={16} /> Modes</button><header className="policy-intro"><div><p className="eyebrow">Policy Lab</p><h1>Recorded exercise<span>.</span></h1><p>Inspect the saved model outputs and decisions.</p></div></header>
    {error && <div className="policy-alert" role="alert">{error}</div>}{!replay && !error && <p role="status">Loading recorded exercise…</p>}{replay && <ReplayContent replay={replay} gaps={gaps} />}
  </main>;
}

export default function PolicyLab(props) {
  return import.meta.env.VITE_POLICY_REPLAY === '1' ? <ReplayLab {...props} /> : <InteractivePolicyLab {...props} />;
}

function InteractivePolicyLab({ onBack }) {
  const [tab, setTab] = useState('search');
  const [institution, setInstitution] = useState('general');
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
  const [coordinationStatus, setCoordinationStatus] = useState(null);
  const [coordinationInstitution, setCoordinationInstitution] = useState('general');
  const [coordination, setCoordination] = useState(null);
  const [decision, setDecision] = useState('');
  const [audit, setAudit] = useState(null);
  const [timeline, setTimeline] = useState(null);
  const [gaps, setGaps] = useState(null);
  const [gapsError, setGapsError] = useState('');
  const [decisionSaved, setDecisionSaved] = useState(false);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const epoch = useRef(0);
  const scopeEpoch = useRef(0);
  const coordinationEpoch = useRef(0);

  useEffect(() => {
    let active = true;
    policyApi.coordinationStatus().then((status) => { if (active) setCoordinationStatus(status); })
      .catch(() => { if (active) setCoordinationStatus({ enabled: false, unavailable: true }); });
    return () => { active = false; };
  }, []);
  useEffect(() => {
    let active = true;
    policyApi.scenarios().then((cases) => { if (active) setScenarios(cases); })
      .catch((err) => { if (active) setInitialError(err.message); });
    return () => { active = false; };
  }, []);
  useEffect(() => {
    let active = true;
    const current = scopeEpoch.current;
    policyApi.sources(institution).then((sources) => { if (active && current === scopeEpoch.current) setCatalog(sources); })
      .catch((err) => { if (active && current === scopeEpoch.current) setInitialError(err.message); });
    return () => { active = false; };
  }, [institution]);

  useEffect(() => {
    let active = true;
    setGaps(null); setGapsError('');
    if (exercise && exercise.current_stage >= exercise.stage_count) {
      policyApi.gaps(exercise.scenario_id).then((data) => { if (active) setGaps(data); })
        .catch((err) => { if (active) setGapsError(err.message); });
    }
    return () => { active = false; };
  }, [exercise?.exercise_id, exercise?.scenario_id, exercise?.current_stage, exercise?.stage_count]);

  async function run(key, fn, success, isCurrent = () => true) {
    setBusy(key); setError('');
    try { const data = await fn(); if (isCurrent()) success(data); } catch (err) { if (isCurrent()) setError(err.message); } finally { setBusy(''); }
  }
  function changeInstitution(next) {
    scopeEpoch.current += 1;
    setSearch(null); setReview(null); setCatalog(null); setError(''); setInitialError('');
    setInstitution(next);
  }
  function invalidateScenario() {
    epoch.current += 1; coordinationEpoch.current += 1; setSelectedFacts([]); setScenarioReview(null); setCoordination(null); setDecision(''); setAudit(null); setTimeline(null); setDecisionSaved(false);
  }
  function changeRole(next) {
    invalidateScenario(); setRole(next); setError('');
    if (exercise) { setExercise(null); run('exercise', () => policyApi.exercise(exercise.exercise_id, next), setExercise); }
  }
  function viewCoordination() {
    const current = coordinationEpoch.current;
    setCoordination(null); setTimeline(null);
    run('coordinate', () => policyApi.coordinate(exercise.exercise_id, exercise.current_stage, coordinationInstitution), setCoordination, () => current === coordinationEpoch.current);
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
      {tab !== 'scenario' && <div className="policy-scope"><label htmlFor="policy-institution">Reference collection</label><select id="policy-institution" value={institution} onChange={(event) => changeInstitution(event.target.value)}><option value="general">General university context</option><option value="uaeu">UAEU example + general references</option></select><p>Choose which sources to search and review. UAEU documents are institutional examples; inclusion does not establish affiliation or applicability. Check your institution’s current rules.</p></div>}
      {tab === 'search' && <section className="policy-panel" aria-label="Find sources">
        <div className="policy-panel-heading"><div><p className="eyebrow">Source library · {catalog.version}</p><h2>Start with the source.</h2><p>Search the curated reference set by topic or phrase. Read each source in its own context.</p></div><span className="policy-count">{catalog.entries?.length || 0} references</span></div>
        <form className="policy-search-form" onSubmit={(event) => { event.preventDefault(); const current = scopeEpoch.current; run('search', () => policyApi.search(query, 10, institution), setSearch, () => current === scopeEpoch.current); }}>
          <label htmlFor="policy-search">Search sources</label><div><input id="policy-search" value={query} onChange={(e) => setQuery(e.target.value)} maxLength={500} placeholder="e.g. student data, captions, AI feedback" required /><button className="btn btn-primary" disabled={!!busy}>{busy === 'search' ? 'Searching…' : 'Search sources'} <Icon name="arrow" size={16} /></button></div>
        </form>
        {search?.retrieval_mode && <p className="policy-fact-hint">Retrieval: {search.retrieval_mode === 'hybrid' ? 'Hybrid · lexical + local vectors' : 'Lexical'}</p>}
        <div className="policy-reference-head"><h3>{search ? `Results for “${search.query}”` : 'Reference library'}</h3>{search && <button className="link" onClick={() => setSearch(null)}>Show all sources</button>}</div>
        {(search ? search.results : catalog.entries)?.length ? (search ? search.results : catalog.entries).map((source) => <Source key={source.id} source={source} />) : <p className="policy-empty">No matching sources. Try a broader term or browse the reference library.</p>}
        {catalog.limitations && <p className="policy-audit">Library limits: {Array.isArray(catalog.limitations) ? catalog.limitations.join(' ') : catalog.limitations}</p>}
      </section>}
      {tab === 'review' && <section className="policy-panel" aria-label="Review a question">
        <div className="policy-panel-heading"><div><p className="eyebrow">Structured review</p><h2>Put a question on the table.</h2><p>Describe a policy or classroom practice. The review surfaces topical considerations and related references. If a model provider is configured, your submitted text may be sent to it.</p></div></div>
        <form className="policy-form" onSubmit={(event) => { event.preventDefault(); const current = scopeEpoch.current; setReview(null); run('review', () => policyApi.review(text, topics, context, institution), setReview, () => current === scopeEpoch.current); }}>
          <label htmlFor="policy-text">What would you like to review?</label><textarea id="policy-text" value={text} onChange={(e) => setText(e.target.value)} maxLength={8000} required rows={6} placeholder="Describe the practice or question, without personal student information." />
          <label htmlFor="policy-context">Context <span>optional</span></label><input id="policy-context" value={context} onChange={(e) => setContext(e.target.value)} maxLength={1000} placeholder="e.g. a university teaching assistant" />
          <fieldset><legend>Focus areas <span>optional · leave empty to identify topics from the text</span></legend><div className="policy-checks">{TOPICS.map(([id, label]) => <label key={id}><input type="checkbox" checked={topics.includes(id)} onChange={() => toggle(topics, setTopics, id)} /> {label}</label>)}</div></fieldset>
          <button className="btn btn-primary" disabled={!!busy}>{busy === 'review' ? 'Reviewing…' : 'Review question'} <Icon name="arrow" size={16} /></button>
        </form><ReviewResult result={review} />
      </section>}
      {tab === 'scenario' && <section className="policy-panel" aria-label="Practice a scenario">
        <div className="policy-panel-heading"><div><p className="eyebrow">Staged exercise</p><h2>Practice with a changing picture.</h2><p>Choose a role, reveal one stage at a time, and record your judgment. Only facts visible to that role are sent for review. Scenario reviews use the general reference collection.</p></div></div>
        <div className="policy-alert policy-alert-subtle">{scenarios.disclaimer} Exercises and decisions are temporary and stored in server memory.</div>
        <div className="policy-role"><label htmlFor="policy-role">View as</label><select id="policy-role" value={role} disabled={!!busy} onChange={(e) => changeRole(e.target.value)}>{ROLES.map(([id, label]) => <option value={id} key={id}>{label}</option>)}</select></div>
        {!exercise ? <div className="policy-scenarios">{(scenarios.scenarios || []).map((scenario) => <article key={scenario.id}><div><p className="policy-topic">{scenario.stage_count} stages</p><h3>{scenario.title}</h3><p>{scenario.summary}</p></div><button className="btn btn-ghost" disabled={!!busy} onClick={() => { invalidateScenario(); run('exercise', () => policyApi.startExercise(scenario.id, role), setExercise); }}>{busy === 'exercise' ? 'Starting…' : 'Start scenario'} <Icon name="arrow" size={16} /></button></article>)}</div> : <>
          <div className="policy-stage-head"><div><p className="eyebrow">Stage {exercise.current_stage} of {exercise.stage_count}</p><h3>{scenarios.scenarios.find((s) => s.id === exercise.scenario_id)?.title || 'Scenario'}</h3></div><div className="policy-stage-controls"><button className="link" disabled={!!busy} onClick={() => run('refresh', () => policyApi.exercise(exercise.exercise_id, role), (data) => { invalidateScenario(); setExercise(data); })}>{busy === 'refresh' ? 'Refreshing…' : 'Refresh exercise'}</button><button className="link" disabled={!!busy} onClick={() => { invalidateScenario(); setExercise(null); }}>Choose another scenario</button></div></div>
          <p className="policy-fact-hint">Select released facts to review or cite in your decision.</p>
          {exercise.released_stages.map((stage) => <div className="policy-stage" key={stage.stage}><h4><span>{String(stage.stage).padStart(2, '0')}</span> {stage.title}</h4>{stage.facts.map((fact) => <label className="policy-fact" key={fact.id}><input type="checkbox" checked={selectedFacts.includes(fact.id)} onChange={() => { epoch.current += 1; setScenarioReview(null); toggle(selectedFacts, setSelectedFacts, fact.id); }} /><span>{fact.text}</span></label>)}</div>)}
          <div className="policy-actions"><button className="btn btn-ghost" disabled={!!busy || !selectedFacts.length} onClick={() => { const current = epoch.current; setScenarioReview(null); run('scenario-review', () => policyApi.review(selectedText, [], '', 'general'), (data) => { if (current === epoch.current) setScenarioReview(data); }); }}>{busy === 'scenario-review' ? 'Reviewing…' : 'Review selected facts'}</button><button className="btn btn-primary" disabled={!!busy || exercise.current_stage >= exercise.stage_count} onClick={() => { const stage = exercise.current_stage; run('advance', () => policyApi.advance(exercise.exercise_id, role, stage), (data) => { invalidateScenario(); setExercise(data); }); }}>{busy === 'advance' ? 'Revealing…' : exercise.current_stage >= exercise.stage_count ? 'Final stage reached' : 'Reveal next stage'} <Icon name="arrow" size={16} /></button></div>
          <ReviewResult result={scenarioReview} />
          <section className="policy-coordination" aria-labelledby="policy-coordination-heading"><p className="eyebrow">Facilitator view</p><h3 id="policy-coordination-heading">Coordinate the roles</h3><p>This view combines the released teacher, privacy and accessibility perspectives for human review.</p>
            <p className="policy-fact-hint">{coordinationStatus?.enabled && coordinationStatus.review_mode === 'offline_test' ? 'Scripted offline proposals use released synthetic facts; no model provider is called. Saved views are reused.' : 'New proposals use the configured model with released synthetic facts; saved views are reused.'}</p>
            {coordinationStatus && !coordinationStatus.enabled && !coordinationStatus.unavailable && <p className="policy-fact-hint">New generation is off; saved proposals can still be opened.</p>}
              <div className="policy-role"><label htmlFor="coordination-institution">Reference collection</label><select id="coordination-institution" value={coordinationInstitution} disabled={!!busy} onChange={(event) => { coordinationEpoch.current += 1; setCoordinationInstitution(event.target.value); setCoordination(null); }}><option value="general">General university context</option><option value="uaeu">UAEU example + general references</option></select></div>
              <p className="policy-fact-hint">UAEU references are examples; selection does not establish affiliation or applicability.</p>
              <div className="policy-actions"><button className="btn btn-ghost" disabled={!!busy} onClick={viewCoordination}>{busy === 'coordinate' ? 'Loading proposals…' : 'View role proposals'}</button></div>
              <CoordinationResult result={coordination} />
          </section>
          {exercise.current_stage >= exercise.stage_count && <>{gapsError && <p className="policy-alert" role="alert">Candidate gaps unavailable: {gapsError}</p>}<CandidateGaps result={gaps} /></>}
          <form className="policy-form policy-decision" onSubmit={(event) => { event.preventDefault(); if (!selectedFacts.length) return; const stage = exercise.current_stage; run('decision', () => policyApi.decide(exercise.exercise_id, role, decision, selectedFacts, stage), () => { setDecision(''); setAudit(null); setTimeline(null); setDecisionSaved(true); }); }}><label htmlFor="policy-decision">Record your decision</label><textarea id="policy-decision" rows={3} maxLength={500} value={decision} onChange={(e) => setDecision(e.target.value)} required placeholder="What would you do next, and why?" /><p className="policy-fact-hint">Select at least one released fact above. Selected facts are attached as references to your decision.</p><button className="btn btn-ghost" disabled={!!busy || !selectedFacts.length}>{busy === 'decision' ? 'Recording…' : 'Record decision'}</button>{decisionSaved && <p role="status">Decision recorded.</p>}</form>
          <div className="policy-actions"><button className="btn btn-ghost" disabled={!!busy} onClick={() => run('timeline', () => policyApi.timeline(exercise.exercise_id), setTimeline)}>{busy === 'timeline' ? 'Loading timeline…' : 'View audit timeline'}</button></div>
          <AuditTimeline timeline={timeline} htmlUrl={policyApi.timelineHtmlUrl(exercise.exercise_id)} />
          <div className="policy-audit-block"><button className="link" disabled={!!busy} onClick={() => run('audit', () => policyApi.audit(exercise.exercise_id, role), setAudit)}>View role activity</button>{audit && <div aria-live="polite"><h4>Role activity</h4>{audit.events?.length ? audit.events.map((event, i) => <p key={i}><strong>{event.type === 'decision' ? 'Decision' : event.type}</strong> · Stage {event.stage}{event.decision && ` — ${event.decision}`}{event.source_ids?.length ? ` (facts: ${event.source_ids.join(', ')})` : ''}</p>) : <p>No activity recorded yet.</p>}</div>}</div>
        </>}
      </section>}
    </>}
  </main>;
}
