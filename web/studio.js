'use strict';
/* Intent-led entry, deterministic lesson, request-only Studio, assumption-only economics. */
const studioState = {patterns: [], selected: null, preview: null, sequence: 0, running: false, lesson: [], step: 0, checks: 0};
const economicLabels = {
  volume: ['Cases per period', 'Whole number of attempted cases'],
  model_cost_per_attempt: ['Model cost / attempt · USD', 'Including an assumption for failed calls'],
  failure_rate: ['Request failure rate · fraction', '0.02 means 2%; every failure goes to review'],
  auto_share: ['Automated share of valid answers', '0.60 means 60%; not a confidence threshold'],
  auto_error_rate: ['Error rate in automated cases', 'Conditional on the cases selected for automation'],
  reviewer_error_rate: ['Residual error rate after review', 'Reviewers are not assumed perfect'],
  baseline_error_rate: ['Error rate in the baseline', 'For the existing all-reviewed workflow'],
  review_minutes: ['Minutes per reviewed case', 'Same duration in baseline and proposed workflow'],
  hourly_cost: ['Reviewer cost / hour · USD', 'Fully loaded rate, not salary alone'],
  error_loss: ['Average loss / residual error · USD', 'A simplifying expectation, not tail-risk assurance'],
  overhead: ['Proposed workflow overhead · USD', 'Period-matched integration, monitoring and recovery'],
  review_capacity_hours: ['Available review hours / period', 'Capacity shortfalls prevent a feasible conclusion'],
};
function studioList() {
  const query = $('patternSearch').value.toLowerCase().trim();
  const matches = studioState.patterns.filter(p => `${p.name} ${p.question} ${p.stage}`.toLowerCase().includes(query));
  $('patternList').innerHTML = matches.map(p => `<button class="pattern-option${p.id === studioState.selected ? ' selected' : ''}" data-pattern="${esc(p.id)}" aria-pressed="${p.id === studioState.selected}"><span>${esc(p.stage)}</span>${esc(p.name)}</button>`).join('') || '<p class="empty">No patterns match. Try “claim”, “skill”, or “evidence”.</p>';
  $('patternSelect').innerHTML = matches.map(p => `<option value="${esc(p.id)}">${esc(p.name)}</option>`).join('');
  $('patternSelect').value = studioState.selected || '';
  $('patternSelect').disabled = studioState.running || !matches.length;
  $('patternCount').textContent = `${matches.length} of ${studioState.patterns.length} patterns`;
  $('patternList').querySelectorAll('[data-pattern]').forEach(b => { b.disabled = studioState.running; b.onclick = () => studioSelect(b.dataset.pattern); });
}
async function studioSelect(id) {
  if (studioState.running) return;
  const p = studioState.patterns.find(x => x.id === id);
  if (!p) return error('Unknown pattern. Reload the lab.');
  studioState.selected = id;
  $('patternTitle').textContent = p.name;
  $('patternStage').textContent = `${p.stage} · ${p.version}`;
  $('patternQuestion').textContent = p.question;
  $('patternCode').textContent = p.code_owns;
  $('patternBaseline').textContent = p.baseline;
  $('patternAdverse').textContent = p.adverse_lesson;
  $('patternSource').href = p.source;
  studioList();
  await studioPreview();
}
async function studioPreview() {
  const sequence = ++studioState.sequence;
  studioState.preview = null;
  $('studioConsent').checked = false;
  ['studioExport','studyExport','studioRun','studioResultExport'].forEach(id => { $(id).disabled = true; });
  $('studioRequest').textContent = 'Preparing the local request preview…';
  $('studioChecks').replaceChildren();
  $('studioSituation').replaceChildren(); $('studioQuestions').replaceChildren();
  $('studioResult').replaceChildren();
  $('studioStatus').textContent = 'No live observation for this displayed request.';
  try {
    const p = await api('/api/studio-preview', {pattern_id:studioState.selected, variant:$('studioVariant').value});
    if (sequence !== studioState.sequence) return;
    studioState.preview = p;
    $('studioRequest').textContent = JSON.stringify(p.request, null, 2);
    const input = JSON.parse(p.request.state);
    $('studioSituation').innerHTML = Object.entries(input).map(([key,value]) => `<div><h4>${esc(key.replaceAll('_',' '))}</h4><pre>${esc(typeof value === 'string' ? value : JSON.stringify(value,null,2))}</pre></div>`).join('');
    $('studioQuestions').innerHTML = Object.entries(p.request.questions).map(([key,q]) => `<article><span class="type">${esc(q.type)}</span><h4>${esc(key.replaceAll('_',' '))}</h4><p>${esc(q.instructions)}</p></article>`).join('');
    $('studioChecks').innerHTML = p.code_checks.map(c => `<p class="notice"><strong>Code check:</strong> ${esc(c.check)} = ${esc(c.result)}. ${esc(c.consequence)}.</p>`).join('');
    ['studioExport','studyExport','studioRun'].forEach(id => { $(id).disabled = false; });
  } catch(e) { if (sequence === studioState.sequence) error(e.message); }
}
async function studioRun() {
  if (!studioState.preview || studioState.running || state.busy) return;
  error('');
  if (!state.config.live_enabled) return error('Connect Jev first. This screen has no authored model output and cannot fall back to replay.');
  if (!$('studioConsent').checked) return error('Authorize the displayed synthetic request before making one live call.');
  studioState.running = true; busy(true); studioList();
  $('studioVariant').disabled = true; $('studioRun').disabled = true;
  const p = studioState.preview;
  $('studioStatus').textContent = 'One live attempt in progress. No automatic retry.';
  try {
    const r = await api('/api/studio-run', {pattern_id:p.pattern_id, variant:p.variant, consent:true});
    state.lastStudio = r;
    $('studioStatus').textContent = `${r.result.response.model} · ${fmtMs(r.result.provenance.latency_ms)} · ${fmtCost(r.result.provenance.estimated_cost_usd)} estimated · human review required`;
    $('studioResult').innerHTML = Object.entries(r.result.response.answers).map(([qid,a]) => answerBlock(qid, qid, a, r.result.request.questions[qid].instructions)).join('');
    const details = document.createElement('details'), summary = document.createElement('summary'), pre = document.createElement('pre');
    summary.textContent = 'Inspect complete observation'; pre.textContent = JSON.stringify(r,null,2); details.append(summary,pre); $('studioResult').append(details);
  } catch(e) {
    state.lastStudio = {pattern_id:p.pattern_id, version:p.version, variant:p.variant, request:p.request, request_hash:p.request_hash, failure:true, detail:e.detail || {error:e.message}, external_actions:0};
    $('studioStatus').textContent = 'Live attempt failed. The failure is retained; no replay was substituted.';
    const pre = document.createElement('pre'); pre.textContent = JSON.stringify(state.lastStudio,null,2); $('studioResult').replaceChildren(pre);
    error(e.message);
  } finally {
    studioState.running = false; busy(false); studioList(); $('studioRun').disabled = false; $('studioVariant').disabled = false; $('studioResultExport').disabled = !state.lastStudio;
    $('studioConsent').checked = false;
    try { await refreshConfig(); } catch(e) { error(`Result retained, but connection status refresh failed: ${e.message}`); }
  }
}
async function studyExport() {
  if (!studioState.preview) return;
  try { downloadJSON(`study-${studioState.selected}-UNRUN.json`, await api('/api/studio-study', {pattern_id:studioState.selected})); }
  catch(e) { error(e.message); }
}
async function lessonStep(reset = false) {
  if (state.busy || studioState.running) return;
  error(''); busy(true); $('lessonRun').disabled = true; $('lessonNext').disabled = true; $('lessonReset').disabled = true;
  if (reset) {studioState.lesson=[]; studioState.step=0; studioState.checks=0; $('teachForm').reset(); $('teachResult').textContent=''; $('lessonExport').disabled=true;}
  try {
    const step = studioState.step;
    let observation;
    if (step === 0) {
      observation = await api('/api/run', {case_id:'S02',mode:'replay',consent:false});
      $('lessonTitle').textContent = '01 · A typed answer is not a permission.';
      $('lessonText').textContent = 'The supplier message contains “delay”, but says delivery arrived on time. The authored model fixture recommends a team; explicit policy decides the route. This is replay, not measured Jev output.';
      $('lessonEvidence').textContent = JSON.stringify({mode:observation.provenance.kind,model_calls:observation.provenance.model_calls,owner:observation.decision.owner,route:observation.decision.route},null,2);
    } else if (step === 1) {
      const first = studioState.lesson[0];
      const held = await api('/api/action-preview', {receipt_id:first.receipt_id,current:{state_unchanged:true,source_fresh:true,approval_current:false,permission_granted:true}});
      const stale = await api('/api/reconsider',{receipt_id:first.receipt_id,threshold:0.85,variant:'stale'});
      observation = {approval_revoked:held,expired_evidence:stale};
      $('lessonTitle').textContent = '02 · New constraints do not require new inference.';
      $('lessonText').textContent = 'With approval withdrawn, code holds the simulated action. With evidence expired, policy requests fresh evidence. The original model answer has not changed; no new model call is needed.';
      $('lessonEvidence').textContent = JSON.stringify({action:held,route_after_expiry:stale.decision.route,new_model_calls:0},null,2);
    } else {
      observation=await api('/api/run',{case_id:'S04',mode:'replay',consent:false});
      $('lessonTitle').textContent = '03 · A confident answer can still be wrong.';
      $('lessonText').textContent = 'This fixture deliberately gives operations 98% while the teaching label is quality. The error is authored by the lab, not measured from Jev. Calibration must be checked against outcomes, not inferred from a decimal.';
      $('lessonEvidence').textContent=JSON.stringify({authored_prediction:observation.response.answers.owner,teaching_label:'quality',model_calls:0},null,2);
    }
    studioState.lesson.push(observation); studioState.step=Math.min(3,step+1);
    $('lesson').hidden=false; $('lessonStep').textContent=`STEP ${studioState.step} OF 3 · OFFLINE REPLAY`;
    $('teachBack').hidden=studioState.step<3; $('lessonNext').hidden=studioState.step===3;
    $('lessonNext').textContent=studioState.step===1?'Change evidence and approval':'Inspect the confident wrong fixture';
    $('lesson').scrollIntoView({block:'start',behavior:'instant'});
  } catch(e) {error(`Lesson could not complete this step: ${e.message}. Restart to retry explicitly.`);}
  finally {busy(false); $('lessonRun').disabled=false; $('lessonNext').disabled=false; $('lessonReset').disabled=false;}
}
function teachCheck(event) {
  event.preventDefault();
  const form=new FormData($('teachForm'));
  const expected={q1:'shape',q2:'gate',q3:'estimate'};
  const correct=Object.entries(expected).filter(([k,v])=>form.get(k)===v).length;
  studioState.checks+=1;
  studioState.teach={correct,total:3,attempt:studioState.checks,answers:Object.fromEntries(form)};
  $('teachResult').textContent=correct===3?'3 / 3. The contract controls format; code checks authority; outcome data tests calibration. This is a learning check, not external user validation.':`${correct} / 3. Revisit these distinctions: valid format is not truth; approval expiry must hold action; a probability needs outcome-based evaluation. Revise your answers and try again.`;
  $('lessonExport').disabled=false;
}
function economicsInputs(data) {
  $('economicsInputs').innerHTML=Object.entries(data.economics_defaults).map(([k,v])=>{
    const [label,help]=economicLabels[k], [min,max]=data.economics_bounds[k];
    return `<label for="econ_${k}">${esc(label)}<input id="econ_${k}" name="${esc(k)}" type="number" min="${min}" max="${max}" step="${k==='volume'?'1':'any'}" value="${v}" required aria-describedby="help_${k}"><span id="help_${k}">${esc(help)}</span></label>`;
  }).join('');
}
async function economicsRun(event) {
  event.preventDefault(); error('');
  const assumptions=Object.fromEntries(new FormData($('economicsForm')));
  for(const k of Object.keys(assumptions)) assumptions[k]=Number(assumptions[k]);
  try {
    const r=await api('/api/economics',{assumptions}); state.lastEconomics=r;
    const c=r.costs, capacity=r.capacity;
    $('economicsResult').innerHTML=`<div class="economics-tiles"><div><span>Existing workflow</span><strong>${esc(fmtCost(c.baseline))}</strong></div><div><span>Proposed workflow</span><strong>${esc(fmtCost(c.proposed))}</strong></div><div><span>Difference · assumptions only</span><strong>${esc(fmtCost(c.difference))}</strong></div></div><p class="notice"><strong>${capacity.feasible?'Review fits the stated capacity.':'Review capacity shortfall.'}</strong> ${capacity.required_hours.toFixed(2)} hours required versus ${capacity.available_hours.toFixed(2)} available; shortfall ${capacity.shortfall_hours.toFixed(2)} hours. A positive cost difference is not a deployment recommendation.</p><p>${r.cases.attempted} attempted cases: ${r.cases.automated.toFixed(1)} automated; ${r.cases.reviewed.toFixed(1)} reviewed, including ${r.cases.failed.toFixed(1)} failed requests. Expected counts may be fractional.</p><div class="table-scroll"><table><caption>Where the proposed cost comes from</caption><thead><tr><th>Component</th><th>USD</th></tr></thead><tbody>${[['All model attempts',c.model],['Review effort',c.review],['Residual error loss',c.residual_error_loss],['Overhead',c.overhead]].map(([k,v])=>`<tr><td>${esc(k)}</td><td>${esc(fmtCost(v))}</td></tr>`).join('')}</tbody></table><table><caption>One-assumption-at-a-time sensitivity</caption><thead><tr><th>Changed assumption</th><th>New value</th><th>Cost difference</th><th>Capacity fits?</th></tr></thead><tbody>${r.sensitivity.map(s=>`<tr><td>${esc(economicLabels[s.changed][0])}</td><td>${s.value}</td><td>${esc(fmtCost(s.cost_difference))}</td><td>${s.capacity_feasible?'Yes':'No'}</td></tr>`).join('')}</tbody></table></div><p class="small">${esc(r.warning)}</p>`;
    $('economicsExport').disabled=false;
  } catch(e) {error(e.message);}
}
$('patternSearch').oninput=studioList;
$('patternSelect').onchange = () => studioSelect($('patternSelect').value);
$('studioVariant').onchange=studioPreview;
$('studioRun').onclick=studioRun;
$('studioExport').onclick=()=>studioState.preview&&downloadJSON(`request-${studioState.preview.pattern_id}-${studioState.preview.variant}.json`,studioState.preview.request);
$('studyExport').onclick=studyExport;
$('studioResultExport').onclick=()=>state.lastStudio&&downloadJSON('studio-observation.json',state.lastStudio);
$('lessonRun').onclick=()=>lessonStep(true); $('lessonReset').onclick=()=>lessonStep(true); $('lessonNext').onclick=()=>lessonStep();
$('teachForm').onsubmit=teachCheck;
$('lessonExport').onclick=()=>downloadJSON('lesson-record.json',{kind:'authored_teaching_replay',external_validation:false,observations:studioState.lesson,teach_back:studioState.teach});
$('economicsForm').onsubmit=economicsRun;
$('economicsExport').onclick=()=>state.lastEconomics&&downloadJSON('decision-economics-assumptions.json',state.lastEconomics);
$('studioReport').onclick=exportReport;
document.querySelectorAll('[data-go]').forEach(b=>b.onclick=()=>(b.dataset.go === 'economics' ? (tab('studio'), $('economicsTitle').scrollIntoView({block:'start'})) : tab(b.dataset.go)));
(async()=>{
  try {
    const data=await api('/api/studio');
    studioState.patterns=data.patterns; economicsInputs(data);
    if(!state.config)state.config=await api('/api/config');
    await studioSelect('citation'); $('lessonRun').disabled=false;
  } catch(e) {error('Decision Studio initialization failed: '+e.message);}
})();
