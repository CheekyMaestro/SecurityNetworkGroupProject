"""Draws Figure 1 of the report from one benchmark CSV in results/.

Usage (from the repo root):
    python scripts/fig.py results/benchmark-20261027-203518.csv
Output: results/figure1-benchmark.png
"""

import csv
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

COLORS = {"aes": "#2b7bba", "rc4": "#e69f00", "des": "#c0392b"}


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python scripts/fig.py results/<benchmark>.csv")
    rows = list(csv.DictReader(open(sys.argv[1])))
    sizes = sorted({int(r["size_mb"]) for r in rows})
    x = np.arange(len(sizes))
    w = 0.26
    fig, axes = plt.subplots(1, 2, figsize=(9, 2.9), sharey=True)
    for ax, op, title in [(axes[0], "enc", "Encryption"), (axes[1], "dec", "Decryption")]:
        for k, alg in enumerate(COLORS):
            mine = {int(r["size_mb"]): r for r in rows if r["cipher"] == alg}
            means = [float(mine[s][f"{op}_ms_per_mb"]) for s in sizes]
            sds = [float(mine[s][f"{op}_sd"]) for s in sizes]
            ax.bar(x + (k - 1) * w, means, w, yerr=sds, capsize=3, color=COLORS[alg], label=alg.upper())
        ax.set_xticks(x, [f"{s} MB" for s in sizes])
        ax.set_title(title, fontsize=10)
        ax.grid(axis="y", alpha=0.3)
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].set_ylabel("ms per MB (lower is faster)")
    axes[0].legend(frameon=False)
    fig.tight_layout()
    out = Path("results") / "figure1-benchmark.png"
    out.parent.mkdir(exist_ok=True)
    fig.savefig(out, dpi=200)
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
