# Chapter 6. Data and Experimental Setup

> **Draft note (remove in the final document).** English version of `docs/luan_van/chuong4.md` (21/11/2026). Numbers come from `data/processed/*/stats*.json` and `docs/results/` (`flood_truoc_khoa.md`, `sds_det.md`, `afo_E1_E2.md`, `E2c.md`, `E2e.md`, `visdrone_tiled_vs_sahi.md`, `rq3_*.md`), `docs/LABELING.md`, `docs/TECHNICAL.md` §5, 13–16. Items marked **[UPDATE AFTER LOCK]** are filled from `runs/flood/bang.md` and `runs/flood/relabel_agreement/` once the flood test set is locked: frame and source counts, person counts, size distribution, empty frames, relabelling agreement, manifest hash. **[UPDATE: seeds]** depends on whether extra seeds are trained.

This chapter describes the data used for training and evaluation, the metrics, the experiments that answer the three research questions, and the computing environment. Its purpose is that every number in Chapter 7 can be read correctly and reproduced: which set it was measured on, under which definition, and with which configuration.

## 6.1 Training Data

### 6.1.1 Public Datasets

No UAV flood dataset with person labels large enough for training has been published. The thesis therefore combines public datasets, each covering one aspect that flood scenes need: very small people seen from above, people in water, and larger people against disaster backgrounds (Table 6.1).

**Table 6.1.** Training data after conversion to a single person class.

| Dataset | Content | Training part | Role |
|---|---|---|---|
| VisDrone2019-DET [@zhu2022visdrone] | Urban UAV images, many very small people; no water | 6,471 images, 106,396 people | Small people seen from above |
| AFO [@gasienica2021afo] | Swimmers, boards and boats on lakes and sea, seen from drones | 2,787 images, 22,272 people | People in water |
| C2A [@nihal2024c2a] | Real disaster images (floods, fires, collapsed buildings) with pasted people | 6,129 images, 215,821 people | Experiment adding larger people (training only) |
| HydroVigilance | Swimmers with only the head above muddy river water | 627 training, 179 validation images | Converted but not used (experiment cut for time) |

The validation set used during training (to select the best weights) is VisDrone val plus AFO val: 887 images.

### 6.1.2 Conversion to a Single Person Class

The task only needs to know whether a person is present, so every dataset is converted to a single class in YOLO format. VisDrone separates standing or walking people (`pedestrian`) from sitting or lying people (`people`); both need rescue and are merged. People riding bicycles or motorbikes are labelled as vehicles in VisDrone and are therefore absent; this is a recorded limitation. Regions that VisDrone marks as impossible to label (`ignored regions`: crowds, blurred areas) are kept as **ignore regions**: a detection inside one counts neither as correct nor as a false alarm.

The person class is selected **by name**, not by class index, because every dataset numbers its classes differently (AFO has six classes: person, board, boat, buoy, sailboat, kayak); a wrong index would make the model learn the wrong class without any error. After conversion, the VisDrone labels were checked against the original labels image by image before training, because finding a label error after training wastes a run of many GPU hours.

### 6.1.3 Person Size Distribution

Person size is measured by the **short side** of the bounding box and split into four groups: below 8 px, 8–16 px, 16–32 px and above 32 px. This is finer than the COCO convention (where "small" means anything below 32 × 32 px), because most people in UAV flood imagery fall into what COCO calls small (Chapter 1, Table 1.1).

**Table 6.2.** Number of people by size group in VisDrone.

| Split | Images | People | < 8 px | 8–16 px | 16–32 px | > 32 px |
|---|---|---|---|---|---|---|
| train | 6,471 | 106,396 | 22,952 | 43,596 | 31,001 | 8,847 |
| val | 548 | 13,969 | 3,306 | 6,364 | 3,793 | 506 |
| test-dev | 1,610 | 27,382 | 12,088 | 9,868 | 4,339 | 1,087 |

By contrast, most people in AFO and SeaDronesSee are above 32 px (Section 6.2.1). C2A has small images (long side about 430 px), so training at 1280 px enlarges them about three times, making C2A people "larger" than VisDrone people.

## 6.2 Evaluation Data

### 6.2.1 Public Evaluation Sets

