"""Tool-free, stateless OpenAI Analyst benchmark with a hard USD reservation cap."""

from __future__ import annotations

import argparse, hashlib, json, os, time, urllib.error, urllib.request, uuid
from pathlib import Path

ROOT = Path(__file__).parent
MODELS = ("gpt-5.6-terra", "gpt-5.6-sol", "gpt-5.6-luna")
SCHEMA_VERSION = "analyst-benchmark-1.1"
PRICES = {
    "gpt-5.6-terra": (2.50, 15.00),
    "gpt-5.6-sol": (5.00, 30.00),
    "gpt-5.6-luna": (1.00, 6.00),
}
PRICE_BASIS_DATE = "2026-08-23"
OWNER_BUDGET_CEILING_USD = 8.0
MAX_OUTPUT_TOKENS = 1200
FORBIDDEN = ("account_number", "account number", "exact_balance", "ticket_id", "password", "api_key", "server_id")


def canonical(value): return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def payload(case):
    analysis_id = str(uuid.uuid5(uuid.NAMESPACE_URL, "xauusd-benchmark/" + case["id"]))
    snapshot_id = hashlib.sha256((SCHEMA_VERSION + ":" + case["id"]).encode()).hexdigest()
    facts = {k: case[k] for k in ("family","direction","regime","structure","location","confirmation","freshness","spread","volatility","event","exposure","rr","entry","stop","target_1","target_final","note")}
    return {"schema_version":SCHEMA_VERSION,"analysis_id":analysis_id,"snapshot_id":snapshot_id,"synthetic":True,"derived_facts":facts,"evidence_refs":["regime-1","structure-1","trigger-1","geometry-1"]}


def local_block(obj):
    text = canonical(obj).lower()
    return any(term in text for term in FORBIDDEN)


def geometry_ok(out):
    if out["decision"] == "NO_TRADE": return out["proposal"] == {"kind":"NONE"}
    p=out["proposal"]
    if p.get("kind") != "TRADE": return False
    e,s,t1,tf=map(float,(p["entry_price"],p["stop_loss"],p["target_1"],p["target_final"]))
    return (p["direction"]=="BUY" and s<e<t1<=tf) or (p["direction"]=="SELL" and s>e>t1>=tf)


def proposal_matches_case(out, case):
    if case["expected"] == "NO_TRADE":
        return out["proposal"] == {"kind":"NONE"}
    p=out["proposal"]
    if p.get("kind") != "TRADE": return False
    expected={"setup_family":case["family"],"direction":case["direction"],"entry_price":case["entry"],"stop_loss":case["stop"],"target_1":case["target_1"],"target_final":case["target_final"]}
    return all(p.get(k)==v for k,v in expected.items()) and sorted(p.get("evidence_refs",[])) == ["geometry-1","regime-1","structure-1","trigger-1"]


def output_checks(parsed, case, obj):
    return {
        "decision_match": parsed.get("decision") == case["expected"],
        "schema_version_match": parsed.get("schema_version") == SCHEMA_VERSION,
        "analysis_id_match": parsed.get("analysis_id") == obj["analysis_id"],
        "snapshot_id_match": parsed.get("snapshot_id") == obj["snapshot_id"],
        "proposal_exact_match": proposal_matches_case(parsed,case),
        "geometry_valid": geometry_ok(parsed),
        "required_reason_present": case["expected_reason"] in parsed.get("reason_codes",[]),
    }


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
    """List-price estimate from usage; the provider billing record is authoritative."""
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
    assert all(c.get("expected_reason") for c in cases)
    assert all(payload(c)["synthetic"] is True for c in cases)
    assert all(local_block(payload(c)) == (c["expected"]=="LOCAL_BLOCK") for c in cases)
    assert schema["additionalProperties"] is False and schema["properties"]["schema_version"]["enum"] == [SCHEMA_VERSION] and prompt.strip()
    return schema,cases,prompt


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--live",action="store_true"); ap.add_argument("--budget",type=float,default=OWNER_BUDGET_CEILING_USD); ap.add_argument("--prior-spend",type=float,default=0.0); ap.add_argument("--output",type=Path,default=ROOT/"BENCHMARK_RESULTS_V1_1.json"); args=ap.parse_args()
    if args.budget<=0 or args.budget>OWNER_BUDGET_CEILING_USD: raise SystemExit(f"budget must be >0 and <={OWNER_BUDGET_CEILING_USD:g}")
    if args.prior_spend<0 or args.prior_spend>=args.budget: raise SystemExit("prior spend must be >=0 and below budget")
    schema,cases,prompt=validate_files()
    if not args.live:
        print(json.dumps({"status":"DRY_PASS","schema_version":SCHEMA_VERSION,"models":MODELS,"cases":len(cases),"local_blocks":sum(c["expected"]=="LOCAL_BLOCK" for c in cases),"max_budget_usd":args.budget,"prior_spend_usd":args.prior_spend,"store":False,"tools":[]},indent=2)); return 0
    key=os.environ.get("OPENAI_API_KEY");
    if not key: raise SystemExit("OPENAI_API_KEY is absent; no live calls made")
    spent=args.prior_spend; rows=[]
    for case in cases:
        obj=payload(case)
        if local_block(obj):
            rows.append({"case":case["id"],"model":None,"expected":"LOCAL_BLOCK","observed":"LOCAL_BLOCK","pass":True,"cost_usd":0.0}); continue
        for model in MODELS:
            body=request_body(model,case,schema,prompt); reserve=reserve_cost(model,body)
            if spent+reserve>args.budget: raise SystemExit(f"budget reservation stop before {case['id']} {model}; spent={spent:.6f} reserve={reserve:.6f}")
            response,latency=call(key,body); cost=actual_cost(model,response); spent+=cost
            parsed=json.loads(output_text(response)); observed=parsed.get("decision"); checks=output_checks(parsed,case,obj); passed=all(checks.values())
            rows.append({"case":case["id"],"model":model,"expected":case["expected"],"observed":observed,"pass":passed,"checks":checks,"latency_ms":latency,"usage":response.get("usage",{}),"cost_usd":round(cost,8),"response_sha256":hashlib.sha256(canonical(parsed).encode()).hexdigest()})
    report={"schema_version":SCHEMA_VERSION,"status":"PASS" if all(r["pass"] for r in rows) else "FAIL","budget_usd":args.budget,"prior_spend_usd":round(args.prior_spend,8),"run_actual_cost_usd":round(spent-args.prior_spend,8),"cumulative_actual_cost_usd":round(spent,8),"cost_semantics":"LIST_PRICE_ESTIMATE_PROVIDER_BILLING_AUTHORITATIVE","price_basis_date":PRICE_BASIS_DATE,"store":False,"tools":[],"rows":rows}
    args.output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n"); print(json.dumps({k:report[k] for k in ("status","budget_usd","prior_spend_usd","run_actual_cost_usd","cumulative_actual_cost_usd")},indent=2)); return 0 if report["status"]=="PASS" else 2


if __name__=="__main__": raise SystemExit(main())
