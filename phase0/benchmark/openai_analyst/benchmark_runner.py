"""Tool-free, stateless OpenAI Analyst benchmark with a hard USD reservation cap."""

from __future__ import annotations

import argparse, hashlib, json, os, time, urllib.error, urllib.request, uuid
from pathlib import Path

ROOT = Path(__file__).parent
MODELS = ("gpt-5.6-terra", "gpt-5.6-sol", "gpt-5.6-luna")
PRICES = {
    "gpt-5.6-terra": (2.00, 12.00),
    "gpt-5.6-sol": (4.00, 20.00),
    "gpt-5.6-luna": (0.20, 1.20),
}
OWNER_BUDGET_CEILING_USD = 8.0
MAX_OUTPUT_TOKENS = 1200
FORBIDDEN = ("account_number", "account number", "exact_balance", "ticket_id", "password", "api_key", "server_id")


def canonical(value): return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def payload(case):
    analysis_id = str(uuid.uuid5(uuid.NAMESPACE_URL, "xauusd-benchmark/" + case["id"]))
    snapshot_id = hashlib.sha256(("analyst-benchmark-1.0:" + case["id"]).encode()).hexdigest()
    facts = {k: case[k] for k in ("family","direction","regime","structure","location","confirmation","freshness","spread","volatility","event","exposure","rr","entry","stop","target_1","target_final","note")}
    return {"schema_version":"analyst-benchmark-1.0","analysis_id":analysis_id,"snapshot_id":snapshot_id,"synthetic":True,"derived_facts":facts,"evidence_refs":["regime-1","structure-1","trigger-1","geometry-1"]}


def local_block(obj):
    text = canonical(obj).lower()
    return any(term in text for term in FORBIDDEN)


def geometry_ok(out):
    if out["decision"] == "NO_TRADE": return out["proposal"] == {"kind":"NONE"}
    p=out["proposal"]
    if p.get("kind") != "TRADE": return False
    e,s,t1,tf=map(float,(p["entry_price"],p["stop_loss"],p["target_1"],p["target_final"]))
    return (p["direction"]=="BUY" and s<e<t1<=tf) or (p["direction"]=="SELL" and s>e>t1>=tf)


def output_text(response):
    for item in response.get("output",[]):
        if item.get("type") == "message":
            for content in item.get("content",[]):
                if content.get("type") == "output_text": return content.get("text","")
                if content.get("type") == "refusal": raise RuntimeError("model refusal")
    raise RuntimeError("no output_text")


def reserve_cost(model, request):
    inp,out=PRICES[model]
    conservative_input_tokens=len(canonical(request).encode("utf-8"))
    return conservative_input_tokens*inp/1_000_000 + MAX_OUTPUT_TOKENS*out/1_000_000


def actual_cost(model, response):
    usage=response.get("usage",{}); inp,out=PRICES[model]
    return usage.get("input_tokens",0)*inp/1_000_000 + usage.get("output_tokens",0)*out/1_000_000


def request_body(model, case, schema, prompt):
    return {"model":model,"store":False,"tools":[],"reasoning":{"effort":"low"},"max_output_tokens":MAX_OUTPUT_TOKENS,"input":[{"role":"system","content":[{"type":"input_text","text":prompt}]},{"role":"user","content":[{"type":"input_text","text":canonical(payload(case))}]}],"text":{"format":{"type":"json_schema","name":"xauusd_analyst_benchmark","strict":True,"schema":schema}}}


def call(key, body):
    req=urllib.request.Request("https://api.openai.com/v1/responses",data=canonical(body).encode(),headers={"Authorization":"Bearer "+key,"Content-Type":"application/json"},method="POST")
    started=time.monotonic()
    with urllib.request.urlopen(req,timeout=60) as resp: result=json.load(resp)
    return result, round((time.monotonic()-started)*1000,2)


def validate_files():
    schema=json.loads((ROOT/"analyst_output_schema.json").read_text()); cases=json.loads((ROOT/"benchmark_cases.json").read_text()); prompt=(ROOT/"system_prompt.txt").read_text()
    assert [c["id"] for c in cases] == [f"BM-{i:03d}" for i in range(1,19)]
    assert set(c["expected"] for c in cases) <= {"PROPOSE_TRADE","NO_TRADE","LOCAL_BLOCK"}
    assert all(payload(c)["synthetic"] is True for c in cases)
    assert all(local_block(payload(c)) == (c["expected"]=="LOCAL_BLOCK") for c in cases)
    assert schema["additionalProperties"] is False and prompt.strip()
    return schema,cases,prompt


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--live",action="store_true"); ap.add_argument("--budget",type=float,default=OWNER_BUDGET_CEILING_USD); ap.add_argument("--output",type=Path,default=ROOT/"BENCHMARK_RESULTS.json"); args=ap.parse_args()
    if args.budget<=0 or args.budget>OWNER_BUDGET_CEILING_USD: raise SystemExit(f"budget must be >0 and <={OWNER_BUDGET_CEILING_USD:g}")
    schema,cases,prompt=validate_files()
    if not args.live:
        print(json.dumps({"status":"DRY_PASS","models":MODELS,"cases":len(cases),"local_blocks":sum(c["expected"]=="LOCAL_BLOCK" for c in cases),"max_budget_usd":args.budget,"store":False,"tools":[]},indent=2)); return 0
    key=os.environ.get("OPENAI_API_KEY");
    if not key: raise SystemExit("OPENAI_API_KEY is absent; no live calls made")
    spent=0.0; rows=[]
    for case in cases:
        obj=payload(case)
        if local_block(obj):
            rows.append({"case":case["id"],"model":None,"expected":"LOCAL_BLOCK","observed":"LOCAL_BLOCK","pass":True,"cost_usd":0.0}); continue
        for model in MODELS:
            body=request_body(model,case,schema,prompt); reserve=reserve_cost(model,body)
            if spent+reserve>args.budget: raise SystemExit(f"budget reservation stop before {case['id']} {model}; spent={spent:.6f} reserve={reserve:.6f}")
            response,latency=call(key,body); cost=actual_cost(model,response); spent+=cost
            parsed=json.loads(output_text(response)); observed=parsed.get("decision"); passed=observed==case["expected"] and parsed.get("analysis_id")==obj["analysis_id"] and parsed.get("snapshot_id")==obj["snapshot_id"] and geometry_ok(parsed)
            rows.append({"case":case["id"],"model":model,"expected":case["expected"],"observed":observed,"pass":passed,"latency_ms":latency,"usage":response.get("usage",{}),"cost_usd":round(cost,8),"response_sha256":hashlib.sha256(canonical(parsed).encode()).hexdigest()})
    report={"status":"PASS" if all(r["pass"] for r in rows) else "FAIL","budget_usd":args.budget,"actual_cost_usd":round(spent,8),"store":False,"tools":[],"rows":rows}
    args.output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n"); print(json.dumps({k:report[k] for k in ("status","budget_usd","actual_cost_usd")},indent=2)); return 0 if report["status"]=="PASS" else 2


if __name__=="__main__": raise SystemExit(main())
