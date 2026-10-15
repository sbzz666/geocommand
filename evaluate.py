"""Reproducible fixture checks, not a claim of real-world agent accuracy."""
import json
from app.engine import Constraints, Query, run

cases=[('default',{},'S02',True),('risk',{},'S01',False),('budget',{},'S04',False),('risk_allowed',{'exclude_risk':False},'S01',True),('no_budget',{'max_rent':1000},'S02',False),('wide_metro',{'max_metro_m':3000},'S09',True)]
report=[]
for mode in ['single','multi']:
    passed=0
    elapsed=0
    for name,values,sid,expected in cases:
        result=run(Query(mode=mode,constraints=Constraints(**values)))
        row=next(r for r in result['results'] if r['id']==sid)
        passed+=row['eligible']==expected
        elapsed+=result['duration_ms']
    report.append({'mode':mode,'cases':len(cases),'passed':passed,'mean_ms':round(elapsed/len(cases),2),'llm_calls':0})
print(json.dumps({'benchmark':'synthetic-fixture-v1','note':'Shared deterministic tools: no accuracy uplift claimed for multi-agent mode.','results':report},ensure_ascii=False,indent=2))
if any(r['passed']!=r['cases'] for r in report):
    raise SystemExit(1)