**Table 6.3.** Public evaluation sets.

| Set | Images | People | Characteristics | Used for |
|---|---|---|---|---|
| VisDrone val | 548 | 13,969 | Urban, very small people; 76 videos | Comparison with other work; biased because weights are selected on it |
| VisDrone test-dev | 1,610 | 27,382 | As above, not used for weight selection | Main table for small people |
| AFO test | 514 | 6,511 | People in water; images from 1280 × 720 to 3840 × 2160 | People in water, same source as the training part |
| AFO test, shared locations removed | 363 | | Two image groups sharing scenes with the training part removed | Checking whether gains come from shared scenes |
| SeaDronesSee val [@varga2022seadronessee] (detection version) | 317 | 1,055 | 11 4K videos of swimmers at sea; median short side 65 px; 976 people above 32 px | People in water, **independent** of the training data; larger people |

For SeaDronesSee, one frame in 15 is taken (0.5 s at 30 frames per second) to reduce near-duplicates; "swimmer" and "swimmer with life jacket" count as people, boats are dropped. The video part of SeaDronesSee (the multi-object tracking version, SeaDronesSee-MOT) also provides a track ID for each person and real flight metadata (GPS position, altitude, heading, gimbal angles), used for research question 3 (Section 6.4.3).

### 6.2.2 Self-Labelled Flood Test Set

The flood test set is the **main set** for conclusions about flood scenes and one of the contributions of this thesis. VisDrone shows dry cities, AFO and SeaDronesSee show clear lakes and sea, and C2A is composited; none of them has flooded roofs, muddy water, floating debris and people clinging to floating objects as in real floods.

**Sources.** UAV videos of floods with people, taken from YouTube and online news, covering floods in Vietnam and abroad. Each video is recorded with its source (link, download date, resolution, copyright note). Because most videos are copyrighted, the thesis publishes only the labels and the sources, not the images.

**Frame extraction.** Frames from the same video are at least 2 seconds apart; a frame that is a near-duplicate of any already kept frame of the same video (dHash distance below 10 bits) is dropped; each video contributes at most 30 frames, spread evenly over time; blurred frames and frames that do not show a flood are then removed by eye. The 30-frame cap keeps any single video from dominating the results, and the time gap prevents nearly identical consecutive frames from making confidence intervals falsely narrow. About 10–20% of frames without people are kept to measure false alarms (waves, debris, reflections).

**Review before labelling.** Initially there were 212 frames from 10 videos. Two checks were done before labelling, while the composition of the set could still change:

- *Leakage against the training data*: the dHash of every frame was compared with the 16,193 images of the five training sets (VisDrone train, AFO train, HydroVigilance train and val, C2A train). At a threshold of 5 bits there was no near-duplicate and no shared video. At a looser threshold of 10 bits there were 37 pairs; inspection by eye showed that none shared a scene, only a similar light and dark layout.
- *Duplicate sources inside the set*, which hashing cannot detect: two videos with different names turned out to be footage from the San Angelo (Texas) police of the same flood (same logo and caption in every frame), 54 frames in total, above the 30-frame cap per source. The two videos were merged into one source, keeping 15 frames of each, spread evenly over time. Another video (Washington) was most likely filmed from a helicopter rather than a UAV; it was kept, since its oblique view resembles a UAV view, and this is recorded as a limitation.

After the review the set had **188 frames from 9 sources**, with 30, 30, 29, 23, 23, 22, 15, 8 and 8 frames per source. Four of the ten videos are below 1080p (two at 480p and two at 720p, 74 frames in total); they were kept because removing them would leave only 114 frames, below the minimum of 150 frames set at the start. People in these videos cover fewer pixels than they would at the same altitude in 1080p.

