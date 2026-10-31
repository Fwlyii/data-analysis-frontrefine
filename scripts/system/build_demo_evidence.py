"""Derive the five classroom cases from existing anonymous local features."""
import gzip
import json
import statistics
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'project.json').is_file())


def build():
    packed = json.loads(gzip.decompress((ROOT/'app/data/features.json.gz').read_bytes()))
    fields = packed['fields']
    rows = [dict(zip(fields, row)) for row in packed['rows']]
    summary = json.loads((ROOT/'app/data/summary.json').read_text())
    fixed = [r for r in rows if r['dataset']=='document_qa' and r['task']=='document_qa' and r['model']=='qwen' and r['prompt']=='NoCoT']
    values = sorted(r['tokens'] for r in fixed if r['tokens'] is not None)
    def quantile(p):
        i = (len(values)-1)*p
        lo = int(i)
        hi = min(lo+1,len(values)-1)
        return values[lo]+(values[hi]-values[lo])*(i-lo)
    histogram = [{'lo':i,'hi':i+10,'n':sum(i<=x<i+10 for x in values)} for i in range(0,(max(values)//10+1)*10,10)]
    anomaly = [r for r in rows if r['dataset']=='document_qa' and r['task']=='document_qa' and r['model']=='qwen3' and r['prompt']=='NoProperGrammar']
    joint = [sum((bool(r['truncated'])==t and r['scores'][0]==hit) for r in anomaly) for t,hit in [(False,1),(False,0),(True,1),(True,0)]]
    evidence = {
        'schema_version':'classroom-evidence-v1',
        'length':{'n':len(fixed),'valid':len(values),'questions':len({r['question'] for r in fixed}),'median':quantile(.5),'q1':quantile(.25),'q3':quantile(.75),'p95':quantile(.95),'mean':statistics.mean(values),'min':values[0],'max':values[-1],'histogram':histogram},
        'prompt': [r for r in summary['comparisons']['reasoning'] if r['benchmark']=='gsm8k' and r['first']=='DefaultCoT' and r['second']=='NoCoT'],
        'efficiency':[r for r in summary['comparisons']['reasoning'] if r['first']=='BeConcise' and r['second']=='DefaultCoT'],
        'position':[r for r in summary['comparisons']['document_qa'] if r['kind']=='position'],
        'anomaly':{'n':len(anomaly),'questions':len({r['question'] for r in anomaly}),'scores':[sum(r['scores'][i] for r in anomaly) for i in range(4)],'truncated':sum(r['truncated'] for r in anomaly),'joint':joint,'truncated_final_hits':sum(r['truncated'] and r['scores'][2]==1 for r in anomaly)}
    }
    assert len(fixed)==1200 and sum(b['n'] for b in histogram)==len(values)
    assert len(evidence['efficiency'])==12
    assert joint==[578,198,311,113] and len(anomaly)==1200
    out=ROOT/'app/data/demo-evidence.json'
    out.write_text(json.dumps(evidence,ensure_ascii=False,separators=(',',':'))+'\n')
    return evidence


if __name__=='__main__':
    evidence=build()
    print('Five classroom cases derived from local features; 1D + 2D + 2 multivariate + anomaly.')
