# Chapter 7. Results and Discussion

> **Draft note (remove in the final document).** English version of `docs/luan_van/chuong5.md` (24/11/2026), after the flood test set was locked and evaluated (`docs/results/flood.md`). Every number is copied from `docs/results/` (each table names its source file), which in turn copies from CSV files in `runs/`. Results labelled **Preliminary** or **Simulation** keep that label. Tables are numbered consecutively in this chapter (the Vietnamese draft used provisional numbers). Figures marked **[FIGURE]** are inserted when the document is laid out.

This chapter reports the results for the three research questions. Each sub-question (Table 1.2) has its own subsection: the table, what it shows, and its limitations. Data, metrics and experiment codes were defined in Chapter 6 and are repeated here only where needed to read a table correctly.

Three conventions apply throughout the chapter:

- **AP50** is average precision at IoU 0.5, computed from predictions at confidence threshold 0.001. **Operating recall** is the share of people detected at confidence 0.25, the threshold a deployed system would use.
- **95% CI** is a 95% bootstrap confidence interval with 1,000 resamples, resampling images, or whole videos when images come from the same video (SeaDronesSee, flood test set).
- When two models are compared, "**significant**" means that the 95% confidence interval of the **difference** (paired bootstrap, the same resampled images for both models) does not contain 0. Two overlapping individual intervals do not mean that two models are equal (Chapter 6, Section 6.3.2).

## 7.1 Research Question 1: Detecting Small People

### 7.1.1 How Small Can a Person Be Before Being Missed (RQ1a)

**Base model.** Table 7.1 is the starting point: YOLO26s pre-trained on COCO, run on the full image at two input sizes, on VisDrone val.

**Table 7.1.** Base model on VisDrone val, IoU 0.5 (`visdrone_baseline.md`).

| Setting | Size group | AP50 | Operating recall | Maximum recall |
|---|---|---|---|---|
| Full image, 640 input (E0) | all | 0.277 | 0.151 | 0.467 |
| | < 8 px | 0.050 | 0.007 | 0.105 |
| | 8–16 px | 0.255 | 0.105 | 0.462 |
| Full image, 1280 input (E1) | all | 0.497 | 0.322 | 0.720 |
| | < 8 px | 0.167 | 0.053 | 0.401 |
| | 8–16 px | 0.507 | 0.304 | 0.753 |
| | 16–32 px | 0.716 | 0.539 | 0.913 |
| | > 32 px | 0.836 | 0.733 | 0.966 |

Two points follow. First, **input size matters before anything else**: resizing to 640 leaves more than half of the people undetected at any threshold (maximum recall 0.467), as the table of pixels by altitude in Chapter 1 predicts. Second, **the base model "sees" small people but is not confident about them**: at 1280 input, maximum recall for people below 8 px is 0.401 but operating recall only 0.053. Most small people receive a box, but with confidence below the threshold. This is the direct motivation for fine-tuning (Section 7.1.2).

Lowering IoU from 0.5 to 0.3 raises AP for people below 8 px from 0.167 to 0.339 (E1): for a person a few pixels wide, most "misses" at IoU 0.5 are boxes a few pixels off. For rescue, a box a few pixels off around the right person is still useful, so every table for people below 8 px is also reported at IoU 0.3 (Chapter 6).

**Recall by pixels on the person.** To locate the miss threshold more precisely than four size groups allow, 4K SeaDronesSee images were downscaled by factors 1, 2, 3, 4 and 6, and tiled so that one image pixel equals one network input pixel at every level. The number of pixels on the person is then the only variable that changes (Table 7.2, Figure 7.1).

**Table 7.2.** Operating recall by the person's short side, downscaled SeaDronesSee, bootstrap by video (`e6_sds_pilot.md`). **Preliminary.**

| Short side (px) | People | Base model (E1) | Main model (E2c) |
|---|---|---|---|
| 0–4 | 24 | 0.000 | 0.000 |
| 4–6 | 160 | 0.006 | 0.256 |
| 6–8 | 257 | 0.047 | 0.494 |
| 8–11 | 500 | 0.124 | 0.532 |
| 11–16 | 758 | 0.210 | 0.588 |
| 16–23 | 868 | 0.198 | 0.624 |
| 23–32 | 655 | 0.260 | 0.537 |
| 32–45 | 706 | 0.357 | 0.516 |
| 45–64 | 492 | 0.514 | 0.390 |
| 64–91 | 357 | 0.529 | 0.261 |
| ≥ 91 | 498 | 0.637 | 0.133 |

**Figure 7.1.** [FIGURE] Operating recall by the person's short side on downscaled SeaDronesSee (`docs/results/e6_sds_recall_by_pixels.png`).

Below about 6 px both models detect almost no one; for the main model to keep a recall of about 0.5, a person needs at least about 6–8 px. This is a lower bound on flight altitude: with a 4K camera and an 82° field of view it corresponds to a specific maximum altitude (table in Chapter 1). Table 7.2 also shows something unexpected: **the main model drops sharply for large people** (from 45 px upwards it is worse than the base model). Section 7.1.4 addresses this weakness.

Limitations: 1,055 people appear at five downscaling levels, so the size groups are not independent; there are only 11 videos, so the intervals are very wide (the full table with intervals is in `e6_sds_pilot.md`); downscaling does not reproduce the sensor noise and blur of a real camera.

**On the flood test set.** Table 7.3 is the main result of research question 1 on the target data: five models fixed in advance, each run once after the set was locked (188 frames, 509 people, Chapter 6), with bootstrap over the 9 sources (`flood.md`).

**Table 7.3.** AP50 and operating recall (confidence 0.25) on the flood test set, IoU 0.5; the last column is AP50 for people below 8 px at IoU 0.3. In brackets: 95% CI.

| Model | Metric | All | < 8 px | 8–16 px | 16–32 px | > 32 px | < 8 px, IoU 0.3 |
|---|---|---|---|---|---|---|---|
| Base (E1) | AP50 | 0.269 (0.183–0.411) | 0.123 (0.015–0.258) | 0.124 (0.092–0.182) | 0.332 (0.182–0.585) | 0.661 (0.515–0.911) | 0.298 (0.070–0.414) |
| | Recall | 0.216 (0.164–0.332) | 0.057 (0.000–0.085) | 0.098 (0.067–0.159) | 0.279 (0.147–0.522) | 0.588 (0.429–0.781) | |
| Fine-tuned on VisDrone (E2) | AP50 | 0.147 (0.062–0.313) | 0.068 (0.012–0.150) | 0.073 (0.049–0.253) | 0.249 (0.063–0.530) | 0.402 (0.225–0.681) | 0.228 (0.076–0.313) |
| | Recall | 0.283 (0.207–0.440) | 0.216 (0.043–0.667) | 0.229 (0.123–0.437) | 0.375 (0.209–0.625) | 0.338 (0.151–0.691) | |
| Main model (E2c) | AP50 | 0.148 (0.070–0.334) | 0.083 (0.043–0.319) | 0.082 (0.061–0.202) | 0.233 (0.060–0.532) | 0.434 (0.282–0.687) | 0.308 (0.131–0.468) |
| | Recall | 0.244 (0.186–0.364) | 0.182 (0.054–0.591) | 0.205 (0.117–0.356) | 0.316 (0.194–0.625) | 0.287 (0.128–0.571) | |
| P2 head (E3) | AP50 | 0.162 (0.079–0.332) | 0.097 (0.024–0.181) | 0.094 (0.071–0.251) | 0.227 (0.042–0.482) | 0.468 (0.324–0.735) | 0.279 (0.093–0.383) |
| | Recall | 0.240 (0.173–0.345) | 0.171 (0.014–0.429) | 0.220 (0.133–0.374) | 0.287 (0.163–0.472) | 0.287 (0.096–0.611) | |
| Main model + tiling (E4tiled) | AP50 | 0.161 (0.058–0.315) | 0.048 (0.015–0.302) | 0.098 (0.066–0.239) | 0.251 (0.049–0.449) | 0.376 (0.218–0.620) | 0.237 (0.080–0.521) |
| | Recall | 0.295 (0.227–0.445) | 0.171 (0.056–0.706) | 0.263 (0.145–0.491) | 0.404 (0.200–0.583) | 0.325 (0.175–0.611) | |
| | People | 509 | 88 | 205 | 136 | 80 | 88 |

