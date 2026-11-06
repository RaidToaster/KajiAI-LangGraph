# Interim verification

This record covers the 47 reused DeepSeek cells. The 953 fresh cells remain untouched at this checkpoint. The paper and package therefore describe an incomplete evaluation. The next cell and earliest quota eligibility are recorded in status.json.

## Commands and results

1. Used the project Python 3.12 virtualenv to run `launch.py --verify`, `launch.py --checkpoint`, and `offline_check.py`. Frozen file hashes, source import isolation, the 1,000-cell schedule, 4,106 reused file hashes, spend reservations, quota gating, and Windows worker identity/timeout behavior passed.
2. Built the reproduction ZIP with the allowlisted `package.py`. Scanned included bytes and nested ZIP entries for project credentials and excluded secret files. Extracted the ZIP in a clean directory and ran `analyze.py`, `forecast.py` and `render_table.py`. The attempt CSV, service ledger, score summary, report, forecast, and manuscript table reproduced byte for byte.
3. Extracted the editable ZIP into a fresh directory and ran `tectonic -X compile --outfmt pdf --keep-logs --print --untrusted paper.tex` using Tectonic 0.17.0+20260731. The PDF has 10 letter pages, all 19 font resources embedded, 11 resolved bibliography entries and no overfull boxes or unresolved reference markers. Tectonic reported font substitutions and underfull spacing warnings. Poppler rendered all 10 pages, and the page images were inspected for legibility, clipping, figure and table placement, and layout. The delivered PDF is the clean build.
4. A fresh Sol reviewer recounted the DeepSeek and historical figures from primary records. The claim audit passed with the documented corrections. Review is same-family and provisional. Independent human annotation of citation support and credibility remains open.

## SHA-256

- `evaluation/paper.pdf` — `164e287eb991b73b1084082ef653f51e31734c346556c7dd0b8e7e1a89b0501c`
- `evaluation/paper.tex` — `d41c7fcea6aa59ddec057477c771469fec44bf22758c3cfc237df4260c0f3fe2`
- `evaluation/paper-source.zip` — `3cb401f3a945a86f0a18b442faf7a0a4562b13945082d3c3ccf28fc32c39359f`
- `evaluation/deepseek-results.tex` — `b19e42293dbaa1546a368cf7d5745dca89360f42b942a0b4a502f84fb14bed18`
- `artifacts/aris/run_20261106_deepseek500/protocol.json` — `36f42f6eb075e54ad0a3c47539789309b0a43634906e8d7160ca3c761bbab94c`
- `artifacts/aris/run_20261106_deepseek500/approval.json` — `a06d4cc7457622f2244c43f8388d901a6414ac66b6f7e36d1ae5e8c78001fd39`
- `artifacts/aris/run_20261106_deepseek500/schedule.json` — `c8f7ba2a942e26feee3ef3e27779e1bf2ab080070cbd9668ba5779e32becddac`
- `artifacts/aris/run_20261106_deepseek500/reused.json` — `88ff63895cd9f5a85d79cd3843da108d5e8c8420cd2c0713b156c06cce70ce28`
- `artifacts/aris/run_20261106_deepseek500/account-confirmation.json` — `5ef601cba4c26ccd79847dd3b96e9c17c4ea8066e5517a7ecab8f4bfe77fe00a`
- `artifacts/aris/run_20261106_deepseek500/REPORT.md` — `fae9900e3772aaf6a9b1f8cb701e12e50e81059838d9d473e8dec38d922c652f`
- `artifacts/aris/run_20261106_deepseek500/attempts.csv` — `569ac7001baa67f9633afc69c1f9845d80c88f46e66915e99b69eae940a12f35`
- `artifacts/aris/run_20261106_deepseek500/service-ledger.json` — `ae3e6b45487f8bd6e32af3b5b16c4aff96cedc753ea71feac2c361b70ba989d6`
- `artifacts/aris/run_20261106_deepseek500/summary.json` — `0636ace68dbc6231b7c64953f9ba5022159ea39f028c204ac5b2b134a9a89bea`
- `artifacts/aris/run_20261106_deepseek500/forecast.json` — `c9b66a08e356e541af59830456e5be016d593bd2b53ff45a18c7e83f31833089`
- `artifacts/aris/run_20261106_deepseek500/deepseek500-reproducibility.zip` — `111d57e8be7e939b951d7679f84aef7b36af7cbb34096c8dc7de5db6e893de1b`
- `artifacts/aris/run_20261106_deepseek500/paper-clean-final/compile.log` — `095fe205ab948ee12cc07dd35c5b2138fb62c8f8d5c7671636b1eee7b1314382`
- `artifacts/aris/run_20261106_deepseek500/paper-clean-final/pdf-check.json` — `3b71373be28d460589ea6a687c23429c7929c753ffe5db9d57efd6cc67ca6751`
- `artifacts/aris/run_20261106_deepseek500/PAPER_CLAIM_AUDIT.json` — `2ba2469dc9e655eaf1584b2d7df1319fc32a65900100c26adc7443c1977a28b1`
