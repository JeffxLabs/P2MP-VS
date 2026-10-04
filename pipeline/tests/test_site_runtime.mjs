#!/usr/bin/env node
/** Dependency-free runtime regressions. The DOM stub checks generated content,
 * state and handlers; browser layout/accessibility require separate visual QA.
 * Synthetic weeks exist only in memory, never under generated data/weeks/.
 */
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import vm from 'node:vm';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const read = file => readFileSync(path.join(root, file), 'utf8');
const html = read('index.html');
const scripts = [...html.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/gi)]
  .filter(match => !/\bsrc\s*=/.test(match[1])).map(match => match[2]);
assert.equal(scripts.length, 2, 'Expected before-paint theme script and app script');
const exportCode = `window.TEST = {state, overview, members, leaderboards, stages, dataView,
  trends, render, eventBar, boardKey, rankChange, rosterRows, visibleBoard, openProfile,
  closeProfile, sync, theme, statusStage, date, t, n, loadWeek,
  setLang:value=>lang=value, getLang:()=>lang, setData:value=>data=value,
  getData:()=>data, getRenderToken:()=>renderToken};`;
assert.match(scripts[1], /\nrender\(\);\n/, 'App startup instrumentation anchor changed');
const app = scripts[1].replace(/\nrender\(\);\n/, '\n' + exportCode + '\n');

function harness({ query = '', storage = {}, twoWeeks = true, preloadOriginal = true } = {}) {
  const nodes = new Map(), errors = [], events = new Map(), requestedScripts = [];
  const location = { search: query, href: 'file://' + root + '/index.html' + query };
  const store = new Map(Object.entries(storage));
  let document;
  function node(selector) {
    if (!nodes.has(selector)) nodes.set(selector, {
      innerHTML: '', value: '', textContent: '', content: '', hidden: false,
      open: false, isConnected: true, dataset: {}, attributes: {}, events: new Map(),
      setAttribute(name, value) { this.attributes[name] = String(value); },
      addEventListener(name, callback) { this.events.set(name, callback); },
      querySelectorAll() { return []; },
      focus() { document.activeElement = this; },
      showModal() { this.open = true; }, close() { this.open = false; },
      select() {}, remove() {},
    });
    return nodes.get(selector);
  }
  document = {
    querySelector: node, querySelectorAll: () => [],
    documentElement: { dataset: { theme: 'dark' } }, activeElement: node('body'),
    addEventListener(name, callback) { events.set(name, callback); },
    createElement(tag) {
      assert.equal(tag, 'script', 'Lazy loading must inject a script');
      return { src: '', removed: false, remove() { this.removed = true; } };
    },
    head: { append(script) { requestedScripts.push(script); } },
  };
  const context = vm.createContext({
    window: { addEventListener(name, callback) { events.set('window:' + name, callback); } },
    document, location, URLSearchParams, URL, Intl, Blob,
    localStorage: { getItem: key => store.get(key) ?? null, setItem: (key, value) => store.set(key, value) },
    history: { replaceState(_state, _title, url) {
      location.href = String(url); location.search = new URL(url).search;
    } },
    console: { error: (...args) => errors.push(args.map(String).join(' ')) },
    setTimeout, navigator: {},
  });
  const run = (code, filename) => new vm.Script(code, { filename }).runInContext(context);
  for (const file of ['data/i18n.js', 'data/manifest.js', 'data/stages.js']) run(read(file), file);
  const manifest = context.window.VS_MANIFEST;
  assert.ok(manifest.length, 'Need at least one generated week');
  const first = manifest[0];
  run(read(`data/weeks/${first.id}/week_data.js`), first.id);
  const original = context.window.VS_WEEKS[first.id];
  original.summary.status = 'final';
  original.summary.stages.forEach(stage => { stage.status = 'final'; stage.winner = 'home'; });
  // Fixture: the real week is treated as a finished home win, whichever alliance's data this is
  Object.assign(original.summary, { score: { home: 13, opp: 0 }, decided: 'home', wins_remaining: 0, leading_live: {} });
  // Use a fixed synthetic date later than the captured fixture. Loading all real
  // weeks is the separate contract check's responsibility.
  const synthetic = JSON.parse(JSON.stringify(original));
  synthetic.summary.id = '2099-10-03';
  Object.assign(synthetic.summary, {
    status: 'in_progress', live_tabs: ['sat', 'week'], captured_at_server: '2099-10-03T15:30:00-02:00',
    score: { home: 2, opp: 7 }, wins_remaining: 4, decided: 'opp', leading_live: { sat: 'home' },
  });
  synthetic.summary.stages.forEach(stage => {
    stage.status = stage.day === 'sat' ? 'live' : 'final';
    stage.winner = stage.day === 'tue' || stage.day === 'sat' ? 'home' : 'opp';
  });
  // A roster turnover regression: one historical player is absent this week.
  const absent = original.members.find(player => !player.not_on_weekly);
  synthetic.members = synthetic.members.filter(player => player.key !== absent.key);
  synthetic.opponents = synthetic.opponents.filter(player => player.key !== absent.key);
  synthetic.others = (synthetic.others || []).filter(player => player.key !== absent.key);
  for (const [board, rows] of Object.entries(synthetic.boards)) {
    const rank = board === 'week' ? absent.weekly_rank : absent.days?.[board]?.rank;
    synthetic.boards[board] = rows.filter(row => row.rank !== rank);
  }
  context.window.VS_MANIFEST = [first];
  if (twoWeeks) {
    context.window.VS_MANIFEST.push({ ...first, id: synthetic.summary.id, status: 'in_progress' });
    context.window.VS_WEEKS[synthetic.summary.id] = synthetic;
  }
  if (!preloadOriginal) delete context.window.VS_WEEKS[first.id];
  run(scripts[0], 'theme prepaint'); run(app, 'dashboard instrumented');
  function completeRealWeek(script) {
    const url = new URL(script.src, location.href);
    const relative = url.pathname.slice(root.length + 1);
    assert.equal(relative, `data/weeks/${first.id}/week_data.js`, 'Only load the real fixture source');
    run(read(relative), relative);
    script.onload();
  }
  return { context, T: context.window.TEST, node, errors, original, synthetic, absent, store, location, document,
    requestedScripts, completeRealWeek, first };
}

