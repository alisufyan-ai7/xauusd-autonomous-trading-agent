import json, unittest
from benchmark_runner import MODELS, local_block, payload, request_body, reserve_cost, validate_files

class BenchmarkTests(unittest.TestCase):
    def test_files_and_local_blocks(self):
        schema,cases,prompt=validate_files(); self.assertEqual(18,len(cases)); self.assertEqual(2,sum(c["expected"]=="LOCAL_BLOCK" for c in cases))
    def test_every_request_is_stateless_tool_free_and_bounded(self):
        schema,cases,prompt=validate_files()
        for case in cases:
            if local_block(payload(case)): continue
            for model in MODELS:
                body=request_body(model,case,schema,prompt)
                self.assertIs(body["store"],False); self.assertEqual([],body["tools"]); self.assertLessEqual(body["max_output_tokens"],1200); self.assertGreater(reserve_cost(model,body),0)
    def test_payloads_have_no_broker_identity(self):
        _,cases,_=validate_files()
        for case in cases:
            if case["expected"]=="LOCAL_BLOCK": continue
            text=json.dumps(payload(case)).lower()
            for forbidden in ("account_number","ticket_id","server_id","password","api_key","exact_balance"):
                self.assertNotIn(forbidden,text)

if __name__=="__main__": unittest.main(verbosity=2)
