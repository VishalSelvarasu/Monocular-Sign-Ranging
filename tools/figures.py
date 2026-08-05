import matplotlib.pyplot as plt
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")

RES, FIG = "results", "figures"
H_PRIOR_MM = 650
RANGE_EDGES = [15, 25, 35, 50, 70, 100, 150]
os.makedirs(FIG, exist_ok=True)

plt.rcParams.update({
    "figure.dpi": 150, "font.size": 9, "axes.grid": True,
    "grid.alpha": 0.25, "axes.spines.top": False, "axes.spines.right": False,
})
C_GT, C_DET, C_MISS = "#1f4e79", "#c1666b", "#888888"


def binned(x, y, edges):
    """median and IQR of y within bins of x. returns centres, med, lo, hi, n"""
    c, m, lo, hi, n = [], [], [], [], []
    for a, b in zip(edges[:-1], edges[1:]):
        s = (x >= a) & (x < b) & np.isfinite(y)
        if s.sum() < 10:
            continue
        c.append(np.sqrt(a * b))          # geometric centre, log-ish spacing
        m.append(np.median(y[s]))
        lo.append(np.percentile(y[s], 25))
        hi.append(np.percentile(y[s], 75))
        n.append(int(s.sum()))
    return map(np.array, (c, m, lo, hi, n))


# ---------------------------------------------------------------- fig 1
def fig_error_vs_range(conf=0.25):
    f = f"{RES}/pipeline_val_conf{conf}.csv"
    if not os.path.exists(f):
        print(f"skip fig1: {f} missing")
        return
    d = np.loadtxt(f, delimiter=",", skiprows=1)
    Zt, Zdet, Zgt = d[:, 1], d[:, 2], d[:, 3]

    fig, ax = plt.subplots(figsize=(6.2, 3.6))
    for Zp, col, lab in ((Zgt, C_GT, "ground-truth boxes"),
                         (Zdet, C_DET, f"detector boxes (conf {conf})")):
        rel = 100 * (Zp - Zt) / Zt
        c, m, lo, hi, n = binned(Zt, rel, RANGE_EDGES)
        ax.fill_between(c, lo, hi, color=col, alpha=0.15, linewidth=0)
        ax.plot(c, m, "o-", color=col, label=lab, markersize=4)

    ax.axhline(0, color="black", linewidth=0.8)
    ax.axhspan(-24, 24, color="#cccccc", alpha=0.2, zorder=0)
    ax.set_xscale("log")
    ax.set_xticks([20, 30, 50, 70, 100])
    ax.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
    ax.set_xlabel("stereo reference distance (m)")
    ax.set_ylabel("signed distance error (%)")
    ax.set_title("Ranging error vs range, shaded band = IQR")
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(f"{FIG}/error_vs_range.png")
    plt.close(fig)
    print("wrote error_vs_range.png")


# ---------------------------------------------------------------- fig 2
def fig_size_prior(split="train"):
    f = f"{RES}/implied_height_{split}.csv"
    if not os.path.exists(f):
        print(f"skip fig2: {f} missing")
        return
    d = np.loadtxt(f, delimiter=",", skiprows=1)
    H = d[:, 1]

    fig, ax = plt.subplots(figsize=(6.2, 3.4))
    ax.hist(H, bins=np.arange(0, 2100, 50), color=C_GT, alpha=0.8)
    ax.axvline(H_PRIOR_MM, color=C_DET, linewidth=1.8,
               label=f"prior adopted, {H_PRIOR_MM} mm")
    for v, lab in ((420, "Größe 1"), (600, "Größe 2"), (750, "Größe 3")):
        ax.axvline(v, color="black", linestyle=":", linewidth=0.9)
        ax.text(v, ax.get_ylim()[1] * 0.95, lab, rotation=90,
                fontsize=7, ha="right", va="top")
    ax.set_xlabel("physical sign height implied by stereo depth (mm)")
    ax.set_ylabel("signs")
    ax.set_title(f"Sign height recovered from stereo, {split} split "
                 f"(n={len(H)})")
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(f"{FIG}/size_prior.png")
    plt.close(fig)
    print("wrote size_prior.png")


# ---------------------------------------------------------------- fig 3
def fig_coverage(conf=0.25):
    f = f"{RES}/pipeline_val_conf{conf}.csv"
    if not os.path.exists(f):
        print(f"skip fig3: {f} missing")
        return
    d = np.loadtxt(f, delimiter=",", skiprows=1)
    Zt, Zdet = d[:, 1], d[:, 2]

    c, cov, n = [], [], []
    for a, b in zip(RANGE_EDGES[:-1], RANGE_EDGES[1:]):
        s = (Zt >= a) & (Zt < b)
        if s.sum() < 10:
            continue
        c.append(np.sqrt(a * b))
        cov.append(100 * np.isfinite(Zdet[s]).mean())
        n.append(int(s.sum()))

    fig, ax = plt.subplots(figsize=(6.2, 3.2))
    ax.bar(range(len(c)), cov, color=C_GT, alpha=0.85, width=0.65)
    for i, (v, k) in enumerate(zip(cov, n)):
        ax.text(i, v + 1.5, f"{v:.0f}%", ha="center", fontsize=8)
        ax.text(i, 3, f"n={k}", ha="center", fontsize=7, color="white")
    ax.set_xticks(range(len(c)))
    ax.set_xticklabels([f"{a}\u2013{b}" for a, b in
                        zip(RANGE_EDGES[:-1], RANGE_EDGES[1:])][:len(c)])
    ax.set_ylim(0, 105)
    ax.set_xlabel("stereo reference distance (m)")
    ax.set_ylabel("signs with a distance estimate (%)")
    ax.set_title(f"Coverage falls with range, conf {conf}")
    fig.tight_layout()
    fig.savefig(f"{FIG}/coverage_vs_range.png")
    plt.close(fig)
    print("wrote coverage_vs_range.png")


# ---------------------------------------------------------------- fig 4
def fig_operating_point():
    # measured on cityscapes val, stage4_pipeline_eval.py at three thresholds
    conf = np.array([0.40, 0.25, 0.10])
    cover = np.array([64.9, 74.1, 81.1])
    prec = np.array([0.826, 0.730, 0.560]) * 100

    fig, ax = plt.subplots(figsize=(5.4, 3.6))
    ax.plot(cover, prec, "o-", color=C_GT, markersize=6)
    for x, y, t in zip(cover, prec, conf):
        ax.annotate(f"conf {t:.2f}", (x, y), textcoords="offset points",
                    xytext=(8, 6), fontsize=8)
    ax.annotate("3.4 FP per sign gained", (69.5, 77.8), fontsize=7.5,
                color=C_MISS, ha="center")
    ax.annotate("13.4 FP per sign gained", (77.6, 64.5), fontsize=7.5,
                color=C_DET, ha="center")
    ax.set_xlabel("coverage: signs with a distance estimate (%)")
    ax.set_ylabel("precision (%)")
    ax.set_title(
        "Operating point: cost per recovered sign\nquadruples below conf 0.25")
    fig.tight_layout()
    fig.savefig(f"{FIG}/operating_point.png")
    plt.close(fig)
    print("wrote operating_point.png")


if __name__ == "__main__":
    fig_error_vs_range()
    fig_size_prior()
    fig_coverage()
    fig_operating_point()
