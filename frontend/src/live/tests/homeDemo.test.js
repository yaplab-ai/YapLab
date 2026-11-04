import test from 'node:test';
import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { createServer } from 'vite';

// Render actual components rather than exercising a parallel copy of the copy.
test('offline demo entry and feature labels match available paths', async () => {
  const server = await createServer({ root: fileURLToPath(new URL('../../../', import.meta.url)), server: { middlewareMode: true, hmr: false }, appType: 'custom', logLevel: 'error' });
  try {
    const { default: Home } = await server.ssrLoadModule('/src/screens/Home.jsx');
    const { ModeIndicator, makeSessionConfig } = await server.ssrLoadModule('/src/App.jsx');
    const { PERSONAS } = await server.ssrLoadModule('/src/data.js');
    const render = (hackathonDemo) => renderToStaticMarkup(createElement(Home, { roster: PERSONAS, hackathonDemo, onStart() {}, onSample() {}, onPolicy() {} }));
    const demo = render(true);
    assert.match(demo, /AI for Good · Offline demo/);
    assert.match(demo, /Start teaching/);
    assert.match(demo, /Open Policy Lab/);
    assert.match(demo, /Pitch(?:<!-- -->)? · Scripted preview/);
    assert.match(demo, /Interview(?:<!-- -->)? · Coming soon/);
    assert.match(demo, /Camera is a self-view; gesture and posture analysis is planned/);
    assert.doesNotMatch(render(false), /AI for Good · Offline demo/);
    const status = renderToStaticMarkup(createElement(ModeIndicator, { hackathonDemo: true, view: 'setup', headerLive: true }));
    assert.match(status, /Offline demo/);
    assert.doesNotMatch(status, /Backend live/);
    const normal = renderToStaticMarkup(createElement(ModeIndicator, { hackathonDemo: false, view: 'setup', headerLive: true }));
    assert.match(normal, /Backend live/);
    const { default: Session } = await server.ssrLoadModule('/src/screens/Session.jsx');
    const { defaultConfig } = await server.ssrLoadModule('/src/lib/config.js');
    const demoConfig = makeSessionConfig('teaching', undefined, PERSONAS, true);
    const pitchConfig = makeSessionConfig('pitch', undefined, PERSONAS, true);
    const normalConfig = makeSessionConfig('teaching', undefined, PERSONAS, false);
    assert.equal(demoConfig.camera, false);
    assert.equal(demoConfig.voices, false);
    assert.equal(pitchConfig.camera, false);
    assert.equal(pitchConfig.voices, false);
    assert.equal(normalConfig.camera, true);
    assert.equal(normalConfig.voices, true);
    const { default: Setup } = await server.ssrLoadModule('/src/screens/Setup.jsx');
    const setup = renderToStaticMarkup(createElement(Setup, { config: demoConfig, roster: PERSONAS, hackathonDemo: true, setConfig() {}, setRoster() {}, onStart() {}, onBack() {} }));
    assert.match(setup, /Use the demo deck and typed input; microphone and camera are optional/);
    assert.match(setup, /Off by default; browser speech may be used/);
    assert.doesNotMatch(setup, /Your browser will ask for microphone and camera access/);
    const ordinarySetup = renderToStaticMarkup(createElement(Setup, { config: normalConfig, roster: PERSONAS, setConfig() {}, setRoster() {}, onStart() {}, onBack() {} }));
    assert.match(ordinarySetup, /Your browser will ask for microphone and camera access/);
    const room = renderToStaticMarkup(createElement(Session, { config: defaultConfig('teaching'), hackathonDemo: true, onExit() {}, onEnd() {} }));
    assert.match(room, /Offline demo/);
    const { default: LiveReport } = await server.ssrLoadModule('/src/live/LiveReport.jsx');
    const report = renderToStaticMarkup(createElement(LiveReport, { report: {}, hackathonDemo: true }));
    assert.match(report, /timing comes from typed input and room responses are scripted/);
    assert.match(report, /do not measure speaking ability or learning/);
  } finally { await server.close(); }
});
