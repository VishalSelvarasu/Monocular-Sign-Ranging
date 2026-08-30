import glob
import json
import os
import sys
import cv2
import numpy as np

PATTERN = (9, 6)
SQUARE_MM = 25.0

folder = sys.argv[1] if len(sys.argv) > 1 else "calib"
files = sorted(sum([glob.glob(os.path.join(folder, e))
                    for e in ("*.jpg", "*.jpeg", "*.png", "*.JPG")], []))
if not files:
    sys.exit(f"no images in {folder}/")

objp = np.zeros((PATTERN[0] * PATTERN[1], 3), np.float32)
objp[:, :2] = np.mgrid[0:PATTERN[0], 0:PATTERN[1]].T.reshape(-1, 2)
objp *= SQUARE_MM

crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
obj_pts, img_pts, used = [], [], []
shape = None

for f in files:
    img = cv2.imread(f)
    if img is None:
        continue
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    if shape is None:
        shape = gray.shape[::-1]
    elif gray.shape[::-1] != shape:
        print(f"  skip {os.path.basename(f)}: {gray.shape[::-1]} != {shape}")
        continue
    ok, corners = cv2.findChessboardCorners(
        gray, PATTERN,
        cv2.CALIB_CB_ADAPTIVE_THRESH + cv2.CALIB_CB_NORMALIZE_IMAGE)
    print(f"  {'found ' if ok else 'MISS  '} {os.path.basename(f)}")
    if not ok:
        continue
    corners = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), crit)
    obj_pts.append(objp)
    img_pts.append(corners)
    used.append(f)

print(f"\n{len(used)}/{len(files)} images usable, resolution {shape}")
if len(used) < 10:
    sys.exit("need at least ~10 usable views; check PATTERN matches the "
             "board's INNER corner count and that the board is fully "
             "visible and unclipped in each shot")

rms, K, dist, rvecs, tvecs = cv2.calibrateCamera(
    obj_pts, img_pts, shape, None, None)

# per-view reprojection error, so a bad shot can be found and removed
errs = []
for i in range(len(obj_pts)):
    proj, _ = cv2.projectPoints(obj_pts[i], rvecs[i], tvecs[i], K, dist)
    errs.append(cv2.norm(img_pts[i], proj, cv2.NORM_L2) / len(proj))
errs = np.array(errs)

fx, fy = K[0, 0], K[1, 1]
cx, cy = K[0, 2], K[1, 2]

print(f"\nRMS reprojection error: {rms:.3f} px")
print(f"per-view error: median {np.median(errs):.3f} px, "
      f"worst {errs.max():.3f} px ({os.path.basename(used[int(errs.argmax())])})")
print(f"\nfx = {fx:.1f} px")
print(f"fy = {fy:.1f} px      <- this is what the ranging equation needs")
print(f"cx, cy = {cx:.1f}, {cy:.1f}")
print(f"distortion = {np.round(dist.ravel(), 4).tolist()}")

print(f"\nsanity: a 600 mm sign at 30 m should span "
      f"{fy * 0.600 / 30:.1f} px in this camera")

if rms > 1.0:
    print("\nRMS above 1 px. Usually means a blurry or clipped view, or "
          "SQUARE_MM not matching the printed board. Drop the worst images "
          "and rerun.")

out = os.path.join(folder, "intrinsics.json")
json.dump({
    "resolution": list(shape),
    "fx": fx, "fy": fy, "cx": cx, "cy": cy,
    "dist_coeffs": dist.ravel().tolist(),
    "rms_reprojection_px": float(rms),
    "n_views": len(used),
    "pattern_inner_corners": list(PATTERN),
    "square_mm": SQUARE_MM,
}, open(out, "w"), indent=2)
print(f"\nwrote {out}")
