import matplotlib.ticker as mticker
import matplotlib.pyplot as plt
import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")

CONF = sys.argv[1] if len(sys.argv) > 1 else "0.3"
RES, FIG = "results", "figures"
H_PRIOR_MM = 650
RANGE_EDGES = [15, 25, 35, 50, 70, 100, 150]
os.makedirs(FIG, exist_ok=True)

plt.rcParams.update({
    "figure.dpi": 150, "font.size": 9, "axes.grid": True,
    "grid.alpha": 0.25, "axes.spines.top": False, "axes.spines.right": False,
})
C_GT, C_DET, C_3 = "#1f4e79", "#c1666b", "#4f7942"


def binned(x, y, edges, minimum=10):
    c, m, lo, hi = [], [], [], []
    for a, b in zip(edges[:-1], edges[1:]):
        s = (x >= a) & (x < b) & np.isfinite(y)
        if s.sum() < minimum:
            continue
        c.append(np.sqrt(a * b))
        m.append(np.median(y[s]))
        lo.append(np.percentile(y[s], 25))
        hi.append(np.percentile(y[s], 75))
    return map(np.array, (c, m, lo, hi))


def load(name):
    p = f"{RES}/{name}"
    if not os.path.exists(p):
        print(f"  missing {p}")
        return None
    return np.loadtxt(p, delimiter=",", skiprows=1)


# ---------------------------------------------------------------- fig 1
def fig_error_vs_range():
    d = load(f"pipeline_test_conf{CONF}.csv")
    if d is None:
        return
    Zt, Zdet, Zgt = d[:, 1], d[:, 2], d[:, 3]

    fig, ax = plt.subplots(figsize=(6.4, 3.7))
    for Zp, col, lab in ((Zgt, C_GT, "annotation boxes"),
                         (Zdet, C_DET, f"detector boxes (conf {CONF})")):
        rel = 100 * (Zp - Zt) / Zt
        c, m, lo, hi = binned(Zt, rel, RANGE_EDGES)
        ax.fill_between(c, lo, hi, color=col, alpha=0.15, linewidth=0)
        ax.plot(c, m, "o-", color=col, label=lab, markersize=4)

    # Legend entry for the shaded uncertainty band. The actual bands above
    # retain each series colour; this neutral proxy explains their meaning.
    ax.fill_between([], [], [], color="gray", alpha=0.2,
                    label="interquartile range")

    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xscale("log")
    ax.set_xticks([20, 30, 50, 70, 100])
    ax.get_xaxis().set_major_formatter(mticker.ScalarFormatter())
    ax.get_xaxis().set_minor_formatter(mticker.NullFormatter())
    ax.set_xlabel("stereo reference distance (m)")
    ax.set_ylabel("signed distance error (%)")
    ax.set_title("Signed ranging error against range")
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(f"{FIG}/error_vs_range.png")
    plt.close(fig)
    print("wrote error_vs_range.png")


# ---------------------------------------------------------------- fig 2
def fig_size_prior(split="train"):
    d = load(f"implied_height_{split}.csv")
    if d is None:
        return
    H = d[:, 1]

    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    ax.hist(H, bins=np.arange(0, 2100, 50), color=C_GT, alpha=0.85)
    top = ax.get_ylim()[1]

    ax.axvline(H_PRIOR_MM, color=C_DET, linewidth=2,
               label=f"prior used: {H_PRIOR_MM} mm")

    # Round-sign diameters only. VwV-StVO triangle figures are side
    # lengths, not vertical extents, so they do not belong on this axis.
    for v in (420, 600, 750):
        ax.axvline(v, color="black", linestyle=":", linewidth=0.9)
        ax.text(v, top * 0.98, f"{v}", fontsize=7, ha="right", va="top")
    ax.text(0.98, 0.70, "dotted: nominal round-sign\ndiameters (VwV-StVO)",
            transform=ax.transAxes, fontsize=7.5, ha="right", va="top")

    ax.set_xlabel("physical sign height implied by stereo reference (mm)")
    ax.set_ylabel("signs")
    ax.set_title(f"Implied sign height, {split} split (n={len(H)})")
    ax.legend(frameon=False, fontsize=8, loc="upper right")
    fig.tight_layout()
    fig.savefig(f"{FIG}/size_prior.png")
    plt.close(fig)
    print("wrote size_prior.png")


