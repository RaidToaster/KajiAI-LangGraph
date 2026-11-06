# Build the KajiAI manuscript

The editable manuscript is `paper.tex`. Its bibliography is embedded in the document, and `paper-figures/` contains the historical figure and its provenance. The DeepSeek table comes from `deepseek-results.tex`. It is regenerated offline from the study's frozen journals and included for an ordinary manuscript build.

From an extracted source directory, use the existing Tectonic compiler with the IEEEtran bundle:

```powershell
tectonic -X compile --outfmt pdf --keep-logs --print --untrusted paper.tex
```

The PDF was compiled with Tectonic 0.17.0+20260731. A TeX Live installation with IEEEtran and the declared packages can also build the source with `latexmk -pdf -halt-on-error paper.tex`.

See the separate DeepSeek reproducibility archive for the journal recount and table regeneration. The manuscript is an interim snapshot of the frozen comparison. Its study status is fixed to the reported checkpoint.

