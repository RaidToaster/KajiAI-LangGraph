# Independent citation audit

The computational study is complete only when status.json says so. The audit worksheet is a separate, unperformed human-validation step. Its blank fields must not be treated as annotations, and Jev's judgments are not human ground truth.

Give annotators human-citation-audit.csv without human-audit-key.json. The key contains gold labels, claim IDs and acceptance status. The sample is stratified by acceptance, so its pooled accuracy is not an unbiased estimate of all generated citations.

For each row, review the claim, attached finding, quoted text, source URL and provided context. The task is whether this source evidence supports the attached finding, rather than whether the overall claim sounds true. If more context is needed, consult the archived retrieved text from the matching execution record; current webpages may have changed.

Use the following values in human_supports_finding:

- yes: the evidence supports the finding, including its qualifications, entities, quantities and time frame.
- no: the evidence contradicts the finding or does not substantiate it.
- unclear: the available archived context is insufficient to decide.

Record source credibility separately in human_source_credibility, with a short explanation in human_notes. Avoid inferring credibility from the model's confidence or treating different domains as proof of source independence. Note missing provenance, misleading quotation boundaries, omitted qualifications and unavailable context.

Prefer two independent annotators, retain their original decisions, measure agreement, then adjudicate disagreements. Report support rates separately for accepted and rejected strata and distinguish citation support from final-label correctness. Verify the evidence-gate threshold on a separate evaluation sample before claiming calibrated risk or optimality.

After real annotations are available, update the metrics and manuscript with the annotator count, rubric, sample sizes, agreement and adjudication procedure. Do not replace the current statement that independent human validation has not been performed before those steps are complete.
