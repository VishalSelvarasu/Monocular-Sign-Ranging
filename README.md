# Monocular Sign Ranging

Monocular Sign Ranging estimates traffic-sign distance from a single camera image using projective geometry, and measures what a detector costs when it replaces ground-truth boxes.

> [!IMPORTANT]
> Every number below is measured on the Cityscapes **val** split (frankfurt, lindau, munster). The size prior was fitted on train cities, and the detector was trained on train cities with three further train cities held out for checkpoint selection. No fitted quantity has seen the evaluation images.

## End-to-end result

Detector boxes feed the ranging equation. Confidence threshold 0.25, match threshold IoU 0.5.

| GT box height | Signs | Recall | Median true distance | Bias | p25 | p75 | \|error\| detected | \|error\| all |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 15–30 px | 730 | 73.8% | 63.9 m | +3.1% | -12% | +37% | 22.2% | 35.2% |
| 30–60 px | 527 | 91.3% | 36.0 m | +1.8% | -19% | +40% | 25.0% | 29.7% |
| 60+ px | 223 | 94.2% | 18.4 m | -11.7% | -28% | +8% | 22.5% | 23.8% |

*\|error\| detected* covers signs the detector found. *\|error\| all* covers every annotated sign, scoring a miss as infinite error, so it goes undefined once recall drops below 50%.

**The system is a ±24% ranging instrument over 18–64 m with 74% coverage and precision between 0.73 and 0.83.**

Detection contributes almost nothing to ranging error on signs it finds. Its cost is coverage, which falls from 94% at 18 m to 35% beyond 100 m.

## Reference measurement

Stereo disparity is the ground truth, so it needs its own check. Median disparity inside a sign box could be contaminated by background pixels, particularly on thin plates against sky.

Comparing median against 90th-percentile disparity (the nearer surface) per box gives a gap of 2-4% that shrinks as boxes grow: 3.9% below 15 px, 2.0% above 60 px. Background bleed would do the opposite, hitting small boxes hardest and erratically. The observed pattern fits plate tilt and annotation margin instead, so median disparity is retained.

Across five train cities, 4,863 of 5,512 annotated signs (88%) yield a usable reference distance.

## What the detector actually costs

Ranging with ground-truth boxes on the same images, no detector involved:

| GT box height | Signs | Median true distance | Bias | p25 | p75 | Median \|error\| |
|---|---:|---:|---:|---:|---:|---:|
| 15–30 px | 730 | 63.9 m | +9.0% | -12% | +43% | 23.7% |
| 30–60 px | 527 | 36.0 m | +3.1% | -20% | +38% | 24.7% |
| 60+ px | 223 | 18.4 m | -13.3% | -28% | +11% | 23.5% |

Detector boxes give 22.2–25.0% against this 23.5–24.7%. The difference is inside the noise, and bias tracks closely.

This contradicts the obvious prediction. Distance is inversely proportional to measured box height:

$$
\frac{\Delta Z}{Z} \approx -\frac{\Delta h}{h}
$$

A box 2 px short at 30 px height should produce a 7% distance error, so detector boxes ought to degrade the estimate. They do not, because YOLO localizes to a pixel or two while the fixed 650 mm size prior is wrong by ±25%. The larger error term swamps the smaller one.

The real cost is the 26% of signs that produce no estimate at all. Reporting only *\|error\| detected* would hide this: misses concentrate in small boxes, which are exactly the far-range signs where geometry is already weakest.

## Method

The original concept combined a GTSDB detector, Depth Anything V2, and `near`/`mid`/`far` outputs. I rejected per-image relative depth because independent normalization prevents stable metric comparison across frames. I replaced it with:

$$
Z = \frac{f_y H_{\text{real}}}{h_{\text{px}}}
$$

GTSDB lacks the calibration and metric reference data needed for validation. Cityscapes supplies camera intrinsics, stereo disparity, and traffic-sign polygons, so stereo depth serves as the reference distance.

Geometry was validated with ground-truth boxes before a detector was introduced, so that the two error sources stay separable.

## Sign-size prior

Inverting the equation for 991 near-square train signs at least 30 px high gives a median inferred height of 651 mm, IQR 574–842 mm. The peak at 600–700 mm matches VzKat Größe 2. The model uses $H_{\text{real}} = 0.650\text{ m}$.

Re-deriving on val gives 641 mm, so the prior transfers. Val still produces a wider spread because its distribution is more bimodal: 17.7% of clean val signs fall in the 400–500 mm bin against 13.1% on train.

