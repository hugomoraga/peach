#!/usr/bin/env node
/**
 * Traduce literales y texto JSX de `frontend/src` sobre la copia de build.
 *
 * El escáner de Python no entiende todos los literales de plantilla: un
 * comentario con backticks lo desincroniza y deja pasar `天`/`小时` sin
 * traducir. Aquí se usa el parser de TypeScript que ya trae el frontend
 * (`oxc-parser`), así que los rangos son los del AST y los comentarios no
 * cuentan. Solo se sustituye una unidad completa que exista en el glosario.
 *
 * Uso:
 *   node tools/i18n/translate_frontend.mjs \
 *     --root .i18n/es --modules frontend/node_modules \
 *     --glossary tools/i18n/glossary.zh-es.json --report .i18n/es/frontend-report.json
 */
import { readFileSync, readdirSync, statSync, writeFileSync } from 'node:fs';
import { join, relative, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

const CJK = /[\u3400-\u4dbf\u4e00-\u9fff]/;

//: Valores de datos y código de la biblioteca de componentes: no son texto de
//: la app. `jav-title.ts` compara `中字`/`无码` contra el valor que guarda la
//: base; traducirlo rompe la lógica.
const EXCLUDED = /(?:core\/tags\.ts|core\/jav-title\.ts|react\/boardui\/)/;

function args() {
  const out = {};
  const argv = process.argv.slice(2);
  for (let i = 0; i < argv.length; i += 1) {
    if (!argv[i].startsWith('--')) continue;
    out[argv[i].slice(2)] = argv[i + 1];
    i += 1;
  }
  return out;
}

function files(root) {
  const found = [];
  const walk = (dir) => {
    for (const name of readdirSync(dir)) {
      const path = join(dir, name);
      const stat = statSync(path);
      if (stat.isDirectory()) walk(path);
      else if (/\.(ts|tsx|js|jsx)$/.test(name)) found.push(path);
    }
  };
  walk(root);
  return found;
}

function collect(node, source, glossary, out, missed, file) {
  if (!node || typeof node !== 'object') return;
  if (Array.isArray(node)) {
    for (const item of node) collect(item, source, glossary, out, missed, file);
    return;
  }
  if (typeof node.type !== 'string') return;

  const record = (value, index) => {
    missed[value] ??= [];
    const line = source.slice(0, index).split('\n').length;
    if (missed[value].length < 3) missed[value].push(`${file}:${line}`);
  };

  if (node.type === 'TemplateLiteral') {
    const body = source.slice(node.start + 1, node.end - 1);
    const translated = glossary[body];
    if (translated !== undefined && CJK.test(body)) {
      out.push({ start: node.start, end: node.end, text: `\`${translated}\``, kind: 'template' });
      return;
    }
    if (CJK.test(body)) record(body, node.start);
  }

  if (node.type === 'Literal' && typeof node.value === 'string' && !node.regex) {
    const value = node.value;
    const translated = glossary[value];
    if (translated !== undefined && CJK.test(value)) {
      out.push({ start: node.start, end: node.end, text: JSON.stringify(translated), kind: 'string' });
      return;
    }
    if (CJK.test(value)) record(value, node.start);
  }

  if (node.type === 'JSXText' && typeof node.value === 'string') {
    const value = node.value;
    const trimmed = value.trim();
    const translated = glossary[trimmed];
    if (translated !== undefined && CJK.test(trimmed)) {
      const lead = value.slice(0, value.indexOf(trimmed));
      const trail = value.slice(value.indexOf(trimmed) + trimmed.length);
      out.push({ start: node.start, end: node.end, text: lead + translated + trail, kind: 'jsx' });
      return;
    }
    if (CJK.test(trimmed)) record(trimmed, node.start);
  }

  for (const [key, value] of Object.entries(node)) {
    if (key === 'parent' || key === 'comments') continue;
    collect(value, source, glossary, out, missed, file);
  }
}

const options = args();
const root = resolve(options.root || '.');
const modules = resolve(options.modules || 'frontend/node_modules');
const glossary = JSON.parse(readFileSync(resolve(options.glossary || 'tools/i18n/glossary.zh-es.json'), 'utf8'));
const reportPath = resolve(options.report || join(root, 'frontend-report.json'));
const oxc = await import(pathToFileURL(join(modules, 'oxc-parser', 'src-js', 'index.js')).href);

let applied = 0;
const missed = {};
for (const path of files(join(root, 'frontend', 'src'))) {
  if (EXCLUDED.test(path.replaceAll('\\', '/'))) continue;
  const source = readFileSync(path, 'utf8');
  if (!CJK.test(source)) continue;
  const parsed = oxc.parseSync(path, source, { sourceType: 'module' });
  if (parsed.errors?.length) {
    throw new Error(`${path}: ${parsed.errors.map((error) => error.message).join('; ')}`);
  }
  const edits = [];
  collect(parsed.program, source, glossary, edits, missed, relative(root, path));
  if (!edits.length) continue;
  edits.sort((a, b) => b.start - a.start);
  let output = source;
  let lastStart = Infinity;
  for (const edit of edits) {
    if (edit.end > lastStart) continue;
    output = output.slice(0, edit.start) + edit.text + output.slice(edit.end);
    lastStart = edit.start;
    applied += 1;
  }
  writeFileSync(path, output, 'utf8');
}

writeFileSync(reportPath, JSON.stringify({
  applied,
  untranslated_count: Object.keys(missed).length,
  untranslated: Object.fromEntries(Object.entries(missed).slice(0, 400)),
}, null, 1), 'utf8');
console.log(`frontend AST: ${applied} literales traducidos, ${Object.keys(missed).length} formas sin entrada`);