**Labelling rules.** Labels are drawn in CVAT with two labels: `person` (one person) and `ignore` (a region that cannot be labelled). A person is labelled when certainly a person, even if only partly visible: wading, swimming, clinging to a floating object, standing on a roof, sitting in a boat; a person of only a few pixels if recognisable from shape, shadow or motion in neighbouring frames. Reflections, cast shadows and people inside vehicles or buildings without a visible body are not labelled. Objects that may or may not be people are covered by an ignore region. Boxes tightly enclose the visible part, without guessing submerged parts; people below 16 px are drawn at 300–400% zoom, because an error of 1–2 px at that size is enough to push IoU below the threshold. Each box has two attributes: *partly submerged* (water covering from the knees up) and *occluded* (another object covering about a third of the body or more). Each image has four nuisance tags: *glare* (sun glare large enough to hide a person), *weather* (rain, fog, darkness), *blur* and *floating debris* (debris or objects about the size of a person); the tags are used to measure recall by nuisance type (research sub-question RQ1e).

**Quality control and locking.** The plan was to review all labels at 100% zoom after every 50 frames and, at least two days later, to label 20 frames again without looking at the earlier labels. Because labelling ran late, the second labelling was not done. Two videos (Texas and Hue, 37 frames, 72 people) were, however, labelled twice on the same day in separate CVAT tasks; the first labelling is the one evaluated. Matched at IoU 0.5, 58 of the 72 people were found in both labellings (61 at IoU 0.3), 14 only in the evaluated labelling and 10 only in the other; the median IoU of matched boxes was 0.738 and the median largest edge offset 3.890 px. Agreement was lower for attributes (partly submerged 0.500, occluded 0.655) and for some tags (glare 0.649, floating debris 0.595, blur 0.892) (`docs/results/flood.md`). Because both labellings were made on the same day, this is only an indication of annotator consistency, not the planned measurement. When labelling was complete, all images, labels, ignore regions, attributes and tags were **locked** with a SHA-256 manifest on 24 November 2026 (566 files); from then on labels are not edited and frames are neither added nor removed, and the evaluation tool refuses to run if a hash differs. Label errors found after locking are recorded as limitations, not silently corrected: one frame with a clearly visible crowd and no labels was found after evaluation (Section 7.1). All parameters (confidence threshold, target person size for downscaling, number of sightings for confirmation, …) are chosen on other datasets before running on the flood set, and each final configuration runs on it only once. No model is used to pre-label the flood set, so the labels are not biased towards what a model already detects.

**Table 6.4.** Statistics of the flood test set after locking (`docs/results/flood.md`). People are binned by the short side of the box.

| Video | Frames | Resolution | People | < 8 px | 8–16 px | 16–32 px | > 32 px | Frames without people |
|---|---|---|---|---|---|---|---|---|
| duvall-2HE-TIf4Lk0 | 15 | 854×480 | 0 | 0 | 0 | 0 | 0 | 15 |
| hue-BIxBHs0dZ3s | 22 | 1920×1080 | 51 | 2 | 27 | 21 | 1 | 7 |
| hue-short-Ak83K9FSBTY | 23 | 1080×1920 | 35 | 4 | 5 | 16 | 10 | 9 |
| mientrung-short-A-i9t2kJMlU | 23 | 1080×1920 | 0 | 0 | 0 | 0 | 0 | 23 |
| nidarx-flood-1 | 8 | 1920×1080 | 241 | 22 | 116 | 81 | 22 | 0 |
| sanangelo-police | 15 | 1280×720 | 5 | 0 | 0 | 0 | 5 | 13 |
| texas-xBvDRr6vy-k | 15 | 1280×720 | 21 | 3 | 4 | 3 | 11 | 7 |
| thainguyen-6W-QUHCh4ok | 29 | 854×480 | 98 | 57 | 41 | 0 | 0 | 20 |
| vn-tuoitre-1 | 8 | 1920×1080 | 5 | 0 | 3 | 2 | 0 | 6 |
| washington-D4xd0xNP9Gg | 30 | 1920×1080 | 53 | 0 | 9 | 13 | 31 | 9 |
| **Total** (9 sources, 10 videos) | 188 | | 509 | 88 | 205 | 136 | 80 | 109 |

Across the set, 70 people are marked partly submerged and 68 occluded; 42 frames are tagged glare, 1 weather, 54 blur and 117 floating debris. No ignore region was drawn. One source (nidarx-flood-1) contributes 241 of the 509 people in only 8 frames, and two videos contain no person at all, so pooled numbers are dominated by a few sources; this is one reason for the source-level bootstrap below.