The result **contradicts the prediction recorded before evaluation** (Section 7.1.6): on the locked set the base model has the highest AP50, 0.120 above the main model (interval −0.191 to −0.020 for the difference E2c − E1, significant). Following the procedure set in advance, configurations and labels were checked first. The configurations were correct (the same 1280 input, threshold 0.001 and conventions as on the other sets). The labels contained one error: frame `thainguyen_003120` shows a crowd on a flooded street with many clearly visible people, but has no labels at all. The fine-tuned models report 135–167 boxes with confidence ≥ 0.25 on this frame alone (the base model 14), all counted as false alarms; for the main model this is 152 of the 432 boxes on the whole set. Under the locking rule the labels are not changed; the main numbers remain those of Table 7.3, and a sensitivity analysis repeats the same evaluation without this one frame (the reason for excluding it can be checked from the image and labels alone and does not depend on which model does better).

**Table 7.4.** Overall AP50 without the unlabelled frame (187 frames; recall is unchanged because the frame has no labels).

| Model | AP50, locked set | AP50, without unlabelled frame | Precision, locked set | Precision, without frame |
|---|---|---|---|---|
| Base (E1) | 0.269 | 0.286 (0.224–0.411) | 0.615 | 0.667 |
| Fine-tuned on VisDrone (E2) | 0.147 | 0.220 (0.141–0.340) | 0.262 | 0.377 |
| Main model (E2c) | 0.148 | 0.233 (0.165–0.349) | 0.287 | 0.443 |
| P2 head (E3) | 0.162 | 0.248 (0.175–0.341) | 0.305 | 0.460 |
| Tiling (E4tiled) | 0.161 | 0.219 (0.128–0.332) | 0.209 | 0.265 |

Without that frame the gap between the main model and the base model narrows to −0.053 (−0.166 to −0.001, p 0.050), still in favour of the base model. Three findings hold under both computations:

- **Fine-tuning trades precision for recall on small people.** The main model's operating recall is significantly higher than the base model's for people below 8 px (+0.125; at IoU 0.3 +0.307) and for 8–16 px (+0.107, p 0.050). The base model is more conservative (precision 0.615 versus 0.287) and significantly stronger for people above 32 px (AP50 difference −0.226, recall −0.300): the same weakness with large people already seen on SeaDronesSee (Table 7.2). At IoU 0.3 and without the unlabelled frame, the main model's AP50 for people below 8 px is significantly higher than the base model's (+0.047).
- **Below 8 px remains the limit:** the highest operating recall in this group is 0.216, with a very wide interval.
- **The P2 head does not differ from the main model** in any group; **tiling** raises operating recall (+0.051, significant) but not AP50, and has the lowest precision (0.209).

### 7.1.2 Which Training Data Help (RQ1b)

The three fine-tuning runs use the same YOLO26s architecture and the same 1280 input, and differ only in data:

- **urban UAV images only** (E2): VisDrone;
- **adding people in water** (E2c): VisDrone plus AFO;
- **adding disaster images with large people** (E2e): VisDrone, AFO plus C2A.

**Urban UAV images help small people strongly** (Table 7.5). On VisDrone val, AP50 for people below 8 px rises from 0.167 to 0.554, and the gain holds on test-dev, which was not used to select weights. The gain shrinks with person size: the base model was already good with large people.

**Table 7.5.** Base model (E1) and fine-tuned on VisDrone (E2), IoU 0.5, paired bootstrap (`visdrone_E2.md`).

| Set | Size group | Base model | Fine-tuned on VisDrone | Difference (95% CI) |
|---|---|---|---|---|
| VisDrone val | all | 0.497 | 0.758 | +0.261 (0.248 to 0.275) |
| | < 8 px | 0.167 | 0.554 | +0.388 (0.361 to 0.411) |
| | 8–16 px | 0.507 | 0.791 | +0.284 (0.266 to 0.303) |
| | > 32 px | 0.836 | 0.884 | +0.048 (0.024 to 0.077) |
| VisDrone test-dev | all | 0.269 | 0.513 | +0.244 (0.231 to 0.262) |
| | < 8 px | 0.086 | 0.247 | +0.161 (0.145 to 0.181) |

The gain in operating recall is larger than the gain in AP: on val, people below 8 px rise from 0.053 to 0.480. The gap between operating and maximum recall narrows (all sizes: from 0.322 versus 0.720 for the base model to 0.687 versus 0.916), so fine-tuning mainly makes the model **more confident** about small people it already saw. The price is lower operating precision (test-dev, below 8 px: 0.762 down to 0.573): the model emits more boxes on very small objects. False alarms of this kind are the job of multi-frame confirmation (Section 7.3.2), not of the detector.

**But urban images alone lose people in water** (Table 7.6). On AFO test and SeaDronesSee, the model fine-tuned on VisDrone is **worse than even the base model**, significantly so on AFO. Most people in these two sets are larger than 32 px, so the cause is not size but appearance: VisDrone only has pedestrians on streets seen obliquely; swimmers lie horizontally, partly submerged, against water.

**Table 7.6.** AP50 on data with water, IoU 0.5 (`afo_E1_E2.md`, `E2c.md`, `sds_det.md`).

| Set | Base model | Fine-tuned on VisDrone | Adding people in water |
|---|---|---|---|
| AFO test (514 images) | 0.147 | 0.103 | 0.568 |
| AFO test without images sharing a location with training (363 images) | 0.188 | 0.105 | 0.734 |
| SeaDronesSee (317 images, 11 videos) | 0.535 | 0.186 | 0.468 |

Adding AFO to the training data (E2c) recovers people in water: on AFO test the difference from the base model is +0.421 (+0.391 to +0.454), significant. On SeaDronesSee, a set of people in water **independent** of the training data, E2c is clearly better than the VisDrone-only model (+0.281, +0.053 to +0.506, significant) but **not yet better than the base model** (−0.067, −0.426 to +0.171, not significant). The large gain on AFO test is therefore partly due to test and training images sharing sources. The cost on urban images is small: compared with E2, VisDrone val drops by 0.011 (−0.015 to −0.008) and test-dev by 0.006 (−0.010 to −0.002), significant but much smaller than what is recovered on water. **E2c is selected as the main model** for everything that follows.

**Adding disaster images with large people is a negative result** (Table 7.7). C2A was added to fix E2c's weakness with large people (Table 7.2). The prediction was that large people would improve while small people stayed the same. The opposite happened: small people became clearly worse on both VisDrone sets, while on SeaDronesSee, where most people are large, the gain is not significant.

**Table 7.7.** Main model (E2c) and adding C2A (E2e), AP50 at IoU 0.5, paired bootstrap (`E2e.md`).

| Set | Size group | Main model | Adding C2A | Difference (95% CI) | Significant |
|---|---|---|---|---|---|
| VisDrone val | all | 0.747 | 0.718 | −0.029 (−0.035 to −0.023) | yes |
| | < 8 px | 0.546 | 0.492 | −0.053 (−0.067 to −0.040) | yes |
| VisDrone test-dev | all | 0.507 | 0.466 | −0.041 (−0.047 to −0.035) | yes |
| | < 8 px | 0.241 | 0.202 | −0.040 (−0.048 to −0.030) | yes |
| AFO test | all | 0.568 | 0.624 | +0.057 (+0.037 to +0.078) | yes |
| SeaDronesSee | all | 0.468 | 0.509 | +0.041 (−0.167 to +0.167) | no |
| | > 32 px | 0.470 | 0.525 | +0.055 (−0.161 to +0.173) | no |

