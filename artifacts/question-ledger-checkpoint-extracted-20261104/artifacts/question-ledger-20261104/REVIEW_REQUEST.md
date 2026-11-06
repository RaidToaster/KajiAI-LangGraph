# New mechanism diagnostic review

Act as a senior ML reviewer. Verify the primary files yourself; do not accept my account. This is a diagnostic-design boundary, not paper acceptance. Same-family/provisional review. Never use Astra or launch service requests, other reviewers, or experiments. Read only development/controls, not confirmation/final case contents.

Objective: find a workflow that improves correct evidence-supported acceptance under unchanged guards, then frozen development (8 cases/model), untouched confirmation (12/model), then 2,000 final attempts (500 candidate + 500 matched baseline on each exact Flash model). No qualified workflow yet. Revision 8 and method packet are closed; do not reopen or retry their attempts. They do not prove universal impossibility. User now conditionally authorizes 68 new required workflow attempts (20 development plus 48 confirmation; reuse 12 matching baseline cells) only AFTER a small diagnostic justifies a candidate. Before that only a few targeted service calls; two used in this new investigation. Historical prior chain had 218 Ollama reservations and 549 Jev, retained separately. No more spending merely to find an output format.

Primary files in D:/Projects/!skripsi/KajiAI-LangGraph:
- CONTINUE_RESEARCH_PROMPT.md
- artifacts/flash-workflow-20261103/PROTOCOL.md
- artifacts/flash-workflow-20261103/method-packet-replay/decision.json
- artifacts/flash-workflow-20261103/method-packet-replay/glm-method/result.json
- artifacts/question-ledger-20261104/protocol.json
- artifacts/question-ledger-20261104/glm-planning/answer.json, result.json, usage.json
- artifacts/question-ledger-20261104/deepseek-planning/answer.json, result.json, usage.json
- src/kaji_langgraph/llm.py (decompose_with_questions, analyze)
- src/kaji_langgraph/graph.py (decompose, _unused_queries, check_evidence)
- src/kaji_langgraph/gate.py
- src/kaji_langgraph/evidence_ledger.py
- evaluation/flash_question_ledger.py

Observed: GLM output fenced JSON, strict diagnostic parser failed, but JSON content is retained and existing runtime parser can recover fenced objects. Both planners emit some meta-propositions ("the claim states...", "reference date is..."). GLM Bloomberg comparison statement omits "owns more than"; graph prepends original claim, so the runtime still requires the whole claim. DeepSeek asks measurement/population/time and counterevidence; GLM omits household/person conversion. No retrieval or assessment calls yet; no acceptance or discovery result. The literal ledger validator stores source version, exact quote offsets, dates/origins and material unresolved questions; it explicitly cannot certify semantics or independence and is not integrated in the runtime.

Please answer:
1. What is actually broken, versus harmless redundancy, in these observed plans and their graph use? Do not count the diagnostic parser failure as a runtime defect if runtime recovers it.
2. Is there a substantially new, evidence-backed premise for a question-driven material-component ledger rather than another cosmetic prompt? Specify what it could and could not fix in the Bloomberg anchor's concrete gaps. No confidence forcing, clearing genuine uncertainty, removing inconvenient citations, or threshold changes.
3. Design the smallest defensible NEXT diagnostic with sufficient, insufficient embedded-content/attribution, conflicting, and shared-lineage controls, plus the retained train-1225 anchor. Separate question effects from ledger effects with identical evidence/retrieval ceilings. Target <=6 further model calls and <=6 free Search requests, no unbounded grid. If the scientific comparison needs more, say exact counts rather than proposing a contaminated within-response pseudo-pair. Prefer saved evidence and explain whether any retrieval discovery is measurable. Define positive/negative outcomes and failure handling before calls. Passing format/labels alone cannot justify the 68 workflow attempts.
4. Identify any actual guard defect, or state that none is established. Give allowed claims and prioritized next steps. Do not infer study-wide futility from this candidate.

Report actionable findings and a concrete minimal design in your final response. You may write your raw review to artifacts/question-ledger-20261104/review-round1.md; do not edit runtime, frozen records or other files.

Scope limits: research-workflow tool, cooperating operator. No new hash frameworks, speculative wrappers/feature flags or exotic threat models. Existing source freeze integrity is retained. Say plainly when something is correct. No need to score venue readiness: no final study exists.
