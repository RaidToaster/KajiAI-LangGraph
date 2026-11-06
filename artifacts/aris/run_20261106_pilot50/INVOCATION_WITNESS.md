# Frozen pilot invocation witness

Result: documented zero-live invocation succeeded, exit code 0. No doc-versus-reality divergence or additional concrete operational blocker observed. This witness does not qualify the method or verify account balances/provider billing.

Working directory: `D:\Projects\!skripsi\KajiAI-LangGraph`.

Exact documented command executed:

```powershell
.venv/Scripts/python.exe artifacts/aris/run_20261106_pilot50/pilot50.py --verify
```

The invocation environment set `OMP_NUM_THREADS`, `MKL_NUM_THREADS`, `OPENBLAS_NUM_THREADS`, `NUMEXPR_NUM_THREADS`, and `VECLIB_MAXIMUM_THREADS` to `2`. Existing venv reused; no dependencies changed. Tool-observed wall time: 1.558622 seconds.

Standard output:

```text
Frozen hashes and isolated imports verified; zero live inference
```

Standard error: empty. Exit code: `0`.

Separately checked SHA256 values match the supplied final freeze:

- protocol.json: `24437f4f7f8fd24443ec7f01ebf1753897c3f6752464fcd87b216a37f231cb3d`
- source-package.zip: `0c5875ec70e3b96bacea3d7b52fb6738e526a675e7529d805d15e27cd574a4bc`

The archived pilot accounting branch now requires a complete model reply and no transport error before marking usage known, resolving the final static-review follow-up. The frozen offline-check.json records six passed safety checks and zero live service calls; those fixture checks were read, not independently rerun for this invocation witness. The documented command itself independently verified all frozen file hashes, exact schedule/cap/model invariants, source digest, and actual isolated imports.

No live calls were made and no selected-case content or labels were opened. The verifier computes frozen file digests without displaying their contents. No method source, settings, protocol, schedule, or frozen review file was modified.

Reviewer requested: `gpt-6.1-sol`, reasoning effort `high`. Observed runtime model identity: unavailable. `review_independence: same-family`; `acceptance_status: provisional`.
