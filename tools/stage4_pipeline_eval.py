import glob
import json
import os
import sys
import numpy as np
from PIL import Image
from ultralytics import YOLO

ROOT, H_PRIOR = "data", 0.650
SPLIT = "val"                         # cityscapes val = held-out test set
WEIGHTS = sys.argv[1] if len(sys.argv) > 1 else \
    "runs/detect/runs/cs_1280_clean-2/weights/best.pt"
CONF = float(sys.argv[2]) if len(sys.argv) > 2 else 0.30
IOU_MATCH = 0.5
MIN_GT_PX = 8
MIN_EVAL_PX = 15                      # headline population floor
BOOT = 2000
rng = np.random.default_rng(0)

H_BINS = [(0, 15), (15, 30), (30, 60), (60, 10_000)]
Z_BINS = [(15, 25), (25, 35), (35, 50), (50, 70), (70, 100), (100, 150)]

model = YOLO(WEIGHTS)
CITIES = sorted(os.listdir(f"{ROOT}/gtFine/{SPLIT}"))


def iou_matrix(gt, pr):
    if len(gt) == 0 or len(pr) == 0:
        return np.zeros((len(gt), len(pr)))
    g = np.asarray(gt, dtype=float)[:, None, :]
    p = np.asarray(pr, dtype=float)[None, :, :]
    iw = np.clip(np.minimum(g[..., 2], p[..., 2]) -
                 np.maximum(g[..., 0], p[..., 0]), 0, None)
    ih = np.clip(np.minimum(g[..., 3], p[..., 3]) -
                 np.maximum(g[..., 1], p[..., 1]), 0, None)
    inter = iw * ih
    ag = (g[..., 2] - g[..., 0]) * (g[..., 3] - g[..., 1])
    ap = (p[..., 2] - p[..., 0]) * (p[..., 3] - p[..., 1])
    return inter / np.clip(ag + ap - inter, 1e-9, None)


rows = []          # (gt_h, Z_true, Z_pred_det, Z_pred_gt)
n_img = n_empty = 0
tp = fp = 0
n_gt_det = 0
fp_best_iou = []

for city in CITIES:
    for pf in sorted(glob.glob(f"{ROOT}/gtFine/{SPLIT}/{city}/*_polygons.json")):
        stem = os.path.basename(pf).replace("_gtFine_polygons.json", "")
        imf = f"{ROOT}/leftImg8bit/{SPLIT}/{city}/{stem}_leftImg8bit.png"
        cf_ = f"{ROOT}/camera/{SPLIT}/{city}/{stem}_camera.json"
        df = f"{ROOT}/disparity/{SPLIT}/{city}/{stem}_disparity.png"
        if not all(os.path.exists(x) for x in (imf, cf_, df)):
            continue

        meta = json.load(open(pf))
        W, H = meta["imgWidth"], meta["imgHeight"]
        objs = [o for o in meta["objects"] if o["label"] == "traffic sign"]

        gt_boxes = []
        seen = set()
        for o in objs:
            p = np.array(o["polygon"], dtype=float)
            x0, y0 = np.floor(p.min(0)).astype(int)
            x1, y1 = np.ceil(p.max(0)).astype(int)
            x0, y0 = max(x0, 0), max(y0, 0)
            x1, y1 = min(x1, W), min(y1, H)
            if x1 - x0 < MIN_GT_PX or y1 - y0 < MIN_GT_PX:
                continue
            key = (x0, y0, x1, y1)
            if key in seen:
                continue
            seen.add(key)
            gt_boxes.append((x0, y0, x1, y1))

        res = model.predict(imf, imgsz=1280, conf=CONF, verbose=False)[0]
        if len(res.boxes):
            cs = res.boxes.conf.cpu().numpy()
            pr = res.boxes.xyxy.cpu().numpy()[np.argsort(-cs)]
        else:
            pr = np.zeros((0, 4))
        n_img += 1
        if not gt_boxes:
            n_empty += 1
        n_gt_det += len(gt_boxes)

        G = np.array(gt_boxes).reshape(-1, 4)
        M = iou_matrix(G, pr)
        claimed = np.full(len(G), -1, dtype=int)
        for j in range(len(pr)):
            col = M[:, j].copy() if len(G) else np.zeros(0)
            if len(col):
                col[claimed >= 0] = 0.0
            i = int(np.argmax(col)) if len(col) else -1
            if len(col) and col[i] >= IOU_MATCH:
                claimed[i] = j
                tp += 1
            else:
                fp += 1
                fp_best_iou.append(float(col[i]) if len(col) else 0.0)

        if not gt_boxes:
            continue

        cam = json.load(open(cf_))
        fx, fy = cam["intrinsic"]["fx"], cam["intrinsic"]["fy"]
        b = cam["extrinsic"]["baseline"]
        disp = np.array(Image.open(df)).astype(float)

        for i, (x0, y0, x1, y1) in enumerate(gt_boxes):
            w, h = x1 - x0, y1 - y0
            if abs(w / h - 1) > 0.25:
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
            j = claimed[i]
            if j >= 0:
                ph = pr[j][3] - pr[j][1]
                Z_det = fy * H_PRIOR / ph if ph > 0 else np.nan
            else:
                Z_det = np.nan
            rows.append((h, Z_true, Z_det, fy * H_PRIOR / h))

