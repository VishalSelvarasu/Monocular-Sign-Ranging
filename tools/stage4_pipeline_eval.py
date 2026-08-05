import json
import glob
import os
import sys
import numpy as np
from PIL import Image
from ultralytics import YOLO

ROOT, H_PRIOR = "data", 0.650
SPLIT = "val"                       # cityscapes val = pipeline test set
WEIGHTS = sys.argv[1] if len(sys.argv) > 1 else \
    "runs/detect/runs/cs_1280_clean-2/weights/best.pt"
CONF = float(sys.argv[2]) if len(sys.argv) > 2 else 0.25
IOU_MATCH = 0.5

model = YOLO(WEIGHTS)
CITIES = sorted(os.listdir(f"{ROOT}/gtFine/{SPLIT}"))


def iou(a, b):
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    ix0, iy0 = max(ax0, bx0), max(ay0, by0)
    ix1, iy1 = min(ax1, bx1), min(ay1, by1)
    iw, ih = max(0.0, ix1 - ix0), max(0.0, iy1 - iy0)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    return inter / ((ax1-ax0)*(ay1-ay0) + (bx1-bx0)*(by1-by0) - inter)


rows = []            # (gt_h_px, Z_true, Z_pred or nan if missed)
n_img = 0
n_pred = n_fp = 0
fp_heights = []
fp_best_iou = []

for city in CITIES:
    for pf in sorted(glob.glob(f"{ROOT}/gtFine/{SPLIT}/{city}/*_polygons.json")):
        stem = os.path.basename(pf).replace("_gtFine_polygons.json", "")
        imf = f"{ROOT}/leftImg8bit/{SPLIT}/{city}/{stem}_leftImg8bit.png"
        cf = f"{ROOT}/camera/{SPLIT}/{city}/{stem}_camera.json"
        df = f"{ROOT}/disparity/{SPLIT}/{city}/{stem}_disparity.png"
        if not all(os.path.exists(p) for p in (imf, cf, df)):
            continue

        meta = json.load(open(pf))
        objs = [o for o in meta["objects"] if o["label"] == "traffic sign"]
        if not objs:
            continue

        cam = json.load(open(cf))
        fx, fy = cam["intrinsic"]["fx"], cam["intrinsic"]["fy"]
        b = cam["extrinsic"]["baseline"]
        disp = np.array(Image.open(df)).astype(float)

        res = model.predict(imf, imgsz=1280, conf=CONF, verbose=False)[0]
        preds = res.boxes.xyxy.cpu().numpy() if len(res.boxes) else np.zeros((0, 4))
        n_img += 1
        n_pred += len(preds)

        # every annotated sign, unfiltered, for false-positive scoring
        all_gt = []
        for o in objs:
            p = np.array(o["polygon"], dtype=float)
            gx0, gy0 = np.floor(p.min(0)).astype(int)
            gx1, gy1 = np.ceil(p.max(0)).astype(int)
            gx0, gy0 = max(gx0, 0), max(gy0, 0)
            gx1 = min(gx1, disp.shape[1])
            gy1 = min(gy1, disp.shape[0])
            if gx1 - gx0 >= 1 and gy1 - gy0 >= 1:
                all_gt.append((gx0, gy0, gx1, gy1))

        for pb in preds:
            best = max((iou(g, pb) for g in all_gt), default=0.0)
            fp_best_iou.append(best)
            if best < IOU_MATCH:
                n_fp += 1
                fp_heights.append(pb[3] - pb[1])

        seen = set()
        for o in objs:
            p = np.array(o["polygon"], dtype=float)
            x0, y0 = np.floor(p.min(0)).astype(int)
            x1, y1 = np.ceil(p.max(0)).astype(int)
            x0, y0 = max(x0, 0), max(y0, 0)
            x1 = min(x1, disp.shape[1])
            y1 = min(y1, disp.shape[0])
            w, h = x1 - x0, y1 - y0
            # same population as stage 2, so the numbers are comparable
            if w < 2 or h < 2 or abs(w / h - 1) > 0.25:
                continue
            key = (x0, y0, x1, y1)
            if key in seen:        # duplicate polygon, identical bbox
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

            best_i, best_iou = -1, 0.0
            for i, pb in enumerate(preds):
                v = iou((x0, y0, x1, y1), pb)
                if v > best_iou:
                    best_i, best_iou = i, v

            if best_iou >= IOU_MATCH:
                ph = preds[best_i][3] - preds[best_i][1]
                Z_pred = fy * H_PRIOR / ph if ph > 0 else np.nan
            else:
                Z_pred = np.nan          # miss

            rows.append((h, Z_true, Z_pred, fy * H_PRIOR / h))