The conclusion is the same at IoU 0.3. A plausible explanation, not tested separately: C2A makes up 6,129 of 15,387 training images and contains only large people, so the share of small people in the training data falls and the model shifts its capacity to large people. This runs against what the thesis needs, because people in UAV flood images are mostly small. The negative result is kept because it directly answers "do disaster images help": with simple mixing, they do not. Other mixing strategies (sampling part of C2A, balancing by person size) are future work (Chapter 8).

**Answer to RQ1b.** Urban UAV images teach the model small people; images of people in water keep swimmers without losing much on small people; disaster images with pasted large people, mixed in directly, cost small people. On the flood test set this ordering is not repeated in AP50: both fine-tuned models have lower AP50 than the base model, but significantly higher recall for small people; the main model and the VisDrone-only model are almost equal in AP50 (difference +0.002), the main model is better in AP50 for people below 8 px matched at IoU 0.3 (+0.080, significant) and slightly worse in overall recall (−0.039, significant). Adding people in water therefore does no harm on flood images; whether fine-tuning in general helps on flood images depends on the metric (Sections 7.1.1 and 7.1.6).

Common limitations: one seed per configuration (Chapter 6, Section 6.5); the number of epochs differs between fine-tuning runs because of Kaggle's 12-hour limit (60 epochs for E2, 55 for E2c and E2e).

### 7.1.3 Tiling and the P2 Detection Head (RQ1c)

**Tiling.** On VisDrone, 640 px tiling with a full-image pass (SAHI, E4) is **not better** than running the full image at 1280: AP50 0.460 versus 0.497, people below 8 px 0.149 versus 0.167 (`visdrone_baseline.md`), and much slower on the same machine (141.1 versus 19.3 ms per image, RTX 5060). The reason lies in the data: three quarters of the val images are only 1360 px wide, so running the full image at 1280 almost keeps the original resolution; tiling adds no detail but creates boxes cut at tile edges. This conclusion does **not** carry over to 4K video: for a 3840 px image, running the full image at 1280 means downscaling three times, while tiling keeps the original resolution.

The on-board pipeline uses its own tiler instead of SAHI because it runs all tiles of a frame in one batch and can be exported to TensorRT (Chapter 4). A paired bootstrap against SAHI (Table 7.8) shows small but significant differences, in a direction acceptable for this thesis: worse for large people, slightly better for people below 8 px.

**Table 7.8.** Own tiler versus SAHI, base model, VisDrone val, paired bootstrap (`visdrone_tiled_vs_sahi.md`).

| IoU | Size group | SAHI | Own tiler | Difference (95% CI) |
|---|---|---|---|---|
| 0.5 | all | 0.460 | 0.454 | −0.006 (−0.011 to −0.003) |
| 0.5 | < 8 px | 0.149 | 0.153 | +0.004 (+0.001 to +0.009) |
| 0.5 | > 32 px | 0.749 | 0.706 | −0.043 (−0.071 to −0.015) |
| 0.3 | all | 0.569 | 0.585 | +0.016 (+0.011 to +0.021) |
| 0.3 | < 8 px | 0.300 | 0.324 | +0.024 (+0.017 to +0.030) |

This table also shows why the paired bootstrap is needed: the two individual AP50 intervals (0.437–0.470 and 0.444–0.477) overlap, and read separately would wrongly suggest "equal". At IoU 0.3 the own tiler is **higher**: its boxes find the right place but fit less tightly, because boxes from overlapping tiles are merged by keeping the highest-scoring box rather than fusing coordinates. Coordinate fusion was tried and dropped, because a large low-score box covering a group of people turned each person's box into a box of the whole group.

**P2 head.** Adding a detection level at stride 4 (E3), with the same data and epochs as the main model, gives a significant but very small gain for people below 8 px, at the cost of worse results for large people (Table 7.9).

**Table 7.9.** P2 head (E3) versus the main model (E2c), AP50 at IoU 0.5, paired bootstrap (`E3.md`).

| Set | Size group | Main model | P2 head | Difference (95% CI) | Significant |
|---|---|---|---|---|---|
| VisDrone val | all | 0.747 | 0.747 | −0.000 (−0.005 to +0.005) | no |
| | < 8 px | 0.546 | 0.558 | +0.012 (+0.000 to +0.025) | yes |
| | > 32 px | 0.888 | 0.858 | −0.029 (−0.045 to −0.011) | yes |
| VisDrone test-dev | < 8 px | 0.241 | 0.254 | +0.013 (+0.004 to +0.021) | yes |
| | > 32 px | 0.887 | 0.873 | −0.014 (−0.026 to −0.003) | yes |
| SeaDronesSee | all | 0.468 | 0.408 | −0.060 (−0.104 to +0.013) | no |

At IoU 0.3 the gain for people below 8 px disappears (val −0.008, −0.018 to +0.003): P2 makes boxes of small people **tighter** rather than **finding more people**. Operating recall on VisDrone is even lower (val −0.027, test-dev −0.025). With a computational cost of 115.0 versus 93.9 GFLOPs, and the training batch halved because of out-of-memory errors, P2 is not worth it compared with the main model.

**Answer to RQ1c.** On medium-resolution images, neither tiling nor P2 improves small people meaningfully; the gain from P2 (+0.012 AP50 below 8 px over the main model) is very small compared with the gain from data (+0.388 when fine-tuning on VisDrone over the base model, Table 7.5). Tiling matters for 4K images, and then it must go together with altitude-based downscaling (Section 7.1.4).

### 7.1.4 Altitude-Based Frame Downscaling (RQ1d)

Table 7.2 shows that the main model is strongest for people of about 10–30 px and weak for people above 45 px. A plausible explanation: the training data are resized to 1280 input and further rescaled by augmentation, so most people reach the network small. Label statistics support this: at 1280 input without rescaling, people above 32 px are only 0.0477 of the people in VisDrone train and 0.1833 in AFO train (`e6_sds_pilot.md`). Consequently, tiling a 4K image taken at low altitude at original resolution feeds the model exactly the kind of person it is weak on.

The thesis proposes **altitude-based frame downscaling** (Chapter 4): from altitude and focal length, estimate how many pixels a 0.5 m person will cover, then downscale the frame before tiling so that people come close to a target size; never upscale. Table 7.10 tests this on 4K SeaDronesSee, the only set with both person labels and real flight altitude.

**Table 7.10.** Altitude-based downscaling, main model, 4K SeaDronesSee, IoU 0.5, bootstrap by video (`scale_by_altitude.md`). **Preliminary.**

| Setting | AP50 | 95% CI | Operating recall | Operating precision |
|---|---|---|---|---|
| Base model, full image 1280 | 0.535 | 0.362–0.616 | 0.481 | 0.660 |
| Main model, full image 1280 | 0.468 | 0.151–0.554 | 0.465 | 0.640 |
| Main model, tiling at original resolution | 0.235 | 0.083–0.551 | 0.374 | 0.065 |
| Main model, tiling, downscaled to an expected 20 px | 0.523 | 0.337–0.660 | 0.510 | 0.690 |
| Main model, tiling, downscaled to an expected 10 px | 0.531 | 0.451–0.684 | 0.579 | 0.656 |

Paired comparisons: downscaling to 10 px versus tiling at original resolution, +0.296 AP50 (+0.061 to +0.412) and +0.205 recall (+0.118 to +0.318), significant; versus the full image, recall is significantly higher (+0.114, +0.053 to +0.392) and AP50 higher but not significantly; versus the base model, AP50 is equal (−0.005, −0.115 to +0.273).

Three points follow. **Tiling at original resolution is the worst option** for a fine-tuned model on low-altitude images: precision 0.065, with very many false alarms on the background. **Altitude-based downscaling fixes most of this**, bringing the main model level with the base model on sea water while keeping its large advantage on small people (Table 7.5). This gives a better answer to the concern in Section 7.1.2 ("the main model is not better than the base model for people in water"): part of the gap comes from feeding people of the wrong size to the model, not from the model itself. Finally, the method **uses data the UAV already has** (flight altitude) to choose the processing scale instead of fixing it; this is the first part of the cross-cutting argument (Section 7.4).

