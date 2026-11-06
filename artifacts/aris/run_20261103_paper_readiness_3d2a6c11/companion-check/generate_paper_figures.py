"""Regenerate the paper's vector plot from the completed frozen evaluation."""
from pathlib import Path
import hashlib
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent
METRICS = ROOT / "results/study-20261009-v3/study-metrics.json"
data = json.loads(METRICS.read_text(encoding="utf-8"))
assert data["complete"] is True and data["n"] == 500
metrics = data["metrics"]
thresholds = np.array([0.5, 0.6, 0.7, 0.8, 0.9, 0.95])
coverage = np.array([metrics[f"semantic_threshold_{t:.2f}"]["coverage"] for t in thresholds])
accuracy = np.array([metrics[f"semantic_threshold_{t:.2f}"]["selective_accuracy"] for t in thresholds])
output = ROOT / "paper-figures"
output.mkdir(exist_ok=True)
plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "Nimbus Roman", "Times", "DejaVu Serif"],
    "font.size": 8,
    "axes.labelsize": 8,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "svg.fonttype": "none",
})
fig, ax = plt.subplots(figsize=(3.5, 2.25), layout="constrained")
ax.plot(thresholds, coverage*100, "o-", color="#17623b", linewidth=1.4,
        markersize=4, label="Coverage")
ax.plot(thresholds, accuracy*100, "s--", color="#275d91", linewidth=1.4,
        markersize=4, label="Accuracy among accepted")
ax.set(xlabel="Citation-review confidence threshold", ylabel="Percentage",
       ylim=(-3, 105), xlim=(0.47, 0.98), yticks=range(0, 101, 20),
       xticks=[0.5, 0.6, 0.7, 0.8, 0.9, 0.95])
ax.set_xticklabels(["0.50", "0.60", "0.70", "0.80", "0.90", "0.95"])
ax.grid(axis="y", alpha=0.18, linewidth=0.6)
ax.legend(loc="center left", frameon=False, fontsize=8)
for ext in ("pdf", "svg", "png"):
    fig.savefig(output/f"acceptance-thresholds.{ext}", dpi=240)
plt.close(fig)
(output/"provenance.json").write_text(json.dumps({
    "source_metrics": str(METRICS.relative_to(ROOT)),
    "source_metrics_sha256": hashlib.sha256(METRICS.read_bytes()).hexdigest(),
    "complete": True, "all_full_attempted": data["n"],
    "matched_n": data["n"],
    "plot_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    "thresholds": thresholds.tolist(),
    "coverage": coverage.tolist(),
    "selective_accuracy": accuracy.tolist(),
}, indent=2), encoding="utf-8")
print(output)

