#!/usr/bin/env node
/**
 * Validateur du scénario stage_ui (skill stage-ui-step-authoring).
 *
 * Usage : node .agents/skills/stage-ui-step-authoring/scripts/check_demo_config.mjs
 * Code retour 1 si au moins une ERROR ; les WARN sont informatifs.
 */
import { createRequire } from 'node:module';
import { existsSync, readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '../../../..');
const require = createRequire(resolve(ROOT, 'stage_ui/package.json'));
const YAML = require('yaml');

const PUBLIC = resolve(ROOT, 'stage_ui/public/demo_config.yaml');
const DIST = resolve(ROOT, 'stage_ui/dist/demo_config.yaml');

const ENUMS = {
  traceAction: ['ran', 'analyzed', 'edited'],
  icon: ['sql', 'yml', 'py', 'dak', 'cpy', 'csv', 'mp4', 'md'],
  chipKind: ['sql', 'yml', 'py', 'bq', 'kc', 'mp4'],
  language: ['sql', 'yaml', 'python', 'markdown'],
  tone: ['neutral', 'positive', 'warning', 'ruby', 'blue'],
  subagentStatus: ['completed', 'running'],
  demoId: ['demo1', 'demo2', 'demo3', 'demo4'],
};
const CONV_FIELDS = ['id', 'demoId', 'shortName', 'conversationTitle', 'projectFolder', 'gitBranch', 'greetingName', 'modelLabel', 'turns'];
const TURN_FIELDS = ['id', 'chipLabel', 'prompt', 'workedDurationLabel', 'workGroupSummary', 'intermediateMessage', 'taskFinishedLabel', 'leadConfirmation', 'sectionHeading', 'items', 'traces', 'filesChanged', 'terminalLogs', 'subagents', 'backgroundTasks'];

const errors = [];
const warns = [];
const err = (m) => errors.push(m);
const warn = (m) => warns.push(m);

function load(path) {
  try {
    return YAML.parse(readFileSync(path, 'utf8'));
  } catch (e) {
    err(`${path} : YAML illisible — ${e.message.split('\n')[0]}`);
    return null;
  }
}

const cfg = load(PUBLIC);
if (existsSync(DIST)) {
  const pub = readFileSync(PUBLIC, 'utf8');
  const dist = readFileSync(DIST, 'utf8');
  load(DIST);
  if (pub !== dist) warn('stage_ui/dist/demo_config.yaml diffère de public/ : recopier public/ vers dist/');
}
if (!cfg) {
  errors.forEach((m) => console.log(`ERROR ${m}`));
  process.exit(1);
}

const seenIds = new Map();
const uniq = (id, where) => {
  if (!id) return err(`${where} : id manquant`);
  if (seenIds.has(id)) err(`id dupliqué « ${id} » (${where} et ${seenIds.get(id)})`);
  else seenIds.set(id, where);
};
const inEnum = (value, enumName, where) => {
  if (value !== undefined && !ENUMS[enumName].includes(value)) err(`${where} : valeur « ${value} » non autorisée (${ENUMS[enumName].join(', ')})`);
};
const numbered = (labels, where) => {
  labels.forEach((label, i) => {
    const m = /^(\d+)\.\s/.exec(label ?? '');
    if (!m) err(`${where} : « ${label} » doit commencer par « ${i + 1}. »`);
    else if (Number(m[1]) !== i + 1) err(`${where} : « ${label} » devrait être numéroté ${i + 1}`);
  });
};
const normalize = (s) => s.replace(/\r\n/g, '\n').replace(/\s+$/g, '').split('\n').map((l) => l.replace(/\s+$/, '')).join('\n');