const h = harness(), { T, original, synthetic, node } = h;
let combinations = 0;
for (const lang of Object.keys(h.context.window.I18N)) {
  T.setLang(lang);
  for (const view of ['overview', 'record', 'members', 'leaderboards', 'opponent', 'trends', 'stages', 'data']) {
    T.state.view = view; T.state.player = ''; T.state.week = original.summary.id;
    await T.render();
    assert.ok(node('#view').innerHTML.length > 100, `${lang}.${view} did not render`);
    assert.equal(node('#view').attributes['aria-busy'], 'false');
    combinations++;
  }
}
assert.deepEqual(h.errors, [], 'Runtime exceptions or untranslated dynamic keys');

T.setLang('en'); T.setData(original); T.state.week = original.summary.id;
// Daily OCR spelling variations must use the canonical roster identity that the
// pipeline already established by overall rank, including the previous day.
const roster = [...original.members, ...original.opponents, ...(original.others || [])];
let variants = 0;
for (const [board, rows] of Object.entries(original.boards)) for (const row of rows) {
  const player = roster.find(p => board === 'week' ? p.weekly_rank === row.rank : p.days?.[board]?.rank === row.rank);
  if (!player) continue;
  assert.equal(T.boardKey(row, board), player.key, `${board} #${row.rank} canonical key`);
  if (row.player !== player.player) variants++;
}
assert.ok(variants > 0, 'Real data fixture must cover an OCR spelling variant');
for (const [day, previous] of [['tue', 'mon'], ['wed', 'tue'], ['thu', 'wed'], ['fri', 'thu'], ['sat', 'fri']]) {
  T.state.tab = day;
  for (const player of roster.filter(p => p.days?.[day] && p.days?.[previous])) {
    const row = original.boards[day].find(r => r.rank === player.days[day].rank);
    const diff = player.days[previous].rank - row.rank, change = T.rankChange(row);
    assert.ok(diff === 0 ? change === '↔' : change.includes(`${diff > 0 ? '↑' : '↓'} ${T.n(Math.abs(diff))}`), `${player.key} ${day} rank movement`);
  }
}
Object.assign(T.state, { query: '', tier: 'all', quota: 'all', active: false, sort: 'weekly_points', direction: -1 });
let rows = T.rosterRows(false);
assert.ok(rows.every((row, index) => !index || rows[index - 1].weekly_points >= row.weekly_points));
Object.assign(T.state, { tier: 'titan', quota: 'met', active: true });
assert.ok(T.rosterRows(false).every(player => player.tier === 'titan' && player.quota_met && player.active_days > 0));
Object.assign(T.state, { tier: 'all', quota: 'all', active: false, query: original.members[0].player });
assert.ok(T.rosterRows(false).some(player => player.key === original.members[0].key));
Object.assign(T.state, { tab: 'week', side: 'home', query: '' });
assert.ok(T.visibleBoard().every(row => row.alliance_tag === original.summary.home.tag));

