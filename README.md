# Monocular Sign Ranging

Estimating how far away a traffic sign is, from one camera image, using the fact that German traffic signs come in standard sizes.

> [!IMPORTANT]
> Every number here is measured on the Cityscapes **val** split (frankfurt, lindau, munster). The size prior was fitted on train cities, and the detector was trained on train cities with three further train cities held out for checkpoint selection. Nothing fitted has seen the evaluation images.

## End-to-end result

Detector boxes feed the ranging equation. Confidence threshold 0.25, match threshold IoU 0.5.

| GT box height | Signs | Recall | Median true distance | Bias | p25 | p75 | \|error\| detected | \|error\| all |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 15–30 px | 730 | 73.8% | 63.9 m | +3.1% | -12% | +37% | 22.2% | 35.2% |
| 30–60 px | 527 | 91.3% | 36.0 m | +1.8% | -19% | +40% | 25.0% | 29.7% |
| 60+ px | 223 | 94.2% | 18.4 m | -11.7% | -28% | +8% | 22.5% | 23.8% |

![Ranging error against range](figures/error_vs_range.png)

*\|error\| detected* covers signs the detector found. *\|error\| all* covers every annotated sign and scores a miss as infinite error, which is why it goes undefined once recall drops below 50%.

**The system is a ±24% ranging instrument over 18–64 m, with 74% coverage and precision somewhere between 0.73 and 0.83.**

Three numbers, not one. A single accuracy figure would hide the part that actually matters.

## Is the reference measurement trustworthy?

Stereo disparity is the ground truth here, so it needed checking before anything was built on it. The worry: a sign is a thin plate, often against sky, and the median disparity inside its box might be picking up background instead of the sign.

I compared median disparity against the 90th percentile (the nearer surface) for every box. The gap is 2–4%, and it *shrinks* as boxes get bigger: 3.9% below 15 px, 2.0% above 60 px. Background bleed would do the opposite, hitting small boxes hardest and erratically. What I'm seeing looks more like plate tilt and annotation margin, so median disparity stays.

Across five train cities, 4,863 of 5,512 annotated signs (88%) give a usable reference distance.

## What the detector actually costs

Same images, same equation, but with ground-truth boxes instead of detected ones:

| GT box height | Signs | Median true distance | Bias | p25 | p75 | Median \|error\| |
|---|---:|---:|---:|---:|---:|---:|
| 15–30 px | 730 | 63.9 m | +9.0% | -12% | +43% | 23.7% |
| 30–60 px | 527 | 36.0 m | +3.1% | -20% | +38% | 24.7% |
| 60+ px | 223 | 18.4 m | -13.3% | -28% | +11% | 23.5% |

23.5–24.7% with perfect boxes. 22.2–25.0% with detected boxes. The difference is inside the noise.

That surprised me, because the geometry says it shouldn't be. Distance is inversely proportional to measured box height:

$$
\frac{\Delta Z}{Z} \approx -\frac{\Delta h}{h}
$$

A box 2 px short at 30 px height is a 7% distance error, so detector boxes ought to make things visibly worse. They don't, and the reason is that YOLO localizes to a pixel or two while the fixed 650 mm size prior is wrong by ±25%. The bigger error term swamps the one the detector adds.

So detection doesn't degrade the estimates. It removes them.

![Coverage against range](figures/coverage_vs_range.png)

26% of signs get no estimate at all, and the misses pile up in small boxes, which are the far-away signs where the geometry was already weakest. Reporting only *\|error\| detected* would have hidden this completely and made the pipeline look better than it is.

## How I got here

The first plan was a GTSDB detector plus Depth Anything V2, with `near`/`mid`/`far` outputs. I dropped the relative-depth part because it normalizes per image: the same predicted value means different real distances in different frames, so a `near` in one frame can be further away than a `mid` in another. Useless for anything that has to be consistent across time.

What replaced it:

$$
Z = \frac{f_y H_{\text{real}}}{h_{\text{px}}}
$$

GTSDB turned out to have no camera intrinsics and no depth ground truth, so there was nothing to validate against. Cityscapes has intrinsics, stereo disparity, and traffic-sign polygons, so validation moved there.

I also built it backwards on purpose: geometry first with ground-truth boxes, detector last. If I'd trained the detector first and the distances came out wrong, I'd have had no way to tell whether it was bad boxes, a bad size assumption, or bad intrinsics.

## The size prior

Inverting the equation on 991 near-square train signs at least 30 px high gives a median implied height of 651 mm, IQR 574–842 mm.

![Implied sign height distribution](figures/size_prior.png)

The peak at 600–700 mm lands on VzKat Größe 2, which is a decent sanity check on the whole chain: if the disparity decode, baseline, or focal length were wrong, that peak would sit somewhere arbitrary. The model uses $H_{\text{real}} = 0.650\text{ m}$.

Re-deriving on val gives 641 mm, so the prior transfers. Val still comes out with a wider spread because its distribution is more bimodal: 17.7% of clean val signs sit in the 400–500 mm bin against 13.1% on train. Same centre, more signs the prior is wrong about.

This is the ceiling on the whole project. Sign-size variation alone puts a −12% / +30% floor under the error, before any pixel is measured. Classifying sign type and picking the matching prior is the one change that would move the number, and neither Cityscapes nor a single-class detector gives you the type.

