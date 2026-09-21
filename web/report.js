'use strict';
/* Offline snapshot export. Only explicit result objects are read; configuration credentials
   are never copied. User-authored text is not automatically safe to share. */
function reportEsc(v) {
  return String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
function reportEntries() {
  return [
    ['Burst', state.lastBurst], ['Stability probe', state.lastProbe],
    ['Evidence ablation', state.lastAblate], ['Comparison', state.lastCompare],
    ['Playground', state.lastPlayground], ['Decision Studio', state.lastStudio],
    ['Decision economics', state.lastEconomics],
  ].filter(([, r]) => r);
}
function reportHas() { return reportEntries().length > 0; }
function reportRaw(r) {
  return `<details><summary>Inspect complete retained result, including failures</summary><pre>${reportEsc(JSON.stringify(r, null, 2))}</pre></details>`;
}
function reportCompare(r) {
  return r.arms.map(arm => {
    const e = armEvidence(arm, r.expected_owner, r.planted_error);
    const rows = (arm.cases || []).map(c => `<tr><td>${reportEsc(c.case_id)}</td><td>Answered</td><td>${reportEsc(c.answers.owner)}</td><td>${reportEsc(c.model)}</td><td>${reportEsc(fmtMs(c.latency_ms))}</td><td>${reportEsc(fmtCost(c.estimated_cost_usd))}</td></tr>`);
    rows.push(...(arm.failures || []).map(f => `<tr class="failure"><td>${reportEsc(f.case_id)}</td><td>Failed</td><td colspan="2">${reportEsc(f.error)}</td><td>${reportEsc(fmtMs(f.latency_ms))}</td><td>${reportEsc(fmtCost(f.estimated_cost_usd))}</td></tr>`));
    const free = ['synthetic_replay','deterministic_rules'].includes(arm.kind);
    return `<h3>${reportEsc(ARM_LABEL[arm.name] || arm.name)}</h3><p>${reportEsc(liveLabel(arm))}. ${e.answered}/${e.attempted} answered. Owner-label agreement ${e.agreement}/${e.scored} among scored answers${e.excluded ? `; ${e.excluded} authored planted result excluded` : ''}. ${reportEsc(armCostLabel(e,free))}.</p><div class="scroll"><table><thead><tr><th>Case</th><th>Status</th><th>Owner or failure</th><th>Model</th><th>Latency</th><th>Cost</th></tr></thead><tbody>${rows.join('')}</tbody></table></div>`;
  }).join('') + (r.paired ? `<p>Common answered subset: ${r.paired.case_ids.length}/${r.cases.length} requested cases. This selected subset is not operational coverage.</p>` : '');
}
function reportSummary(name,r) {
  if (name === 'Comparison') return reportCompare(r);
  if (name === 'Decision economics') return `<p>Assumption-only worksheet; zero model calls. ${reportEsc(r.status)}.</p><p>Baseline ${reportEsc(fmtCost(r.costs.baseline))}; proposed ${reportEsc(fmtCost(r.costs.proposed))}; difference ${reportEsc(fmtCost(r.costs.difference))}. Review ${r.capacity.required_hours.toFixed(2)} hours; capacity ${r.capacity.available_hours.toFixed(2)} hours.</p>`;
  if (name === 'Burst') return `<p>${r.summary.succeeded}/${r.summary.requested} answered; ${r.summary.failed} failures retained. ${reportEsc(r.kind)}. Cost ${reportEsc(fmtCost(r.summary.estimated_cost_usd))}; ${r.summary.cost_unknown_cases} unknown case costs.</p>`;
  if (name === 'Stability probe') return `<p>${r.succeeded}/${r.requested} answered. ${r.complete ? 'Complete' : 'Incomplete'}; ${r.comparable ? 'same observed contract' : 'mixed contracts: no pooled spread'}. Route stability: ${r.route_stable === null ? 'not established' : r.route_stable ? 'unchanged in this sample' : 'changed in this sample'}. Cost ${reportEsc(fmtCost(r.estimated_cost_usd))}.</p>`;
  if (name === 'Evidence ablation') return `<p>${r.succeeded}/${r.requested} answered. Largest observed probability movement: ${reportEsc(r.most_influential || 'none exceeding reference')}. Reference range ${r.noise_floor.toFixed(2)}; not a significance test or causal attribution. Owner deltas compare the same baseline label.</p>`;
  if (name === 'Decision Studio') return `<p>${reportEsc(r.pattern_id)} · ${reportEsc(r.version)} · ${reportEsc(r.variant)}. ${r.result ? 'Live response retained; human review required.' : r.failure ? 'Live attempt failed; details retained.' : 'Request preview; no model call.'} Zero external actions.</p>`;
  return `<p>${r.failure ? 'Live attempt failed; details retained.' : 'Live response retained; no policy applied.'}</p>`;
}
function buildSessionReport() {
  const c = state.config || {}, when = new Date().toISOString();
  const entries = reportEntries();
  const parts = entries.map(([name,r]) => `<section><h2>${reportEsc(name)}</h2>${reportSummary(name,r)}<p class="warning">${reportEsc(r.warning || (r.warnings || []).join(' '))}</p>${reportRaw(r)}</section>`);
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Jev Decision Lab · snapshot</title><style>
body{font:15px/1.6 system-ui,sans-serif;color:#182c31;max-width:1100px;margin:36px auto;padding:0 22px}h1{font-size:30px;line-height:1.15}h2{font-size:23px;border-top:1px solid #ccd9d8;padding-top:24px;margin-top:32px}h3{font-size:18px}small,.warning,footer{color:#465d61}.warning{border-left:3px solid #006c60;padding-left:12px}table{width:100%;border-collapse:collapse;font-size:13px}th,td{text-align:left;padding:8px;border-bottom:1px solid #ccd9d8;overflow-wrap:anywhere}.failure{color:#8b2424}.scroll{overflow:auto}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px;background:#f3f7f6;padding:16px}summary{cursor:pointer;padding:12px 0}footer{margin-top:40px}@media print{details{display:block}pre{font-size:9px}}
</style></head><body><h1>Jev Decision Lab</h1><p>Experiment snapshot · ${reportEsc(when)} · lab ${reportEsc(c.lab_version || 'unknown')}</p>
<p class="warning">This is the latest retained result from each surface, not a complete session history. Re-running a surface replaces its snapshot. Export individual runs before replacing them. Mode, model, failures and billing basis are recorded per result; an attempted live call is not a verified response.</p>
<p>Authored teaching cases do not establish model accuracy or calibration. A probability cannot grant permission. Provider cost estimates, subscription list-price equivalents and assumption-only economics are different quantities. Inspect each result's provenance and denominator.</p>${parts.join('\n')}
<footer>Review all text before sharing. The exporter does not add connection credentials, but user-authored inputs and provider messages may contain sensitive material. Source: github.com/jlov7/jev-decision-lab.</footer></body></html>`;
}
function exportReport() {
  if (!reportHas()) return error('Nothing to report yet. Run an experiment or calculate a decision-economics scenario.');
  const url = URL.createObjectURL(new Blob([buildSessionReport()], {type:'text/html'}));
  const a = document.createElement('a'); a.href=url; a.download=`jev-lab-snapshot-${new Date().toISOString().slice(0,10)}.html`; a.click();
  setTimeout(() => URL.revokeObjectURL(url),1000);
}
$('exportReport').onclick = exportReport;
