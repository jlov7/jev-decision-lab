'use strict';
const $ = (id) => document.getElementById(id);
const state = {
  config: null,
  cases: [],
  packs: {},
  signals: [],
  pack: 'supply',
  caseId: 'S01',
  receipt: null,
  busy: false,
};
const names = {
  issue: 'Primary exception',
  owner: 'Investigating team',
  severity: 'Consequence level',
  sufficient: 'Evidence sufficient',
  contradiction: 'Material contradiction',
  next_evidence: 'Next evidence candidate',
};
const routes = {
  VERIFY_SOURCE: ['Verify the source', 'Unverified evidence needs a trusted source check.'],
  REFRESH_EVIDENCE: [
    'Refresh the evidence',
    'A confident old answer cannot make expired evidence current.',
  ],
  HUMAN_REVIEW: ['Human review', 'A policy boundary or uncertain judgment requires a person.'],
  REQUEST_EVIDENCE: [
    'Repair the evidence',
    'Resolve a material gap or conflict before proceeding.',
  ],
  ROUTE_TO_TEAM: [
    'Recommend a team',
    'The teaching policy permits a recommendation. No external action is taken.',
  ],
};
const esc = (value) =>
  String(value).replace(
    /[&<>"']/g,
    (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c],
  );
function error(text) {
  $('error').textContent = text;
  $('error').hidden = !text;
}
function busy(value) {
  state.busy = value;
  ['run', 'evaluate', 'gardenRun', 'burstRun', 'pgRun', 'compareRun', 'pgAdd', 'probeRun', 'ablateRun'].forEach(
    (id) => ($(id).disabled = value),
  );
  ['reconsider', 'export', 'action'].forEach((id) => ($(id).disabled = value || !state.receipt));
  $('exportBurst').disabled = value || !state.lastBurst;
  $('exportPg').disabled = value || !state.lastPlayground;
  $('exportCompare').disabled = value || !state.lastCompare;
  document.querySelectorAll('.case,.domains button').forEach((x) => (x.disabled = value));
  $('mode').disabled = value;
}
async function api(path, body) {
  const options =
    body === undefined
      ? {}
      : {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Lab-Token': state.config.session_token,
          },
          body: JSON.stringify(body),
        };
  const response = await fetch(path, options);
  const data = await response.json();
  if (!response.ok) {
    const failure = new Error(data.error || `Request failed (${response.status})`);
    failure.detail = data;
    throw failure;
  }
  return data;
}
function provenance() {
  const p = state.receipt?.provenance;
  const live = p?.kind === 'live_typesafe';
  $('provenance').classList.toggle('live', live);
  const latency =
    live && typeof p.latency_ms === 'number' ? ` · ${fmtMs(p.latency_ms)} client-observed` : '';
  $('provenance').textContent = live
    ? `Live TypeSafe result · ${state.receipt.response.model}${latency} · Price estimate, not an invoice`
    : 'Synthetic replay · Authored teaching probabilities · No Jev API call';
}
function domains() {
  $('domains').innerHTML = Object.entries(state.packs)
    .map(
      ([id, p]) =>
        `<button data-pack="${esc(id)}" class="${id === state.pack ? 'active' : ''}" aria-pressed="${id === state.pack}">${esc(p.name)}<span>${esc(p.subtitle)}</span></button>`,
    )
    .join('');
  $('domains')
    .querySelectorAll('button')
    .forEach(
      (b) =>
        (b.onclick = () => {
          state.pack = b.dataset.pack;
          selectCase(state.cases.find((c) => c.pack === state.pack).id);
          domains();
        }),
    );
}
function queue() {
  $('cases').innerHTML = state.cases
    .filter((c) => c.pack === state.pack)
    .map(
      (c) =>
        `<button class="case ${c.id === state.caseId ? 'active' : ''}" data-case="${esc(c.id)}" aria-pressed="${c.id === state.caseId}"><span>${esc(c.id)}</span>${esc(c.title)}</button>`,
    )
    .join('');
  $('cases')
    .querySelectorAll('button')
    .forEach((b) => (b.onclick = () => selectCase(b.dataset.case)));
}
function fillCaseView(id) {
  const c = state.cases.find((x) => x.id === id);
  state.pack = c.pack;
  state.caseId = id;
  domains();
  queue();
  $('caseId').textContent = id;
  $('caseTitle').textContent = c.title;
  $('message').textContent = c.state.message;
  $('evidence').innerHTML = c.state.evidence
    .map((e) => `<div class="source"><strong>${esc(e.id)}</strong>${esc(e.text)}</div>`)
    .join('');
}
function teachingNote() {
  const c = state.cases.find((x) => x.id === state.caseId);
  $('teachingNote').innerHTML =
    c && c.teaching_note
      ? `<p class="notice">${esc(c.teaching_note)}${
          c.planted_error ? ' This is a planted teaching error, not a measured Jev failure.' : ''
        }</p>`
      : '';
}
function selectCase(id) {
  state.receipt = null;
  error('');
  $('variant').value = 'original';
  fillCaseView(id);
  $('route').textContent = 'Ready to inspect';
  $('routeText').textContent = 'Run this case to inspect the model–policy boundary.';
  ['decisionMetrics', 'nextEvidence', 'trace', 'actionResult', 'headCallout', 'teachingNote'].forEach(
    (k) => ($(k).innerHTML = ''),
  );
  $('answers').innerHTML =
    '<p class="empty">Run a case to inspect typed answers and distributions.</p>';
  $('raw').textContent = 'Run a case first.';
  $('callCount').textContent = 'No call yet';
  busy(false);
  provenance();
}
function metric(label, value) {
  return `<div class="metric"><span>${esc(label)}</span><strong>${esc(value)}</strong></div>`;
}
function answerBlock(id, label, a, instructions) {
  const val =
    a.type === 'choice' ? a.choice : a.type === 'noul' ? a.noul.toFixed(3) : a.score.toFixed(2);
  const probs = a.type === 'noul' ? { yes: a.noul, no: 1 - a.noul } : a.probabilities;
  const rows = Object.entries(probs)
    .map(
      ([k, v]) =>
        `<div class="prob-row"><span>${esc(a.type === 'score' ? `${k}: ${a.legend[k]}` : k)}</span><meter min="0" max="1" value="${v}" aria-label="${esc(k)} probability ${v}"></meter><span>${(v * 100).toFixed(0)}%</span></div>`,
    )
    .join('');
  const conf =
    a.confidence === undefined
      ? '<p>No separate confidence statistic for Noul.</p>'
      : `<p>Separate confidence statistic: ${a.confidence.toFixed(3)}. Not measured probability of correctness.</p>`;
  return `<details><summary><span class="answer-head"><span><span class="type">${esc(a.type)}</span>${esc(label)}</span><span class="answer-value">${esc(val)}</span></span></summary><div class="distribution">${rows}<p>${esc(instructions)}</p>${conf}</div></details>`;
}
function render() {
  const r = state.receipt,
    d = r.decision,
    p = r.provenance;
  provenance();
  teachingNote();
  $('route').textContent = routes[d.route][0];
  $('routeText').textContent = routes[d.route][1];
  const mismatch = d.inconsistencies && d.inconsistencies[0];
  $('headCallout').innerHTML = mismatch
    ? `<p class="notice">${esc(mismatch.explanation)} ${
        d.variant === 'strict'
          ? 'Strict policy held this for a person.'
          : 'Default policy still follows the owner head. Switch to “Hold on issue/owner disagreement” and replay policy — zero new model calls.'
      }</p>`
    : '';
  $('callCount').textContent = r.additional_model_calls
    ? `${r.additional_model_calls} new model call`
    : '0 new model calls';
  $('decisionMetrics').innerHTML =
    metric('Suggested owner', d.owner) +
    metric('Top-owner probability', `${(d.owner_probability * 100).toFixed(0)}%`) +
    metric('Critical consequence probability', `${(d.critical_probability * 100).toFixed(0)}%`);
  if (p.kind === 'live_typesafe') {
    const tokens = p.usage && typeof p.usage.input_tokens === 'number' ? p.usage.input_tokens : null;
    $('decisionMetrics').innerHTML +=
      metric('Observed input tokens', tokens === null ? 'Unknown' : tokens) +
      metric(
        'Estimated inference cost',
        p.estimated_cost_usd === null || p.estimated_cost_usd === undefined
          ? 'Unknown'
          : '$' + p.estimated_cost_usd.toFixed(7),
      );
  }
  $('nextEvidence').innerHTML =
    `<h3>Next evidence candidate</h3><p>${esc(r.request.questions.next_evidence.criteria[d.next_evidence])}</p>`;
  $('answers').innerHTML = Object.entries(r.response.answers)
    .map(([id, a]) => answerBlock(id, names[id], a, r.request.questions[id].instructions))
    .join('');
  $('trace').innerHTML = d.trace
    .map(
      (t) =>
        `<li class="${t.matched ? 'matched' : ''}"><code>${esc(t.rule)} · ${t.matched ? 'triggered' : 'not triggered'}</code>${esc(t.explanation)}</li>`,
    )
    .join('');
  $('raw').textContent = JSON.stringify(r, null, 2);
  $('actionResult').innerHTML = '';
  busy(false);
}
async function run() {
  error('');
  busy(true);
  try {
    if ($('mode').value === 'live' && !state.config.live_enabled)
      throw new Error('Live mode is not configured. Open Connect Jev for server-side setup.');
    state.receipt = await api('/api/run', {
      case_id: state.caseId,
      mode: $('mode').value,
      threshold: Number($('threshold').value),
      consent: $('consent').checked,
    });
    render();
  } catch (e) {
    const retained = e.detail && e.detail.provider_response;
    if (retained) $('raw').textContent = JSON.stringify(e.detail, null, 2);
    error(
      e.message +
        (retained ? ' The provider answered; its raw response is in the request panel below.' : '') +
        (state.receipt ? ' The prior result remains visible; no new result was produced.' : ''),
    );
  } finally {
    busy(false);
  }
}
async function reconsider() {
  if (!state.receipt) return;
  error('');
  busy(true);
  try {
    state.receipt = await api('/api/reconsider', {
      receipt_id: state.receipt.receipt_id,
      threshold: Number($('threshold').value),
      variant: $('variant').value,
    });
    render();
  } catch (e) {
    error(e.message);
  } finally {
    busy(false);
  }
}
async function action() {
  if (!state.receipt) return;
  busy(true);
  try {
    const current = Object.fromEntries(
      ['state_unchanged', 'source_fresh', 'approval_current', 'permission_granted'].map((k) => [
        k,
        $(k).checked,
      ]),
    );
    const r = await api('/api/action-preview', { receipt_id: state.receipt.receipt_id, current });
    $('actionResult').innerHTML =
      `<h3>${esc(r.result)}</h3><p>0 external actions · 0 new model calls</p><ul>${r.checks.map((c) => `<li>${esc(c.rule || c.check)}: ${c.passed ? 'passed' : 'held'}</li>`).join('')}</ul><p class="small">${esc(r.warning)}</p>`;
  } catch (e) {
    error(e.message);
  } finally {
    busy(false);
  }
}
async function garden() {
  busy(true);
  try {
    const r = await api('/api/garden', {
      task: $('task').value,
      allow_cloud: $('cloud').checked,
      consequence_high: $('consequence').checked,
    });
    $('gardenResult').innerHTML =
      `<h2>${esc(r.lane.replaceAll('_', ' '))}</h2><p>${esc(r.explanation)}</p><p><strong>Hosted Jev candidate:</strong> ${r.hosted_jev_eligible ? 'May be evaluated; approval still required' : 'Not indicated for this role or data boundary'}</p><p><strong>Human authority required:</strong> ${r.human_authority_required ? 'Yes' : 'Decide against the actual consequence and policy'}</p><ul>${r.checks.map((x) => `<li>${esc(x)}</li>`).join('')}</ul><p class="small">${esc(r.warning)}</p>`;
  } catch (e) {
    error(e.message);
  } finally {
    busy(false);
  }
}
function signals() {
  const date = $('asOf').value,
    kind = $('signalKind').value;
  const rows = state.signals.filter((s) => s.date <= date && (kind === 'all' || s.kind === kind));
  $('signalList').innerHTML =
    rows
      .map(
        (s) =>
          `<article class="signal"><div><time>${esc(s.date)}</time><span>${esc(s.kind)}</span></div><section><h2>${esc(s.title)}</h2><p>${esc(s.implication)}</p><a href="${esc(s.url)}" target="_blank" rel="noreferrer">${esc(s.source)} ↗</a><p class="small">Date basis: ${esc(s.date_basis)}<br>Actual tracker ingestion: UNKNOWN</p></section></article>`,
      )
      .join('') ||
    '<p>No curated sources in this window. This is not proof that no public signal existed.</p>';
}
async function evaluate() {
  busy(true);
  try {
    const r = await api('/api/evaluate', {});
    $('evalResults').innerHTML =
      `<p class="notice">${esc(r.warning)}</p><h2>Owner classification · authored fixtures only</h2><div class="table-wrap"><table><thead><tr><th>Scenario</th><th>Cases</th><th>Accuracy</th><th>Brier ↓</th><th>ECE ↓</th></tr></thead><tbody>${Object.entries(
        r.by_pack,
      )
        .map(
          ([k, m]) =>
            `<tr><td>${esc(state.packs[k].name)}</td><td>${m.n}</td><td>${(m.accuracy * 100).toFixed(0)}%</td><td>${m.brier.toFixed(3)}</td><td>${m.ece_10.toFixed(3)}</td></tr>`,
        )
        .join(
          '',
        )}</tbody></table></div><p class="small">${esc(r.overall.definition)}</p><h2>Coverage is part of the result</h2><div class="table-wrap"><table><thead><tr><th>Threshold</th><th>Accepted</th><th>Coverage</th><th>Error among accepted</th></tr></thead><tbody>${r.overall.risk_coverage.map((x) => `<tr><td>${x.threshold.toFixed(2)}</td><td>${x.accepted}</td><td>${(x.coverage * 100).toFixed(0)}%</td><td>${x.error_rate === null ? 'No accepted cases' : (x.error_rate * 100).toFixed(1) + '%'}</td></tr>`).join('')}</tbody></table></div><p>This curve varies the owner threshold only, not the complete policy. No deployment risk estimate follows.</p><h2>Teaching notes</h2>${Object.entries(
        r.notes,
      )
        .map(([id, n]) => `<p><strong>${esc(id)}</strong> · ${esc(n)}</p>`)
        .join('')}`;
  } catch (e) {
    $('evalResults').textContent = e.message;
  } finally {
    busy(false);
  }
}
function tab(id) {
  document.querySelectorAll('.panel').forEach((x) => (x.hidden = x.id !== id));
  document.querySelectorAll('.nav').forEach((x) => {
    x.classList.toggle('active', x.dataset.tab === id);
    x.setAttribute('aria-current', x.dataset.tab === id ? 'page' : 'false');
  });
  error('');
}

