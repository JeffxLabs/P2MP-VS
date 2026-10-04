#!/usr/bin/env node
/** Offline dashboard contract and JavaScript syntax checks; no dependencies. */
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { existsSync, readFileSync, readdirSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import vm from 'node:vm';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const read = relative => readFileSync(path.join(root, relative), 'utf8');
const hash = relative => createHash('sha1').update(readFileSync(path.join(root, relative))).digest('hex').slice(0, 10);
const context = vm.createContext({ window: {} });
const run = relative => new vm.Script(read(relative), { filename: relative }).runInContext(context, { timeout: 5000 });
const languages = ['en', 'fr', 'ru', 'tr', 'pl', 'es', 'pt', 'de', 'ko', 'zh'];
const days = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat'];
const tabs = [...days, 'week'];

for (const asset of ['data/i18n.js', 'data/manifest.js', 'data/stages.js']) run(asset);
const { I18N, LANG_LOCALES, LANG_NAMES, VS_MANIFEST, VS_STAGES } = context.window;
assert.ok(I18N && I18N.en, 'window.I18N.en must exist');
const keys = Object.keys(I18N.en).sort();
assert.ok(keys.length > 0, 'English translation table must not be empty');
const placeholders = text => [...text.matchAll(/\{([A-Za-z_][A-Za-z0-9_]*)\}/g)].map(match => match[1]).sort();
assert.deepEqual(Object.keys(I18N).sort(), [...languages].sort(), 'Exactly the ten supported languages must be present');
for (const lang of languages) {
  assert.ok(I18N[lang] && typeof I18N[lang] === 'object', `Missing translation table: ${lang}`);
  assert.deepEqual(Object.keys(I18N[lang]).sort(), keys, `Translation keys differ for ${lang}`);
  assert.ok(typeof LANG_LOCALES?.[lang] === 'string', `Missing locale: ${lang}`);
  assert.ok(typeof LANG_NAMES?.[lang] === 'string' && LANG_NAMES[lang].trim(), `Missing language name: ${lang}`);
  assert.doesNotThrow(() => new Intl.NumberFormat(LANG_LOCALES[lang]), `Invalid locale: ${lang}`);
  for (const key of keys) {
    assert.ok(typeof I18N[lang][key] === 'string' && I18N[lang][key].trim(), `Empty translation: ${lang}.${key}`);
    assert.deepEqual(placeholders(I18N[lang][key]), placeholders(I18N.en[key]), `Placeholders differ: ${lang}.${key}`);
  }
}

const html = read('index.html');
let attributeCount = 0;
for (const match of html.matchAll(/\bdata-i18n(?:-ph|-aria)?\s*=\s*(["'])(.*?)\1/g)) {
  const key = match[2];
  if (key.includes('${')) continue; // A dynamic template expression is checked by the JS compiler below.
  assert.ok(Object.hasOwn(I18N.en, key), `Unknown markup translation key: ${key}`);
  attributeCount++;
}
assert.ok(attributeCount > 0, 'index.html must use translation attributes');
let inlineCount = 0;
for (const match of html.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script\s*>/gi)) {
  const attrs = match[1];
  if (/\bsrc\s*=/i.test(attrs)) continue;
  const type = attrs.match(/\btype\s*=\s*(["'])(.*?)\1/i)?.[2]?.toLowerCase();
  if (type && !['text/javascript', 'application/javascript'].includes(type)) continue;
  new vm.Script(match[2], { filename: `index.html inline script ${++inlineCount}` });
}
assert.ok(inlineCount > 0, 'index.html must have inline application scripts');
for (const asset of ['data/i18n.js', 'data/manifest.js', 'data/stages.js']) {
  const escaped = asset.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const urls = [...html.matchAll(new RegExp(`(["'])(${escaped}(?:\\?[^"'#]*)?(?:#[^"']*)?)\\1`, 'g'))];
  assert.ok(urls.length > 0, `index.html must load ${asset}`);
  for (const [, , url] of urls) assert.equal(new URL(url, 'https://offline.invalid/').searchParams.get('v'), hash(asset), `Stale cache version for ${asset}; run pipeline/stamp_assets.py`);
}

assert.ok(Array.isArray(VS_MANIFEST) && VS_MANIFEST.length > 0, 'Manifest must contain at least one week');
const ids = VS_MANIFEST.map(entry => entry.id);
assert.equal(new Set(ids).size, ids.length, 'Manifest week IDs must be unique');
assert.deepEqual([...ids], [...ids].sort(), 'Manifest must be oldest first');
for (const entry of VS_MANIFEST) {
  assert.match(entry.id, /^\d{4}-\d{2}-\d{2}$/, 'Invalid week ID');
  const file = `data/weeks/${entry.id}/week_data.js`;
  assert.ok(existsSync(path.join(root, file)), `Missing week file: ${file}`);
  assert.equal(entry.data_version, hash(file), `Manifest data_version does not match ${file}`);
  assert.ok(['final', 'in_progress'].includes(entry.status), `Invalid status for ${entry.id}`);
}
const weekDirectories = readdirSync(path.join(root, 'data/weeks'), { withFileTypes: true }).filter(entry => entry.isDirectory());
let weekCount = 0;
for (const directory of weekDirectories) {
  const file = `data/weeks/${directory.name}/week_data.js`;
  if (!existsSync(path.join(root, file))) continue;
  run(file);
  const week = context.window.VS_WEEKS?.[directory.name];
  assert.ok(week, `${file} must register its own week ID`);
  assert.ok(week.summary && week.boards, `Missing summary or boards in ${file}`);
  for (const tab of tabs) assert.ok(Array.isArray(week.boards[tab]), `Missing ${tab} board in ${file}`);
  assert.ok(Array.isArray(week.members) && Array.isArray(week.opponents), `Missing rosters in ${file}`);
  weekCount++;
}
for (const id of ids) assert.ok(context.window.VS_WEEKS?.[id], `Manifest week ${id} was not registered`);
assert.ok(VS_STAGES && Array.isArray(VS_STAGES.stages), 'window.VS_STAGES.stages must be an array');
assert.equal(VS_STAGES.stages.length, 6, 'There must be six stages');
assert.deepEqual(Array.from(VS_STAGES.stages, stage => stage.day_code), days, 'Stage days must be Monday through Saturday');
assert.deepEqual(Array.from(VS_STAGES.stages, stage => stage.wins_awarded), [1, 2, 2, 2, 2, 4], 'Stage win values must total thirteen');
assert.equal(VS_STAGES.total_wins, 13, 'Total wins must be thirteen');
for (const stage of VS_STAGES.stages) assert.ok(Array.isArray(stage.activities) && stage.activities.length, `Missing activities for ${stage.day_code}`);

console.log(`Site data checks passed: ${languages.length} languages, ${keys.length} keys, ${attributeCount} translation attributes, ${inlineCount} inline scripts, ${weekCount} week files.`);
