const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const evidencePath = path.join(__dirname, '..', 'web', 'evidence.js');
test('evidence helpers exist', () => assert.ok(fs.existsSync(evidencePath)));
if (fs.existsSync(evidencePath)) {
  const { armEvidence, liveLabel } = require(evidencePath);
  test('known failed-call costs are included, unknown stays unknown', () => {
    const arm = {kind:'live_typesafe', live:true, attempts:3, cases:[{case_id:'S01', answers:{owner:'a'},estimated_cost_usd:.1}], failures:[{case_id:'S02',estimated_cost_usd:.2}, {case_id:'S03'}]};
    const e = armEvidence(arm, {S01:'a'}, {});
    assert.equal(e.knownAttempts,2); assert.equal(e.unknownAttempts,1);
    assert.equal(e.totalCost,null); assert.ok(Math.abs(e.knownCost-.3)<1e-9);
    assert.equal(e.agreement,1); assert.equal(e.attempted,3);
  });
  test('S04 is excluded only from authored replay', () => {
    const arm={kind:'live_typesafe', attempts:1, cases:[{case_id:'S04', answers:{owner:'quality'}, estimated_cost_usd:.01}],failures:[]};
    assert.equal(armEvidence(arm,{S04:'quality'},{S04:true}).scored,1);
    assert.equal(armEvidence({...arm,kind:'synthetic_replay'},{S04:'quality'},{S04:true}).scored,0);
  });
  test('all failed live attempts do not become replay or success', () => {
    assert.match(liveLabel({live:true,live_verified:false}),/attempted/i);
    assert.doesNotMatch(liveLabel({live:true,live_verified:false}),/no live call/);
  });
  test('report retains failures and escapes untrusted text', () => {
    const arm={name:'native',kind:'live_typesafe',live:true,live_verified:false,pinned_version:'test',attempts:1,succeeded:0,failed:1,cases:[],failures:[{case_id:'S01',error:'<img src=x onerror=alert(1)>',estimated_cost_usd:.03}]};
    const context={state:{config:{},lastCompare:{cases:['S01'],expected_owner:{},planted_error:{},arms:[arm],warnings:[]}},ARM_LABEL:{},names:{},routes:{},$(){return {};},fmtCost(v){return v==null?'Unknown':`$${v}`;},fmtMs(v){return String(v);},console,setTimeout};
    vm.createContext(context);
    vm.runInContext(fs.readFileSync(evidencePath,'utf8'),context);
    vm.runInContext(fs.readFileSync(path.join(__dirname,'..','web','report.js'),'utf8'),context);
    const html=vm.runInContext('buildSessionReport()',context);
    assert.match(html,/&lt;img/); assert.doesNotMatch(html,/<img src=x/);
    assert.match(html,/0.03/); assert.match(html,/attempted/i);
    assert.doesNotMatch(html,/Every result here is synthetic replay/);
    assert.doesNotMatch(html,/No key, session token or company data is in this file/);
  });
}
test('incompatible billing bases cannot render a summed subtotal', () => {
  const ctx={module:{exports:{}},fmtCost(v){return `$${v}`;}};
  vm.createContext(ctx); vm.runInContext(fs.readFileSync(evidencePath,'utf8'),ctx);
  const e=ctx.module.exports.armEvidence({attempts:2,cases:[{case_id:'a',answers:{owner:'x'},estimated_cost_usd:1,billing:'api'}],failures:[{estimated_cost_usd:2,billing:'subscription'}]});
  const text=ctx.module.exports.armCostLabel(e);
  assert.match(text,/api: \$1/); assert.match(text,/subscription: \$2/); assert.doesNotMatch(text,/\$3/);
});
test('received live outputs are not relabeled as no response', () => {
 const {liveLabel}=require(evidencePath);
 assert.match(liveLabel({live:true,succeeded:1,live_verified:false}),/outputs retained/);
});