Two variants of the same idea were tried and not kept: adding a full-image pass after downscaling, to catch large people cut between tiles, does not raise AP50 (−0.013, −0.071 to +0.001) and costs one more inference per frame (`full_pass.md`); in the opposite direction, upscaling the frame when people are expected below 8 px brings no significant improvement at any downscaling level, while the number of tiles more than doubles at the 6× level (`upscale_small.md`). Separate confidence thresholds by box size (lower for small boxes) do not help either: selected on VisDrone val, overall recall on that same set only rises from 0.6655 to 0.6657, because the threshold for 8–16 px people must be raised to keep precision (`conf_by_size.md`). People below about 6–8 px therefore remain the lower limit of detection; the remedy is to fly lower (Section 7.3.1).

Limitations: one set, 11 videos, mostly large people; the target sizes 10 and 20 px were chosen after seeing results on this same set, so this is an exploration rather than an independent evaluation; the camera field of view is assumed to be 82°, and the pixel estimate is usually smaller than the labelled person size. The flood test set has no flight altitude (YouTube videos), so the method cannot be evaluated on flood images (decision recorded in Chapter 6); further evidence comes from simulation (Section 7.3.1).

### 7.1.5 Flood-Specific Nuisances (RQ1e)

**Table 7.11.** Operating recall and false alarms per frame of the main model by image tag and person attribute, locked flood test set, IoU 0.5 (`flood.md`).

| Subset | People | Recall | Frames | False alarms per frame |
|---|---|---|---|---|
| All | 509 | 0.244 (0.186–0.364) | 188 | 1.638 (0.309–3.624) |
| Glare | 184 | 0.321 (0.000–0.429) | 42 | 1.738 (0.222–4.408) |
| Rain, fog, darkness | 4 | 0.500 | 1 | 1.000 |
| Blur | 223 | 0.305 (0.146–0.469) | 54 | 1.407 (0.257–4.709) |
| Floating debris | 213 | 0.324 (0.164–0.447) | 117 | 0.863 (0.250–1.855) |
| Frames without tags | 262 | 0.191 (0.000–0.204) | 58 | 3.534 (0.100–6.392) |
| Partly submerged people | 70 | 0.243 (0.048–0.461) | | |
| Occluded people | 68 | 0.279 (0.136–0.535) | | |
| People without attributes | 373 | 0.236 (0.165–0.362) | | |

No tag clearly lowers recall compared with the whole set; the intervals are too wide to conclude anything (only one frame has bad weather). Frames with glare, blur or floating debris even have a higher point recall than untagged frames, probably because they tend to be close-up scenes with larger people, not because the nuisance helps the model. Untagged frames have the most false alarms per frame, partly because the unlabelled frame (which also has no tags) falls in this group. The tags themselves are only moderately reliable: when 37 frames were labelled twice, the glare and floating-debris tags agreed only 0.649 and 0.595 (Chapter 6). Answer to RQ1e: on these 188 frames, no separate effect of glare, blur or floating debris on recall could be measured.

### 7.1.6 From Urban and Maritime Images to Flood Scenes (RQ1f)

**Table 7.12.** Overall AP50 (IoU 0.5) of the same models on three sets (`E2c.md`, `E3.md`, `sds_det.md`, `flood.md`). The model with C2A was not run on the flood set (Chapter 6).

| Model | VisDrone test-dev | SeaDronesSee | Flood set, locked | Flood set, without unlabelled frame |
|---|---|---|---|---|
| Base (E1) | 0.269 | 0.535 | 0.269 | 0.286 |
| Fine-tuned on VisDrone (E2) | 0.513 | 0.186 | 0.147 | 0.220 |
| Main model (E2c) | 0.507 | 0.468 | 0.148 | 0.233 |
| P2 head (E3) | 0.510 | 0.408 | 0.162 | 0.248 |

The ranking on the flood set **resembles SeaDronesSee more than VisDrone**: the base model is first on both sets with water, while on VisDrone it is far behind. An urban set, even one with many small people, therefore does not predict which model is best for flood scenes; AP50 on urban images measures the difficulty of "small people on a street background", not false alarms on water, roofs and crowds. Unlike SeaDronesSee, on the flood set the gap between the main model and the VisDrone-only model almost disappears, probably because people in flood images mostly stand or wade rather than swim as in AFO and SeaDronesSee.

The prediction recorded before evaluation, kept here for comparison: the 188 flood frames contain both small people on roofs and medium-sized people in water, so the main model was expected to beat the base model on small people and not to be worse on people in water. If the result contradicted the prediction, the first step would be to check configurations and labels before drawing conclusions (done in Section 7.1.1).

## 7.2 Research Question 2: Keeping Up on the Edge Device

Research question 2 is measured on a Kaggle Tesla T4 GPU with TensorRT, because no Jetson was available (Chapter 6). T4 numbers are not Jetson numbers; what they show is the **relative ranking** of configurations on the same hardware and **which stage takes the most time**. Timings measured on the development machine in earlier sections (Mac, RTX 5060) are only for relative comparison and do not appear in this section.

### 7.2.1 Model Compression and the Best Configuration (RQ2a, RQ2b)

One option was tried before the T4 measurements: YOLO26 has a one-to-one, NMS-free output head, presented as simpler for edge devices. With the same main-model weights, this head lowers operating recall significantly on VisDrone, most for people below 8 px (val −0.056, test-dev −0.029), while AP50 is almost unchanged and PyTorch time is the same (`nms_free.md`). All configurations below use the default head with NMS. Another way to reduce computation was also tried and dropped: when the UAV hovers, reusing results for tiles that barely change reduces the tiles to run to 0.518–0.852 of the full count, but recall drops by up to 0.238, because swimmers still move and the downscaled tile comparison does not notice (`tile_skip.md`).

Nine configurations were measured on the T4: the main model in PyTorch, TensorRT FP16 and TensorRT INT8, each run on the full image at 1280, with 640 tiling at original resolution, and with tiling after downscaling to an expected 10 px by altitude. Speed is that of **the whole on-board pipeline** (frame reading, downscaling, tiling, inference, box merging, ground projection, confirmation) on 100 frames of a 4K SeaDronesSee video with real telemetry; accuracy is scored on SeaDronesSee val and VisDrone test-dev.

**Table 7.13.** Whole-pipeline speed on 4K frames, Tesla T4 (`rq2_t4.md`). Relative comparison only.

| Configuration | Tiles | Frame downscaling p50 (ms) | Inference p50 (ms) | Total p50 (ms) | Frames per second at p95 |
|---|---|---|---|---|---|
| PyTorch, full image | 1 | 0.00 | 54.37 | 54.71 | 18.01 |
| FP16, full image | 1 | 0.00 | 23.72 | 24.06 | 39.90 |
| INT8, full image | 1 | 0.00 | 20.11 | 20.37 | 44.58 |
| PyTorch, tiling at original resolution | 32 | 0.05 | 385.50 | 386.06 | 2.48 |
| FP16, tiling at original resolution | 32 | 0.05 | 120.10 | 120.57 | 7.50 |
| INT8, tiling at original resolution | 32 | 0.05 | 105.98 | 106.58 | 9.04 |
| PyTorch, downscaled to 10 px | 6 | 46.35 | 90.97 | 138.49 | 6.32 |
| FP16, downscaled to 10 px | 6 | 46.28 | 30.56 | 77.34 | 11.58 |
| INT8, downscaled to 10 px | 6 | 45.74 | 25.84 | 72.10 | 11.98 |

**FP16 loses almost nothing.** Compared with PyTorch in the same setting, FP16 is 1.833–3.028 times faster (at p95). On SeaDronesSee the differences in AP50 and operating recall are not significant; on VisDrone AP50 drops by 0.005 and operating recall for people below 8 px does not differ significantly (`rq2_t4.md`).

