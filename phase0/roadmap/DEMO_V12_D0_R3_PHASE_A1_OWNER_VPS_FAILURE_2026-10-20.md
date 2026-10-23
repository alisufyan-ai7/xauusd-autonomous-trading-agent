# D0-R3 Phase A1 owner-attended Python version check — failure (2026-10-20)

**Immutable owner-reported incident, not broker/OS attestation.** This is the only output received for the ONE explicitly approved Phase A VERSION_ONLY attempt against PR21. No VPS command was issued/executed by the assistant; owner pasted the source hash-pinned ScriptBlock locally. Preserve original chat transcript; never replay/relabel this one-use A1 approval. This record is placed on new prospective stacked draft PR22 only; PR21 exact source/registration and prior R1/R2 are not modified.

## Source and approval

- Exact approved frozen PR21 HEAD: `f0423f40ae1cb51c01b915b6cfb5f7d7e799ce1e`.
- Reviewed PS5.1 verifier: `demo_adapter/scripts/v12-d0-r3-phased-runtime-verifier.ps1` SHA256 `3bc6a33b459bfebd732cf08725b2d34b95edf33b223266f6b9839f6aa3490281`.
- Invocation: `-Phase VERSION_ONLY -OwnerApprovalCode APPROVE_D0_R3_VERSION_ONLY_ONCE` embedded in SHA-checked `ScriptBlock`.
- Local candidate: `C:\Program Files\Python312\python.exe` with `-B -I -c`. Exact A1 source embeds Python `expected=r"C:\Program Files\Python312\python.exe"` and other double-quoted Python literals into `$code`, passed through Windows PowerShell 5.1 native argument marshaling.
- **Only** Phase A1 VERSION_ONLY was approved once. Phase B import, C terminal, D attachment were not approved.

## Exact essential owner-supplied stdout/stderr

```text
PS C:\Users\Administrator\Desktop\xauusd-autonomous-trading-agent>
R3_VERIFIER_SHA256=3bc6a33b459bfebd732cf08725b2d34b95edf33b223266f6b9839f6aa3490281
R3_VERIFIER_SHA256_VERIFIED
python.exe :   File "<string>", line 1
At line:71 char:19
+ $pythonOutput = @(& $pythonExecutable -B -I -c $code 2>&1)
+                   ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : NotSpecified: (  File "<string>", line 1:String) [], RemoteException
    + FullyQualifiedErrorId : NativeCommandError
PS C:\Users\Administrator\Desktop\xauusd-autonomous-trading-agent>
```

There is **no** `R3_VERSION_ONLY_PASS__PYTHON=3.12`, `PYTHON_EXE=...`, or `R3_PHASE_COMPLETE_NO_MT5_ATTACH__VERSION_ONLY` marker in supplied output. No full Python traceback, terminal process follow-up or exit status was shown. The absence of these markers is not proof that Python3.12 is absent or incompatible.

## Classification / causality / strict limits

- **A1 FAIL_CLOSED / INCOMPLETE VERSION VERIFICATION**, one attended A1 owner approval **CONSUMED**, no retry under A1 permission.
- Exact PS source SHA check **PASS**. `python.exe` evidently started and produced Python `File "<string>", line 1` error, but no verified interpreter version or path result. PowerShell surfaced a `NativeCommandError`; the traceback shown is truncated.
- **Plausible—not conclusively established—cause:** PowerShell 5.1 Legacy native argument handling stripped/mangled embedded Python double quotes in a `-c` argument, creating a syntax error. No sufficient traceback exists to prove this specific syntax. A software-quoting defect should be tested independently on isolated CI Windows runners, NOT by rerunning the consumed owner A1 attempt.
- Neither `MetaTrader5` import nor `mt5.initialize` is in the executed VERSION_ONLY branch; no broker read, order, MT5 connection, capture or VPS config mutation was requested. These cannot be independently disproven globally but are not evidenced by this run.
- Independent R1 `ab1c266290f3c38f5b8e08bd44b0b06645c0e496839b7c9fa47fd4581f9d0534` and R2 `13c1ece5068a18b04512776a7387615c51c7075bd9df850d7e4415f6cd773c61` remain two separately consumed immutable FAIL_CLOSED D0 pre-attach attempts. This Phase A1 error is a **third distinct diagnostic failure**, NOT an R1/R2 retry, **NOT** a consumed D0-R3 broker attachment attempt, and NOT any read-only broker/admission result.

## Prospective, not yet approved corrective next step

Propose a **different A2 owner-gated version-only invocation**, not a retry using A1 approval. A2 source `demo_adapter/scripts/v12-d0-r3-a2-version-only-ps51.ps1` uses a Python `-c` payload with **no embedded quote literals**, returns `3|12|<actual sys.executable>` and checks all three fields in PowerShell. It never imports MetaTrader5 or references MT5. A2 native Windows PS5.1 CI will test the exact `-c` argument against GitHub-hosted Python3.12, without accessing VPS. A2 registration `phase0/roadmap/DEMO_V12_D0_R3_PHASE_A2_PROSPECTIVE_VERSION_ONLY_REGISTRATION_2026-10-20.json` remains unapproved/unexecuted. Any renewed VPS Python start requires **NEW explicit owner A2 approval after exact HEAD/PS source SHA and native CI**, not the consumed A1 token. A2 cannot authorize future MT5 import or attachment.

**NO A2 OWNER APPROVAL YET. DO NOT GIVE A VPS A2 EXECUTION COMMAND UNTIL SEPARATELY APPROVED.**