/* Shared formatters used by the workbench and live.js */
const fmtMs = (v) => {
  if (v === null || v === undefined) return '–';
  return v >= 1000 ? `${(v / 1000).toFixed(2)} s` : `${Math.round(v)} ms`;
};
const fmtCost = (v) =>
  v === null || v === undefined ? 'Unknown' : v < 0.01 ? `$${v.toFixed(6)}` : `$${v.toFixed(4)}`;
const cents = (v) => (v === null || v === undefined ? '' : `≈ ${(v * 100).toFixed(3)}¢`);
const median = (xs) => {
  const a = xs.filter((x) => x !== null && x !== undefined).sort((x, y) => x - y);
  return a.length ? a[Math.floor((a.length - 1) / 2)] : null;
};

function syncThreshold(from) {
  const value = Number($(from).value);
  ['threshold', 'burstThreshold'].forEach((id) => {
    if ($(id) && id !== from) $(id).value = String(value);
  });
  $('thresholdValue').textContent = value.toFixed(2);
  $('burstThresholdValue').textContent = value.toFixed(2);
}
function consentHint() {
  $('consent').closest('label').classList.toggle('needed', $('mode').value === 'live');
  const liveWork =
    $('burstMode').value === 'live' || $('armNative').checked || $('armClaude').checked;
  $('liveConsent').closest('label').classList.toggle('needed', liveWork);
}
function downloadJSON(name, data) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob),
    a = document.createElement('a');
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

$('run').onclick = run;
$('reconsider').onclick = reconsider;
$('action').onclick = action;
$('gardenRun').onclick = garden;
$('evaluate').onclick = evaluate;
$('threshold').oninput = () => syncThreshold('threshold');
$('mode').onchange = consentHint;
$('consent').onchange = consentHint;
$('asOf').onchange = signals;
$('signalKind').onchange = signals;
document.querySelectorAll('.nav').forEach((b) => (b.onclick = () => tab(b.dataset.tab)));
$('connect').onclick = () => $('setup').showModal();
$('closeSetup').onclick = () => $('setup').close();
$('export').onclick = () => {
  if (!state.receipt) return;
  downloadJSON(`${state.caseId}-${state.receipt.provenance.kind}-receipt.json`, state.receipt);
};
