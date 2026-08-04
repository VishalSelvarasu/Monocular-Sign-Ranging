import json
import glob
import os
import sys
import numpy as np
from PIL import Image

ROOT, H_PRIOR = "data", 0.650
SPLIT = sys.argv[1] if len(sys.argv) > 1 else "val"
CITIES = sorted(os.listdir(f"{ROOT}/gtFine/{SPLIT}"))

rows = []  # (h_px, Z_true, Z_pred)

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
            if w < 2 or h < 2 or abs(w / h - 1) > 0.25:
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
            Z_true = b * fx / d
            if not (2 < Z_true < 250):
                continue
            rows.append((h, Z_true, fy * H_PRIOR / h))

r = np.array(rows)
h_px, Zt, Zp = r[:, 0], r[:, 1], r[:, 2]
rel = (Zp - Zt) / Zt          # signed, not absolute

print(f"split={SPLIT}  n={len(r)}  prior={H_PRIOR*1000:.0f} mm\n")
print(f"{'box h (px)':<12}{'n':>6}{'med Z_true':>12}{'bias':>9}{'p25':>8}{'p75':>8}{'|err|%':>8}")
for lo, hi in [(0, 15), (15, 30), (30, 60), (60, 10_000)]:
    m = (h_px >= lo) & (h_px < hi)
    if m.sum() < 10:
        continue
    lbl = f"{lo}-{hi if hi < 9999 else '+'}"
    print(f"{lbl:<12}{m.sum():>6}{np.median(Zt[m]):>11.1f}m"
          f"{100*np.median(rel[m]):>8.1f}%{100*np.percentile(rel[m], 25):>7.0f}%"
          f"{100*np.percentile(rel[m], 75):>7.0f}%{100*np.median(np.abs(rel[m])):>7.1f}%"
          f"{np.median(Zp[m]):>10.1f}m")
