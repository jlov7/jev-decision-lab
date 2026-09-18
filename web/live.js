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
  if (c.lab_version) document.querySelector('.brand > span').textContent = c.lab_version;
  if (!state.liveInitialised) {
    $('burstMode').value = c.live_enabled ? 'live' : 'replay';
    $('armNative').checked = c.live_enabled;
    $('armClaude').checked = claudeOn;
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
    $('armClaude').checked && 'claude',
    $('armReplay').checked && 'replay',
    $('armRules').checked && 'rules',
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
    state.lastCompare = r;
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
  rules: 'Keyword rules · delay trap',
};
function renderCompare(r) {
  const expected = r.expected_owner;
  const planted = r.planted_error || {};
  $('compareSummary').innerHTML = r.arms
    .map((arm) => {
      const rows = arm.cases || [];
      const honest = rows.filter((x) => !planted[x.case_id]);
      const agree = honest.filter((x) => x.answers.owner === expected[x.case_id]).length;
      const costs = rows.map((x) => x.estimated_cost_usd);
      const known = costs.filter((c) => c !== null && c !== undefined);
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
      return `<div class="arm-card ${arm.failed ? 'failing' : ''}"><h3>${esc(ARM_LABEL[arm.name] || arm.name)}<small>${esc(model)}</small></h3>${metric('Answered', `${arm.succeeded} / ${arm.attempts}`)}${metric('Owner agrees with label', agreeText)}${metric('Median latency', medianLatency !== null ? fmtMs(medianLatency) : '–')}${metric('Total cost', free ? 'No call' : known.length ? `${fmtCost(known.reduce((a, b) => a + b, 0))}${known.length < rows.length ? ' +?' : ''}` : rows.length ? 'Unknown' : '–')}${fails}${arm.failed > 2 ? `<p class="compare-fail">…and ${arm.failed - 2} more failures retained in the report.</p>` : ''}</div>`;
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
          const issue = row.answers.issue ? `${esc(row.answers.issue)} · ` : '';
          if (planted[id]) {
            return `<td class="planted">${esc(row.answers.owner)}<span class="planted-tag">planted teaching error</span><span class="cell-sub">${issue}${row.latency_ms === null ? 'no call' : fmtMs(row.latency_ms)} · ${row.estimated_cost_usd === null ? 'cost n/a' : fmtCost(row.estimated_cost_usd)}</span></td>`;
          }
          const ok = row.answers.owner === expected[id];
          return `<td class="${ok ? 'agree' : 'disagree'}">${esc(row.answers.owner)}<span class="cell-sub">${issue}${row.latency_ms === null ? 'no call' : fmtMs(row.latency_ms)} · ${row.estimated_cost_usd === null ? 'cost n/a' : fmtCost(row.estimated_cost_usd)}</span></td>`;
        })
        .join('');
      const plantedCell = planted[id]
        ? `${esc(expected[id])}<span class="planted-tag">do not score</span>`
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
$('liveConsent').onchange = consentHint;
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
    $('liveStatus').textContent = state.config.live_enabled
      ? `Key and enable flag present; account access remains unverified. Model ${state.config.model}. Process attempt cap ${state.config.live_attempt_limit}.`
      : 'This server is offline-only. Your account is not connected to this process.';
  } catch (e) {
    error('Initialization failed: ' + e.message);
  }
})();
