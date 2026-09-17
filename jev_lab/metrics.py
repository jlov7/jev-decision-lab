"""Small transparent metrics. Gold data must never enter provider payloads."""
import math
from .engine import distribution

def wilson(correct: int, n: int) -> list[float] | None:
    if not n: return None
    z=1.959963984540054; p=correct/n; den=1+z*z/n
    centre=(p+z*z/(2*n))/den
    radius=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return [max(0,centre-radius),min(1,centre+radius)]

def classification(rows: list[tuple[dict,str]]) -> dict:
    for probs,gold in rows:
        distribution(probs,set(probs))
        if gold not in probs: raise ValueError('Gold label is absent from option set')
    n=len(rows)
    observations=[(max(p.values()), max(p,key=p.get)==g) for p,g in rows]
    correct=sum(ok for _,ok in observations)
    brier=sum(sum((v-(k==g))**2 for k,v in p.items()) for p,g in rows)/n if n else None
    loss=-sum(math.log(max(p[g],1e-15)) for p,g in rows)/n if n else None
    ece=0.
    bins=[]
    for i in range(10):
        group=[(p,ok) for p,ok in observations if min(int(p*10),9)==i]
        count=len(group)
        acc=sum(ok for _,ok in group)/count if count else None
        conf=sum(p for p,_ in group)/count if count else None
        if count: ece+=count/max(n,1)*abs(acc-conf)
        bins.append({'lower':i/10,'upper':(i+1)/10,'n':count,'accuracy':acc,'mean_top_probability':conf})
    curve=[]
    for t in [0,.5,.7,.8,.85,.9,.95,.99,1.]:
        selected=[ok for p,ok in observations if p>=t]
        curve.append({'threshold':t,'accepted':len(selected),'coverage':len(selected)/n if n else None,
                      'error_rate':1-sum(selected)/len(selected) if selected else None})
    return {'n':n,'accuracy':correct/n if n else None,'accuracy_wilson_95':wilson(correct,n),
            'brier':brier,'log_loss':loss,'ece_10':ece if n else None,'calibration_bins':bins,'risk_coverage':curve,
            'definition':'Owner classification only. Multiclass Brier is the unhalved sum over classes, averaged over cases. ECE uses top-class probability, not vendor confidence. Policy gates are not included in this risk-coverage curve.'}

def evaluate(receipts: list[dict], labels: dict) -> dict:
    ids=[r['case_id'] for r in receipts]
    if len(set(ids))!=len(ids): raise ValueError('Repeated case IDs must not inflate the evaluation sample')
    kinds={r['provenance']['kind'] for r in receipts}
    if len(kinds)>1: raise ValueError('Do not mix synthetic and live outputs in one evaluation')
    grouped={}
    for r in receipts:
        if r['case_id'] not in labels: raise ValueError('Missing gold label')
        row=(r['response']['answers']['owner']['probabilities'],labels[r['case_id']]['expected_owner'])
        grouped.setdefault(r['pack'],[]).append(row)
    return {'provenance':next(iter(kinds),'empty'),'warning':'Synthetic teaching cases are not a representative benchmark. Authored replay probabilities do not measure Jev accuracy. Even live results on these twelve cases are a smoke test, not a product claim.',
            'by_pack':{k:classification(v) for k,v in grouped.items()},
            'overall':classification([x for rows in grouped.values() for x in rows]),
            'notes':{i:labels[i]['teaching_note'] for i in ids}}