## The detector

Single-class YOLO11s at `imgsz=1280`, trained on 15 Cityscapes cities (2,465 images, 17,869 boxes). Three more train cities are held out for checkpoint selection, and Cityscapes val is never touched during training.

Resolution is the whole game here. Cityscapes is 2048×1024 and the median sign is 22 px on its short side. At the usual `imgsz=640` that sign scales down to 7 px, which is smaller than one stride-8 output cell, so it simply cannot be learned. At 1280 it's 13.8 px. Anyone who runs the default on this dataset gets a bad mAP and blames the data.

On its own validation cities: precision 0.769, recall 0.676, mAP@50 0.767, mAP@50-95 0.485.

## Picking the confidence threshold

I didn't want to inherit 0.25 from the defaults, so I measured what each recovered sign costs in false positives.

| Threshold | Coverage | Predictions | False positives | Precision |
|---|---:|---:|---:|---:|
| 0.40 | 64.9% | 2,703 | 470 | 0.826 |
| 0.25 | 74.1% | 3,864 | 1,045 | 0.730 |
| 0.10 | 81.1% | 6,221 | 2,739 | 0.560 |

![Coverage against precision at three thresholds](figures/operating_point.png)

Going 0.40 → 0.25 buys 167 signs for 575 false positives: 3.4 per sign. Going 0.25 → 0.10 buys 126 signs for 1,694: 13.4 per sign. The price quadruples below 0.25, so that's where it stays. Same number as the default, but now for a reason.

The false positives can't be filtered out by range either. Their box heights track the real signs almost exactly (p50 25 px against a 22 px real median), so they show up as phantom signs at around 59 m, right in the middle of the useful range.

Precision is a range rather than a number because I can't fully separate real false positives from annotation artefacts. Relaxing the match threshold from IoU 0.5 to 0.1 drops false positives from 1,045 to 662, so 37% of them do overlap a real sign, probably multi-plate assemblies annotated as a single polygon where detecting each plate correctly still scores below threshold. The other 662 touch nothing annotated at all. I haven't looked at crops of those, so I don't know whether they're hallucinations, sign backs, or things Cityscapes just didn't label.

## What's excluded and why

Signs below 15 px box height don't get an error number. At that size the predicted range is past 100 m and stereo disparity is under 5 px, which means my reference is less certain than the thing I'm measuring. Recall for that bin is still reported, because coverage stays meaningful even where error doesn't.

## Three things I got wrong

**Filters that touched only one side.** I tried `Z_true < 120 m` and later `disparity ≥ 6 px`. Both produced huge positive bias in the smallest bin, +44.6% and +102.6%. Each one selects on the reference side only: for a fixed observed box height, dropping the samples with large true distance leaves behind a group the model looks like it's overestimating. A filter has to be independent of both sides, or applied to both.

**A prior fitted to its own test set.** The first error numbers came from the same train cities the 650 mm prior was derived from, which forces near-zero bias in the middle bins by construction. Moving to val took median absolute error from 21% to 24%. The 21% was never real.

**A detector checkpoint chosen on the evaluation set.** My first data prep pointed YOLO's validation split at Cityscapes val, so `best.pt` was selected by performance on the exact images the pipeline would later be scored on. Rebuilt as a three-way split. The corrected run scored 0.767 mAP@50 against the leaked run's 0.750, so it made no measurable difference, but the result wasn't defensible the way it was produced.

All three would have produced numbers that looked completely reasonable.

## Where this stands

The ranging pipeline works end to end and every number in it is measured on held-out data. As a piece of engineering it's finished enough to be honest about, and nowhere near finished as a system.

The largest remaining gap is the size prior. Everything here is capped at roughly ±24% by not knowing which size class a sign belongs to, and no amount of detector or geometry work moves that. Fixing it means a multi-class detector and a per-class prior, which Cityscapes can't supply because it labels every sign the same way. That's a GTSDB job, and GTSDB has no depth to validate against, so it needs both datasets stitched together.

Also missing: a GTSDB-trained detector run against these same val images, which would measure the camera domain gap as a straight difference against the number reported here. Then INT8 quantization, latency and memory on real target hardware, and temporal stability across video frames rather than single images. None of that is started.

## Reproduce

Download `gtFine_trainvaltest`, `camera_trainvaltest`, `disparity_trainvaltest`, and `leftImg8bit_trainvaltest` from cityscapes-dataset.com into `data/`. Used under the Cityscapes non-commercial licence and not redistributed here.

Stages 0 to 2 take the split as the first argument and an optional city count as the second.

```bash
# feasibility and prior derivation, five train cities
python tools/stage0_check.py train 5
python tools/stage0_bleed_check.py train 5
python tools/stage1_size_prior.py train 5

# geometry-only error, held-out val split
python tools/stage2_error_curve.py val

# detector data prep and training
python tools/stage3_prep.py
yolo detect train model=yolo11s.pt data=data/yolo/data.yaml \
    imgsz=1280 epochs=100 batch=4 patience=20

# end-to-end evaluation, second argument is the confidence threshold
python tools/stage4_pipeline_eval.py path/to/best.pt 0.25

# figures, reads the CSVs the two stages above write into results/
python tools/figures.py
```