# ---------------------------------------------------------------- fig 3
def fig_coverage():
    d = load(f"pipeline_test_conf{CONF}.csv")
    if d is None:
        return
    Zt, Zdet = d[:, 1], d[:, 2]

    labels, cov, n = [], [], []
    for a, b in zip(RANGE_EDGES[:-1], RANGE_EDGES[1:]):
        s = (Zt >= a) & (Zt < b)
        if s.sum() < 10:
            continue
        labels.append(f"{a}\u2013{b}")
        cov.append(100 * np.isfinite(Zdet[s]).mean())
        n.append(int(s.sum()))

    fig, ax = plt.subplots(figsize=(6.4, 3.3))
    ax.bar(range(len(cov)), cov, color=C_GT, alpha=0.85, width=0.65)
    for i, (v, k) in enumerate(zip(cov, n)):
        ax.text(i, v + 1.5, f"{v:.0f}%", ha="center", fontsize=8)
        ax.text(i, 3, f"n={k}", ha="center", fontsize=7, color="white")
    ax.set_xticks(range(len(cov)))
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 105)
    ax.set_xlabel("stereo reference distance (m)")
    ax.set_ylabel("signs receiving an estimate (%)")
    ax.set_title(f"Coverage falls with range (conf {CONF})")
    fig.tight_layout()
    fig.savefig(f"{FIG}/coverage_vs_range.png")
    plt.close(fig)
    print("wrote coverage_vs_range.png")


# ---------------------------------------------------------------- fig 4
def fig_operating_point():
    d = load("conf_sweep_detval.csv")
    if d is None:
        return
    conf, prec, rec, f1 = d[:, 0], d[:, 1], d[:, 2], d[:, 3]
    best = int(np.argmax(f1))

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.2, 3.5))

    a1.plot(conf, prec, "o-", color=C_GT, ms=4, label="precision")
    a1.plot(conf, rec, "s-", color=C_DET, ms=4, label="recall")
    a1.plot(conf, f1, "^-", color=C_3, ms=4, label="F1")
    a1.axvline(conf[best], color="black", linestyle=":", linewidth=1)
    a1.annotate(f"selected: {conf[best]:.2f}", (conf[best], 0.30),
                textcoords="offset points", xytext=(6, 0), fontsize=8)
    a1.set_xlabel("confidence threshold")
    a1.set_ylabel("score")
    a1.set_ylim(0.25, 1.0)
    a1.set_title("Threshold sweep on detector-val cities")
    a1.legend(frameon=False, fontsize=8)

    a2.plot(100 * rec, 100 * prec, "o-", color=C_GT, ms=4)
    for i in range(0, len(conf), 2):
        a2.annotate(f"{conf[i]:.2f}", (100 * rec[i], 100 * prec[i]),
                    textcoords="offset points", xytext=(6, 4), fontsize=7)
    a2.plot(100 * rec[best], 100 * prec[best], "o", color=C_DET, ms=9,
            markerfacecolor="none", markeredgewidth=2)
    a2.set_xlabel("recall (%)")
    a2.set_ylabel("precision (%)")
    a2.set_title("Precision against recall")

    fig.tight_layout()
    fig.savefig(f"{FIG}/operating_point.png")
    plt.close(fig)
    print("wrote operating_point.png")


# ---------------------------------------------------------------- fig 5
def fig_paired():
    d = load(f"pipeline_test_conf{CONF}.csv")
    if d is None:
        return
    h, Zt, Zdet, Zgt = d[:, 0], d[:, 1], d[:, 2], d[:, 3]
    m = np.isfinite(Zdet) & (h >= 15)
    if m.sum() < 30:
        return
    dh = 100 * (Zgt[m] / Zdet[m] - 1)       # detector box height vs annotation

    fig, ax = plt.subplots(figsize=(5.6, 3.4))

    # Keep a wider visible range so large detector box-height errors are not
    # artificially piled up at +/-40%. Values beyond +/-60% are still clipped
    # to the boundary, so report their counts explicitly in the console.
    lo_tail = int(np.sum(dh < -60))
    hi_tail = int(np.sum(dh > 60))
    if lo_tail or hi_tail:
        print(f"  box-height tail beyond plot range: {lo_tail} < -60%, "
              f"{hi_tail} > +60%")

    ax.hist(np.clip(dh, -80, 80), bins=np.arange(-80, 81, 4),
            color=C_DET, alpha=0.85)
    ax.axvline(0, color="black", linewidth=0.9)
    med = np.median(np.abs(dh))
    ax.axvline(med, color=C_GT, linestyle="--", linewidth=1.4,
               label=f"median |error| = {med:.1f}%")
    ax.axvline(-med, color=C_GT, linestyle="--", linewidth=1.4)
    ax.set_xlabel("detector box height error vs annotation (%)")
    ax.set_ylabel("signs")
    ax.set_title("Detector box height error")
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(f"{FIG}/box_height_error.png")
    plt.close(fig)
    print("wrote box_height_error.png")


if __name__ == "__main__":
    fig_error_vs_range()
    fig_size_prior()
    fig_coverage()
    fig_operating_point()
    fig_paired()
