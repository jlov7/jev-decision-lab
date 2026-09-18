'use strict';
/* Session report: one self-contained HTML file built in the browser from what this tab has seen.
   No server call, no external asset, no key, no session token. Numbers are copied verbatim from
   the results already on screen, with their warnings. */
function reportEsc(v) {
  return String(v).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
}
function reportHas() {
  return Boolean(state.lastBurst || state.lastProbe || state.lastAblate || state.lastCompare || state.lastPlayground);
}
function reportBar(v, max) {
  const pct = max ? Math.max(1, Math.round((v / max) * 100)) : 0;
  return `<i class="bar"><b style="width:${pct}%"></b></i>`;
}
function reportBurst(r) {
  const s = r.summary, live = r.kind === 'live_typesafe';
  const max = Math.max(1, ...r.results.map((x) => x.latency_ms || 0));
  const rows = r.results
    .map((x) => {
      const c = state.cases.find((k) => k.id === x.case_id) || { title: x.case_id };
      if (!x.ok) return `<tr class="fail"><td>${reportEsc(x.case_id)}</td><td>${reportEsc(c.title)}</td><td colspan="3">${reportEsc(x.error)}</td></tr>`;
      return `<tr><td>${reportEsc(x.case_id)}</td><td>${reportEsc(c.title)}</td><td>${reportEsc(x.owner)} ${(x.owner_probability * 100).toFixed(0)}%</td><td>${reportEsc(routes[x.route][0])}</td><td>${x.latency_ms === null ? '–' : `${reportBar(x.latency_ms, max)} ${fmtMs(x.latency_ms)}`}</td></tr>`;
    })
    .join('');
  return `<section><h2>Burst · ${live ? 'live' : 'synthetic replay'}</h2>
<div class="tiles"><div><span>Answered</span><strong>${s.succeeded} of ${s.requested}</strong></div><div><span>Median latency</span><strong>${live ? fmtMs(s.latency_ms.p50) : '–'}</strong></div><div><span>Tail latency (p95)</span><strong>${live ? fmtMs(s.latency_ms.p95) : '–'}</strong></div><div><span>Input tokens</span><strong>${s.input_tokens === null ? '–' : s.input_tokens.toLocaleString()}</strong></div><div><span>Estimated cost</span><strong>${live ? fmtCost(s.estimated_cost_usd) : '–'}</strong></div><div><span>Model</span><strong>${reportEsc(s.models.join(', ') || 'none')}</strong></div></div>
<table><thead><tr><th>Case</th><th>Title</th><th>Owner</th><th>Route</th><th>Latency</th></tr></thead><tbody>${rows}</tbody></table>
<p class="warn">${reportEsc(r.warning)}</p></section>`;
}
function reportProbe(r) {
  const blocks = Object.entries(r.spread)
    .map(([qid, s]) => {
      let rows = '';
      const line = (label, o) => `<tr><td>${reportEsc(label)}</td><td>${reportBar(o.median, 1)}</td><td>${o.min.toFixed(2)} – ${o.max.toFixed(2)}</td><td>${o.range.toFixed(2)}</td></tr>`;
      if (s.type === 'noul') rows = line('probability of yes', s.value);
      else if (s.type === 'score') rows = Object.entries(s.options).map(([k, o]) => line(`level ${k}`, o)).join('') + `<tr><td colspan="4" class="sub">weighted score ${s.value.min.toFixed(2)} – ${s.value.max.toFixed(2)}</td></tr>`;
      else rows = Object.entries(s.options).sort((a, b) => b[1].median - a[1].median).map(([k, o]) => line(k, o)).join('');
      return `<h3>${reportEsc(names[qid] || qid)} <small>${reportEsc(s.type)}</small></h3><table><thead><tr><th>Option</th><th>Median</th><th>Min – max</th><th>Range</th></tr></thead><tbody>${rows}</tbody></table>`;
    })
    .join('');
  const routeText = Object.entries(r.routes).map(([k, n]) => `${routes[k][0]} in ${n} of ${r.succeeded}`).join(', ');
  return `<section><h2>Stability probe · ${reportEsc(r.case_id)} · ${r.requested} calls · ${r.mode === 'live' ? 'live' : 'synthetic replay'}</h2>
<p>${r.succeeded} of ${r.requested} answered${r.mode === 'live' ? ` · p50 ${fmtMs(r.latency_ms.p50)} · ${fmtCost(r.estimated_cost_usd)}` : ''} · route: ${reportEsc(routeText)}${r.widest_option_range.question ? ` · widest range ${r.widest_option_range.range.toFixed(2)} on ${reportEsc(names[r.widest_option_range.question] || r.widest_option_range.question)}` : ''}</p>
${blocks}<p class="warn">${reportEsc(r.warning)}</p></section>`;
}
function reportAblate(r) {
  const rows = r.variants
    .map((v) => {
      if (!v.ok) return `<tr class="fail"><td>${reportEsc(v.label)}</td><td colspan="6">${reportEsc(v.error)}</td></tr>`;
      const a = v.answers;
      const d = (k) => (v.deltas ? `${v.deltas[k] > 0 ? '+' : ''}${v.deltas[k].toFixed(2)}` : '–');
      const lead = r.most_influential && v.removed_evidence && v.removed_evidence.id === r.most_influential;
      return `<tr${lead ? ' class="lead"' : ''}><td><b>${reportEsc(v.label)}</b><br><span class="sub">${reportEsc(v.removed_evidence ? v.removed_evidence.text : 'every excerpt present')}</span></td><td>${reportEsc(a.owner)} ${(a.owner_probability * 100).toFixed(0)}% <span class="sub">${d('owner_probability')}</span></td><td>${a.severity.toFixed(2)} <span class="sub">${d('severity')}</span></td><td>${a.sufficient.toFixed(2)} <span class="sub">${d('sufficient')}</span></td><td>${a.contradiction.toFixed(2)} <span class="sub">${d('contradiction')}</span></td><td>${reportEsc(routes[a.route][0])}</td><td>${v.deltas ? (v.above_noise ? `<b>${v.movement.toFixed(2)}</b>` : `${v.movement.toFixed(2)} <span class="sub">noise</span>`) : '–'}</td></tr>`;
    })
    .join('');
  return `<section><h2>Evidence ablation · ${reportEsc(r.case_id)} · ${r.mode === 'live' ? 'live' : 'synthetic replay'}</h2>
<p>${r.most_influential ? `The judgment leaned most on <b>${reportEsc(r.most_influential)}</b>.` : 'No single excerpt moved the judgment beyond the noise floor.'} Noise floor ${r.noise_floor.toFixed(2)}${r.noise_floor_source ? ` (${reportEsc(r.noise_floor_source)})` : ''}.</p>
<table><thead><tr><th>Variant</th><th>Owner (Δ)</th><th>Severity (Δ)</th><th>Sufficient (Δ)</th><th>Contradiction (Δ)</th><th>Route</th><th>Movement</th></tr></thead><tbody>${rows}</tbody></table>
<p class="warn">${reportEsc(r.warning)}</p></section>`;
}
function reportCompare(r) {
  const arms = r.arms
    .map((arm) => {
      const rows = arm.cases.map((c) => `<tr><td>${reportEsc(c.case_id)}</td><td>${reportEsc(c.answers.owner)}</td><td>${reportEsc(c.answers.issue)}</td><td>${c.latency_ms === null ? '–' : fmtMs(c.latency_ms)}</td><td>${c.estimated_cost_usd === null ? '–' : fmtCost(c.estimated_cost_usd)}</td></tr>`).join('');
      return `<h3>${reportEsc(ARM_LABEL[arm.name] || arm.name)} <small>${reportEsc(arm.pinned_version)} · ${arm.live_verified ? 'authenticated' : 'no live call'}</small></h3><p>${arm.succeeded} of ${arm.attempts} answered${arm.failed ? `, ${arm.failed} failed and retained` : ''}.</p><table><thead><tr><th>Case</th><th>Owner</th><th>Issue</th><th>Latency</th><th>Cost</th></tr></thead><tbody>${rows}</tbody></table>`;
    })
    .join('');
  return `<section><h2>Compare · ${r.cases.length} cases · arms reported side by side, never pooled</h2>${arms}<p class="warn">${r.warnings.map(reportEsc).join(' ')}</p></section>`;
}
function reportPlayground(r) {
  const answers = Object.entries(r.response.answers)
    .map(([qid, a]) => {
      const val = a.type === 'choice' ? `${a.choice}` : a.type === 'noul' ? a.noul.toFixed(2) : a.score.toFixed(2);
      const dist = a.type === 'noul' ? '' : Object.entries(a.probabilities).map(([k, p]) => `${reportEsc(a.type === 'score' ? a.legend[k] : k)} ${(p * 100).toFixed(0)}%`).join(' · ');
      return `<tr><td>${reportEsc(qid)}</td><td>${reportEsc(a.type)}</td><td>${reportEsc(val)}</td><td class="sub">${dist}</td></tr>`;
    })
    .join('');
  return `<section><h2>Playground · one live call on text written in this session</h2><blockquote>${reportEsc(r.request.state)}</blockquote><table><thead><tr><th>Question</th><th>Type</th><th>Answer</th><th>Distribution</th></tr></thead><tbody>${answers}</tbody></table><p class="sub">${reportEsc(r.response.model)} · ${fmtMs(r.provenance.latency_ms)} · ${fmtCost(r.provenance.estimated_cost_usd)}</p></section>`;
}
function buildSessionReport() {
  const c = state.config || {};
  const when = new Date().toISOString().replace('T', ' ').slice(0, 16) + ' UTC';
  const parts = [];
  if (state.lastBurst) parts.push(reportBurst(state.lastBurst));
  if (state.lastProbe) parts.push(reportProbe(state.lastProbe));
  if (state.lastAblate) parts.push(reportAblate(state.lastAblate));
  if (state.lastCompare) parts.push(reportCompare(state.lastCompare));
  if (state.lastPlayground) parts.push(reportPlayground(state.lastPlayground));
  const anyLive = [state.lastBurst, state.lastProbe, state.lastAblate].some((r) => r && (r.mode === 'live' || r.kind === 'live_typesafe')) || Boolean(state.lastPlayground) || Boolean(state.lastCompare && state.lastCompare.arms.some((a) => a.live_verified));
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Jev Decision Lab · session report · ${when}</title>
<style>
body{font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;color:#142226;max-width:1100px;margin:32px auto;padding:0 20px}
h1{font-size:26px;margin:0 0 4px}h2{font-size:18px;margin:36px 0 8px;padding-top:18px;border-top:1px solid #dfe7e6}h3{font-size:14px;margin:18px 0 6px}h3 small{color:#6d8d89;font-weight:400}
p{margin:6px 0}.lead{color:#3f5c59}.sub{color:#6d8d89;font-size:12px}.warn{font-size:12px;color:#6d8d89;border-left:3px solid #cfe0dd;padding-left:10px;margin-top:12px}
table{width:100%;border-collapse:collapse;font-size:12.5px;margin:8px 0}th,td{text-align:left;padding:7px 8px;border-bottom:1px solid #e6eeec;vertical-align:top}th{color:#6d8d89;font-weight:600}
tr.lead td{background:#eef8f5}tr.fail td{color:#962f32}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:12px 0}.tiles div{border:1px solid #dfe7e6;border-radius:8px;padding:10px 12px}.tiles span{display:block;font-size:11px;color:#6d8d89;text-transform:uppercase;letter-spacing:.05em}.tiles strong{font-size:20px}
.bar{display:inline-block;width:120px;height:8px;background:#e9efee;border-radius:4px;vertical-align:middle;margin-right:6px}.bar b{display:block;height:100%;background:#1f8f7a;border-radius:4px}
blockquote{margin:8px 0;padding:10px 14px;background:#f5f8f7;border-radius:6px;white-space:pre-wrap}
footer{margin-top:40px;font-size:12px;color:#6d8d89;border-top:1px solid #dfe7e6;padding-top:12px}
@media print{body{margin:0}h2{break-before:auto}}
</style></head><body>
<h1>Jev Decision Lab · session report</h1>
<p class="lead">Generated ${when} in the browser from results already on screen. ${anyLive ? `Model ${reportEsc(c.model || 'unknown')}. Live calls were made on the account owner's key with per-run consent.` : 'Every result here is synthetic replay: authored teaching fixtures, no model call.'} Lab version ${reportEsc(c.lab_version || '')}.</p>
<p class="sub">Twelve authored synthetic cases are a smoke test, not a benchmark. Confidence is a spread statistic, not probability of correctness. Costs are estimates from reported usage and a dated public price ($${c.price_per_million_input} per million input tokens as of ${reportEsc(c.price_as_of || '')}), not an invoice. Client-observed latency includes network time. The model recommends; code decides; a person approves.</p>
${parts.join('\n')}
<footer>Built with Jev Decision Lab. No key, session token or company data is in this file. Source: github.com/jlov7/jev-decision-lab</footer>
</body></html>`;
}
function exportReport() {
  if (!reportHas()) return error('Nothing to report yet. Run a burst, probe, ablation, compare or playground call first.');
  const html = buildSessionReport();
  const blob = new Blob([html], { type: 'text/html' });
  const url = URL.createObjectURL(blob), a = document.createElement('a');
  a.href = url;
  a.download = `jev-lab-session-${new Date().toISOString().slice(0, 10)}.html`;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
$('exportReport').onclick = exportReport;
