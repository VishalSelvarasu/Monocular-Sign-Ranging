import glob
import json
import os
import sys
import numpy as np
from PIL import Image

ROOT, H_PRIOR = "data", 0.650
MIN_GT_PX = 8
BOOT = 2000
rng = np.random.default_rng(0)

H_BINS = [(0, 15), (15, 30), (30, 60), (60, 10_000)]
Z_BINS = [(15, 25), (25, 35), (35, 50), (50, 70), (70, 100), (100, 150)]

SPLIT = sys.argv[1] if len(sys.argv) > 1 else None
if SPLIT not in ("train", "val"):
    sys.exit("usage: python stage2_error_curve.py <train|val> [n_cities]")
CITIES = sorted(os.listdir(f"{ROOT}/gtFine/{SPLIT}"))
if len(sys.argv) > 2:
    CITIES = CITIES[:int(sys.argv[2])]

rows = []          # (h_px, Z_true, Z_pred)

for city in CITIES:
    for pf in sorted(glob.glob(f"{ROOT}/gtFine/{SPLIT}/{city}/*_polygons.json")):
        stem = os.path.basename(pf).replace("_gtFine_polygons.json", "")
        cf = f"{ROOT}/camera/{SPLIT}/{city}/{stem}_camera.json"
        df = f"{ROOT}/disparity/{SPLIT}/{city}/{stem}_disparity.png"
        if not (os.path.exists(cf) and os.path.exists(df)):
            continue
        meta = json.load(open(pf))
        objs = [o for o in meta["objects"] if o["label"] == "traffic sign"]
        if not objs:
            continue

        cam = json.load(open(cf))
        fx, fy = cam["intrinsic"]["fx"], cam["intrinsic"]["fy"]
        b = cam["extrinsic"]["baseline"]
        disp = np.array(Image.open(df)).astype(float)

        seen = set()
        for o in objs:
            p = np.array(o["polygon"], dtype=float)
            x0, y0 = np.floor(p.min(0)).astype(int)
            x1, y1 = np.ceil(p.max(0)).astype(int)
            x0, y0 = max(x0, 0), max(y0, 0)
            x1 = min(x1, disp.shape[1])
            y1 = min(y1, disp.shape[0])
            w, h = x1 - x0, y1 - y0
            if w < MIN_GT_PX or h < MIN_GT_PX:
                continue
            if abs(w / h - 1) > 0.25:
                continue
            key = (x0, y0, x1, y1)
            if key in seen:
                continue
            seen.add(key)

            patch = disp[y0:y1, x0:x1]
            if patch.size == 0:
                continue
            valid = patch[patch > 0]
            if len(valid) < 0.2 * patch.size:
                continue
            d = (np.median(valid) - 1) / 256
            if d <= 0:
                continue
            Z_true = b * fx / d
            if not (2 < Z_true < 250):
                continue
            rows.append((h, Z_true, fy * H_PRIOR / h))

r = np.array(rows)
h_px, Zt, Zp = r[:, 0], r[:, 1], r[:, 2]
rel = (Zp - Zt) / Zt

# implied physical height, exact: H = Z_true * h / fy = H_prior * Z_true/Z_pred
# (avoids hardcoding fy, which varies slightly per frame)
H_imp = 1000.0 * H_PRIOR * Zt / Zp


def boot_ci(x, stat, n=BOOT):
    idx = rng.integers(0, len(x), size=(n, len(x)))
    return np.percentile([stat(x[i]) for i in idx], [2.5, 97.5])


