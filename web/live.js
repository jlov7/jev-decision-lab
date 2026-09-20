'use strict';
function setStatus(id, text, on) {
  const el = $(id);
  el.textContent = text;
  el.className = on ? 'on' : 'off';
}
function liveStatus() {
  const c = state.config;
  setStatus(
    'jevStatus',
    c.live_enabled ? `Live · ${c.model}` : 'Offline · no key in this server process',
    c.live_enabled,
  );
  const b = c.baselines || {};
  const on = Object.entries(b).filter(([, v]) => v.enabled);
  const claudeOn = on.length > 0;
  setStatus(
    'claudeStatus',
    claudeOn
      ? on.map(([k, v]) => `${BASELINE_SHORT[k] || k} · ${v.model}`).join(' · ')
      : 'None configured · see How to connect',
    claudeOn,
  );
  $('attemptStatus').textContent =
    `${c.live_attempts} of ${c.live_attempt_limit} Jev · ${c.compare_attempts} of ${c.compare_attempt_limit} generative`;
  $('armClaudeModel').textContent = (b.claude || {}).model || c.compare_model;
  $('armClaudeCodeModel').textContent = (b['claude-code'] || {}).model || '';
  $('armOpenAIModel').textContent = (b.openai || {}).model || '';
  if (c.lab_version) document.querySelector('.brand > span').textContent = c.lab_version;
  connectionUi(c);
  if (state.cases.length) expCases();
  if (!state.expInitialised) {
    $('expMode').value = c.live_enabled ? 'live' : 'replay';
    state.expInitialised = true;
  }
  if (!state.liveInitialised) {
    $('burstMode').value = c.live_enabled ? 'live' : 'replay';
    $('armNative').checked = c.live_enabled;
    $('armClaude').checked = Boolean((b.claude || {}).enabled);
    $('armClaudeCode').checked = Boolean((b['claude-code'] || {}).enabled);
    $('armOpenAI').checked = Boolean((b.openai || {}).enabled);
    $('armReplay').checked = !c.live_enabled;
    $('armRules').checked = !c.live_enabled;
    state.liveInitialised = true;
  }
  consentHint();
}
async function refreshConfig() {
  state.config = await api('/api/config');
  liveStatus();
}
/* experiments */
function expCases() {
  if ($('expCase').options.length) return;
  $('expCase').innerHTML = state.cases
    .map((c) => `<option value="${esc(c.id)}">${esc(c.id)} · ${esc(c.title)}</option>`)
    .join('');
  $('expCase').value = 'S02';
}
function expGuard(mode, needed) {
  if (mode !== 'live') return null;
  if (!state.config.live_enabled)
    return 'Jev is not connected in this server process. Open Connect Jev, or switch to replay to see the layout.';
  if (!$('liveConsent').checked) return 'Tick the consent box at the top of Live lab first.';
  const remaining = state.config.live_attempt_limit - state.config.live_attempts;
  if (remaining < needed)
    return `This needs ${needed} Jev attempt slots and ${remaining} remain in this server process. Nothing was sent.`;
  return null;
}
const rangeBar = (o, label) =>
  `<div class="range-row"><span class="range-label">${esc(label)}</span><div class="range-track"><i class="range-span" data-lo="${o.min}" data-hi="${o.max}"></i><b class="range-mid" data-at="${o.median}"></b></div><span class="range-nums">${o.min.toFixed(2)}–${o.max.toFixed(2)}</span></div>`;