r = np.array(rows)
h_px, Zt, Zp, Zp_prior = r[:, 0], r[:, 1], r[:, 2], r[:, 3]
found = ~np.isnan(Zp)

rel = np.full(len(r), np.inf)
rel[found] = (Zp[found] - Zt[found]) / Zt[found]

print(
    f"\nweights={os.path.basename(WEIGHTS)}  conf={CONF}  iou_match={IOU_MATCH}")
print(f"images={n_img}  ranging signs={len(r)}  detected={found.sum()} "
      f"({100*found.mean():.1f}%)")

prec = 1 - n_fp / max(n_pred, 1)
print(f"predictions={n_pred}  false positives={n_fp} "
      f"({n_fp/max(n_img, 1):.2f}/image)  precision={prec:.3f}")
if fp_heights:
    fh = np.array(fp_heights)
    print(f"false-positive box height px: p50={np.median(fh):.0f} "
          f"p90={np.percentile(fh, 90):.0f}  "
          f"implied range at 650 mm: p50={2262*H_PRIOR/np.median(fh):.0f} m")

fb = np.array(fp_best_iou)
print("precision vs match threshold:")
for t in (0.5, 0.4, 0.3, 0.2, 0.1):
    fp = int((fb < t).sum())
    print(f"  IoU>={t:.1f}  FP={fp:<5} precision={1-fp/max(n_pred, 1):.3f}")
print()

hdr = (f"{'gt h (px)':<12}{'n':>6}{'recall':>9}{'med Z_true':>12}"
       f"{'bias':>9}{'p25':>8}{'p75':>8}{'|err| det':>11}{'|err| all':>11}")
print(hdr)
print("-" * len(hdr))
for lo, hi in [(0, 15), (15, 30), (30, 60), (60, 10_000)]:
    m = (h_px >= lo) & (h_px < hi)
    if m.sum() < 10:
        continue
    md = m & found
    lbl = f"{lo}-{hi if hi < 9999 else '+'}"
    all_err = np.median(np.abs(rel[m]))
    all_s = "inf" if not np.isfinite(all_err) else f"{100*all_err:.1f}%"
    if md.sum() < 5:
        print(f"{lbl:<12}{m.sum():>6}{100*md.sum()/m.sum():>8.1f}%"
              f"{np.median(Zt[m]):>11.1f}m{'':>9}{'':>8}{'':>8}{'n/a':>11}{all_s:>11}")
        continue
    print(f"{lbl:<12}{m.sum():>6}{100*md.sum()/m.sum():>8.1f}%"
          f"{np.median(Zt[m]):>11.1f}m"
          f"{100*np.median(rel[md]):>8.1f}%"
          f"{100*np.percentile(rel[md], 25):>7.0f}%"
          f"{100*np.percentile(rel[md], 75):>7.0f}%"
          f"{100*np.median(np.abs(rel[md])):>10.1f}%"
          f"{all_s:>11}")

print("\n|err| det = over detected signs only")
print("|err| all = over every gt sign, misses = infinite error")
print("false positives matched against ALL sign polygons, not the "
      "near-square ranging subset")

os.makedirs("results", exist_ok=True)
np.savetxt(f"results/pipeline_val_conf{CONF}.csv", r, delimiter=",",
           header="h_px,Z_true,Z_pred_det,Z_pred_gt", comments="")
