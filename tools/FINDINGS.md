# Stage 0 — Feasibility (Cityscapes, 5 cities, train split)

## Can stereo disparity provide ground-truth distance for traffic signs?

Yes. 825 images, 5512 sign polygons, 4863 usable (88%).
Median disparity fill inside sign boxes: 1.00.

Sign short side: p10=10 px, median=22 px, p90=61 px
Distance:        p10=19 m,  median=48 m,  p90=97 m

## Is median disparity inside the box contaminated by background?

Tested median vs 90th-percentile disparity (nearer surface) per box.
Gap is 2-4% and shrinks with box size — inconsistent with background
bleed, consistent with plate tilt and annotation margin. Median retained.

| short side (px) | n    | med vs p90 gap | median Z (m) |
|-----------------|------|----------------|--------------|
| 0-15            | 1296 | 3.9%           | 72.9         |
| 15-30           | 1951 | 3.7%           | 54.3         |
| 30-60           | 1108 | 2.7%           | 32.2         |
| 60+             | 508  | 2.0%           | 19.5         |

## Consequence for validation

Box size and range are coupled, so error can be reported against range
directly. Validation is dominated by the 15-30 px / ~50 m regime, where
dZ/Z = dh/h implies ~7% distance error per 1 px of box-height error
before any size-class ambiguity. Results must be stratified, never
reported as a single MAE.

## Stage 1 — Is physical sign height recoverable?

Inverted Z = fy*H/h on 991 near-square signs with h >= 30 px.

Peak at 600-700 mm (n=261), matching VzKat Größe 2 (600 mm round /
630 mm triangular). Secondary bump at 400-500 mm consistent with
Größe 1 (420 mm). Tail above 1500 mm (n=42) is likely multi-plate
sign assemblies annotated as single polygons.

Median implied height 651 mm; IQR 574-842 mm.

Prior adopted: H = 650 mm.
Implied irreducible bias from unknown size class: -12% / +30%.
This bound is independent of detector quality and cannot be reduced
without classifying sign type.