function placeRanges(root) {
  root.querySelectorAll('.range-span').forEach((el) => {
    const lo = Number(el.dataset.lo), hi = Number(el.dataset.hi);
    el.style.left = `${(lo * 100).toFixed(1)}%`;
    el.style.width = `${Math.max(0.8, (hi - lo) * 100).toFixed(1)}%`;
  });
  root.querySelectorAll('.range-mid').forEach((el) => {
    el.style.left = `${(Number(el.dataset.at) * 100).toFixed(1)}%`;
  });
}
async function probeRun() {
  error('');
  const mode = $('expMode').value, repeats = Number($('probeRepeats').value);
  const blocked = expGuard(mode, repeats);
  if (blocked) return error(blocked);
  busy(true);
  try {
    const r = await api('/api/probe', {
      case_id: $('expCase').value,
      repeats,
      mode,
      consent: $('liveConsent').checked,
      threshold: Number($('burstThreshold').value),
    });
    state.lastProbe = r;
    renderProbe(r);
    $('exportProbe').disabled = false;
    await refreshConfig();
  } catch (e) {
    error(e.message);
  } finally {
    busy(false);
  }
}
function renderProbe(r) {
  const live = r.mode === 'live';
  const routeText = Object.entries(r.routes)
    .map(([k, n]) => `${routes[k][0]} in ${n} of ${r.succeeded}`)
    .join(', ');
  $('probeSummary').textContent =
    `${r.case_id} · ${r.succeeded} of ${r.requested} answered` +
    (live ? ` · p50 ${fmtMs(r.latency_ms.p50)} · ${r.estimated_cost_usd === null ? 'cost unknown' : cents(r.estimated_cost_usd)}` : '') +
    ` · ${r.complete ? 'complete' : 'incomplete: stability not established'} · ${r.comparable ? 'same observed contract' : 'mixed contracts: spread withheld'} · route: ${routeText || 'none'}` +
    (r.widest_option_range.question
      ? ` · widest range ${r.widest_option_range.range.toFixed(2)} on ${names[r.widest_option_range.question] || r.widest_option_range.question}`
      : '') +
    ` · ${r.warning}`;
  const blocks = Object.entries(r.spread).map(([qid, s]) => {
    let rows = '';
    if (s.type === 'noul') rows = rangeBar(s.value, 'probability of yes');
    else if (s.type === 'score') {
      rows = Object.entries(s.options).map(([k, o]) => rangeBar(o, `level ${k}`)).join('');
      rows += `<p class="small">Weighted score ${s.value.min.toFixed(2)}–${s.value.max.toFixed(2)}</p>`;
    } else {
      rows = Object.entries(s.options)
        .sort((a, b) => b[1].median - a[1].median)
        .map(([k, o]) => rangeBar(o, k))
        .join('');
      if (s.top_choices.length > 1)
        rows += `<p class="small warn-text">Top choice changed between calls: ${s.top_choices.map(esc).join(', ')}</p>`;
    }
    return `<div class="probe-q"><h4>${esc(names[qid] || qid)} <span class="type">${esc(s.type)}</span></h4>${rows}</div>`;
  });
  $('probeRows').innerHTML = blocks.join('');
  placeRanges($('probeRows'));
  if (r.failures.length)
    $('probeRows').innerHTML += `<p class="warn-text">${r.failures.length} call(s) failed and were kept: ${esc(r.failures.map((f) => f.error).join(' · '))}</p>`;
}
async function ablateRun() {
  error('');
  const mode = $('expMode').value;
  const c = state.cases.find((x) => x.id === $('expCase').value);
  const blocked = expGuard(mode, 1 + c.state.evidence.length);
  if (blocked) return error(blocked);
  busy(true);
  try {
    const r = await api('/api/ablate', {
      case_id: c.id,
      mode,
      consent: $('liveConsent').checked,
      threshold: Number($('burstThreshold').value),
    });
    state.lastAblate = r;
    renderAblate(r, c);
    $('exportAblate').disabled = false;
    await refreshConfig();
  } catch (e) {
    error(e.message);
  } finally {
    busy(false);
  }
}
function renderAblate(r, c) {
  const most = r.most_influential;
  $('ablateSummary').textContent =
    `${r.case_id} · ${r.succeeded} of ${r.requested} variants answered · ` +
    (most
      ? `largest observed probability movement: ${most}.`
      : r.mode === 'live'
        ? 'no variant exceeded the descriptive reference, or comparison was unavailable.'
        : 'replay layout only.') +
    ` Descriptive reference ${r.noise_floor.toFixed(2)}. ${r.warning}`;
  const delta = (v, key) => {
    if (!v.deltas) return '<td>–</td>';
    const d = v.deltas[key];
    const cls = Math.abs(d) < r.noise_floor ? 'noise' : d > 0 ? 'up' : 'down';
    return `<td class="${cls}">${d > 0 ? '+' : ''}${d.toFixed(2)}</td>`;
  };
  const rows = r.variants
    .map((v) => {
      if (!v.ok)
        return `<tr class="fail"><td>${esc(v.label)}</td><td colspan="7">${esc(v.error)}</td></tr>`;
      const a = v.answers;
      const lead = most && v.removed_evidence && v.removed_evidence.id === most ? ' class="lead"' : '';
      const text = v.removed_evidence ? `<span class="cell-sub">${esc(v.removed_evidence.text)}</span>` : '<span class="cell-sub">every excerpt present</span>';
      return `<tr${lead}><td><b>${esc(v.label)}</b>${text}</td><td class="${v.owner_changed ? 'changed' : ''}">${esc(a.owner)} ${(a.owner_probability * 100).toFixed(0)}%${delta(v, 'owner_probability').replace(/<\/?td[^>]*>/g, ' ')}</td><td>${a.severity.toFixed(2)}${delta(v, 'severity').replace(/<\/?td[^>]*>/g, ' ')}</td><td>${a.sufficient.toFixed(2)}${delta(v, 'sufficient').replace(/<\/?td[^>]*>/g, ' ')}</td><td>${a.contradiction.toFixed(2)}${delta(v, 'contradiction').replace(/<\/?td[^>]*>/g, ' ')}</td><td class="${v.route_changed ? 'changed' : ''}">${esc(routes[a.route][0])}</td><td>${v.deltas ? (v.above_noise ? `<b>${v.movement.toFixed(2)}</b>` : `<span class="noise">${v.movement.toFixed(2)} below reference</span>`) : '–'}</td></tr>`;
    })
    .join('');
  $('ablateRows').innerHTML = `<table class="ablate-table"><thead><tr><th>Variant</th><th>Owner · Δ for baseline label</th><th>Severity (Δ)</th><th>Sufficient (Δ)</th><th>Contradiction (Δ)</th><th>Route</th><th>Movement</th></tr></thead><tbody>${rows}</tbody></table>`;
}
function connectionUi(c) {
  const connected = Boolean(c.live_enabled);
  const fromTerminal = c.key_source === 'terminal';
  $('connect').textContent = connected ? `Connected · ····${c.key_hint}` : 'Connect Jev ↗';
  $('connect').classList.toggle('connected', connected);
  $('apiKey').disabled = fromTerminal;
  $('connectSubmit').disabled = fromTerminal;
  $('forgetKey').hidden = c.key_source !== 'browser';
  $('connectStatus').textContent = fromTerminal
    ? `Connected with the key from this server's terminal (ending ····${c.key_hint}). The paste box is disabled while it is set.`
    : connected
      ? `Connected. Key ending ····${c.key_hint} is held in this server's memory only. Open Live lab, tick consent, and fire the burst.`
      : 'Not connected. Paste a key to enable live calls in this server process.';
}
async function connectSubmit(event) {
  event.preventDefault();
  const field = $('apiKey');
  const key = field.value;
  field.value = '';
  if (!key.trim()) return ($('connectStatus').textContent = 'Paste a key first.');
  $('connectSubmit').disabled = true;
  try {
    await api('/api/connect', { api_key: key });
    state.liveInitialised = false;
    await refreshConfig();
  } catch (e) {
    $('connectStatus').textContent = e.message;
  } finally {
    $('connectSubmit').disabled = state.config.key_source === 'terminal';
  }
}
async function forgetKey() {
  try {
    await api('/api/disconnect', {});
    state.liveInitialised = false;
    await refreshConfig();
  } catch (e) {
    $('connectStatus').textContent = e.message;
  }
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
      threshold: Number($('burstThreshold').value),
    });
    state.lastBurst = r;
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
  const cost = s.estimated_cost_usd;
  const subCent = live && cost !== null && cost < 0.01;
  tile('tCost', live ? (subCent ? `${(cost * 100).toFixed(3)}¢` : fmtCost(cost)) : '–', dim);
  $('tCostNote').textContent = live
    ? cost === null
      ? `${s.cost_unknown_cases} case(s) unknown`
      : `${subCent ? fmtCost(cost) : cents(cost)} · dated public price`
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
      if (!x.ok) {
        const answered = Boolean(x.provider_response);
        const badge = answered
          ? `Answered · failed validation${x.cost_unknown ? '' : ` · ${cents(x.estimated_cost_usd)}`}`
          : 'Failed · cost unknown';
        const raw = answered
          ? `<details class="burst-raw"><summary>Provider response retained for inspection</summary><pre>${esc(JSON.stringify(x.provider_response, null, 2))}</pre></details>`
          : '';
        return `<div class="burst-row fail"><code>${esc(x.case_id)}</code><span class="title">${esc(c.title)}</span><span class="owner">–</span><span class="badge fail">${badge}</span><div class="bar"><i class="none"></i></div><span class="ms ${x.latency_ms == null ? 'none' : ''}">${x.latency_ms == null ? '–' : fmtMs(x.latency_ms)}</span><span class="err">${esc(x.error)}</span>${raw}</div>`;
      }
      const pct = x.latency_ms ? Math.max(3, (x.latency_ms / max) * 100) : 0;
      const owner = `${esc(x.owner)} ${(x.owner_probability * 100).toFixed(0)}%`;
      return `<button type="button" class="burst-row inspectable" data-receipt="${esc(x.receipt_id)}" data-case="${esc(x.case_id)}" aria-label="Inspect ${esc(x.case_id)} on the workbench"><code>${esc(x.case_id)}</code><span class="title">${esc(c.title)}</span><span class="owner">${owner}</span><span class="badge ${x.route === 'ROUTE_TO_TEAM' ? '' : 'hold'}">${esc(routes[x.route][0])}</span><div class="bar">${x.latency_ms === null ? '<i class="none"></i>' : `<i data-w="${pct}"></i>`}</div><span class="ms ${x.latency_ms === null ? 'none' : ''}">${fmtMs(x.latency_ms)}</span></button>`;
    })
    .join('');
  $('burstRows')
    .querySelectorAll('button.inspectable')
    .forEach((row) => {
      row.onclick = () => inspectBurst(row.dataset.receipt, row.dataset.case);
    });
  requestAnimationFrame(() =>
    requestAnimationFrame(() =>
      document
        .querySelectorAll('.bar i[data-w]')
        .forEach((i) => (i.style.transform = `scaleX(${Number(i.dataset.w) / 100})`)),
    ),
  );
}
async function inspectBurst(receiptId, caseId) {
  error('');
  busy(true);
  try {
    const receipt = await api('/api/receipt', { receipt_id: receiptId });
    fillCaseView(caseId);
    $('variant').value = receipt.decision.variant || 'original';
    $('threshold').value = receipt.decision.threshold;
    syncThreshold('threshold');
    state.receipt = receipt;
    tab('workbench');
    render();
  } catch (e) {
    error(e.message);
  } finally {
    busy(false);
  }
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
      card.querySelector('.q-id').oninput = (e) => {
        q.id = e.target.value.trim();
        pgBytes();
      };
      card.querySelector('.q-instr').oninput = (e) => {
        q.instructions = e.target.value;
        pgBytes();
      };
      card.querySelector('.q-crit').oninput = (e) => {
        q.criteria = e.target.value;
        pgBytes();
      };
      card.querySelector('.q-type').onchange = (e) => {
        q.type = e.target.value;
        pgRender();
      };
      card.querySelector('.remove').onclick = () => {
        pg.questions.splice(i, 1);
        pgRender();
      };
    });
  pgBytes();
}
function pgBytes() {
  const el = $('pgBytes');
  if (!el || !state.config) return;
  try {
    const body = { ...pgCollect(), consent: true };
    const envelope = new TextEncoder().encode(JSON.stringify(body)).length;
    const payload = new TextEncoder().encode(
      JSON.stringify({
        model: state.config.model,
        state: body.state,
        questions: body.questions,
      }),
    ).length;
    const http = state.config.http_body_limit || 16384;
    const provider = state.config.provider_input_limit || 16000;
    el.textContent = `${envelope.toLocaleString()} / ${http.toLocaleString()} HTTP · ${payload.toLocaleString()} / ${provider.toLocaleString()} provider`;
    el.classList.toggle('warn', envelope > http || payload > provider);
  } catch {
    el.textContent = 'Complete the questions to count bytes against the lab ceilings.';
    el.classList.remove('warn');
  }
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
    state.lastPlayground = r;
    renderPg(r);
    await refreshConfig();
  } catch (e) {
    if (e.detail) {
      state.lastPlayground = {failure:true, detail:e.detail, warning:'Live request failed. Details retained; no retry or fallback.'};
      $('pgMeta').textContent = 'Live request failed. Export retains the failure details.';
      $('pgAnswers').textContent = JSON.stringify(e.detail, null, 2);
    }
    error(e.message);
  } finally {
    busy(false);
    pgRender();
  }
}
function renderPg(r) {
  const p = r.provenance;
  const tokens =
    p.usage && typeof p.usage.input_tokens === 'number' ? p.usage.input_tokens : 'Unknown';
  $('pgMeta').innerHTML =
    `<span>Model <b>${esc(r.response.model)}</b></span><span>Latency <b>${fmtMs(p.latency_ms)}</b></span><span>Input tokens <b>${esc(tokens)}</b></span><span>Cost <b>${fmtCost(p.estimated_cost_usd)}</b> ${esc(cents(p.estimated_cost_usd))}</span><span>Request hash <b>${esc(r.request_hash.slice(0, 12))}</b></span>`;
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
    $('armClaudeCode').checked && 'claude-code',
    $('armClaude').checked && 'claude',
    $('armOpenAI').checked && 'openai',
    $('armReplay').checked && 'replay',
    $('armRules').checked && 'rules',
  ].filter(Boolean);
  if (!arms.length) return error('Choose at least one arm to compare.');
  if (arms.includes('native') && !state.config.live_enabled)
    return error('Jev is not connected in this server process. Open Connect Jev, or untick the Jev arm.');
  const remaining = state.config.live_attempt_limit - state.config.live_attempts;
  if (arms.includes('native') && remaining < state.cases.length)
    return error(
      `Compare needs ${state.cases.length} Jev attempt slots and ${remaining} remain in this server process. Nothing was sent. Restart the server, or start it with a higher JEV_MAX_LIVE_CALLS.`,
    );
  const baselines = state.config.baselines || {};
  for (const name of ['claude-code', 'claude', 'openai']) {
    if (arms.includes(name) && !(baselines[name] && baselines[name].enabled))
      return error(
        `${ARM_LABEL[name]} is not configured: it needs ${(baselines[name] || {}).needs || 'setup'}. Open How to connect, or untick that arm.`,
      );
  }
  const generative = arms.filter((n) => ['claude-code', 'claude', 'openai'].includes(n)).length;
  const left = state.config.compare_attempt_limit - state.config.compare_attempts;
  if (generative && left < generative * state.cases.length)
    return error(
      `Compare needs ${generative * state.cases.length} generative attempt slots and ${left} remain in this server process. Nothing was sent. Restart with a higher JEV_MAX_COMPARE_CALLS.`,
    );
  busy(true);
  try {
    const r = await api('/api/compare', { arms, case_ids: [], consent: $('liveConsent').checked });
    state.lastCompare = r;
    renderCompare(r);
    await refreshConfig();
  } catch (e) {
    error(e.message);
  } finally {
    busy(false);
  }
}
const BASELINE_SHORT = { claude: 'Claude API', 'claude-code': 'Claude subscription', openai: 'OpenAI' };
const ARM_LABEL = {
  native: 'Jev · native API',
  claude: 'Claude · API key',
  'claude-code': 'Claude · your subscription',
  openai: 'OpenAI · API key',
  replay: 'Synthetic replay',
  gateway: 'Vercel AI Gateway',
  rules: 'Keyword rules · delay trap',
};
function renderCompare(r) {
  const expected = r.expected_owner;
  const planted = r.planted_error || {};
  $('compareSummary').innerHTML = r.arms
    .map((arm) => {
      const rows = arm.cases || [];
      const audit = armEvidence(arm, expected, planted);
      const honest = rows.filter((x) => !(arm.kind === 'synthetic_replay' && planted[x.case_id]));
      const agree = honest.filter((x) => x.answers.owner === expected[x.case_id]).length;
      const model = rows[0]?.model || arm.pinned_version;
      const fails = arm.failures
        .slice(0, 2)
        .map((f) => `<p class="compare-fail">${esc(f.case_id)}: ${esc(f.error)}</p>`)
        .join('');
      const agreeText = arm.succeeded
        ? `${agree} / ${honest.length}${honest.length < rows.length ? ' excl. planted' : ''}`
        : '–';
      const medianLatency = median(rows.map((x) => x.latency_ms));
      const free = arm.kind === 'synthetic_replay' || arm.kind === 'deterministic_rules';
      return `<div class="arm-card ${arm.failed ? 'failing' : ''}"><h3>${esc(ARM_LABEL[arm.name] || arm.name)}<small>${esc(model)}</small></h3>${metric('Answered', `${arm.succeeded} / ${arm.attempts}`)}${metric('Owner agrees with label', agreeText)}${metric('Answered-call median latency', medianLatency !== null ? fmtMs(medianLatency) : '–')}${metric('All-attempt cost', armCostLabel(audit, free))}${metric('Common subset agreement', arm.paired_owner_agreement ? `${arm.paired_owner_agreement.numerator} / ${arm.paired_owner_agreement.denominator}` : 'Unavailable')}${fails}${arm.failed > 2 ? `<p class="compare-fail">…and ${arm.failed - 2} more failures retained in the report.</p>` : ''}</div>`;
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
            return `<td class="na" title="${esc(f ? f.error : '')}">failed<span class="cell-sub">${f?.estimated_cost_usd == null ? 'cost unknown' : fmtCost(f.estimated_cost_usd) + ' estimated'}</span></td>`;
          }
          const issue = row.answers.issue ? `${esc(row.answers.issue)} · ` : '';
          if (arm.kind === 'synthetic_replay' && planted[id]) {
            return `<td class="planted">${esc(row.answers.owner)}<span class="planted-tag">planted teaching error</span><span class="cell-sub">${issue}${row.latency_ms === null ? 'no call' : fmtMs(row.latency_ms)} · ${row.estimated_cost_usd === null ? (row.billing === 'subscription' ? 'subscription' : 'cost n/a') : fmtCost(row.estimated_cost_usd)}</span></td>`;
          }
          const ok = row.answers.owner === expected[id];
          return `<td class="${ok ? 'agree' : 'disagree'}">${esc(row.answers.owner)}<span class="cell-sub">${issue}${row.latency_ms === null ? 'no call' : fmtMs(row.latency_ms)} · ${row.estimated_cost_usd === null ? (row.billing === 'subscription' ? 'subscription' : 'cost n/a') : fmtCost(row.estimated_cost_usd)}</span></td>`;
        })
        .join('');
      const plantedCell = planted[id]
        ? `${esc(expected[id])}<span class="planted-tag">planted only in authored replay</span>`
        : esc(expected[id]);
      return `<tr><td><strong>${esc(id)}</strong><span class="cell-sub">${esc(c.title)}</span></td><td${planted[id] ? ' class="planted"' : ''}>${plantedCell}</td>${cells}</tr>`;
    })
    .join('');
  $('compareTable').innerHTML =
    `<table><thead><tr><th>Case</th><th>Teaching label</th>${head}</tr></thead><tbody>${body}</tbody></table>`;
  $('compareWarnings').textContent = r.warnings.join(' ');
}