Sign-size variation creates a bias floor of roughly $-12\%$ to $+30\%$ even with a perfectly measured box. Every result here sits on top of that floor. Classifying sign shape or size class before selecting the prior is the single change that would move the number.

## Detector

Single-class YOLO11s, `imgsz=1280`, trained on 15 Cityscapes cities (2,465 images, 17,869 boxes). Three further train cities are held out for checkpoint selection; Cityscapes val is never seen during training.

Native resolution is 2048×1024 and the median sign is 22 px. At the usual `imgsz=640` that sign becomes 7 px, smaller than one stride-8 output cell, and is unlearnable. `imgsz=1280` puts it at 13.8 px.

Detector metrics on its own validation cities: precision 0.769, recall 0.676, mAP@50 0.767, mAP@50-95 0.485.

## Operating point

Confidence threshold was chosen by measuring what each recovered sign costs in false positives.

| Threshold | Coverage | Predictions | False positives | Precision |
|---|---:|---:|---:|---:|
| 0.40 | 64.9% | 2,703 | 470 | 0.826 |
| 0.25 | 74.1% | 3,864 | 1,045 | 0.730 |
| 0.10 | 81.1% | 6,221 | 2,739 | 0.560 |

Lowering 0.40 to 0.25 buys 167 signs for 575 false positives, or 3.4 per sign. Lowering 0.25 to 0.10 buys 126 signs for 1,694 false positives, or 13.4 per sign. The cost quadruples below 0.25, so that is the operating point.

False positives cannot be discarded by range gating. Their box heights match the real-sign distribution closely (p50 25 px against 22 px), implying phantom signs at around 59 m, inside the validated envelope.

Precision is bounded rather than exact. Relaxing the match threshold from IoU 0.5 to 0.1 reduces false positives from 1,045 to 662, so 37% of them do overlap a real sign. The likely cause is multi-plate assemblies annotated as one polygon, where correctly detecting each plate scores below threshold against the merged box. The remaining 662 predictions touch no annotated sign at all and have not been inspected.

## Excluded samples

Signs below 15 px box height are excluded from the error columns. There the predicted range exceeds 100 m and stereo disparity falls below 5 px, so the reference carries more uncertainty than the estimate under test. Recall for that bin is still reported, since coverage remains meaningful where error is not.

## Validation errors found and fixed

**Two truth-side filters.** `Z_true < 120 m` and `disparity ≥ 6 px` both produced large positive bias in the smallest bin (+44.6% and +102.6%). Each selects on the reference side only: for a fixed observed sign height, dropping samples with large true distance leaves a group the model appears to overestimate. Any filter must be independent of both sides or applied symmetrically.

**A prior fitted to its own test set.** Early numbers were reported on the same train cities the 650 mm prior was derived from, which forced near-zero bias in the middle bins. Moving to val raised median absolute error from 21% to 24%.

**A detector checkpoint selected on the evaluation set.** The first data preparation pointed YOLO's validation split at Cityscapes val, so `best.pt` was chosen by performance on the pipeline test images. Rebuilt as a three-way split. The corrected run scored 0.767 mAP@50 against the leaked run's 0.750, so the leak had no measurable effect, but the result was not defensible as reported.

## Planned work

A GTSDB-trained detector evaluated on the same val images would measure the cost of the camera domain gap directly, as the difference against the Cityscapes-trained detector reported here.

Beyond that: sign-type classification to replace the fixed size prior, INT8 quantization, latency and memory on target hardware, and temporal stability across video frames.

## Reproduce

Download `gtFine_trainvaltest`, `camera_trainvaltest`, `disparity_trainvaltest`, and `leftImg8bit_trainvaltest` from cityscapes-dataset.com into `data/`. Dataset used under the Cityscapes non-commercial licence; not redistributed.

Stages 0 to 2 take the split as first argument and an optional city count as second.

```bash
# feasibility and prior derivation, five train cities
python tools/stage0_check.py train 5
python tools/stage0_bleed_check.py train 5
python tools/stage1_size_prior.py train 5

# geometry-only error, held-out val split
python tools/stage2_error_curve.py val

# detector data preparation and training
python tools/stage3_prep.py
yolo detect train model=yolo11s.pt data=data/yolo/data.yaml \
    imgsz=1280 epochs=100 batch=4 patience=20

# end-to-end evaluation, argument 2 is the confidence threshold
python tools/stage4_pipeline_eval.py path/to/best.pt 0.25
```