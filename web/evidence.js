'use strict';
/* Shared accounting for the browser and its exported report. No missing cost becomes zero. */
function armEvidence(arm, expected = {}, planted = {}) {
  const rows = arm.cases || [], failures = arm.failures || [];
  const all = [...rows, ...failures];
  const known = all.filter(r => typeof r.estimated_cost_usd === 'number' && Number.isFinite(r.estimated_cost_usd) && r.estimated_cost_usd >= 0);
  const bases = new Set(known.map(r => r.billing || 'provider_estimate'));
  const attempted = Number.isInteger(arm.attempts) ? arm.attempts : all.length;
  const basisTotals = Object.fromEntries([...bases].map(b => [b, known.filter(r => (r.billing || 'provider_estimate') === b).reduce((s,r) => s + r.estimated_cost_usd, 0)]));
  const knownCost = known.reduce((s, r) => s + r.estimated_cost_usd, 0);
  const honest = rows.filter(r => !(arm.kind === 'synthetic_replay' && planted[r.case_id]));
  return {knownCost, basisTotals, knownAttempts: known.length, unknownAttempts: Math.max(0, attempted - known.length),
    totalCost: attempted > 0 && known.length === attempted && bases.size === 1 ? knownCost : null,
    mixedBilling: bases.size > 1, subscription: bases.has('subscription'),
    scored: honest.length, agreement: honest.filter(r => r.answers.owner === expected[r.case_id]).length,
    attempted, answered: rows.length, excluded: rows.length - honest.length};
}
function liveLabel(arm) {
  if (arm.live_verified) return 'Authenticated response observed';
  if (arm.live && arm.succeeded > 0) return 'Live-provider outputs retained; integration verification incomplete';
  if (arm.live) return 'Live attempted; no verified response';
  if (arm.kind === 'synthetic_replay') return 'Authored replay; no model call';
  if (arm.kind === 'deterministic_rules') return 'Deterministic rules; no model call';
  return 'Live execution unverified';
}
function armCostLabel(e, free = false) {
  if (free) return 'No model call';
  if (e.mixedBilling) return `${Object.entries(e.basisTotals).map(([b,v]) => `${b}: ${fmtCost(v)}`).join('; ')}; separate billing bases, not a combined total; ${e.unknownAttempts} costs unknown`;
  if (e.totalCost !== null) return `${fmtCost(e.totalCost)}${e.subscription ? ' list-price equivalent, not subscription charge' : ' estimated'}`;
  return `${e.knownAttempts ? `${fmtCost(e.knownCost)} known subtotal; ` : ''}${e.unknownAttempts} attempt costs unknown${e.mixedBilling ? '; mixed billing bases' : ''}`;
}
if (typeof module !== 'undefined' && module.exports) module.exports = {armEvidence, liveLabel, armCostLabel};