The flood test set has no flight altitude (videos downloaded from the internet carry no telemetry), so altitude-based downscaling is evaluated only on SeaDronesSee and in simulation, not on this set.

## 6.3 Metrics

### 6.3.1 Detection Accuracy

The evaluation tool was written for this thesis instead of using the mAP printed by the training library, because that number is not broken down by person size, does not support ignore regions and has no confidence interval. The conventions are fixed for all experiments:

- **AP50** (average precision at IoU 0.5), 101-point interpolation, computed from predictions at a confidence threshold of 0.001 with at most 1,000 boxes per image.
- **By person size group** (Section 6.1.3), next to the "all" group. A single overall number is dominated by large (easy) people; the thesis cares about small ones.
- **IoU 0.3 in addition to IoU 0.5.** For a 6 px person, an error of 1–2 px already pushes IoU below 0.5 although the detection is in the right place; in rescue, the right place is enough.
- **Operating recall and precision** at a confidence threshold of 0.25. AP summarises all thresholds, while a deployed system must choose one; the two numbers answer different questions.
- **Ignore regions**: predictions inside ignore regions (VisDrone, flood set) are not counted as false alarms.

The tool is checked with hand-computed examples and against the training library's number for the base model: the two differ by less than 1% with ignore regions turned off.

### 6.3.2 Uncertainty

**Bootstrap confidence intervals.** Every metric comes with a 95% confidence interval from 1,000 bootstrap resamples: images (not boxes, since people in the same image share lighting and altitude) are drawn with replacement, the metric is recomputed, and the 2.5th and 97.5th percentiles are taken.

**Resampling by video** (cluster bootstrap). Images from the same video share scene and altitude, so the model's errors on them are correlated; treating them as independent makes confidence intervals falsely narrow. For SeaDronesSee (11 videos) and the flood set (9 sources), the bootstrap draws whole videos: a video drawn k times contributes all its images k times. For example, on VisDrone val (548 images from 76 videos), the AP50 confidence interval of the same configuration is 0.034 wide when resampling images and 0.061 wide when resampling videos.

**Comparing two configurations with a paired bootstrap.** Two overlapping confidence intervals do *not* mean that two configurations are equal, because both find the same images hard. The paired bootstrap uses the same resample for both configurations and takes the difference:

```
repeat 1,000 times:
    draw n images (or n videos) with replacement from the evaluation set, the same sample for A and B
    difference = metric of B on the sample − metric of A on the sample
95% confidence interval of the difference = 2.5th and 97.5th percentiles
```

A difference is significant at the 5% level when its confidence interval does not contain 0. For example, on VisDrone val the self-written tiler and the SAHI library have individual AP50 intervals of 0.437–0.470 and 0.444–0.477, overlapping almost entirely, yet the interval of their difference is −0.011 to −0.003: the self-written tiler is slightly but consistently worse.

Two cautions for reading Chapter 7. First, when many pairs are compared at once (five size groups, two metrics, several configurations), some pairs will appear "significant" by chance; the main conclusions rest on the "all" group and the small-person groups, fixed in advance. Second, the bootstrap captures the uncertainty due to the choice of images; the uncertainty due to random initialisation during training (seed) is a different source, measured by retraining with other seeds (Section 6.5).

### 6.3.3 System Metrics

