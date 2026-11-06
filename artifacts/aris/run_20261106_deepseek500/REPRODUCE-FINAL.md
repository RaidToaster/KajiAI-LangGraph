# Reproduce the frozen DeepSeek evaluation

Extract the reproducibility ZIP into an empty directory. Keep all paths as
stored. Use Python 3.12 with the frozen runtime dependencies listed under
the study's frozen directory. The original environment is recorded in the
parent pilot directory. Run these commands from the extraction root.

    $study = 'artifacts/aris/run_20261106_deepseek500'
    python "$study/verify_extraction.py" .

The verifier checks the SHA-256 index, rehashes the reused raw records and
frozen inputs, recounts the attempt and service ledgers, and regenerates the
report, summary, tariff ledger, acceptance audit and DeepSeek table. It compares
the regenerated files to the archived hashes. The analysis joins gold labels
offline and retains failed attempts and unknown provider reservations.

Extract the nested historical archive at
artifacts/flash-workflow-20261103/flash-study-negative-development-20261104-verified.zip
into a separate directory. Its REPRODUCE_20261104.md instructions regenerate
the Flash and stopping analyses from those raw records and document the Gemma
analysis. Run the following from the DeepSeek extraction to regenerate and
check the historical result-table rows against the final manuscript.

    python "$study/historical_tables.py" PATH_TO_HISTORICAL_EXTRACTION evaluation/paper.tex historical-table-rows.tex

Extract evaluation/paper-source.zip to a clean directory. Follow the build
instructions in that source archive. The bibliography is embedded and the
figures and generated DeepSeek table are included. VERIFICATION.md gives
the exact extraction and build checks used for delivery.

The archive supports offline reproduction. It contains no account credentials.
Live launchers are included as protocol evidence. The selected 50-case stratum
includes cases used to choose DeepSeek. The other 450 cases and the pooled 500
are shown separately. Independent human evidence annotation remains open.
