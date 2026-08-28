import glob
import json
import os
import sys
import numpy as np
from ultralytics import YOLO

ROOT = "data"
SPLIT = "train"                       # det-val cities live in the train split
DET_VAL = ["ulm", "weimar", "zurich"]
WEIGHTS = sys.argv[1] if len(sys.argv) > 1 else \
    "runs/detect/runs/cs_1280_clean-2/weights/best.pt"
THRESHOLDS = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.50, 0.60]
IOU_MATCH = 0.5
MIN_GT_PX = 8                         # same floor used when building labels

model = YOLO(WEIGHTS)


def iou_matrix(gt, pr):
    """(n_gt, n_pred) IoU matrix"""
    if len(gt) == 0 or len(pr) == 0:
        return np.zeros((len(gt), len(pr)))
    g = np.asarray(gt, dtype=float)[:, None, :]
    p = np.asarray(pr, dtype=float)[None, :, :]
    ix0 = np.maximum(g[..., 0], p[..., 0])
    iy0 = np.maximum(g[..., 1], p[..., 1])
    ix1 = np.minimum(g[..., 2], p[..., 2])
    iy1 = np.minimum(g[..., 3], p[..., 3])
    iw = np.clip(ix1 - ix0, 0, None)
    ih = np.clip(iy1 - iy0, 0, None)
    inter = iw * ih
    ag = (g[..., 2] - g[..., 0]) * (g[..., 3] - g[..., 1])
    ap = (p[..., 2] - p[..., 0]) * (p[..., 3] - p[..., 1])
    return inter / np.clip(ag + ap - inter, 1e-9, None)


# ---- one inference pass at the lowest threshold, reused for all others ----
LOW = min(THRESHOLDS)
frames = []          # (gt boxes, pred boxes, pred confidences)
n_img = 0

for city in DET_VAL:
    for pf in sorted(glob.glob(f"{ROOT}/gtFine/{SPLIT}/{city}/*_polygons.json")):
        stem = os.path.basename(pf).replace("_gtFine_polygons.json", "")
        imf = f"{ROOT}/leftImg8bit/{SPLIT}/{city}/{stem}_leftImg8bit.png"
        if not os.path.exists(imf):
            continue
        meta = json.load(open(pf))
        W, H = meta["imgWidth"], meta["imgHeight"]

        gt = []
        for o in meta["objects"]:
            if o["label"] != "traffic sign":
                continue
            p = np.array(o["polygon"], dtype=float)
            x0, y0 = np.clip(p.min(0), [0, 0], [W, H])
            x1, y1 = np.clip(p.max(0), [0, 0], [W, H])
            if x1 - x0 >= MIN_GT_PX and y1 - y0 >= MIN_GT_PX:
                gt.append((x0, y0, x1, y1))

        # note: no `if not gt: continue`. Sign-free images are evaluated too.
        res = model.predict(imf, imgsz=1280, conf=LOW, verbose=False)[0]
        if len(res.boxes):
            pr = res.boxes.xyxy.cpu().numpy()
            cf = res.boxes.conf.cpu().numpy()
        else:
            pr, cf = np.zeros((0, 4)), np.zeros(0)
        frames.append((np.array(gt).reshape(-1, 4), pr, cf))
        n_img += 1

n_gt_total = sum(len(g) for g, _, _ in frames)
n_empty = sum(1 for g, _, _ in frames if len(g) == 0)
print(f"weights={os.path.basename(WEIGHTS)}")
print(f"det-val cities={DET_VAL}")
print(f"images={n_img} ({n_empty} with no annotated sign)  "
      f"gt signs={n_gt_total}\n")


def evaluate(conf):
    """one-to-one, confidence-ordered matching across all frames"""
    tp = fp = 0
    matched_gt = 0
    for gt, pr, cf in frames:
        keep = cf >= conf
        p, c = pr[keep], cf[keep]
        if len(p) == 0:
            continue
        order = np.argsort(-c)
        p = p[order]
        if len(gt) == 0:
            fp += len(p)
            continue
        M = iou_matrix(gt, p)
        claimed = np.zeros(len(gt), dtype=bool)
        for j in range(len(p)):
            col = M[:, j].copy()
            col[claimed] = 0.0
            i = int(np.argmax(col))
            if col[i] >= IOU_MATCH:
                claimed[i] = True
                tp += 1
            else:
                fp += 1
        matched_gt += int(claimed.sum())
    rec = matched_gt / max(n_gt_total, 1)
    prec = tp / max(tp + fp, 1)
    f1 = 2 * prec * rec / max(prec + rec, 1e-9)
    return prec, rec, f1, tp, fp


hdr = (f"{'conf':>6}{'precision':>11}{'recall':>9}{'F1':>8}"
       f"{'TP':>7}{'FP':>7}{'FP/img':>9}")
print(hdr)
print("-" * len(hdr))
rows = []
for t in THRESHOLDS:
    prec, rec, f1, tp, fp = evaluate(t)
    rows.append((t, prec, rec, f1, tp, fp))
    print(f"{t:>6.2f}{prec:>11.3f}{rec:>9.3f}{f1:>8.3f}"
          f"{tp:>7}{fp:>7}{fp/max(n_img, 1):>9.2f}")

best = max(rows, key=lambda r: r[3])
print(f"\nbest F1 at conf={best[0]:.2f} "
      f"(precision {best[1]:.3f}, recall {best[2]:.3f}, F1 {best[3]:.3f})")

print("\nmarginal cost per recovered sign, moving down the threshold list:")
for a, b in zip(rows, rows[1:]):
    d_tp, d_fp = b[4] - a[4], b[5] - a[5]
    if d_tp > 0:
        print(f"  {a[0]:.2f} -> {b[0]:.2f}: +{d_tp} TP, +{d_fp} FP "
              f"({d_fp/d_tp:.1f} FP per sign)")

os.makedirs("results", exist_ok=True)
np.savetxt("results/conf_sweep_detval.csv",
           np.array([[r[0], r[1], r[2], r[3], r[4], r[5]] for r in rows]),
           delimiter=",", header="conf,precision,recall,f1,tp,fp",
           comments="")
print("\nwrote results/conf_sweep_detval.csv")
