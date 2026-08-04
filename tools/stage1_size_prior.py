import json
import glob
import os
import sys
import numpy as np
from PIL import Image

ROOT = "data"
SPLIT = sys.argv[1] if len(sys.argv) > 1 else None
if SPLIT not in ("train", "val"):
    sys.exit("usage: python <script>.py <train|val> [n_cities]")
CITIES = sorted(os.listdir(f"{ROOT}/gtFine/{SPLIT}"))
if len(sys.argv) > 2:
    CITIES = CITIES[:int(sys.argv[2])]

rows = []  # (h_px, w_px, Z, H_implied_mm)

for city in CITIES:
    for pf in sorted(glob.glob(f"{ROOT}/gtFine/{SPLIT}/{city}/*_polygons.json")):
        stem = os.path.basename(pf).replace("_gtFine_polygons.json", "")
        cf = f"{ROOT}/camera/{SPLIT}/{city}/{stem}_camera.json"
        df = f"{ROOT}/disparity/{SPLIT}/{city}/{stem}_disparity.png"
        if not (os.path.exists(cf) and os.path.exists(df)):
            continue
        cam = json.load(open(cf))
        fx, fy = cam["intrinsic"]["fx"], cam["intrinsic"]["fy"]
        b = cam["extrinsic"]["baseline"]
        objs = [o for o in json.load(
            open(pf))["objects"] if o["label"] == "traffic sign"]
        if not objs:
            continue
        disp = np.array(Image.open(df)).astype(float)
        for o in objs:
            p = np.array(o["polygon"], dtype=float)
            x0, y0 = np.floor(p.min(0)).astype(int)
            x1, y1 = np.ceil(p.max(0)).astype(int)
            x0, y0 = max(x0, 0), max(y0, 0)
            x1 = min(x1, disp.shape[1])
            y1 = min(y1, disp.shape[0])
            w, h = x1 - x0, y1 - y0
            if w < 2 or h < 2:
                continue
            patch = disp[y0:y1, x0:x1]
            if patch.size == 0:
                continue
            valid = patch[patch > 0]
            if len(valid) < 0.2 * patch.size:
                continue
            d = (np.median(valid) - 1) / 256
            if d <= 0:
                continue
            Z = b * fx / d
            if not (2 < Z < 120):
                continue
            H_mm = 1000.0 * Z * h / fy          # invert Z = fy*H/h
            rows.append((h, w, Z, H_mm))

r = np.array(rows)
h_px, w_px, Z, H = r[:, 0], r[:, 1], r[:, 2], r[:, 3]
ar = w_px / h_px

print(f"split={SPLIT}  cities={len(CITIES)}  n={len(r)}")
print(f"aspect ratio w/h: p10={np.percentile(ar, 10):.2f} "
      f"median={np.median(ar):.2f} p90={np.percentile(ar, 90):.2f}")

# restrict to near, square-ish, well-resolved signs: least noisy estimate
m = (h_px >= 30) & (np.abs(ar - 1) < 0.25)
print(f"\nclean subset (h>=30px, near-square): n={m.sum()}")
for q in [10, 25, 50, 75, 90]:
    print(f"  p{q:<2} implied height = {np.percentile(H[m], q):6.0f} mm")

print("\nhistogram, clean subset, 100 mm bins:")
counts, edges = np.histogram(H[m], bins=np.arange(0, 2100, 100))
for c, e in zip(counts, edges):
    if c:
        print(f"  {e:4.0f}-{e+100:4.0f} mm  {'#' * int(60*c/counts.max()):<60} {c}")
