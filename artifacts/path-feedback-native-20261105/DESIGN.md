# Review evidence paths before adjudication

The preceding context-reference compiler fix passed local tests and live native
compilation, but that phase remains CLOSED FAILED: GLM inferred actual source
independence from separately reported searches despite shared underlying tweet
evidence and explicit cross-citations, omitting the material uncertainty.

Concrete workflow diagnosis: the existing final Jev provenance check runs ONLY
after all structural and citation checks pass. A weak Reuters snippet (.64)
therefore prevented the model from ever receiving shared-origin feedback on this
packet. Merely repeating confidence instructions or retrying the old phase would
not address this ordering problem.

New opt-in mechanism model.predecision_source_path_review: one Jev Choice over
the same ranked12/completeparagraph3500character record view BEFORE each passage
decision. Independent/shared/unclear assesses relevant evidence paths, separately
from any factual verdict. Inputs, source IDs, model ID, input hash, returned
relation/confidence and raw usage remain retained. The Flash model receives this
explicitly fallible automated review plus all original records. It still owns
every class, stance, issue materiality, actual independence and confidence;
the client never rewrites a judgment or clears gaps. A test intentionally returns
independence=true after shared feedback and verifies that it is preserved: the
semantic audit must reject that if unsupported. This is not a planted answer.

The original acceptance-stage citation/provenance checks remain unchanged. Early
feedback does not certify world truth, substitute for final checks or justify
acceptance. Standard baseline mode never performs the opt-in precheck. Its analyze
AST and models.py remain unchanged. Existing per-cell40Jev/8Flash/6Search/12Fetch,
300seconds and original8/12scientificguards remain unchanged; added prechecks
consume those existing limits. Missing/failed Jev stops analysis without bypass.

New prospective native phase: at most2Flash/6Jev, zeroSearch/Fetch/retries, at most
1Flash/3Jev per model, GLMhigh then audit before DeepSeekfalse, fixed previously
audited source-blind plans,6144Flashoutput tokens/call,300seconds/job600aggregate,
one worker/two threads. Existing approximately$60Ollama/$4.77Jev credits; hard
scheduling ceilings$3Ollama/$.30Jev, no purchase/Builder/topup/billing change.
First service/accounting or substantive fidelity failure closes phase. Prior
continuation123Flash165Jev78Search144Fetch; old historical unknown stays unknown.
Both truthful native fidelity passes establish engineering entry only, then
promptly run original-order development19newcells/13identicalbaseline reuses;
48confirmation cells only afterdevelopmentpass. Final2000in anotherchat only.

This is a new upstream semantic-review boundary, not a renewed generic review of
the exhausted single-call compiler boundary. Allow one focused native reviewer
of this concrete integration, then execute, preserving any negative outcome.

Official TypeSafe SDK/Choice/citation-check docs were consulted on2026-11-05:
https://docs.typesafe.ai/sdk/python
https://docs.typesafe.ai/primitives/choice
https://docs.typesafe.ai/cookbooks/citation_check
Markdown endpoints failed; normal official HTML documentation was available.
