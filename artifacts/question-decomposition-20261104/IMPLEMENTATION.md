# Optional statements-and-questions decomposition

User requested model decomposition into both statements and verification questions; later clarified this was intended for the next-session prompt and allowed keeping the implementation. CONTINUE_RESEARCH_PROMPT.md now contains the full updated prompt.

QuestionDecomposition requires 1-6 nonempty self-contained statements and 1-8 nonempty questions. Ollama receives only the claim and runtime reference date for this planning step, with scope/attribution/counterevidence instructions and no verdict request. The existing structured adapter and one schema-repair path are reused.

Workflow preserves the original claim plus generated statements for its unchanged evidence gate. Questions remain separate, feed the shared unused-query inventory after targeted assessment follow-ups, and consume the existing search/time/token budgets. Retrieval/exhaustion use the same queue. JSON and report retain the questions; actual searches remain separate. Failure or malformed plans fall back to existing statement splitting with an error and incomplete token accounting. Default behavior remains statement-only.

Configuration: model.decomposition_method: statements_and_questions. CLI: --decomposition-method statements_and_questions. --mock uses deterministic templates and makes no cloud calls.

Validation: full offline pytest suite passed (95 tests). A first focused run had one test-fixture omission (research_history), corrected before the passing full suite; the failed log is preserved. Offline CLI smoke output is mock-output.json. No live model/retrieval calls were made, and no research-performance/acceptance claim is supported by these checks.

Historical study manifests, attempts, PDF and reproducibility archives are unchanged. Their source digest intentionally differs from the new checkout, and their launchers must not be used to run this feature without a new freeze. source-before.zip preserves the already dirty pre-change runtime; source-after.zip preserves this implementation. No commit, push or publication.