for (const ws of cfg.workspaces ?? []) {
  inEnum(ws.id, 'demoId', `workspace ${ws.id}`);
  const convs = ws.conversations ?? [];
  numbered(convs.map((c) => c.shortName), `workspace ${ws.id} · shortName`);
  for (const conv of convs) {
    const cw = `conversation ${conv.id}`;
    uniq(conv.id, cw);
    CONV_FIELDS.forEach((f) => conv[f] === undefined && err(`${cw} : champ « ${f} » manquant`));
    if (conv.demoId !== ws.id) err(`${cw} : demoId « ${conv.demoId} » ≠ workspace « ${ws.id} »`);
    const turns = conv.turns ?? [];
    numbered(turns.map((t) => t.chipLabel), `${cw} · chipLabel`);
    for (const turn of turns) {
      const tw = `turn ${turn.id}`;
      uniq(turn.id, tw);
      TURN_FIELDS.forEach((f) => turn[f] === undefined && err(`${tw} : champ « ${f} » manquant`));
      (turn.items ?? []).forEach((it, i) => (it.chips ?? []).forEach((c) => inEnum(c.kind, 'chipKind', `${tw} · items[${i}].chips`)));
      (turn.traces ?? []).forEach((tr) => {
        inEnum(tr.action, 'traceAction', `${tw} · trace ${tr.id}`);
        if (tr.action !== 'ran') inEnum(tr.icon, 'icon', `${tw} · trace ${tr.id}`);
        if (typeof tr.durationMs !== 'number') err(`${tw} · trace ${tr.id} : durationMs manquant`);
      });
      (turn.subagents ?? []).forEach((s) => inEnum(s.status, 'subagentStatus', `${tw} · subagent ${s.id}`));
      const qs = turn.askQuestions ?? [];
      if (qs.length && (qs.length < 2 || qs.length > 3)) warn(`${tw} : ${qs.length} question(s) d'arbitrage (2 à 3 attendues)`);
      qs.forEach((q) => {
        uniq(q.id, `${tw} · question`);
        if ((q.options ?? []).length < 2) err(`${tw} · question ${q.id} : au moins 2 options`);
        if (!String(q.options?.[0] ?? '').startsWith('(Recommended) ')) err(`${tw} · question ${q.id} : la 1re option doit commencer par « (Recommended) »`);
      });
      const vc = turn.visualCheck;
      if (vc) {
        (vc.kpis ?? []).forEach((k) => inEnum(k.tone, 'tone', `${tw} · visualCheck.kpis`));
        (vc.bars ?? []).forEach((b) => inEnum(b.tone, 'tone', `${tw} · visualCheck.bars`));
      }
      const psi = turn.pubsubInspector;
      if (psi) {
        (psi.topics ?? []).forEach((tp) => {
          inEnum(tp.tone, 'tone', `${tw} · pubsubInspector.topics`);
          (tp.samples ?? []).forEach((sm) => {
            inEnum(sm.tone, 'tone', `${tw} · pubsubInspector.samples`);
            (sm.groups ?? []).forEach((gr) =>
              (gr.fields ?? []).forEach((fl) => inEnum(fl.tone, 'tone', `${tw} · pubsubInspector.fields`))
            );
          });
        });
      }
      (turn.filesChanged ?? []).forEach((f) => {
        inEnum(f.language, 'language', `${tw} · ${f.path}`);
        const repoFile = resolve(ROOT, f.path ?? '');
        if (f.path && existsSync(repoFile)) {
          const real = normalize(readFileSync(repoFile, 'utf8'));
          const shown = normalize(String(f.content ?? ''));
          if (real !== shown && !real.startsWith(shown)) warn(`${tw} · ${f.path} : le contenu affiché diffère du fichier réel du repo`);
        } else if (f.path) {
          warn(`${tw} · ${f.path} : fichier absent du repo (contenu non vérifiable)`);
        }
      });
    }
  }
}

warns.forEach((m) => console.log(`WARN  ${m}`));
errors.forEach((m) => console.log(`ERROR ${m}`));
console.log(`\n${seenIds.size} identifiants vérifiés · ${errors.length} erreur(s) · ${warns.length} avertissement(s)`);
process.exit(errors.length ? 1 : 0);