**INT8 loses operating recall, not discrimination.** Table 7.14 answers "what does INT8 lose on small people" on VisDrone test-dev (SeaDronesSee val has almost no people below 16 px).

**Table 7.14.** INT8 versus PyTorch, full image at 1280, VisDrone test-dev, IoU 0.5 (`rq2_t4.md`).

| Size group | AP50 PyTorch → INT8 | Operating recall (confidence 0.25) | Maximum recall (any threshold) |
|---|---|---|---|
| < 8 px | 0.241 → 0.223 | 0.217 → 0.108 | 0.477 → 0.461 |
| 8–16 px | 0.623 → 0.592 | 0.572 → 0.407 | 0.853 → 0.834 |
| 16–32 px | 0.823 → 0.808 | 0.783 → 0.664 | 0.951 → 0.945 |
| > 32 px | 0.888 → 0.879 | 0.853 → 0.768 | 0.969 → 0.970 |

The AP50 difference below 8 px is −0.018 (95% CI −0.041 to −0.015), while the operating-recall difference below 8 px is −0.109 (−0.176 to −0.096); at IoU 0.3 these are −0.035 and −0.172. Maximum recall is almost unchanged, while the number of boxes with confidence 0.25 or above falls from 19,423 (FP16) to 10,940 and the 99th percentile of confidence from 0.639 to 0.492. In other words, **INT8 compresses confidence downwards**: the ordering of boxes is nearly preserved so AP changes little, but the 0.25 threshold chosen for the uncompressed model cuts away half of the people below 8 px. In exchange, INT8 is only slightly faster than FP16 (Table 7.13). On SeaDronesSee with altitude-based downscaling, INT8 does not differ significantly from PyTorch, but the interval is wide (operating recall −0.025, from −0.100 to +0.010).

**Altitude-based downscaling is both more accurate and faster, and moves the bottleneck to frame resizing.** On 4K frames, tiling at original resolution runs 32 tiles and gives the lowest AP50 (0.234; INT8 0.164); downscaling to 10 px leaves 6 tiles, with AP50 0.534 in FP16 (difference +0.301, 95% CI +0.060 to +0.414). But resizing one 4K frame on the CPU takes 46.28 ms (median, FP16), more than the inference of 6 tiles (30.56 ms in FP16). From here, further speed-up must come from frame resizing (on the GPU, or by decoding video at a lower resolution), not from further model compression.

**Frame resizing on the GPU (preliminary, measured on the development machine, relative only).** The resizing stage is slow because the Ultralytics library forces OpenCV to run single-threaded when it is loaded. Resizing with torch on the GPU reduces the frame preparation stage on SeaDronesSee val from 21.34 ms to 5.39 ms (median) and the total per image from 50.60 ms to 43.55 ms, with no significant difference in AP50 or recall (AP50 −0.021, 95% CI −0.038 to +0.017; `gpu_resize.md`). It has not been measured on the T4, so the tables above still use CPU resizing.

**Table 7.15.** Pareto front of operating recall versus speed, SeaDronesSee val (`rq2_t4.md`). **[FIGURE]** `runs/rq2/rq2_sds_det.png`.

| Configuration | Frames per second at p95 | Operating recall | AP50 | On the front |
|---|---|---|---|---|
| INT8, full image | 44.58 | 0.443 | 0.470 | yes |
| FP16, full image | 39.90 | 0.468 | 0.457 | yes |
| PyTorch, full image | 18.01 | 0.466 | 0.468 | |
| INT8, downscaled to 10 px | 11.98 | 0.554 | 0.524 | yes |
| FP16, downscaled to 10 px | 11.58 | 0.580 | 0.534 | yes |
| INT8, tiling at original resolution | 9.04 | 0.290 | 0.164 | |
| FP16, tiling at original resolution | 7.50 | 0.372 | 0.234 | |
| PyTorch, downscaled to 10 px | 6.32 | 0.579 | 0.531 | |
| PyTorch, tiling at original resolution | 2.48 | 0.374 | 0.234 | |

**Answer to RQ2a and RQ2b.** On the T4, FP16 is the compression level to use: 1.833–3.028 times faster than PyTorch with accuracy almost unchanged. INT8 adds little speed and, with the current threshold, loses half of the operating recall for people below 8 px because confidence is compressed; using it would require a new threshold chosen on a validation set. The Pareto front has two groups: full image (39.90–44.58 frames per second at p95, operating recall 0.443–0.468) and altitude-based downscaling (11.58–11.98 frames per second, recall 0.554–0.580). Since the rate ceiling needed in Section 7.3.1 is 8 frames per second, the selected configuration is **FP16 with altitude-based downscaling**: the highest recall on the front, and still above the required rate on the T4. Whether a weaker device keeps up is the question of Section 7.2.2.

### 7.2.2 Weak Devices (RQ2c)

Without a Jetson, this question is answered with the **device timing simulation** (Chapter 4): the pipeline runs on the development machine but is "busy" according to another device's profile, and frames arriving while it is busy are dropped. The profiles are calibrated from the T4 measurements in Section 7.2.1; for Jetson devices they also multiply by the published ratio of inference times (Jetson versus T4), so **every number in this section is an estimate** and is not placed next to measured numbers. When the T4 measurements showed that frame downscaling is costly, the profile was extended with a downscaling time per megapixel; otherwise the simulation would ignore exactly the heaviest part of the selected configuration.

**Table 7.16.** Can a weak device keep up: the same flight as Table 7.18, downscaling to 10 px, the pipeline requesting 8 frames per second (`rq2_t4.md`). **Simulation; Jetson profiles are estimates.**

| Altitude | Device | Latency per frame, median (ms) | Frames processed in 60 s | Miss rate |
|---|---|---|---|---|
| 30 m | T4 (measured profile) | 54.283 | 480 | 0.000 |
| 30 m | AGX Orin | 83.659 | 480 | 0.000 |
| 30 m | Orin NX | 131.878 | 240 | 0.067 |
| 30 m | Orin Nano Super | 145.935 | 240 | 0.067 |
| 50 m | T4 (measured profile) | 69.283 | 480 | 0.000 |
| 50 m | Orin Nano Super | 186.295 | 240 | 0.033 |
| 100 m | T4 (measured profile) | 136.783 | 240 | 0.000 |
| 100 m | Orin Nano Super | 367.915 | 160 | 0.000 |

**Answer to RQ2c.** By estimate, the Orin NX and Orin Nano Super process only 4 of 8 frames per second at 30–50 m, so they miss 0.067 at 30 m, exactly the level of requesting only 4 frames per second; at 100 m no device misses anyone because 2 frames per second are enough (Table 7.18). Weak devices fall short exactly when flying low, when the required rate is highest. At that point each frame has only 2 tiles, so latency is dominated by downscaling the 4K frame, not by inference: further model compression (INT8) helps little, while resizing on the GPU or taking lower-resolution video when flying low is the right direction (not done, Chapter 8). These numbers depend on an untested assumption: that the CPU part of a Jetson is slower than the T4 machine by the same ratio as inference.

## 7.3 Research Question 3: Reporting Correctly to the Ground Station

Most results for research question 3 come from **simulation**: a simulated flight with telemetry, people standing at known positions, and a simulated detector whose recall follows the curve measured in Table 7.2. Simulation makes it possible to vary one factor (altitude, GPS, network) while keeping the others fixed, which a few real videos cannot do. The real data are three SeaDronesSee sequences with telemetry (Section 7.3.2). Every simulation number is the mean of 3 seeds (Chapter 6, Table 6.7).

One shared assumption must be kept in mind when reading this section: in the simulation, frames are **independent**, so a person hard to see in one frame is not harder to see in the next. In reality errors are correlated over time (waves, glare lasting several seconds), so the simulation is **optimistic** for configurations that rely on many views.

### 7.3.1 How Many Frames per Second Are Enough (RQ3a)

