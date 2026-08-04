# Findings

All stages use ground-truth Cityscapes sign polygons; no detector is
involved. The size prior is derived on five train cities. Headline error
numbers are measured on the val split (frankfurt, lindau, munster),
which is held out from every fitted quantity.

Note on cutoffs: Stages 0 and 1 discard samples with Z > 120 m, Stage 2
uses Z > 250 m. The Stage 1 prior is derived from signs at least 30 px
high, which implies Z below roughly 50 m, so the tighter cutoff never
binds there and the two are not in conflict.

## Stage 0 — Feasibility

### Can stereo disparity provide ground-truth distance for traffic signs?

Yes. 825 images, 5512 sign polygons, 4863 usable (88%).
Median disparity fill inside sign boxes: 1.00.

Sign short side: p10=10 px, median=22 px, p90=61 px
Distance:        p10=19 m,  median=48 m,  p90=97 m

### Is median disparity inside the box contaminated by background?

Tested median vs 90th-percentile disparity (nearer surface) per box.
Gap is 2-4% and shrinks with box size. That is inconsistent with
background bleed and consistent with plate tilt and annotation margin.
Median retained.

| short side (px) | n    | med vs p90 gap | median Z (m) |
|-----------------|------|----------------|--------------|
| 0-15            | 1296 | 3.9%           | 72.9         |
| 15-30           | 1951 | 3.7%           | 54.3         |
| 30-60           | 1108 | 2.7%           | 32.2         |
| 60+             | 508  | 2.0%           | 19.5         |

### Consequence for validation

Box size and range are coupled, so error can be reported against range
directly. Validation is dominated by the 15-30 px / ~50 m regime, where
dZ/Z = dh/h implies 3-7% distance error per 1 px of box-height error
before any size-class ambiguity. Results must be stratified, never
reported as a single aggregate error.

## Stage 1 — Is physical sign height recoverable?

Inverted Z = fy*H/h on 991 near-square train signs with h >= 30 px.

Peak at 600-700 mm (n=261), matching VzKat Groesse 2 (600 mm round /
630 mm triangular). Secondary bump at 400-500 mm consistent with
Groesse 1 (420 mm). Tail above 1500 mm (n=42) is likely multi-plate
sign assemblies annotated as single polygons.

Median implied height 651 mm; IQR 574-842 mm.

Prior adopted: H = 650 mm.
Implied irreducible bias from unknown size class: -12% / +30%.
This bound is independent of detector quality and cannot be reduced
without classifying sign type.

### Does the prior transfer to val?

Yes, in central tendency. Re-deriving on val (n=727 clean) gives a
median of 641 mm against 651 mm on train, a 1.5% difference.

The distributions differ in shape rather than centre. Val's 400-500 mm
bin holds 17.7% of clean signs against 13.1% on train, so val is more
strongly bimodal between Groesse 1 and Groesse 2. A fixed 650 mm prior
is therefore wrong more often on val in both directions, which widens
the error spread without moving the median.

| statistic | train (n=991) | val (n=727) |
|-----------|---------------|-------------|
| p10       | 424 mm        | 414 mm      |
| p25       | 574 mm        | 499 mm      |
| p50       | 651 mm        | 641 mm      |
| p75       | 842 mm        | 830 mm      |
| p90       | 1227 mm       | 1050 mm     |

The prior is not re-fitted on val. Doing so would fit the test set.

## Stage 2 — Geometric distance error

Z_pred = fy * 0.650 / h_px, evaluated against stereo depth on
near-square Cityscapes sign polygons. No detector involved;
ground-truth boxes only, to isolate the geometric estimator from
detection error.

### Val split (held out) — headline result

| box h (px) | n   | median Z_true | bias   | p25  | p75  | median \|error\| |
|------------|-----|---------------|--------|------|------|------------------|
| 15-30      | 730 | 63.9 m        | +9.0%  | -12% | +43% | 23.7%            |
| 30-60      | 527 | 36.0 m        | +3.1%  | -20% | +38% | 24.7%            |
| 60+        | 223 | 18.4 m        | -13.3% | -28% | +11% | 23.5%            |

### Train split (five cities, same data the prior was fitted on)

| box h (px) | n   | median Z_true | bias  | p25  | p75  | median \|error\| |
|------------|-----|---------------|-------|------|------|------------------|
| 15-30      | 975 | 68.5 m        | 0.0%  | -17% | +29% | 21.3%            |
| 30-60      | 688 | 38.4 m        | 0.1%  | -23% | +17% | 22.5%            |
| 60+        | 331 | 19.8 m        | -5.6% | -24% | +8%  | 19.1%            |

The train numbers are optimistic by construction: the prior is the median
of that same population, which forces near-zero bias in the middle bins.
Val is the number to quote.

Signs below 15 px box height are excluded from both tables. There the
predicted range exceeds 100 m, stereo disparity falls under ~5 px, and
the reference measurement carries larger uncertainty than the estimate
under test. Validated envelope: roughly 18-64 m.

### Result

Monocular sign ranging from a single size prior is a ±24% instrument
across 18-64 m on held-out data, with median bias within ±13%. Median
absolute error is flat (23.5-24.7%) over a 3.5x change in range, so
error is dominated by sign-size ambiguity rather than pixel
quantization. This is consistent with the -12%/+30% floor measured
independently in Stage 1.

The -13.3% bias in the nearest bin is consistent with close signs being
disproportionately Groesse 1 (420 mm), for which 650 mm overestimates
apparent size and therefore underestimates range. The val size
distribution supports this: its excess mass sits in the 400-500 mm bin,
and the nearest-bin bias is more negative on val (-13.3%) than on train
(-5.6%), matching the larger Groesse 1 fraction.

### Method note

Two filters were tried and rejected: Z_true < 120 and disparity >= 6 px.
Both select on one side of the comparison only (truth, not prediction),
producing one-sided bias in the smallest-box bin (+44.6% and +102.6%
respectively). Filters must be independent of both Z_true and Z_pred,
or applied symmetrically.