Research question 3 measures the whole chain after detection: confirmation, geolocation and alert delivery. Each alert is matched to the nearest real person (the person's position at alert time) if within 10 m (`r_eval`).

**Table 6.5.** System metrics.

| Metric | Definition |
|---|---|
| Miss rate | Number of real people without any alert between entering the frame and 10 s after leaving it, divided by the number of people |
| False alarms per minute | Number of alerts not matching any real person, divided by flight duration (minutes) |
| Wrong merges | Number of alerts matching two or more real people |
| Wrong splits | Number of real people receiving two or more alerts |
| Time to alert | Time of the first alert minus the time the person enters the frame |
| Position error | Distance from the first alert to the real person; also the share of people inside the alert's own error radius (1σ) and inside the 95% search area |
| Delivery delay | Time the ground station acknowledges the coordinate message minus the time the alert was created |
| Loss rate | Number of alerts that never reach the ground station, divided by the number of alerts |
| Bytes per alert | Total bytes sent (including resends) divided by the number of alerts |

This definition has one limitation: when two people stand closer than 10 m, every alert about them counts as a wrong merge, even when the system alerts each person correctly.

### 6.3.4 Speed

Speed is measured **per stage** of the pipeline (tiling, inference, box merging, geolocation, confirmation) with an interval timer, separate from the pipeline's simulation clock (Section 6.5). The main result is the **recall versus processed frames per second** curve, with the 2 frames per second level marked, showing how much accuracy each configuration trades for how much speed. Times measured on the development machine are used only to compare configurations on the same machine, never as edge-device figures.

## 6.4 Experiments

### 6.4.1 Research Question 1: Detecting Small People

All models use YOLO26s pre-trained on COCO as the base model. Table 6.6 defines the short codes used in the tables of Chapter 7.

**Table 6.6.** Experiments for research question 1.

| Code | Description | Question it answers |
|---|---|---|
| E0 | Base model, images resized to 640 px | Starting point when used as usual |
| E1 | Base model, 1280 px images | How much input resolution helps |
| E2 | Fine-tuned on VisDrone | How much fine-tuning on UAV images helps compared with the COCO model |
| E2c | Fine-tuned on VisDrone and AFO (**main model**) | Whether adding people in water keeps performance on water scenes |
| E2e | As E2c, plus C2A | Whether adding larger people fixes the weakness with large people |
| E3 | As E2c, plus a P2 detection head | Whether a higher-resolution detection level helps very small people, and whether it is worth the cost |
| E4 | Main model with 640 px tiling, 20% overlap | Whether tiling helps when the image is really large |
| | E4 with altitude-based downscaling | Bringing people to the size the model handles best, using flight altitude |
| E5 | As E2c but with YOLO11s | Whether results depend on the model generation. **Not run** (cut for time); recorded as a limitation |
| E6 | Images downscaled to many levels; recall versus pixels on the person | How high the UAV can fly while people remain detectable |

**Training.** 1280 px images, batch size 8, 55 epochs (E2: 60 epochs), seed 0, the library's default augmentation except vertical flipping (enabled, since aerial images have no fixed up and down). Images are kept at 1280 px because at 640 px the random downscaling augmentation removes the labels of many very small people (up to 26.9% of labels when downscaling by 0.5 on VisDrone val), teaching the model that they are background. The best weights are selected on VisDrone val plus AFO val; the main table for small people therefore uses VisDrone test-dev.

**Evaluation.** Full image at 1280 px, except for tiled configurations. Tiling uses the self-written tiler: the model runs in batches over all tiles of a frame, boxes are shifted back to original image coordinates and duplicates in overlapping areas are merged; it was compared with the SAHI library by paired bootstrap (Section 6.3.2). Altitude-based downscaling computes the expected number of pixels of a 0.5 m person seen from above from the altitude and the camera's field of view, then downscales the frame so that a person covers about 10 px before tiling (Chapter 4, Section 4.4).

### 6.4.2 Research Question 2: Speed on the Edge Device

No Jetson device was available. Research question 2 is answered in two steps. First, measurements on a Kaggle Tesla T4 GPU with TensorRT at two compression levels, FP16 and INT8 (INT8 calibrated on 640 px tiles cut from validation images), for the best configurations of research question 1: accuracy after compression, time per stage, frames per second. The T4 shares the NVIDIA platform and TensorRT with the Jetson, so the **ranking** of configurations is meaningful; absolute frames per second do not transfer. Second, a **device timing simulation**: the pipeline runs on the development machine but charges processing time according to a device profile (time per tile, per full-image pass, fixed overhead), drops frames that arrive while the device is busy, and sends alerts when processing ends. Profiles for the Jetson Orin Nano Super, Orin NX and AGX Orin are estimated from Ultralytics' published YOLO26 benchmarks and calibrated with the T4 measurements. Every number from the simulation is shown in separate tables and called an estimate.

### 6.4.3 Research Question 3: Confirmation, Geolocation and Alert Delivery

Research question 3 requires knowing where and when real people are, which flood videos downloaded from the internet cannot provide. Two sources are used:

- **Real SeaDronesSee-MOT video** with a track ID for each person and real telemetry. Used to compare confirmation methods on real data: ground-plane confirmation (the contribution), ByteTrack-based confirmation, and ByteTrack with camera motion compensation; scored in image space, with a person "eligible" when seen in at least 3 processed frames.
- **Simulation.** Simulated flights (straight or lawn-mower, constant altitude or changing mid-flight), people placed on the water (still or drifting), Gauss–Markov GPS noise (slowly drifting error with a 30 s correlation time, like real GPS), fixed compass and altitude biases, and an unreliable network (random packet loss, outages). Detection uses a simulated detector following the model's **measured recall** by person size (from E6 on SeaDronesSee), plus random false alarms. The pipeline runs the real code; the simulation replaces only the video and the detector. Each parameter combination runs with 3 seeds, reporting mean and standard deviation.

**Table 6.7.** Simulation grids for research question 3.

| Grid | Varied parameters | Sub-question |
|---|---|---|
| GPS noise and confirmation method | GPS σ 0–3 m × three confirmation methods | Ground-plane grouping or tracking |
| Why camera motion compensation fails | GPS σ × correlation time × altitude | As above |
| Flight altitude | 30–200 m × base or fine-tuned model | How many frames per second are enough, by altitude |
| Altitude-dependent rate | Altitude × views per person × altitude-based downscaling | As above |
| Altitude changing mid-flight | Altitude profile × rate | As above |
| Position error | Altitude × GPS σ × compass bias × altitude bias | How far GPS and altitude errors shift positions |
| Network | Packet loss × outages × link probing | How much outages delay alerts, and whether any are lost |
| Alert memory | Density of people × GPS σ × memory of alerted positions | How many duplicate alerts merging into incidents removes |

Common parameters unless varied: 60 s flight, 10 m/s, 2 frames per second, 4K images, 82° diagonal field of view, confirmation after 3 sightings within 5 s, 3 m grouping radius.

## 6.5 Environment and Reproducibility

**Hardware.** Training and the main speed measurements run on Kaggle (Tesla T4, 16 GB). Accuracy evaluation and simulations run on the development machine (RTX 5060 GPU under WSL2); timings on the development machine are used only for relative comparison. Training the main model takes a median of 10.0 minutes per epoch on the T4; the set with C2A takes 18.7–19.1 minutes per epoch, exceeding the 12-hour limit of a Kaggle session, so it was split into two sessions: the second session restores the optimiser state and learning-rate schedule of the first, which is equivalent to one continuous run.

**Software.** Python 3.12, PyTorch 2.14, Ultralytics 8.4.174 on the development machine; on Kaggle Python 3.13 and PyTorch 2.11; speed measurement uses TensorRT 10.16 (pinned in the notebook, because with the latest TensorRT 11 the INT8 export does not build on the T4). All library versions are pinned exactly.

**Reproducibility.** Every run writes a provenance file with the command, parameters, library versions, SHA-256 hash of the weights, device and time (Chapter 5, Section 5.4). Each experiment has its own configuration file, never edited after it has produced results. The training notebook only checks out the code at a fixed commit and calls the training script, so all logic lives in versioned code. The pipeline never reads the computer clock: time comes from frame timestamps, and every random element (GPS noise, network, retry jitter) uses a fixed seed, so a simulation re-run gives exactly the same result. The automated test suite (Chapter 5, Section 5.5) checks the metrics against hand-computed examples, the coordinate projection with pixel → GPS → pixel round trips, and the system metrics.

**Seeds.** Most training experiments have a single seed because of the GPU budget; the final configuration is trained with two more seeds if time allows, otherwise this is recorded as a limitation (Chapter 8). [UPDATE: seeds]

## Chapter Summary

The thesis trains on four public datasets and evaluates on four public sets and one self-labelled flood test set (188 frames and 509 people from 9 sources, locked with a hash before any model was run). Accuracy is measured by person size at two IoU thresholds, with bootstrap confidence intervals that resample whole videos when images are not independent, and configurations are compared with a paired bootstrap. The system stages are measured on real video with tracks and in simulations that run the pipeline's own code. Speed is measured on a T4 and simulated for Jetson devices. Chapter 7 reports the results under exactly these definitions.
