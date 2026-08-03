# Monocular Sign Ranging

Monocular Sign Ranging estimates traffic-sign distance from a single camera image using projective geometry.

> [!IMPORTANT]
> The current results cover the **ranging method only**.  
> No traffic-sign detector is involved yet. All measurements were produced using ground-truth traffic-sign annotations from Cityscapes, so the reported error is **not** an end-to-end detector-and-ranging result.

| Box height | Samples | Median true distance | Median bias | 25th percentile | 75th percentile | Median \|error\| |
|---|---:|---:|---:|---:|---:|---:|
| 15–30 px | 975 | 68.5 m | 0.0% | -17% | +29% | 21.3% |
| 30–60 px | 688 | 38.4 m | 0.1% | -23% | +17% | 22.5% |
| 60+ px | 331 | 19.8 m | -5.6% | -24% | +8% | 19.1% |

Across a distance range of approximately 20–70 metres, the method behaves like a **±20% ranging instrument**.

Median absolute error remains nearly constant while the median distance changes by roughly 3.5 times.

If pixel quantization were the dominant source of error, the smallest and most distant signs should have produced substantially worse results. They did not.

The result instead suggests that the dominant limitation is uncertainty in the real physical size of the sign. This agrees with the variation measured during Stage 1.

Full method notes and intermediate distributions: [FINDINGS.md](FINDINGS.md).

## Method and Validation

The original concept combined a planned GTSDB detector, Depth Anything V2, and `near`/`mid`/`far` outputs. I rejected per-image relative depth because independent normalization prevents stable metric comparison across frames. I replaced it with:

$$
Z = \frac{f_y H_{\text{real}}}{h_{\text{px}}}
$$

GTSDB lacks the calibration and metric reference data needed for validation. Cityscapes supplies camera intrinsics, stereo disparity, and traffic-sign polygons, so I used its ground-truth boxes to isolate ranging error before introducing detector error.

The feasibility study covered 825 images and 5,512 polygons; 4,863 signs were usable, with median size 22 px and median reference distance 48 m. A disparity-bleed check found a typical 2–4% difference between median and 90th-percentile disparity that decreased for larger signs, so I retained median disparity as the reference.

## Stage 1: Sign-Size Prior and Limitation

Inverting the equation for 991 near-square signs at least 30 px high produced a median inferred height of 651 mm and an interquartile range of 574–842 mm. The model uses $H_{\text{real}}=0.650\text{ m}$.

Real variation in sign size and shape creates an approximate bias floor of $-12\%$ to $+30\%$ even with a perfectly measured box. A stronger system would classify the sign shape or size class before selecting its physical-size prior.

## Excluded Samples

I excluded signs below 15 px because they commonly imply distances above 100 m and stereo disparity below 5 px, where the reference may be unreliable. This threshold depends only on an observable image measurement, not true distance.

## Rejected Filters

Two filters were tested and rejected: `Z_true < 120 m` and `disparity ≥ 6 px`. Both produced large positive bias in the smallest bin (+44.6% and +102.6%). The cause is that each selects on the reference side only. For a fixed observed sign height, dropping samples with large true distance leaves a group the monocular model appears to overestimate. This was a validation error, not a property of the ranging model. Any filter must be independent of both sides or applied symmetrically.

## Planned Work

The next stage will train a YOLO-based detector on GTSDB, evaluate tiled inference for small signs, and connect predicted boxes to the ranging model.

Distance is inversely proportional to measured box height, so localization error propagates directly:

$$
\frac{\Delta Z}{Z} \approx -\frac{\Delta h}{h}
$$

A box that is too short will overestimate the distance. A box that is too tall will underestimate it.

The current ±20% result should therefore be treated as the performance of the geometry stage only. Detector errors will add to it. Later work will cover INT8 quantization, latency, memory use, target-hardware testing, and temporal stability.

## Reproduce

Download `gtFine_trainvaltest`, `camera_trainvaltest`, and
`disparity_trainvaltest` from cityscapes-dataset.com into `data/`.
Dataset used under the Cityscapes non-commercial licence; not redistributed.

```bash
python tools/stage0_check.py
python tools/stage0_bleed_check.py
python tools/stage1_size_prior.py
python tools/stage2_error_curve.py
```