// A Saturday lead must not add its four wins to the finalized score.
T.setData(synthetic); T.state.week = synthetic.summary.id; T.state.view = 'overview';
const overview = T.overview();
T.eventBar();
const eventBar = node('#eventBar').innerHTML;
assert.match(overview, /class="score num">2 : 7<\/div>/);
assert.ok(eventBar.includes(T.t('in_progress')) && overview.includes(T.t('leading')));
assert.ok(!overview.includes('class="score num">6 : 7'));
assert.ok(eventBar.includes('Snapshot: ') && eventBar.includes('server time (UTC−2)'), 'Week header must render snapshot window with server time');
T.state.view = 'leaderboards'; T.state.tab = 'week';
const boards = T.leaderboards();
assert.ok(boards.includes('Snapshot') && boards.includes('server time'), 'Leaderboards must render snapshot time for current tab');
const tied = { ...synthetic.summary.stages.at(-1), home_points: 10, opp_points: 10 };
synthetic.summary.leading_live.sat = 'tie';
assert.ok(T.statusStage(tied).includes(T.t('undecided')));
assert.ok(T.statusStage({ ...tied, status: 'final', winner: 'tie' }).includes(T.t('undecided')));
synthetic.summary.leading_live.sat = 'home';
T.state.view = 'trends'; T.state.player = ''; await T.render();
assert.match(node('#view').innerHTML, /<strong>1 – 0<\/strong>/, 'Clinched but live match must not count as a completed loss');
assert.match(node('#view').innerHTML, /<tr><td>Sat<\/td><td>1<\/td><td>1<\/td><td>100%<\/td><\/tr>/, 'Live Saturday must not enter stage win rate');
synthetic.summary.status = 'final'; synthetic.summary.decided = 'opp';
synthetic.summary.stages.at(-1).status = 'final'; synthetic.summary.stages.at(-1).winner = 'opp';
await T.render();
assert.match(node('#view').innerHTML, /<strong>1 – 1<\/strong>/, 'Completed loss must enter the record');
assert.match(node('#view').innerHTML, /<tr><td>Sat<\/td><td>1<\/td><td>2<\/td><td>50%<\/td><\/tr>/, 'Final Saturday must enter stage win rate');

// Missing-current-player profiles must label their source week and preserve history.
T.state.player = ''; T.state.week = synthetic.summary.id; T.setData(synthetic);
await T.openProfile(h.absent.key);
assert.equal(node('#profile').open, true);
assert.ok(node('#profileBody').innerHTML.includes(T.date(original.summary.id)), 'Historical stats must identify their source week');
assert.ok(node('#profileBody').innerHTML.includes(T.t('profile_absent', { date: T.date(original.summary.id) })), 'Historical profile must explain the source of its statistics');
assert.ok(node('#profileHistory').innerHTML.includes(T.date(original.summary.id)));
T.closeProfile();
assert.equal(T.state.player, ''); assert.equal(node('#profile').open, false);