$('burstThreshold').oninput = () => syncThreshold('burstThreshold');
$('burstMode').onchange = consentHint;
$('armNative').onchange = consentHint;
$('armClaude').onchange = consentHint;
$('armClaudeCode').onchange = consentHint;
$('armOpenAI').onchange = consentHint;
$('liveConsent').onchange = consentHint;
$('connectLive').onclick = () => $('setup').showModal();
$('connectForm').onsubmit = connectSubmit;
$('probeRun').onclick = probeRun;
$('ablateRun').onclick = ablateRun;
$('probeRepeats').oninput = () => ($('probeRepeatsValue').textContent = $('probeRepeats').value);
$('exportProbe').onclick = () => state.lastProbe && downloadJSON(`probe-${state.lastProbe.case_id}.json`, state.lastProbe);
$('exportAblate').onclick = () => state.lastAblate && downloadJSON(`ablation-${state.lastAblate.case_id}.json`, state.lastAblate);
$('forgetKey').onclick = forgetKey;
$('burstRun').onclick = burst;
$('pgRun').onclick = pgRun;
$('compareRun').onclick = compareRun;
$('pgAdd').onclick = () => {
  if (pg.questions.length < 8)
    pg.questions.push({ id: '', type: 'noul', instructions: '', criteria: '' });
  pgRender();
};
$('pgPreset').onchange = () => pgPreset($('pgPreset').value);
$('pgState').oninput = pgBytes;
$('exportBurst').onclick = () => {
  if (!state.lastBurst) return;
  downloadJSON(`burst-${state.lastBurst.kind}.json`, state.lastBurst);
};
$('exportPg').onclick = () => {
  if (!state.lastPlayground) return;
  downloadJSON('playground-result.json', state.lastPlayground);
};
$('exportCompare').onclick = () => {
  if (!state.lastCompare) return;
  downloadJSON('compare-report.json', state.lastCompare);
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
  } catch (e) {
    error('Initialization failed: ' + e.message);
  }
})();