**Altitude and person size.** Flying higher makes people smaller and harder to see in each frame, but keeps them in view longer, so they are seen more often. Table 7.17 shows that with the main model the second effect wins.

**Table 7.17.** Miss rate by altitude, 2 frames per second, recall by person size (`rq3_altitude.md`). **Simulation.**

| Altitude | Base model | Main model |
|---|---|---|
| 30 m | 0.767 | 0.567 |
| 50 m | 0.567 | 0.033 |
| 80 m | 0.533 | 0.000 |
| 120 m | 0.600 | 0.000 |
| 160 m | 0.967 | 0.000 |
| 200 m | 0.900 | 0.000 |

The base model is unusable at high altitude (miss rate 0.900 or more from 160 m). The main model misses no one from 80 m to 200 m, but **does badly when flying low**: at 30 m a person stays in only a few frames yet must still be seen 3 times.

**Altitude-dependent rate.** Instead of a fixed 2 frames per second, the rate is computed so that each person is seen a set number of times (`min_views`): the rate equals the number of views times the speed divided by the footprint length, clamped to a ceiling. Table 7.18 compares this with fixed rates.

**Table 7.18.** Miss rate / frames run through the detector in 60 s (`rq3_adaptive.md`). **Simulation.**

| Altitude | Fixed 2 frames/s | Fixed 8 frames/s | 12 views, ceiling 8 |
|---|---|---|---|
| 30 m | 0.567 / 120 | 0.000 / 480 | 0.033 / 279.7 |
| 50 m | 0.067 / 120 | 0.000 / 480 | 0.000 / 169.3 |
| 80 m | 0.000 / 120 | 0.000 / 480 | 0.000 / 106.7 |
| 120 m | 0.000 / 120 | 0.000 / 480 | 0.000 / 71.7 |

The altitude-dependent rate **moves frames from where they are wasted to where they are needed**: flying low, it runs more frames and almost removes misses (30 m: 0.033 versus 0.567); flying high, it runs fewer frames without misses (120 m: 71.7 frames versus 120). The number of views must match the recall: 6 views are too few for the main model's per-frame recall of about 0.5 (miss rate 0.100–0.333 at every altitude, `rq3_adaptive.md`). The rate ceiling is where research question 2 connects: if the device can run only 2 frames per second, every number of views at 30 m is cut back to 2 and the benefit disappears.

When altitude **changes mid-flight** (searching at 120 m, then descending to 40 m), 12 views with ceiling 8 misses 0.033 with 137 frames, close to a fixed 8 frames per second (0.000 with 480 frames); adding downscaling to 10 px misses no one (`rq3_altprofile.md`). In the simulation, altitude-based downscaling gives only a small improvement, because people at 30–120 m fall in the 8–45 px range, where the main model's recall curve is almost flat (Table 7.2); the benefit measured on SeaDronesSee (Table 7.10) comes from people above 45 px and from false alarms when tiling large people, neither of which the simulation contains. Another reason: the simulation assumes a 0.5 m wide person, while labelled person boxes in SeaDronesSee, the source of the recall curve, are about 1.8–2.6 times larger in nadir view. Repeating the simulation with a 1.0 m person, flying at 30 m misses 0.867 and downscaling to an expected 10 px reduces this to 0.400; at 50 m from 0.133 to 0.033 (`person_px_check.md`, **simulation**). The miss rate at low altitude therefore depends strongly on the assumed person size.

**Answer to RQ3a.** No single rate is enough for every altitude. The required rate depends on altitude, speed and the detector's recall; computing it from telemetry reduces misses when flying low and computation when flying high. Linking to research question 2: the selected configuration runs at 11.58 frames per second (p95) on the T4 with 4K frames, above the ceiling of 8; weaker devices reach only 4 frames per second at 30–50 m by estimate (Table 7.16).

### 7.3.2 Grouping on Ground Coordinates or Tracking in the Image (RQ3b)

Confirmation sends an alert only after a person has been seen N = 3 times. Two ways of linking sightings are compared: **grouping on ground coordinates** (geo: projecting boxes onto the ground with telemetry and grouping points within a 3 m radius and a 5 s window), and **tracking in the image** (ByteTrack, linking boxes between frames by overlap; with or without camera motion compensation from telemetry). **Preliminary** results on three real SeaDronesSee-MOT sequences with real GPS, altitude, heading and per-frame person labels are shown in Table 7.19.

**Table 7.19.** Confirmation on real video, main model, 2 frames per second (`sds_mot_confirm.md`). **Preliminary.**

| Sequence | Confirmation | People alerted / eligible | Alerts | False | Duplicate | Time to alert (s, median) |
|---|---|---|---|---|---|---|
| v21, 40 m, 34 people | geo | 12 / 19 | 37 | 13 | 12 | 2.00 |
| | ByteTrack | 2 / 19 | 2 | 0 | 0 | 25.25 |
| | ByteTrack with motion compensation | 2 / 19 | 4 | 0 | 2 | 21.00 |
| v5, 122–140 m, 6 people | geo | 6 / 6 | 9 | 3 | 0 | 1.00 |
| | ByteTrack | 6 / 6 | 11 | 0 | 5 | 1.50 |
| v13, 91 m, 2 people | geo | 2 / 2 | 4 | 0 | 2 | 3.00 |
| | ByteTrack | 1 / 2 | 2 | 0 | 1 | 1.00 |

(ByteTrack with track creation threshold 0.1; threshold 0.25 gives the same number of people alerted.)

On the most crowded sequence (v21), grouping on ground coordinates confirms 12 of 19 people, ByteTrack only 2. **The cause is the frame rate, not how the tracker is used**: at 2 frames per second, the IoU between the true boxes of the same person in two consecutive processed frames has a median of 0.46 (v21), 0.53 (v5) and only 0.05 (v13), versus 0.93, 0.94 and 0.84 at 30 frames per second. UAV drift, slight rotation, moving swimmers and small boxes keep overlap low even when the UAV is almost hovering; together with low per-frame recall, ByteTrack creates a new track in almost every frame (v21: 314 matches, 299 distinct IDs). Re-run at 10 frames per second, ByteTrack works again (12 of 26 people).

The price of geo is **duplicate and false alerts**: one person is split into several clusters when real GPS drifts, and fixed objects detected repeatedly become alerts. Section 7.3.5 deals with duplicates.

**Why telemetry-based motion compensation is not enough.** One might expect that shifting the previous frame's boxes by the motion computed from telemetry would save ByteTrack. The simulation in Table 7.20 shows that this breaks under GPS noise, and shows the mechanism: the error of the shift equals **the difference in GPS noise between two frames**, so the faster GPS jumps (small correlation time τ), the more people are missed.

**Table 7.20.** Miss rate by GPS noise, at 50 m (`rq3_cmc_cause.md`). **Simulation.**

| GPS τ | GPS σ | ByteTrack with motion compensation | geo |
|---|---|---|---|
| 5 s | 0.5 m | 0.900 | 0.033 |
| 5 s | 1 m | 1.000 | 0.033 |
| 30 s | 0.5 m | 0.200 | 0.000 |
| 30 s | 1 m | 0.767 | 0.000 |
| 300 s | 0.5 m | 0.033 | 0.000 |
| 300 s | 1 m | 0.033 | 0.000 |