const deep = harness({ query: `?week=${original.summary.id}&view=leaderboards&tab=thu&player=${encodeURIComponent(h.absent.key)}&lang=fr&theme=light`, storage: { 'p1mp.lang': 'de', 'p1mp.theme': 'dark' } });
assert.equal(deep.T.state.week, original.summary.id);
assert.equal(deep.T.state.view, 'leaderboards'); assert.equal(deep.T.state.tab, 'thu');
assert.equal(deep.T.state.player, h.absent.key); assert.equal(deep.T.getLang(), 'fr');
assert.equal(deep.document.documentElement.dataset.theme, 'light');
await deep.T.render(); deep.T.sync();
assert.ok(deep.node('#view').innerHTML.includes('Instantané') && deep.node('#view').innerHTML.includes('heure serveur'), 'French leaderboards must render snapshot in French');
for (const [key, value] of Object.entries({ week: original.summary.id, view: 'leaderboards', tab: 'thu', player: h.absent.key, lang: 'fr', theme: 'light' })) {
  assert.equal(new URL(deep.location.href).searchParams.get(key), value, `Deep link ${key}`);
}
deep.T.state.view = 'overview';
await deep.T.render();
assert.ok(deep.node('#eventBar').innerHTML.includes('Instantané :') && deep.node('#eventBar').innerHTML.includes('heure serveur (UTC−2)'), 'French week header must render snapshot in French');
deep.node('#themeToggle').events.get('click')();
assert.equal(deep.store.get('p1mp.theme'), 'dark');
assert.equal(new URL(deep.location.href).searchParams.get('theme'), 'dark');
const stored = harness({ storage: { 'p1mp.lang': 'ko', 'p1mp.theme': 'light' } });
assert.equal(stored.T.getLang(), 'ko'); assert.equal(stored.document.documentElement.dataset.theme, 'light');
assert.equal(stored.T.state.week, synthetic.summary.id, 'Newest week is default');
const one = harness({ twoWeeks: false });
one.T.state.view = 'trends'; await one.T.render();
assert.ok(one.node('#view').innerHTML.includes(one.T.t('need_two')), 'Single-week empty state');

// Loading is selection-driven, versioned, shared between concurrent callers,
// and recoverable after a failed script request. Execute the real week source
// through the fake script element instead of substituting a synthetic file.
const lazy = harness({ preloadOriginal: false });
assert.equal(lazy.requestedScripts.length, 0, 'Initialization must not request all weeks');
const load = lazy.T.loadWeek(lazy.first.id), concurrent = lazy.T.loadWeek(lazy.first.id);
assert.equal(concurrent, load, 'Concurrent callers must share the pending load');
assert.equal(lazy.requestedScripts.length, 1, 'Only one script for concurrent calls');
assert.equal(lazy.requestedScripts[0].src,
  `data/weeks/${lazy.first.id}/week_data.js?v=${encodeURIComponent(lazy.first.data_version)}`,
  'Week script must use its manifest data_version');
lazy.completeRealWeek(lazy.requestedScripts[0]);
assert.equal((await load).summary.id, lazy.first.id);
await lazy.T.loadWeek(lazy.first.id);
assert.equal(lazy.requestedScripts.length, 1, 'Loaded weeks must not request another script');

const retry = harness({ preloadOriginal: false });
const failed = retry.T.loadWeek(retry.first.id);
const rejection = assert.rejects(failed, /Script load failed/);
retry.requestedScripts[0].onerror();
await rejection;
assert.equal(retry.requestedScripts[0].removed, true, 'Failed script must be removed');
const retried = retry.T.loadWeek(retry.first.id);
assert.notEqual(retried, failed, 'Retry must create a fresh promise');
assert.equal(retry.requestedScripts.length, 2, 'Retry must create a fresh script');
retry.completeRealWeek(retry.requestedScripts[1]);
assert.equal((await retried).summary.id, retry.first.id);
assert.deepEqual([...h.errors, ...deep.errors, ...stored.errors, ...one.errors, ...lazy.errors, ...retry.errors], []);
console.log(`Site runtime checks passed: ${combinations} view/language combinations, canonical OCR identities, filters, live scores, records, profiles, deep links, themes and lazy-load recovery.`);