r = np.array(rows)
h_px, Zt, Zd, Zg = r[:, 0], r[:, 1], r[:, 2], r[:, 3]
found = np.isfinite(Zd)
H_imp = 1000.0 * H_PRIOR * Zt / Zg     # exact, avoids hardcoding fy

prec = tp / max(tp + fp, 1)
rec = tp / max(n_gt_det, 1)
print(f"\nweights={os.path.basename(WEIGHTS)}  conf={CONF}  "
      f"match IoU={IOU_MATCH}")
print(f"images={n_img} ({n_empty} with no annotated sign)")
print(f"detection, all annotated signs: TP={tp} FP={fp} "
      f"precision={prec:.3f} recall={rec:.3f} "
      f"F1={2*prec*rec/max(prec+rec, 1e-9):.3f}")
print(f"ranging population (near-square, valid disparity): n={len(r)}  "
      f"detected={found.sum()} ({100*found.mean():.1f}%)")

if fp_best_iou:
    fb = np.array(fp_best_iou)
    print("\nfalse positives vs match threshold "
          "(same predictions, relaxed criterion):")
    for t in (0.5, 0.4, 0.3, 0.2, 0.1):
        n_fp_t = int((fb < t).sum())
        print(f"  IoU>={t:.1f}  FP={n_fp_t:<5} "
              f"precision={tp/max(tp+n_fp_t, 1):.3f}")


def boot_ci(x, stat, n=BOOT):
    idx = rng.integers(0, len(x), size=(n, len(x)))
    return np.percentile([stat(x[i]) for i in idx], [2.5, 97.5])


rel = np.full(len(r), np.inf)
rel[found] = (Zd[found] - Zt[found]) / Zt[found]


def table(bins, key, label):
    hdr = (f"{label:<12}{'n':>6}{'coverage':>10}{'med H_imp':>11}"
           f"{'bias':>9}{'p25':>8}{'p75':>8}{'MdARE det':>11}"
           f"{'95% CI':>18}{'MdARE all':>11}")
    print(hdr)
    print("-" * len(hdr))
    for lo, hi in bins:
        m = (key >= lo) & (key < hi)
        if m.sum() < 10:
            continue
        md = m & found
        big = hi >= 9999
        lbl = f"{lo}-{'+' if big else hi}"
        a = np.median(np.abs(rel[m]))
        a_s = "undefined" if not np.isfinite(a) else f"{100*a:.1f}%"
        if md.sum() < 10:
            print(f"{lbl:<12}{m.sum():>6}{100*md.sum()/m.sum():>9.1f}%"
                  f"{np.median(H_imp[m]):>9.0f}mm{'':>9}{'':>8}{'':>8}"
                  f"{'n/a':>11}{'':>18}{a_s:>11}")
            continue
        e = rel[md]
        lo_ci, hi_ci = boot_ci(e, lambda x: 100 * np.median(np.abs(x)))
        print(f"{lbl:<12}{m.sum():>6}{100*md.sum()/m.sum():>9.1f}%"
              f"{np.median(H_imp[m]):>9.0f}mm"
              f"{100*np.median(e):>8.1f}%"
              f"{100*np.percentile(e, 25):>7.0f}%"
              f"{100*np.percentile(e, 75):>7.0f}%"
              f"{100*np.median(np.abs(e)):>10.1f}%"
              f"{f'[{lo_ci:.1f}, {hi_ci:.1f}]':>18}{a_s:>11}")
    print()


print("\nstratified by stereo reference range (primary):")
table(Z_BINS, Zt, "range (m)")

print("stratified by box height (secondary, conditions on the error "
      "source):")
table(H_BINS, h_px, "box h (px)")

m = h_px >= MIN_EVAL_PX
md = m & found
e = rel[md]
lo_ci, hi_ci = boot_ci(e, lambda x: 100 * np.median(np.abs(x)))
print(f"headline population, gt box height >= {MIN_EVAL_PX} px:")
print(f"  signs={m.sum()}  coverage={100*md.sum()/m.sum():.1f}%")
print(f"  MdARE on detected={100*np.median(np.abs(e)):.1f}% "
      f"[95% CI {lo_ci:.1f}, {hi_ci:.1f}]")
print(f"  signed bias={100*np.median(e):+.1f}%  "
      f"IQR=[{100*np.percentile(e, 25):.0f}%, "
      f"{100*np.percentile(e, 75):.0f}%]")
print(f"  range={np.percentile(Zt[m], 5):.0f}-"
      f"{np.percentile(Zt[m], 95):.0f} m")

# detector box height error, on the headline population
dh = 100 * (Zg[md] / Zd[md] - 1)
print(f"\ndetector box height vs annotation, on detected signs >= "
      f"{MIN_EVAL_PX} px:")
print(f"  median {np.median(dh):+.2f}%   |median| "
      f"{np.median(np.abs(dh)):.2f}%   "
      f"IQR [{np.percentile(dh, 25):+.1f}, {np.percentile(dh, 75):+.1f}]")

os.makedirs("results", exist_ok=True)
np.savetxt(f"results/pipeline_test_conf{CONF}.csv", r, delimiter=",",
           header="h_px,Z_true,Z_pred_det,Z_pred_gt", comments="")
print(f"\nwrote results/pipeline_test_conf{CONF}.csv")
