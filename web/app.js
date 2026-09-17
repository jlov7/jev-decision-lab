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
  ['run', 'evaluate', 'gardenRun', 'burstRun', 'pgRun', 'compareRun', 'pgAdd'].forEach(
    (id) => ($(id).disabled = value),
  );
  ['reconsider', 'export', 'action'].forEach((id) => ($(id).disabled = value || !state.receipt));
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
  if (!response.ok) throw new Error(data.error || `Request failed (${response.status})`);
  return data;
}
function provenance() {
  const p = state.receipt?.provenance;
  const live = p?.kind === 'live_typesafe';
  $('provenance').classList.toggle('live', live);
  $('provenance').textContent = live
    ? `Live TypeSafe result · ${state.receipt.response.model} · ${p.latency_ms.toFixed(0)} ms client-observed · Price estimate, not an invoice`
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
function selectCase(id) {
  state.caseId = id;
  state.receipt = null;
  error('');
  $('variant').value = 'original';
  queue();
  const c = state.cases.find((x) => x.id === id);
  $('caseId').textContent = id;
  $('caseTitle').textContent = c.title;
  $('message').textContent = c.state.message;
  $('evidence').innerHTML = c.state.evidence
    .map((e) => `<div class="source"><strong>${esc(e.id)}</strong>${esc(e.text)}</div>`)
    .join('');
  $('route').textContent = 'Ready to inspect';
  $('routeText').textContent = 'Run this case to inspect the model–policy boundary.';
  ['decisionMetrics', 'nextEvidence', 'trace', 'actionResult'].forEach(
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
  $('route').textContent = routes[d.route][0];
  $('routeText').textContent = routes[d.route][1];
  $('callCount').textContent = r.additional_model_calls
    ? `${r.additional_model_calls} new model call`
    : '0 new model calls';
  $('decisionMetrics').innerHTML =
    metric('Suggested owner', d.owner) +
    metric('Top-owner probability', `${(d.owner_probability * 100).toFixed(0)}%`) +
    metric('Critical consequence probability', `${(d.critical_probability * 100).toFixed(0)}%`);
  if (p.kind === 'live_typesafe')
    $('decisionMetrics').innerHTML +=
      metric('Observed input tokens', p.usage.input_tokens) +
      metric(
        'Estimated inference cost',
        p.estimated_cost_usd === null ? 'Unknown' : '$' + p.estimated_cost_usd.toFixed(7),
      );
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
    error(
      e.message +
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

/* ---------------- Live lab ---------------- */
const fmtMs = (v) =>
  v === null || v === undefined
    ? '–'
    : v >= 1000
      ? `${(v / 1000).toFixed(2)} s`
      : `${Math.round(v)}`;
const fmtCost = (v) =>
  v === null || v === undefined ? 'Unknown' : v < 0.01 ? `$${v.toFixed(6)}` : `$${v.toFixed(4)}`;
const cents = (v) => (v === null || v === undefined ? '' : `≈ ${(v * 100).toFixed(3)}¢`);
const median = (xs) => {
  const a = xs.filter((x) => x !== null && x !== undefined).sort((x, y) => x - y);
  return a.length ? a[Math.floor((a.length - 1) / 2)] : null;
};
function setStatus(id, text, on) {
  const el = $(id);
  el.textContent = text;
  el.className = on ? 'on' : 'off';
}
function liveStatus() {
  const c = state.config;
  setStatus(
    'jevStatus',
    c.live_enabled ? `Live · ${c.model}` : 'Offline · key not in this server process',
    c.live_enabled,
  );
  const claudeOn = c.compare_enabled && c.compare_sdk_available;
  setStatus(
    'claudeStatus',
    claudeOn
      ? `Live · ${c.compare_model}`
      : c.compare_enabled
        ? 'Key present · run uv sync --extra compare'
        : 'Offline · ANTHROPIC_API_KEY not set',
    claudeOn,
  );
  $('attemptStatus').textContent =
    `${c.live_attempts} of ${c.live_attempt_limit} Jev · ${c.compare_attempts} of ${c.compare_attempt_limit} Claude`;
  $('armClaudeModel').textContent = c.compare_model;
  if (!state.liveInitialised) {
    $('burstMode').value = c.live_enabled ? 'live' : 'replay';
    $('armNative').checked = c.live_enabled;
    $('armClaude').checked = claudeOn;
    $('armReplay').checked = !c.live_enabled;
    state.liveInitialised = true;
  }
}
async function refreshConfig() {
  state.config = await api('/api/config');
  liveStatus();
}
function tile(id, text, tone) {
  const el = $(id);
  el.textContent = text;
  el.className = tone || '';
}
async function burst() {
  error('');
  busy(true);
  const mode = $('burstMode').value;
  try {
    if (mode === 'live' && !state.config.live_enabled)
      throw new Error('Live mode is not configured in this server process. Open How to connect.');
    const r = await api('/api/burst', {
      mode,
      consent: $('liveConsent').checked,
      threshold: Number($('threshold').value),
    });
    renderBurst(r);
    await refreshConfig();
  } catch (e) {
    error(e.message);
  } finally {
    busy(false);
  }
}
function renderBurst(r) {
  const s = r.summary,
    live = r.kind === 'live_typesafe',
    dim = live ? '' : 'dim';
  tile('tP50', fmtMs(s.latency_ms.p50), dim);
  tile('tP95', fmtMs(s.latency_ms.p95), dim);
  tile('tWall', live ? fmtMs(r.wall_ms) : '–', dim);
  tile('tTokens', s.input_tokens === null ? '–' : s.input_tokens.toLocaleString(), dim);
  tile('tCost', live ? fmtCost(s.estimated_cost_usd) : '–', dim);
  $('tCostNote').textContent = live
    ? s.estimated_cost_usd === null
      ? `${s.cost_unknown_cases} case(s) unknown`
      : `${cents(s.estimated_cost_usd)} · dated public price`
    : 'no model call';
  tile('tCalls', `${s.succeeded} · ${s.failed}`, s.failed ? 'warn' : dim);
  $('tCallsNote').textContent = live
    ? `${s.model_calls} model calls · ${r.concurrency} concurrent`
    : 'replay · 0 model calls';
  $('burstProvenance').textContent = live
    ? `Live TypeSafe · ${s.models.join(', ')} · ${r.warning}`
    : r.warning;
  const max = Math.max(1, ...r.results.map((x) => x.latency_ms || 0));
  $('burstRows').innerHTML = r.results
    .map((x) => {
      const c = state.cases.find((k) => k.id === x.case_id) || { title: x.case_id };
      if (!x.ok)
        return `<div class="burst-row fail"><code>${esc(x.case_id)}</code><span class="title">${esc(c.title)}</span><span class="owner">–</span><span class="badge fail">Failed · cost unknown</span><div class="bar"><i class="none"></i></div><span class="ms none">–</span><span class="err">${esc(x.error)}</span></div>`;
      const pct = x.latency_ms ? Math.max(3, (x.latency_ms / max) * 100) : 0;
      const owner = `${esc(x.owner)} ${(x.owner_probability * 100).toFixed(0)}%`;
      return `<div class="burst-row"><code>${esc(x.case_id)}</code><span class="title">${esc(c.title)}</span><span class="owner">${owner}</span><span class="badge ${x.route === 'ROUTE_TO_TEAM' ? '' : 'hold'}">${esc(routes[x.route][0])}</span><div class="bar">${x.latency_ms === null ? '<i class="none"></i>' : `<i data-w="${pct}"></i>`}</div><span class="ms ${x.latency_ms === null ? 'none' : ''}">${fmtMs(x.latency_ms)}</span></div>`;
    })
    .join('');
  requestAnimationFrame(() =>
    requestAnimationFrame(() =>
      document
        .querySelectorAll('.bar i[data-w]')
        .forEach((i) => (i.style.width = `${i.dataset.w}%`)),
    ),
  );
}
/* playground */
const pg = { questions: [] };
const PG_BLANK = {
  state:
    'Synthetic example. Supplier email: the replacement pump ships Friday and arrives Monday. Carrier portal: no booking exists for this order. Production note: the customer line stops on Thursday if the pump is not installed.',
  questions: [
    {
      id: 'team',
      type: 'choice',
      instructions: 'Which team should investigate? Use only the supplied state.',
      criteria:
        'operations: Delivery planning and logistics\nprocurement: Supplier terms and commitments\nother: No listed team fits',
    },
    {
      id: 'severity',
      type: 'score',
      instructions: 'How consequential is the evidenced situation?',
      criteria:
        'No material consequence\nLimited disruption with a workaround\nMaterial disruption to a delivery\nCritical: production stops',
    },
    {
      id: 'conflict',
      type: 'noul',
      instructions: 'Do the supplier claim and the carrier record materially disagree?',
      criteria: '',
    },
  ],
};
const PG_PRESET_CASE = { supply: 'S02', service: 'T01', review: 'Q01' };
const critToText = (q) =>
  q.type === 'score'
    ? q.criteria.join('\n')
    : q.criteria
      ? Object.entries(q.criteria)
          .map(([k, v]) => `${k}: ${v}`)
          .join('\n')
      : '';
function pgPreset(pack) {
  if (!pack) {
    $('pgState').value = PG_BLANK.state;
    pg.questions = PG_BLANK.questions.map((q) => ({ ...q }));
  } else {
    const c = state.cases.find((x) => x.id === PG_PRESET_CASE[pack]);
    $('pgState').value =
      `${c.state.message}\n\nEvidence:\n${c.state.evidence.map((e) => `- ${e.text}`).join('\n')}`;
    pg.questions = Object.entries(state.packs[pack].questions).map(([id, q]) => ({
      id,
      type: q.type,
      instructions: q.instructions,
      criteria: critToText(q),
    }));
  }
  pgRender();
}
const PG_HINT = {
  choice: 'One option per line as key: description. Keys become the answer vocabulary.',
  score:
    'One ordered level per line, least to most. The answer is a probability-weighted level index.',
  noul: 'Optional: two lines, true: … and false: …, to pin down what yes and no mean.',
};
function pgRender() {
  $('pgCount').textContent = `${pg.questions.length} of 8`;
  $('pgAdd').disabled = pg.questions.length >= 8 || state.busy;
  $('pgQuestions').innerHTML = pg.questions
    .map(
      (q, i) => `<div class="q-card" data-i="${i}">
<input class="q-id" value="${esc(q.id)}" aria-label="Question id" placeholder="question_id" maxlength="32">
<select class="q-type" aria-label="Question type"><option value="choice"${q.type === 'choice' ? ' selected' : ''}>Choice · pick one option</option><option value="score"${q.type === 'score' ? ' selected' : ''}>Score · ordered levels</option><option value="noul"${q.type === 'noul' ? ' selected' : ''}>Noul · probability of yes</option></select>
<button class="remove" aria-label="Remove question ${i + 1}" title="Remove">×</button>
<input class="q-instr" value="${esc(q.instructions)}" aria-label="Instructions" placeholder="The question, in plain words" maxlength="1500">
<textarea class="q-crit" aria-label="Criteria" placeholder="${esc(PG_HINT[q.type])}">${esc(q.criteria)}</textarea>
<p class="hint">${esc(PG_HINT[q.type])}</p></div>`,
    )
    .join('');
  $('pgQuestions')
    .querySelectorAll('.q-card')
    .forEach((card) => {
      const i = Number(card.dataset.i),
        q = pg.questions[i];
      card.querySelector('.q-id').oninput = (e) => (q.id = e.target.value.trim());
      card.querySelector('.q-instr').oninput = (e) => (q.instructions = e.target.value);
      card.querySelector('.q-crit').oninput = (e) => (q.criteria = e.target.value);
      card.querySelector('.q-type').onchange = (e) => {
        q.type = e.target.value;
        pgRender();
      };
      card.querySelector('.remove').onclick = () => {
        pg.questions.splice(i, 1);
        pgRender();
      };
    });
}
function pgCollect() {
  const questions = {};
  pg.questions.forEach((q, n) => {
    if (!q.id) throw new Error(`Question ${n + 1} needs a short snake_case id.`);
    if (questions[q.id]) throw new Error(`Question id "${q.id}" is used twice.`);
    const lines = q.criteria
      .split('\n')
      .map((l) => l.trim())
      .filter(Boolean);
    const entry = { type: q.type, instructions: q.instructions.trim() };
    if (q.type === 'score') entry.criteria = lines;
    else if (lines.length) {
      entry.criteria = {};
      for (const line of lines) {
        const m = line.match(/^([^:]+):\s*(.+)$/);
        if (!m)
          throw new Error(`"${q.id}": write each option as key: description (got "${line}").`);
        entry.criteria[m[1].trim()] = m[2].trim();
      }
    } else if (q.type === 'choice') throw new Error(`"${q.id}" needs at least two options.`);
    questions[q.id] = entry;
  });
  return { state: $('pgState').value, questions };
}
async function pgRun() {
  error('');
  busy(true);
  try {
    if (!state.config.live_enabled)
      throw new Error(
        'The playground needs a live connection. Open How to connect; there is no replay for your own text.',
      );
    const body = pgCollect();
    const r = await api('/api/playground', { ...body, consent: $('liveConsent').checked });
    renderPg(r);
    await refreshConfig();
  } catch (e) {
    error(e.message);
  } finally {
    busy(false);
    pgRender();
  }
}
function renderPg(r) {
  const p = r.provenance;
  $('pgMeta').innerHTML =
    `<span>Model <b>${esc(r.response.model)}</b></span><span>Latency <b>${fmtMs(p.latency_ms)} ms</b></span><span>Input tokens <b>${esc(p.usage.input_tokens)}</b></span><span>Cost <b>${fmtCost(p.estimated_cost_usd)}</b> ${esc(cents(p.estimated_cost_usd))}</span><span>Request hash <b>${esc(r.request_hash.slice(0, 12))}</b></span>`;
  $('pgAnswers').innerHTML = Object.entries(r.response.answers)
    .map(([id, a]) => answerBlock(id, id, a, r.request.questions[id].instructions))
    .join('');
  $('pgRaw').textContent = JSON.stringify(
    { request: r.request, response: r.response, provenance: r.provenance, warning: r.warning },
    null,
    2,
  );
  $('pgRawWrap').hidden = false;
}
/* compare */
async function compareRun() {
  error('');
  const arms = [
    $('armNative').checked && 'native',
    $('armClaude').checked && 'claude',
    $('armReplay').checked && 'replay',
  ].filter(Boolean);
  if (!arms.length) return error('Choose at least one arm to compare.');
  if (arms.includes('native') && !state.config.live_enabled)
    return error(
      'Jev is not connected in this server process. Open How to connect, or untick the Jev arm.',
    );
  if (
    arms.includes('claude') &&
    !(state.config.compare_enabled && state.config.compare_sdk_available)
  )
    return error(
      'The Claude baseline is not configured. Open How to connect, or untick the Claude arm.',
    );
  busy(true);
  try {
    const r = await api('/api/compare', { arms, case_ids: [], consent: $('liveConsent').checked });
    renderCompare(r);
    await refreshConfig();
  } catch (e) {
    error(e.message);
  } finally {
    busy(false);
  }
}
const ARM_LABEL = {
  native: 'Jev · native API',
  claude: 'Claude · structured output',
  replay: 'Synthetic replay',
  gateway: 'Vercel AI Gateway',
};
function renderCompare(r) {
  const expected = r.expected_owner;
  $('compareSummary').innerHTML = r.arms
    .map((arm) => {
      const rows = arm.cases || [];
      const agree = rows.filter((x) => x.answers.owner === expected[x.case_id]).length;
      const costs = rows.map((x) => x.estimated_cost_usd);
      const known = costs.filter((c) => c !== null && c !== undefined);
      const model = rows[0]?.model || arm.pinned_version;
      const fails = arm.failures
        .slice(0, 2)
        .map((f) => `<p class="compare-fail">${esc(f.case_id)}: ${esc(f.error)}</p>`)
        .join('');
      return `<div class="arm-card ${arm.failed ? 'failing' : ''}"><h3>${esc(ARM_LABEL[arm.name] || arm.name)}<small>${esc(model)}</small></h3>${metric('Answered', `${arm.succeeded} / ${arm.attempts}`)}${metric('Owner agrees with label', arm.succeeded ? `${agree} / ${arm.succeeded}` : '–')}${metric('Median latency', rows.length && median(rows.map((x) => x.latency_ms)) !== null ? `${fmtMs(median(rows.map((x) => x.latency_ms)))} ms` : '–')}${metric('Total cost', arm.kind === 'synthetic_replay' ? 'No call' : known.length ? `${fmtCost(known.reduce((a, b) => a + b, 0))}${known.length < rows.length ? ' +?' : ''}` : rows.length ? 'Unknown' : '–')}${fails}${arm.failed > 2 ? `<p class="compare-fail">…and ${arm.failed - 2} more failures retained in the report.</p>` : ''}</div>`;
    })
    .join('');
  const head = r.arms.map((a) => `<th>${esc(ARM_LABEL[a.name] || a.name)}</th>`).join('');
  const body = r.cases
    .map((id) => {
      const c = state.cases.find((k) => k.id === id) || { title: id };
      const cells = r.arms
        .map((arm) => {
          const row = (arm.cases || []).find((x) => x.case_id === id);
          if (!row) {
            const f = arm.failures.find((x) => x.case_id === id);
            return `<td class="na" title="${esc(f ? f.error : '')}">failed<span class="cell-sub">cost unknown</span></td>`;
          }
          const ok = row.answers.owner === expected[id];
          return `<td class="${ok ? 'agree' : 'disagree'}">${esc(row.answers.owner)}<span class="cell-sub">${row.latency_ms === null ? 'no call' : `${fmtMs(row.latency_ms)} ms`} · ${row.estimated_cost_usd === null ? 'cost n/a' : fmtCost(row.estimated_cost_usd)}</span></td>`;
        })
        .join('');
      return `<tr><td><strong>${esc(id)}</strong><span class="cell-sub">${esc(c.title)}</span></td><td>${esc(expected[id])}</td>${cells}</tr>`;
    })
    .join('');
  $('compareTable').innerHTML =
    `<table><thead><tr><th>Case</th><th>Teaching label</th>${head}</tr></thead><tbody>${body}</tbody></table>`;
  $('compareWarnings').textContent = r.warnings.join(' ');
}

$('run').onclick = run;
$('reconsider').onclick = reconsider;
$('action').onclick = action;
$('gardenRun').onclick = garden;
$('evaluate').onclick = evaluate;
$('threshold').oninput = () =>
  ($('thresholdValue').textContent = Number($('threshold').value).toFixed(2));
$('asOf').onchange = signals;
$('signalKind').onchange = signals;
document.querySelectorAll('.nav').forEach((b) => (b.onclick = () => tab(b.dataset.tab)));
$('connect').onclick = () => $('setup').showModal();
$('connectLive').onclick = () => $('setup').showModal();
$('burstRun').onclick = burst;
$('pgRun').onclick = pgRun;
$('compareRun').onclick = compareRun;
$('pgAdd').onclick = () => {
  if (pg.questions.length < 8)
    pg.questions.push({ id: '', type: 'noul', instructions: '', criteria: '' });
  pgRender();
};
$('pgPreset').onchange = () => pgPreset($('pgPreset').value);
$('closeSetup').onclick = () => $('setup').close();
$('export').onclick = () => {
  const blob = new Blob([JSON.stringify(state.receipt, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob),
    a = document.createElement('a');
  a.href = url;
  a.download = `${state.caseId}-${state.receipt.provenance.kind}-receipt.json`;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
};
(async () => {
  try {
    state.config = await api('/api/config');
    const c = await api('/api/cases');
    state.cases = c.cases;
    state.packs = c.packs;
    const s = await api('/api/signals');
    state.signals = s.signals;
    $('signalWarning').textContent = s.warning;
    domains();
    selectCase('S01');
    signals();
    liveStatus();
    pgPreset('');
    $('liveStatus').textContent = state.config.live_enabled
      ? `Key and enable flag present; account access remains unverified. Model ${state.config.model}. Process attempt cap ${state.config.live_attempt_limit}.`
      : 'This server is offline-only. Your account is not connected to this process.';
  } catch (e) {
    error('Initialization failed: ' + e.message);
  }
})();
