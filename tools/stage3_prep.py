import json
import glob
import os
import shutil
import numpy as np

ROOT, OUT = "data", "data/yolo"
MIN_PX = 8   # below this the box is unlearnable and pollutes training

# Cityscapes val (frankfurt, lindau, munster) is reserved for pipeline
# evaluation and must never influence detector training or checkpoint
# selection. The detector's own validation set is carved out of train.
ALL_TRAIN = sorted(os.listdir(f"{ROOT}/gtFine/train"))
DET_TRAIN = ALL_TRAIN[:-3]                     # 15 cities, detector training
DET_VAL = ALL_TRAIN[-3:]                       # 3 cities, checkpoint selection
PIPE_TEST = sorted(os.listdir(f"{ROOT}/gtFine/val"))   # held out entirely


def build(name, src_split, cities):
    im_dir = f"{OUT}/images/{name}"
    lb_dir = f"{OUT}/labels/{name}"
    for d in (im_dir, lb_dir):
        if os.path.exists(d):
            shutil.rmtree(d)
        os.makedirs(d)
    n_img = n_box = n_drop = 0
    for city in cities:
        for pf in sorted(glob.glob(f"{ROOT}/gtFine/{src_split}/{city}/*_polygons.json")):
            stem = os.path.basename(pf).replace("_gtFine_polygons.json", "")
            src = f"{ROOT}/leftImg8bit/{src_split}/{city}/{stem}_leftImg8bit.png"
            if not os.path.exists(src):
                continue
            meta = json.load(open(pf))
            W, H = meta["imgWidth"], meta["imgHeight"]
            lines = []
            for o in meta["objects"]:
                if o["label"] != "traffic sign":
                    continue
                p = np.array(o["polygon"], dtype=float)
                x0, y0 = p.min(0)
                x1, y1 = p.max(0)
                x0, y0 = max(x0, 0), max(y0, 0)
                x1, y1 = min(x1, W), min(y1, H)
                w, h = x1 - x0, y1 - y0
                if w < MIN_PX or h < MIN_PX:
                    n_drop += 1
                    continue
                lines.append(
                    f"0 {(x0+x1)/2/W:.6f} {(y0+y1)/2/H:.6f} {w/W:.6f} {h/H:.6f}")
            if not lines:
                continue
            shutil.copy(src, f"{im_dir}/{stem}.png")
            open(f"{lb_dir}/{stem}.txt", "w").write("\n".join(lines))
            n_img += 1
            n_box += len(lines)
    print(f"{name:<6} ({src_split}, {len(cities)} cities): "
          f"{n_img} images, {n_box} boxes, {n_drop} dropped (<{MIN_PX}px)")


build("train", "train", DET_TRAIN)
build("val",   "train", DET_VAL)
build("test",  "val",   PIPE_TEST)

# data.yaml deliberately omits `test`. The pipeline evaluation loads it
# directly, so no training run can select a checkpoint on it.
open(f"{OUT}/data.yaml", "w").write(
    f"path: {os.path.abspath(OUT)}\ntrain: images/train\nval: images/val\n"
    "nc: 1\nnames: [traffic_sign]\n")

print(f"\ndetector val cities: {DET_VAL}")
print(f"pipeline test cities (never seen by detector): {PIPE_TEST}")
