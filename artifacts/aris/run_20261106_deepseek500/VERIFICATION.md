# Verification of the 80-cell interim snapshot

This archive captures the 47 reused and 33 fresh terminal cells at the Search connection-reset boundary. Live execution subsequently resumed on untouched cells under a separate, hashed continuation receipt.

1. The reproduction archive was extracted separately and rebuilt with `analyze_paid.py`, `forecast.py`, and `render_table.py` using the project Python. The attempt CSV, service ledger, summary, report, forecast, Builder summary, acceptance audit and DeepSeek paper table matched byte for byte. The archive passed credential exclusion.
2. The PDF was built from a clean paper-source extraction using `tectonic -X compile --outfmt pdf --keep-logs --print --untrusted paper.tex`. It has 10 pages, 16 embedded font resources, 11 resolved bibliography entries and zero overfull boxes or unresolved reference markers. Font substitutions and underfull spacing warnings remain in the compiler log. All 10 pages were rendered and inspected.
3. A fresh Sol reviewer independently recounted the interim results from the raw journals. The claim audit is same-family and provisional. Historical results have a separate retained audit. Independent human citation and credibility annotation remains open.

## SHA-256

- `evaluation/paper.pdf` — `8ae547233f4ff67725398303d3aa09fb6a6e401406b8dc8da5127ce2a54c211c`
- `evaluation/paper.tex` — `4ed64435950ab9a0ec1702287361271dd7ed865905ed9e11ef595c45d82ae9ca`
- `evaluation/paper-source.zip` — `5383499493dca4536f3ed10f2e1e1520fd32c5e0fa824a06862f7a019cae3520`
- `evaluation/deepseek-results.tex` — `160022715420cd496e3fb00391553438d8ce352f6f0b5837c26a923e5a47687b`
- `artifacts/aris/run_20261106_deepseek500/deepseek500-reproducibility.zip` — `7ef8be9698ecea3360c2b3db7e6bc168e2635489ef8617007696af0278f60823`
- `artifacts/aris/run_20261106_deepseek500/protocol.json` — `36f42f6eb075e54ad0a3c47539789309b0a43634906e8d7160ca3c761bbab94c`
- `artifacts/aris/run_20261106_deepseek500/schedule.json` — `c8f7ba2a942e26feee3ef3e27779e1bf2ab080070cbd9668ba5779e32becddac`
- `artifacts/aris/run_20261106_deepseek500/reused.json` — `88ff63895cd9f5a85d79cd3843da108d5e8c8420cd2c0713b156c06cce70ce28`
- `artifacts/aris/run_20261106_deepseek500/REPORT.md` — `7a9d502afbb5a0adcc4bce87e9fea6caca3d338929084ca0aba5b6ecc609ec67`
- `artifacts/aris/run_20261106_deepseek500/attempts.csv` — `323cf890417b344efa2f7cffd662be9f7da41a1a7fafc891e6919a55f8e53631`
- `artifacts/aris/run_20261106_deepseek500/service-ledger.json` — `1eb17e3cdd0f6161932c3a9dfb5648377d988d23a410adf98222d06c18813c5f`
- `artifacts/aris/run_20261106_deepseek500/summary.json` — `fc9708b8b8b7b38ca3d0e2d4e056cba9dcddd98c51e4d86cb73a1add531e2f15`
- `artifacts/aris/run_20261106_deepseek500/builder-summary.json` — `b7c023f3270146ecbf647bdcc5ac0a6dee6b0b7612f529ddfc7d6a1a721a3643`
- `artifacts/aris/run_20261106_deepseek500/PAPER_CLAIM_AUDIT.json` — `16ed60e027f29d37b587bce4836811429542b95b9f75a8d4502fcc2ccbb520f4`
- `artifacts/aris/run_20261106_deepseek500/paper-clean-reviewed-stop/compile.log` — `3761484a428e2fb9d3ba590e64b391b4c083a2e31ef9a4d77f7f936c7daf6d65`
- `artifacts/aris/run_20261106_deepseek500/paper-clean-reviewed-stop/pdf-check.json` — `eda3e6c65cbea888c920ef8e961b327d3b525b29028b23f4cc2289917455f263`
