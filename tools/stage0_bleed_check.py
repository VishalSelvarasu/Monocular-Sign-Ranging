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

rows = []  # (short_side_px, Z_med, Z_p90)

for city in CITIES:
    for pf in sorted(glob.glob(f"{ROOT}/gtFine/{SPLIT}/{city}/*_polygons.json")):
        stem = os.path.basename(pf).replace("_gtFine_polygons.json", "")
        cf = f"{ROOT}/camera/{SPLIT}/{city}/{stem}_camera.json"
        df = f"{ROOT}/disparity/{SPLIT}/{city}/{stem}_disparity.png"
        if not (os.path.exists(cf) and os.path.exists(df)):
            continue
        cam = json.load(open(cf))
        fx, b = cam["intrinsic"]["fx"], cam["extrinsic"]["baseline"]
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
            if x1 - x0 < 2 or y1 - y0 < 2:
                continue
            patch = disp[y0:y1, x0:x1]
            if patch.size == 0:
                continue
            valid = patch[patch > 0]
            if len(valid) < 0.2 * patch.size:
                continue
            d_med = (np.median(valid) - 1) / 256
            d_p90 = (np.percentile(valid, 90) - 1) / 256
            if d_med <= 0 or d_p90 <= 0:
                continue
            Z_med, Z_p90 = b * fx / d_med, b * fx / d_p90
            if 2 < Z_med < 120:
                rows.append((min(x1 - x0, y1 - y0), Z_med, Z_p90))

r = np.array(rows)
px, Zm, Zp = r[:, 0], r[:, 1], r[:, 2]
gap = np.abs(Zm - Zp) / Zm

print(f"split={SPLIT}  cities={len(CITIES)}  n={len(r)}")
for lo, hi in [(0, 15), (15, 30), (30, 60), (60, 10_000)]:
    m = (px >= lo) & (px < hi)
    if m.sum() < 10:
        print(f"{lo:>3}-{hi:<5} n={m.sum():<5} (too few)")
        continue
    print(f"{lo:>3}-{hi:<5} n={m.sum():<5} median gap={100*np.median(gap[m]):5.1f}%  "
          f"Z_med={np.median(Zm[m]):5.1f}m  Z_p90={np.median(Zp[m]):5.1f}m")
