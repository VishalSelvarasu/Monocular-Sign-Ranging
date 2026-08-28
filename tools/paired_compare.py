import sys
import numpy as np

CONF = sys.argv[1] if len(sys.argv) > 1 else "0.3"
F = f"results/pipeline_test_conf{CONF}.csv"
H_BINS = [(15, 30), (30, 60), (60, 10_000)]
Z_BINS = [(15, 25), (25, 35), (35, 50), (50, 70), (70, 100), (100, 150)]
MIN_EVAL_PX = 15
BOOT = 2000
rng = np.random.default_rng(0)

d = np.loadtxt(F, delimiter=",", skiprows=1)
h_px, Zt, Zdet, Zgt = d[:, 0], d[:, 1], d[:, 2], d[:, 3]
found = np.isfinite(Zdet)

print(f"file={F}")
print(f"signs={len(d)}  detected={found.sum()} ({100*found.mean():.1f}%)")
print("\nBoth error columns are computed on the SAME detected signs.\n")


def boot_ci(x, stat, n=BOOT):
    idx = rng.integers(0, len(x), size=(n, len(x)))
    return np.percentile([stat(x[i]) for i in idx], [2.5, 97.5])


def table(bins, key, label):
    hdr = (f"{label:<12}{'n':>6}{'GT box':>10}{'det box':>10}"
           f"{'paired diff':>14}{'95% CI':>20}")
    print(hdr)
    print("-" * len(hdr))
    for lo, hi in bins:
        m = (key >= lo) & (key < hi) & found & (h_px >= MIN_EVAL_PX)
        if m.sum() < 20:
            continue
        e_gt = (Zgt[m] - Zt[m]) / Zt[m]
        e_dt = (Zdet[m] - Zt[m]) / Zt[m]
        diff = np.abs(e_dt) - np.abs(e_gt)      # positive = detector worse
        lo_ci, hi_ci = boot_ci(diff, lambda x: 100 * np.median(x))
        big = hi >= 9999
        lbl = f"{lo}-{'+' if big else hi}"
        print(f"{lbl:<12}{m.sum():>6}"
              f"{100*np.median(np.abs(e_gt)):>9.1f}%"
              f"{100*np.median(np.abs(e_dt)):>9.1f}%"
              f"{100*np.median(diff):>13.2f}%"
              f"{f'[{lo_ci:+.2f}, {hi_ci:+.2f}]':>20}")
    print()


print("stratified by stereo reference range:")
table(Z_BINS, Zt, "range (m)")

print("stratified by box height:")
table(H_BINS, h_px, "box h (px)")

print("paired diff = median of per-sign "
      "(|error with detector box| - |error with annotation box|)")
print("positive means the detector box is worse. A CI excluding 0 means")
print("the difference is resolvable at this sample size.\n")

# ---- direct measurement of the mechanism -------------------------------
m = found & (h_px >= MIN_EVAL_PX)
dh = 100 * (Zgt[m] / Zdet[m] - 1)   # h_det/h_gt = Z_pred_gt / Z_pred_det
print(f"detector box height vs annotation, detected signs "
      f">= {MIN_EVAL_PX} px (n={m.sum()}):")
print(f"  median {np.median(dh):+.2f}%   "
      f"p25 {np.percentile(dh, 25):+.2f}%   "
      f"p75 {np.percentile(dh, 75):+.2f}%   "
      f"|median| {np.median(np.abs(dh)):.2f}%")
print("  dZ/Z = -dh/h, so this is directly the distance error the detector")
print("  contributes, independent of the size prior.")

# ---- overall paired test ------------------------------------------------
e_gt = (Zgt[m] - Zt[m]) / Zt[m]
e_dt = (Zdet[m] - Zt[m]) / Zt[m]
diff = np.abs(e_dt) - np.abs(e_gt)
lo_ci, hi_ci = boot_ci(diff, lambda x: 100 * np.median(x))
mg, mdd = 100 * np.median(np.abs(e_gt)), 100 * np.median(np.abs(e_dt))
print(f"\nall detected signs >= {MIN_EVAL_PX} px, n={m.sum()}:")
print(f"  annotation box MdARE {mg:.2f}%")
print(f"  detector box   MdARE {mdd:.2f}%")
print(f"  paired median difference {100*np.median(diff):+.2f}% "
      f"[95% CI {lo_ci:+.2f}, {hi_ci:+.2f}]")
print(f"  quadrature check: sqrt({mg:.1f}^2 + "
      f"{np.median(np.abs(dh)):.1f}^2) = "
      f"{np.hypot(mg, np.median(np.abs(dh))):.1f}%")
