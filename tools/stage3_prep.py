import json
import glob
import os
import shutil
import numpy as np
from PIL import Image

ROOT, OUT = "data", "data/yolo"
MIN_PX = 8   # below this the box is unlearnable and pollutes training


def build(split):
    im_dir = f"{OUT}/images/{split}"
    lb_dir = f"{OUT}/labels/{split}"
    os.makedirs(im_dir, exist_ok=True)
    os.makedirs(lb_dir, exist_ok=True)
    n_img = n_box = n_drop = 0
    for city in sorted(os.listdir(f"{ROOT}/gtFine/{split}")):
        for pf in sorted(glob.glob(f"{ROOT}/gtFine/{split}/{city}/*_polygons.json")):
            stem = os.path.basename(pf).replace("_gtFine_polygons.json", "")
            src = f"{ROOT}/leftImg8bit/{split}/{city}/{stem}_leftImg8bit.png"
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
    print(f"{split}: {n_img} images, {n_box} boxes, {n_drop} dropped (<{MIN_PX}px)")


build("train")
build("val")

open(f"{OUT}/data.yaml", "w").write(
    f"path: {os.path.abspath(OUT)}\ntrain: images/train\nval: images/val\n"
    "nc: 1\nnames: [traffic_sign]\n")
