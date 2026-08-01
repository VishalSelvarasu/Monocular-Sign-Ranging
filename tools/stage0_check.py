import json
import glob
import os
import numpy as np
from PIL import Image

ROOT = "data"
CITIES = sorted(os.listdir(f"{ROOT}/gtFine/train"))[:5]

n_img = n_sign = n_ok = 0
sizes, dists, fills = [], [], []

for city in CITIES:
    for pf in sorted(glob.glob(f"{ROOT}/gtFine/train/{city}/*_polygons.json")):
        stem = os.path.basename(pf).replace("_gtFine_polygons.json", "")
        cf = f"{ROOT}/camera/train/{city}/{stem}_camera.json"
        df = f"{ROOT}/disparity/train/{city}/{stem}_disparity.png"
        if not (os.path.exists(cf) and os.path.exists(df)):
            continue
        n_img += 1
        cam = json.load(open(cf))
        fx, b = cam["intrinsic"]["fx"], cam["extrinsic"]["baseline"]
        objs = [o for o in json.load(
            open(pf))["objects"] if o["label"] == "traffic sign"]
        if not objs:
            continue
        disp = np.array(Image.open(df)).astype(float)
        for o in objs:
            n_sign += 1
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
            fills.append(len(valid) / patch.size)
            if len(valid) < 0.2 * patch.size:
                continue
            d = (np.median(valid) - 1) / 256
            if d <= 0:
                continue
            Z = b * fx / d
            if 2 < Z < 120:
                n_ok += 1
                sizes.append(min(w, h))
                dists.append(Z)

sizes, dists, fills = map(np.array, (sizes, dists, fills))
print(
    f"images={n_img}  signs={n_sign}  usable={n_ok}  ({100*n_ok/max(n_sign, 1):.0f}%)")
print(f"disparity fill inside boxes: median={np.median(fills):.2f}")
print(f"sign short side px: p10={np.percentile(sizes, 10):.0f} "
      f"median={np.median(sizes):.0f} p90={np.percentile(sizes, 90):.0f}")
print(f"distance m: p10={np.percentile(dists, 10):.0f} "
      f"median={np.median(dists):.0f} p90={np.percentile(dists, 90):.0f}")
