import { useEffect, useState } from 'react';
import Avatar from '../components/Avatar.jsx';
import Icon from '../components/Icon.jsx';
import { CHECKLISTS, MODES, isPanel, personaById, seriousnessLabel } from '../data.js';

const HERO_BEATS = [
  { id: 'alex', state: 'raise_hand', text: 'Sorry, what is a "network" here?' },
  { id: 'alex', state: 'nodding', text: 'Oh, so it is a function with knobs.' },
  { id: 'maya', state: 'speaking', text: 'Lower loss always means better? What about overfitting?' },
  { id: 'sam', state: 'distracted', text: '*scrolling on phone*' },
  { id: 'priya', state: 'speaking', text: 'A derivative is a local rate, not a fixed ratio.' },
  { id: 'jordan', state: 'nodding', text: 'The gears picture really works.' },
];
const HERO_SEATS = ['alex', 'maya', 'sam', 'priya', 'jordan'];

function HeroRoom({ roster }) {
  const [beat, setBeat] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setBeat((b) => (b + 1) % HERO_BEATS.length), 2800);
    return () => clearInterval(t);
  }, []);
  const b = HERO_BEATS[beat];
  return (
    <div className="hero-room" aria-label="Animated preview of a YapLab classroom">
      <div className="hero-board">
        <span className="chalk-label">Slide 3 / 5 · simulated preview</span>
        <h3>The chain rule as gears</h3>
        <svg viewBox="0 0 240 70" className="gears" aria-hidden="true">
          <g className="gear g1"><circle cx="40" cy="35" r="22" /><circle cx="40" cy="35" r="5" /></g>
          <g className="gear g2"><circle cx="100" cy="35" r="14" /><circle cx="100" cy="35" r="4" /></g>
          <g className="gear g3"><circle cx="146" cy="35" r="18" /><circle cx="146" cy="35" r="4.5" /></g>
          <path d="M178 35h44m-8-6 8 6-8 6" />
        </svg>
        <div className="hero-wave" aria-hidden="true">
          {Array.from({ length: 28 }).map((_, i) => <i key={i} style={{ animationDelay: `${(i % 7) * 0.11}s` }} />)}
        </div>
      </div>
      <div className="hero-seats">
        {HERO_SEATS.map((id, i) => {
          const p = personaById(id, roster);
          const active = b.id === id;
          return (
            <div key={id} className={`hseat ${active ? 'active' : ''}`}>
              {active && b.text && <div className={`bubble bubble-sm ${b.text.startsWith('*') ? 'bubble-noise' : ''}`}>{b.text.replace(/\*/g, '')}</div>}
              {active && b.state === 'raise_hand' && <span className="hand-badge"><Icon name="hand" size={14} /></span>}
              <Avatar p={p} size={58} state={active ? b.state : 'listening'} delay={i * 0.7} />
              <span className="hseat-name">{p.name}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

const CTA = { teaching: 'Start teaching', pitch: 'Open scripted preview', interview: 'Coming soon' };
const modeStatus = (id) => id === 'pitch' ? ' · Scripted preview' : id === 'interview' ? ' · Coming soon' : '';

function ModeCard({ m, roster, onStart, onSample }) {
  const audience = [...new Set(m.variants.flatMap((v) => v.agents))].map((id) => personaById(id, roster)).filter(Boolean);
  const cl = CHECKLISTS[m.checklist];
  return (
    <article className={`mode-card mode-${m.id}`}>
      <header className="mc-head">
        <span className="mc-icon"><Icon name={m.icon} size={22} /></span>
        <div>
          <h3>{m.name}{modeStatus(m.id)}</h3>
          <p className="mc-tag">{m.tagline}</p>
        </div>
      </header>
      <p className="mc-blurb">{m.id === 'pitch' ? 'Explore a scripted pitch rehearsal and simulated report.' : m.id === 'interview' ? 'Interview rehearsal is planned and not yet available.' : 'Practice explaining a lesson to a simulated classroom and review the session.'}</p>
      <div className="mc-audience">
        <div className="stack">{audience.slice(0, 6).map((p, i) => <Avatar key={p.id} p={p} size={32} delay={i} />)}</div>
        <span className="muted">{audience.some(isPanel) ? audience.filter(isPanel).map((p) => p.trait).slice(0, 3).join(', ') : audience.map((p) => p.name).slice(0, 5).join(', ')}</span>
      </div>
      <div className="mc-variants">
        {m.variants.map((v) => (
          <button key={v.id} className="variant" onClick={() => onStart(m.id, v.id)}>
            <span className="v-top"><strong>{v.name}</strong><span className={`stakes stakes-${Math.min(3, Math.floor(v.seriousness / 25))}`}>{seriousnessLabel(v.seriousness)}</span></span>
            <span className="v-blurb">{m.id === 'interview' ? 'Coming soon' : m.id === 'teaching' && v.id === 'study' ? 'A smaller classroom for practice.' : v.blurb}</span>
          </button>
        ))}
      </div>
      <div className="mc-scored">
        <span className="k">Practice focus</span>
        <span>{cl.items.map((it) => it.label).join(' · ')}</span>
      </div>
      <footer className="mc-foot">
        <button className="btn btn-mode" onClick={() => onStart(m.id)}>{CTA[m.id]} <Icon name="arrow" size={16} /></button>
        <button className="link" onClick={() => onSample(m.id)}>{m.id === 'interview' ? 'Coming soon' : 'Simulated sample report'}</button>
      </footer>
    </article>
  );
}

export default function Home({ onStart, onSample, onPolicy, roster, hackathonDemo = false }) {
  return (
    <main className="home">
      <section className="hero wrap">
        <div className="hero-copy">
          <p className="eyebrow">Your first audience, before the real one</p>
          <h1>Rehearse in front of a room that <em>talks back.</em></h1>
          <p className="lede">
            Rehearse a lesson with a simulated classroom and review the session. Pitch is a scripted preview;
            interview practice is coming soon.
          </p>
          {hackathonDemo && <div aria-label="AI for Good demo"><p className="eyebrow">AI for Good · Offline demo</p><p>Rehearse a lesson or explore the policy sandbox.</p><div className="hero-cta"><button className="btn btn-primary" onClick={() => onStart('teaching')}>Start teaching <Icon name="arrow" size={16} /></button><button className="btn btn-ghost" onClick={onPolicy}>Open Policy Lab <Icon name="arrow" size={16} /></button></div></div>}
          <div className="hero-modes">
            {MODES.map((m) => (
              <button key={m.id} className={`hero-mode mode-${m.id}`} onClick={() => onStart(m.id)}>
                <Icon name={m.icon} size={18} />
                <span><strong>{m.name}{modeStatus(m.id)}</strong><span>{m.tagline}</span></span>
                <Icon name="arrow" size={16} />
              </button>
            ))}
          </div>
        </div>
        <HeroRoom roster={roster} />
      </section>

      <section className="wrap section" id="modes">
        <div className="section-head">
          <h2>Three ways to practice</h2>
          <p>Practice teaching, explore the scripted Pitch preview, or see the planned Interview mode.</p>
        </div>
        <div className="mode-grid">
          {MODES.map((m) => <ModeCard key={m.id} m={m} roster={roster} onStart={onStart} onSample={onSample} />)}
        </div>
      </section>

      <section className="wrap section">
        <div className="section-head">
          <h2>How a session works</h2>
        </div>
        <ol className="steps">
          <li>
            <span className="step-n">1</span>
            <h3>Set up the room</h3>
            <p>Choose a teaching setup and use the sample deck or upload slides.</p>
          </li>
          <li>
            <span className="step-n">2</span>
            <h3>Speak out loud</h3>
            <p>Speak when speech is configured, or type to the room. Simulated students can raise questions as you teach.</p>
          </li>
          <li>
            <span className="step-n">3</span>
            <h3>See what landed</h3>
            <p>Review recorded delivery measurements and responses. Sample reports are simulated.</p>
          </li>
        </ol>
      </section>

      <section className="wrap section">
        <div className="section-head">
          <h2>Meet the room</h2>
          <p>Meet the example personas. The configured teaching backend uses its own fixed classroom roster.</p>
        </div>
        {[['Classroom', (p) => p.role === 'student'], ['Pitch preview', (p) => p.role === 'judge'], ['Interview · coming soon', (p) => p.role === 'interviewer']].map(([label, f]) => (
          <div key={label} className="persona-group">
            <h3 className="pg-label">{label}</h3>
            <div className="persona-row">
              {roster.filter(f).map((p, i) => (
                <article key={p.id} className="persona-card">
                  <Avatar p={p} size={50} delay={i * 0.4} />
                  <div>
                    <h4>{p.name}</h4>
                    <span className={`role role-${p.role}`}>{p.trait}{p.optional ? ' · optional' : ''}</span>
                    <p>{p.blurb}</p>
                  </div>
                </article>
              ))}
            </div>
          </div>
        ))}
      </section>

      <section className="wrap policy-home-callout" aria-labelledby="policy-home-title">
        <div><p className="eyebrow">For teachers &amp; TAs</p><h2 id="policy-home-title">Think through the policy, too.</h2><p>Explore cited sources and practice decisions in a staged classroom scenario.</p></div>
        <button className="btn btn-ghost" onClick={onPolicy}>Open Policy Lab <Icon name="arrow" size={16} /></button>
      </section>

      <section className="wrap section listen">
        <div className="section-head">
          <h2>What YapLab listens for</h2>
        </div>
        <div className="listen-grid">
          {[
            ['wave', 'Pace and pauses', 'The teaching report can show overall pace and recorded pauses.'],
            ['type', 'Filler words', 'The teaching report can show a count of detected filler words.'],
            ['check', 'Teaching moves', 'Optional feedback can describe teaching moves in the recorded transcript.'],
            ['users', 'Audience reaction', 'The simulated room can record questions and responses.'],
            ['clock', 'Timing', 'The session report includes teaching duration.'],
            ['cam', 'Gestures and posture', 'Camera is a self-view; gesture and posture analysis is planned.', 'Planned'],
          ].map(([ic, h, p, tag]) => (
            <div key={h} className="listen-item">
              <Icon name={ic} size={20} />
              <div>
                <h3>{h} {tag && <span className="tag">{tag}</span>}</h3>
                <p>{p}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      <footer className="footer wrap">
        <span>YapLab · Hackachusetts 2026 × BU DS+X</span>
        <a className="link" href="#modes">Back to modes</a>
      </footer>
    </main>
  );
}