Geo is almost unaffected (miss rate at most 0.033 in every cell of the grid), because it compares ground distance with a 3 m radius, much larger than the GPS difference between two frames. Telemetry-based motion compensation is only usable with GPS that is stable in the short term (RTK, or GPS filtered by the flight controller's state estimator).

**Tilted camera.** The ground projection initially assumed a camera looking straight down. Every SeaDronesSee sequence with a moving UAV was recorded with a tilted gimbal, so the projection was extended to account for the tilt and checked by the spread of positions of almost stationary people (`georef_pitch.md`, **preliminary**). The result is mixed: clearly better when the UAV moves with moderate tilt (for example sequence v8, pitch −48.0°: spread 4.982 m reduced to 1.301 m), but worse when the camera is close to the horizon and when the UAV is almost hovering; overall the median spread increases (1.336 to 1.603 m) and only 0.515 of the tracks improve. The tilt-aware projection is therefore optional and not enabled by default.

**Answer to RQ3b.** When only a few frames per second are processed, grouping on ground coordinates is more robust than tracking in the image, both on real video and in simulation with GPS noise. This is the third part of the cross-cutting argument: the UAV's telemetry replaces the frame-to-frame continuity an image tracker needs. Limitation: three sequences, with the UAV almost hovering; the case of a fast-moving UAV still relies on simulation.

### 7.3.3 Alert Position Error (RQ3c)

Each alert carries the person's coordinates and a 1σ error radius computed by the system from the error-propagation model (Chapter 4, Table 4.1: GPS 3 m, altitude 2 m, heading 2°, tilt 1° by default). Table 7.21 asks two things: how far positions shift when real GPS is good or bad, and whether the attached radius contains the real person.

**Table 7.21.** Position error at each person's first alert, GPS noise only (`rq3_geoerr.md`). **Simulation.**

| Altitude | GPS σ | Median error (m) | Inside 1σ radius | Inside 95% area | Missed |
|---|---|---|---|---|---|
| 50 m | 0 m | 0.250 | 1.000 | 1.000 | 0.000 |
| 50 m | 1 m | 1.282 | 1.000 | 1.000 | 0.000 |
| 50 m | 3 m | 3.956 | 0.278 | 1.000 | 0.033 |
| 50 m | 5 m | 6.591 | 0.181 | 0.833 | 0.100 |
| 100 m | 3 m | 4.275 | 0.274 | 1.000 | 0.033 |
| 100 m | 5 m | 7.362 | 0.241 | 0.763 | 0.033 |

**GPS is the main source of error**: the median error follows GPS σ and barely changes with altitude. **The 1σ circle is too narrow to search with**: when real GPS matches the assumption (σ 3 m), only about a quarter of the people lie inside the 1σ radius (0.278 and 0.274). This agrees with theory: a two-dimensional error has a Rayleigh distribution, and the 1σ circle contains only about 39% of the probability. The 95% area (radius 2.448σ) contains every person in every cell with GPS σ up to 3 m; the ground station map therefore draws the **95% search area**, not the 1σ circle. When real GPS is worse than assumed (σ 5 m), the 95% area is no longer enough (0.763–0.833): the radius is only right when the error model is set from the UAV's real GPS. The thesis therefore allows GPS σ to be taken from the accuracy the receiver reports in each frame. In the simulation, when the receiver reports correctly, the 95% area contains every person in every cell, even when GPS degrades mid-flight (a fixed σ contains only 0.833–0.933 in that case), and it narrows when GPS is good (50 m, σ 1 m: radius 8.069 down to 4.141 m); if the receiver reports half the real error, the area is too narrow, containing only 0.652–0.963 (`rq3_gpsacc.md`, **simulation**).

**Heading bias causes false splits at high altitude.** With GPS σ 1 m, a fixed 5° compass bias splits one person into several alerts: on average 5.333 false splits per scenario at 100 m, versus 0.333 at 50 m (`rq3_geoerr.md`). A heading bias rotates coordinates around the point below the UAV; the higher the UAV, the further the same angle pushes the projected point, beyond the 3 m grouping radius. The ground station can merge this part into one incident (Section 7.3.5). The thesis adds an on-board self-calibration step: when flying straight, the course computed from GPS is an independent measurement of the heading, so the median of yaw minus course estimates the compass bias (Chapter 4). In the simulation, the estimated bias is off by at most 0.228° when flying straight with GPS σ 1 m, and false splits at 100 m with a 5° bias drop from 5.333 to 0.333 per scenario; when the compass is not biased, the cost is a slightly larger position error (1.387 to 1.538 m) (`rq3_yawcalib.md`, **simulation**). This is another example of the cross-cutting argument: the UAV's own telemetry is used to correct its telemetry.

Limitations: people are stationary, the camera looks straight down, and the simulated detector places boxes exactly on the person; people whose alert is more than 10 m off are counted as missed and excluded from the "inside" shares, so at σ 5 m those shares are optimistic.

### 7.3.4 Link Outages and Alert Latency (RQ3d)

Alerts are written to disk before being sent and resent with a waiting time that doubles after each failure, up to 30 s (Chapter 4). The thesis adds **link probing**: when packets are waiting and nothing has been sent for 2 s, the oldest pending position packet is tried; if it goes through, all pending packets are sent at once. Table 7.22 compares with and without probing.

**Table 7.22.** Alert latency to the ground station (`rq3_network.md`). **Simulation.**

| Packet loss | Outage | Probing | Median latency (s) | Maximum latency (s) | Alerts lost |
|---|---|---|---|---|---|
| 0 | none | no | 0.000 | 0.000 | 0.000 |
| 0 | 15–45 s | no | 8.667 | 36.500 | 0.000 |
| 0 | 15–45 s | yes | 5.917 | 27.500 | 0.000 |
| 0.5 | none | no | 0.250 | 41.167 | 0.000 |
| 0.5 | none | yes | 1.167 | 8.333 | 0.000 |
| 0.5 | 20–35 s | no | 3.000 | 48.000 | 0.033 |
| 0.5 | 20–35 s | yes | 3.417 | 17.333 | 0.000 |
| 0.5 | 15–45 s | no | 10.583 | 60.500 | 0.000 |
| 0.5 | 15–45 s | yes | 9.000 | 29.167 | 0.000 |

**With probing no alert is lost**, even with half the packets lost plus a 30 s outage; without probing one cell loses 0.033 (one alert in three scenarios did not reach the station within 60 s of resending). **Median latency is small; maximum latency is the problem**: with a doubling waiting time, a packet that fails just before the link returns can wait almost 30 s more. Probing removes that unnecessary wait (packet loss 0.5: maximum latency 41.167 s down to 8.333 s) at almost no extra data (2.647 versus 2.629 KB per alert with a 20–35 s outage), because each probe is a single position packet. The remaining delay with probing is mainly the outage itself: an alert created during an outage cannot reach the station before the link returns.

**Burst loss.** Table 7.22 assumes each send fails independently. Real weak links usually last, so burst loss was also simulated (the Gilbert–Elliott model: the link switches between a good and a bad state, losing every packet in the bad state) and compared with scattered loss at **the same average loss rate** (Table 7.23; 120 s flights and 5 seeds, so not directly comparable with Table 7.22).

**Table 7.23.** Scattered versus burst loss, average loss rate 0.5, with probing (`rq3_burst.md`). **Simulation.**

| Loss pattern | Median latency (s) | Maximum latency (s) | Alerts lost |
|---|---|---|---|
| Scattered 0.5 | 0.850 | 8.400 | 0.000 |
| Bursts bad 10 s / good 10 s | 4.350 | 15.800 | 0.000 |
| Bursts bad 30 s / good 30 s | 19.900 | 44.400 | 0.000 |

At the same loss rate, longer bursts delay alerts more, because every send within a burst fails; this delay is the burst length itself and no resending strategy can shorten it. Probing still loses no alert in any cell; without probing, the 30 s burst cells lose 0.080–0.180 of the alerts.

Limitations: no real network measurements were available to choose burst lengths; the number of seeds is small relative to the variability of long bursts, so maximum latency varies strongly between seeds (standard deviations in `rq3_network.md` and `rq3_burst.md`).

### 7.3.5 Merging Alerts into Incidents (RQ3e)

Geo produces duplicate alerts (Table 7.19). Two ways of reducing duplicates were compared on the three real sequences:

- **Dropping on the edge device**: a new alert within 3 m of an alert sent in the last 60 s is not sent. This reduces duplicates (v21: 12 to 7) but **loses people**: v21 has 10 instead of 12 people alerted, because swimmers close together are treated as one (`alert_memory.md`).
- **Merging at the ground station**: every alert is still sent, and the station attaches each alert to the nearest open incident. No alert is dropped; an operator opening an incident still sees each alert and its crop.

**Table 7.24.** Merging geo alerts into incidents at the ground station, by merging radius (`alert_memory.md`).

| Sequence | Merging radius | Alerts | Incidents | Incidents mixing more than one person | People split |
|---|---|---|---|---|---|
| v21 (12 people alerted) | 3 m | 37 | 27 | 6 | 6 |
| | 5 m | 37 | 19 | 5 | 6 |
| | 10 m | 37 | 10 | 3 | 3 |
| v5 (6 people) | 3 m | 9 | 9 | 0 | 0 |
| | 5 m | 9 | 8 | 0 | 0 |
| | 10 m | 9 | 4 | 2 | 0 |
| v13 (2 people) | 3 m | 4 | 3 | 0 | 1 |
| | 5 m | 4 | 2 | 0 | 0 |
| | 10 m | 4 | 1 | 1 | 0 |

A 5 m radius is chosen as the default: the two sparse sequences merge perfectly (v13 has no more duplicates, v5 mixes no people), and the crowded sequence v21 goes from 37 alerts to 19 incidents. On v21 no radius removes both splits and mixes, because the swimmers are closer together than the drift of their positions: this is a limit of geolocation, not something a merging rule can fix. Because merging at the station drops no alert, the cost is grouped display, not lost people. In rescue, missing a person costs far more than an extra alert, so the thesis **keeps every alert on the edge and merges at the station**.

Limitations: three sequences, matched against labels in image space; merging by the error radius attached to each alert could not be tested because the error radius was still a constant when these runs were made.

**People per incident.** Merging at the station turns a group of people into one incident, so each alert carries an estimated number of people within 5 m (Chapter 4); the incident keeps the largest count. Counting from the detections of the confirming frame falls short when the detector misses some of the group in that frame; also counting clusters seen at least twice recently fixes most of this. In a simulation with groups of 4 people and recall 0.7, the share of alerts with the correct count rises from 0.303 to 0.524 (recall 0.9: 0.533 to 0.900), with no change for single people (**simulation**). On the crowded real sequence v21, however, this count is worse than counting per frame (correct count 0.792 down to 0.583, overcounting in 8 of 24 alerts): one person's position drifts with GPS, so that person is split into several clusters, and the extra clusters are counted as other people (`rq3_group.md`). A third method (people seen together in at least two frames) avoids that overcount but is not better either (0.750). The thesis keeps per-frame counting. This is an example of the simulation ignoring exactly the phenomenon that decides the result, so every simulation conclusion in this chapter should be read together with the checks on real video.

## 7.4 Cross-Cutting Argument: Flight Data Help All Three Stages

The results of the three questions share one mechanism: **using telemetry the UAV already has (altitude, GPS, heading) in place of a fixed assumption**.

- **Detection (RQ1d):** altitude tells how many pixels a person will cover, so the frame can be downscaled to the size the model handles best. On 4K SeaDronesSee this raises the main model's AP50 with tiling from 0.235 to 0.531 (Table 7.10).
- **Speed (RQ2):** the same downscaling reduces the number of tiles to run, and the same altitude and speed tell how many frames per second are needed (Table 7.18). On 4K frames the tiles drop from 32 to 6 and the median total time in FP16 from 120.57 ms to 77.34 ms on the T4 (Table 7.13), while AP50 rises.
- **Confirmation (RQ3b):** GPS and heading allow sightings to be linked on ground coordinates without boxes overlapping between frames; this confirms people at 2 frames per second, where the image tracker breaks (Tables 7.19 and 7.20).

The other side of the argument must also be stated: the system depends on the quality of its telemetry. GPS worse than assumed makes the 95% search area insufficient (Table 7.21), a compass bias causes false splits at high altitude (Section 7.3.3), and noisy gimbal angles make the tilt-aware projection worse on some sequences (Section 7.3.2). Where telemetry is absent, as in the flood test set, altitude-based downscaling cannot be applied and the detector alone decides the result (Section 7.1.1).

## 7.5 Error Analysis

The illustrative frames are chosen by three rules fixed before the lock (`tools/demo_panels.py`, Chapter 6), comparing the base model with the main model: the frame with the most small people (`thainguyen_002160`, 69 people all below 16 px: the base model finds 11, the main model 27 but adds 42 false alarms versus 7), a typical frame (`nidarx_000300`) and the frame with the most errors (`nidarx_000600`, 67 people: the base model finds 7, the main model 19) (`runs/demo/flood_panels/picks.csv`).

**Figure 7.2.** [FIGURE] The three frames chosen by the fixed rules, base model and main model side by side.

The largest error class by count is not the model's but the labels': the clearly visible crowd in frame `thainguyen_003120` was not labelled (Section 7.1.1). According to the labelling guide, a crowd in which individuals cannot be separated should be covered by an ignore region; this frame was left empty. Another frame from the same video (`thainguyen_000144`) also has no labels and 17 boxes with confidence ≥ 0.25 from the main model; this frame has not been reviewed. The remaining false alarms concentrate in the 480p Thai Nguyen video, where people are below 16 px and the fine-tuned models emit many small boxes; a crop-by-crop error analysis has not been done.

Two kinds of false alarms already seen on data with water are recorded for comparison: on AFO, boards, boats and floating objects are called people (operating precision of the base model 0.300, `afo_E1_E2.md`); on SeaDronesSee, fixed objects detected repeatedly become false alerts (v21: 13 of 37 alerts, Table 7.19).

## 7.6 System Demonstration

This section measures nothing new; it shows the components running together as one system.

- **Simulated flight over a flood area** (Chapter 4): the UAV flies a lawn-mower pattern, images are rendered from a synthetic flood scene with roofs, trees, floating debris and people, the on-board pipeline runs exactly as on real video, and the ground station shows the UAV position, the scanned area, alerts and 95% search areas on the map. Because the people's positions are known, the map can check every incident against the real people: found, inside the search area, missed, false alarm.
- **Real SeaDronesSee video** with real telemetry: the same interface, with alerts on real 4K images.
- **Two UAVs** reporting to one station (`multi_uav_demo.md`, **illustration**): 37 alerts per UAV merge into 20 incidents, 18 of which are seen by both UAVs; both UAVs replay the same video with different GPS, so this checks the data flow, not merging accuracy.
- **Sandbox** in the experiment console: change altitude, speed, GPS, network and device, re-run the flight and compare runs side by side.

**Figure 7.3.** [FIGURE] Dispatch screen during a scan. **Figure 7.4.** [FIGURE] Map after the flight with the ground-truth overlay. Captured from `scripts/demo_bao_ve.sh` when the document is laid out.

## Chapter Summary

- **Research question 1.** Training data matter most for small people; architecture (P2) and tiling on medium-resolution images help very little. Fine-tuned models are weak with large people; altitude-based downscaling compensates on SeaDronesSee. Adding disaster images with large people by simple mixing costs small people. On the flood test set, fine-tuning raises recall for small people but not AP50: the base model is more conservative and keeps the highest AP50, even when one unlabelled frame is excluded; the ranking on flood images resembles SeaDronesSee more than VisDrone; no separate effect of glare, blur or floating debris could be measured.
- **Research question 2.** On the T4, TensorRT FP16 is 1.833–3.028 times faster than PyTorch with almost no loss in accuracy; INT8 adds little speed and compresses confidence, losing half of the operating recall for people below 8 px at the current threshold. The selected configuration is FP16 with altitude-based downscaling, on the Pareto front with the highest recall. Its most time-consuming stage is downscaling the 4K frame, not inference; by estimate, weak devices fall short exactly when flying low.
- **Research question 3.** In simulation and on three real sequences: grouping on ground coordinates is more robust than image tracking at 2 frames per second; an altitude-dependent rate reduces misses when flying low and computation when flying high; the 95% search area contains the real person when GPS is no worse than assumed; link probing loses no alert and cuts maximum latency; merging at the station reduces duplicates without dropping alerts.