def table(bins, key, label, unit):
    hdr = (f"{label:<12}{'n':>6}{'med H_imp':>11}{'med Z_true':>12}"
           f"{'bias':>9}{'p25':>8}{'p75':>8}{'MdARE':>9}{'95% CI':>18}")
    print(hdr)
    print("-" * len(hdr))
    for lo, hi in bins:
        m = (key >= lo) & (key < hi)
        if m.sum() < 10:
            continue
        e = rel[m]
        lo_ci, hi_ci = boot_ci(e, lambda x: 100 * np.median(np.abs(x)))
        big = hi >= 9999
        lbl = f"{lo}-{'+' if big else hi}"
        print(f"{lbl:<12}{m.sum():>6}{np.median(H_imp[m]):>9.0f}mm"
              f"{np.median(Zt[m]):>11.1f}m"
              f"{100*np.median(e):>8.1f}%{100*np.percentile(e, 25):>7.0f}%"
              f"{100*np.percentile(e, 75):>7.0f}%"
              f"{100*np.median(np.abs(e)):>8.1f}%"
              f"{f'[{lo_ci:.1f}, {hi_ci:.1f}]':>18}")
    print()


print(f"\nsplit={SPLIT}  cities={len(CITIES)}  n={len(r)}  "
      f"prior={H_PRIOR*1000:.0f} mm")
print("annotation boxes only, no detector\n")

print("stratified by box height:")
table(H_BINS, h_px, "box h (px)", "px")

print("stratified by stereo reference range:")
table(Z_BINS, Zt, "range (m)", "m")

m = h_px >= 15
e = rel[m]
lo_ci, hi_ci = boot_ci(e, lambda x: 100 * np.median(np.abs(x)))
print(f"headline population, box height >= 15 px:")
print(f"  signs={m.sum()}")
print(f"  MdARE={100*np.median(np.abs(e)):.1f}% "
      f"[95% CI {lo_ci:.1f}, {hi_ci:.1f}]")
print(f"  signed bias={100*np.median(e):+.1f}%  "
      f"IQR=[{100*np.percentile(e, 25):.0f}%, {100*np.percentile(e, 75):.0f}%]")
print(f"  range={np.percentile(Zt[m], 5):.0f}-"
      f"{np.percentile(Zt[m], 95):.0f} m")

# ---- why the two stratifications disagree ------------------------------
print("\nselection check: median implied physical height per stratum")
print("error = H_prior/H_actual - 1, so a stratum's bias is fixed by its")
print("median implied height. If that varies across strata, the")
print("stratification is selecting on the error source.\n")

print("  by box height:")
for lo, hi in H_BINS:
    m = (h_px >= lo) & (h_px < hi)
    if m.sum() < 10:
        continue
    big = hi >= 9999
    print(f"    {f'{lo}-{chr(43) if big else hi}':<10} n={m.sum():<5} "
          f"H={np.median(H_imp[m]):>5.0f} mm   "
          f"implies bias {100*(H_PRIOR*1000/np.median(H_imp[m])-1):+.1f}%")

print("\n  by range:")
for lo, hi in Z_BINS:
    m = (Zt >= lo) & (Zt < hi)
    if m.sum() < 10:
        continue
    print(f"    {f'{lo}-{hi}':<10} n={m.sum():<5} "
          f"H={np.median(H_imp[m]):>5.0f} mm   "
          f"implies bias {100*(H_PRIOR*1000/np.median(H_imp[m])-1):+.1f}%")

# minimum physical height observable at a given range, given the 8 px floor
print("\n  smallest sign the annotation floor admits at each range")
print("  (h >= 8 px with fy ~ 2262):")
for lo, hi in Z_BINS:
    print(f"    {f'{lo}-{hi}':<10} H_min = "
          f"{1000*MIN_GT_PX*np.sqrt(lo*hi)/2262:.0f} mm")

print("\nsize-prior error floor, from the stage 1 implied-height IQR:")
for lab, H in (("p25 574 mm", 574), ("p75 842 mm", 842)):
    print(f"  actual height {lab}: distance error "
          f"{100*(H_PRIOR*1000/H - 1):+.1f}%")

os.makedirs("results", exist_ok=True)
np.savetxt(f"results/stage2_{SPLIT}.csv", r, delimiter=",",
           header="h_px,Z_true,Z_pred_gt", comments="")
print(f"\nwrote results/stage2_{SPLIT}.csv")
