# Chapter 2. Background and Related Work

> **Draft note (remove in the final document).** English version of `docs/luan_van/chuong2.md` (21/11/2026). Citations use pandoc keys from `docs/thesis/references.bib` and are rendered author–year (APA) when the document is built. Open items: TensorRT and the radar M-of-N confirmation literature (Blackman; Bar-Shalom) still have to be looked up **[CITATION TO VERIFY]**; claims marked **[READ FULL TEXT]** rest on abstracts only (MIDDTD could not be retrieved automatically; the MDPI page blocks it); Section 2.6 follows decision #19 **[PENDING #19]**.

This chapter covers the foundations of each stage of the system and positions the thesis against existing work: object detection and the YOLO family (2.1), small-object detection (2.2), UAV imagery for search and rescue (2.3), multi-object tracking (2.4), model compression for edge devices (2.5), and the gap addressed by this thesis (2.6).

## 2.1 Object Detection and YOLO26

### 2.1.1 Task and Metrics

Object detection finds every object of the classes of interest in an image and returns, for each object, a bounding box (box for short) and a confidence score (conf). A predicted box counts as correct when its overlap with a ground-truth box, measured by intersection over union (IoU), exceeds a threshold, usually 0.5. Detector quality is commonly summarised by average precision (AP), the area under the precision–recall curve obtained by sweeping the confidence threshold from high to low; AP50 is AP at an IoU threshold of 0.5. The thesis additionally reports recall and precision at a fixed confidence threshold (0.25) as the operating point, because in rescue what matters is how many people are found at the threshold the system actually uses (Chapter 6, Section 6.3).

IoU is harsh on very small people: a box shifted by 2 px around an 8 px person has an IoU of only 0.6, and a 3 px shift already falls below 0.5, while a human annotator can hardly place a box to within 1–2 px. The thesis therefore also reports results at IoU 0.3 for people smaller than 8 px.

### 2.1.2 One-Stage Detectors and the YOLO Family

One-stage detectors predict boxes and classes directly on a feature grid, without a separate region-proposal step. The YOLO family [@redmon2016yolo] is the most widely used representative for real-time detection and comes with tools to export models to deployment formats such as TensorRT. A modern detector has three parts:

- a **backbone** that extracts features while reducing resolution over levels P1 to P5, with strides of 2, 4, 8, 16 and 32 input pixels;
- a **neck** that mixes features across levels with a feature pyramid [@lin2017fpn] and a bottom-up path (PAN), giving fine levels more semantics and coarse levels more detail;
- a **head** that predicts boxes and classes on each level.

The raw output contains several overlapping boxes for the same object, so a final non-maximum suppression (NMS) step removes duplicates.

**YOLO26** [@ultralytics2026yolo26] is the YOLO generation released by Ultralytics in January 2026 and serves as the base model of this thesis (the `s` variant, about 10 million parameters). Two properties matter here. (i) Besides the one-to-many head that requires NMS, YOLO26 has a **one-to-one** head whose output needs no NMS; according to the library documentation and source code, prediction and export still default to the one-to-many head with NMS, and all results in this thesis use that default. (ii) Its finest detection level is P3 (stride 8). Ultralytics also introduces changes to the loss and label assignment that are said to benefit small objects; the thesis does not verify this claim, since the control experiment with YOLO11 was cut for schedule reasons.

### 2.1.3 Why Small People Are Missed

Three mechanisms together make a detector miss people that are only a few pixels in size:

1. **Downsampling.** At level P3, each cell of the feature map corresponds to 8 × 8 input pixels; a 4 px person covers half a cell, and their features are mixed with the background.
2. **Resizing before the network.** The detector resizes the image so that its long side equals the input size, usually 640 px. For 4K video, people shrink six times (Chapter 1, Table 1.1).
3. **Weak training signal.** Very small boxes receive very few positive cells during label assignment, and scale augmentation removes the labels of boxes that become smaller than 2 px even though the person is still in the image (Chapter 6).

Section 2.2 and Chapter 4 discuss ways to counter each mechanism.

## 2.2 Small-Object Detection

**Larger input resolution.** The most direct remedy is to feed the image at a larger size (1280 instead of 640 px). The computational cost grows with the square of the image side.

**Tiling (slicing).** The large image is cut into overlapping tiles, detection runs on each tile at native resolution, and the results are merged. SAHI [@akyon2022sahi] packages this approach as a library that works with many detectors, both at inference and during fine-tuning; on VisDrone and xView the authors report that slicing-aided inference raises AP by 6.8%, 5.1% and 5.3% for the FCOS, VFNet and TOOD detectors, and by 12.7%, 13.4% and 14.5% when slicing-aided fine-tuning is added. By default SAHI also runs one pass on the full image to catch large objects that are cut between tiles, and merges boxes across tiles by fusing their coordinates. SAHI runs the model on one tile at a time; the thesis implements its own tiler that runs all tiles of a frame in one batch to suit the GPU and TensorRT export (Chapter 4, Section 4.3).

**A finer detection level.** Adding a head at level P2 (stride 4) lets an 8 px person cover 2 × 2 cells instead of one, at the cost of extra computation in the neck and head and of training the new layers. The thesis evaluates this option (Chapter 7, Section 7.1.3).

**Scale matching.** TinyPerson [@yu2020scalematch] shows that a mismatch in object scale between pre-training data and target data degrades features, and proposes rescaling the pre-training data to the scale of the target data (Scale Match). The general lesson is that a detector performs best in the size range it has learned.

**Resizing by flight altitude.** In UAV imagery, object size depends mainly on the capture altitude. @messmer2022adaptive resize each UAV image before detection (Adaptive Resizing) to keep the ground sampling distance (GSD) constant: the target image size is inversely proportional to altitude, assuming a fixed nadir camera. Only their self-collected POG set (10–110 m) has real altitude from flight logs; for VisDrone and UAVDT, altitude is inferred from the mean box area of a reference class, i.e. from the labels. With EfficientDet-D0, AP50 on UAVDT rises from 34.1 to 58.8 and speed improves by 2.1–2.7 times; a reduced version runs at about 16 frames per second on a Jetson AGX Xavier (TensorRT FP16). The paper does not use tiling, does not report very small objects separately and gives no confidence intervals. @ahmed2025altitude come even closer: also on SeaDronesSee, they compute the target resolution from altitude, viewing angle and person area (0.48 m²) so that a person covers about 80 px² (a side of about 9 px), round it to six levels between 640 and 3200 px without upscaling, and then tile with SAHI at 640 px and 20% overlap, so the number of tiles falls with altitude. With YOLOv5s, small-object mAP50 rises from 0.34 (640 px input) to 0.47, and the method is faster than fixed tiling (1.87 versus 0.60 frames per second, hardware not stated). They re-split SeaDronesSee train and validation data 70/20/10, report a single run without confidence intervals, and address per-frame detection only. The altitude-based downscaling of Chapter 4 belongs to the same line of work; Section 2.6 states the differences and what the thesis adds.

## 2.3 UAV Imagery and Data for Search and Rescue

**General UAV data.** VisDrone [@zhu2022visdrone] is a large UAV dataset captured in many cities, with labels for image detection, video detection, and single- and multi-object tracking. Most people in VisDrone are very small (Chapter 6, Table 6.2), which makes it the main source for learning small people seen from above. On the other hand, VisDrone shows dry urban scenes without water.

**People in water.** SeaDronesSee [@varga2022seadronessee] is the first large UAV dataset of swimmers in open water, with detection, single-object and multi-object tracking parts, captured at many altitudes and viewing angles, together with flight metadata (position, altitude, camera angles). AFO [@gasienica2021afo] contains people and floating objects (boards, boats, buoys) on water seen from drones, built for water rescue.

**Disasters.** C2A [@nihal2024c2a] pastes human figures into real UAV images of disasters to obtain data of people partly hidden by rubble or flood water; the authors report that models trained with C2A perform better on disaster scenes, especially when combined with general human data.

**Surveys.** Surveys of aerial person detection for search and rescue [@zhang_sarsurvey] and of maritime search and rescue [@martinez2025maritime] review traditional and deep-learning methods and real and synthetic data. Both name the same two difficulties that this thesis faces: people seen from the air are small, sparse and faint, which weakens their features [@zhang_sarsurvey], and the small size of a person against a vast water surface makes detection hard, while labelled data at sea are costly to collect [@martinez2025maritime].

**The data gap.** Among the sources searched while preparing this thesis (Kaggle, Hugging Face, Zenodo, Roboflow), no public dataset of real UAV flood imagery with person labels suitable for evaluation was found. This is why the thesis labels a small flood set for evaluation only (Chapter 6, Section 6.2.2) and trains on a combination of the public datasets above.

## 2.4 Multi-Object Tracking

**Tracking by detection.** Current multi-object trackers associate the detections of a new frame with existing tracks. ByteTrack [@zhang2022bytetrack] associates by box overlap between the position predicted by a Kalman filter and the new detections, in two rounds: high-confidence boxes first, then low-confidence boxes, so that occluded detections are not discarded. These methods are designed and evaluated on pedestrian video at full frame rate (MOT17, MOT20), where a person moves only a few pixels between two frames.

**Camera motion compensation.** When the camera moves, the image position of every object drifts with it. BoT-SORT [@aharon2022botsort] estimates the camera motion between two frames from the images themselves and shifts the tracks before association. On a UAV this shift can be computed from telemetry instead of from the images (Chapter 4, Section 4.6.1).

**Geolocation and association in world coordinates.** Mapping an image detection to ground coordinates with a pinhole camera model and the camera's position and orientation is basic projective geometry [@hartley2004mvg]. @rudol2008human geolocated people detected from a UAV (colour and thermal imagery) on a map for search and rescue. More recently, @wang2025middtd project each detection onto a flat ground plane from the drone's GPS position, altitude and the pitch and yaw of its camera payload, and associate tracks across frames in these world coordinates together with appearance cues; on their dataset (MIDDTD: mostly vehicles, a few people, 50–600 m altitude, 30 frames per second), adding world coordinates reduced identity switches for all six trackers tested, for example from 1198 to 1095 for ByteTrack. Their trackers process the video frame by frame; the paper does not study processing only a few frames per second, and it has no confirmation rule for raising alerts. Confirming a track once it has been associated with a detection at least M times in N consecutive looks (M-of-N logic) is a standard confirmation rule in target tracking [@mathworks2026mot].

## 2.5 Edge Devices and Model Compression

**Edge devices.** Embedded computers that a UAV can carry, such as the NVIDIA Jetson family, have a small GPU and run at a few tens of watts or less; their speed depends on the power mode and drops as the device heats up. Measuring speed properly on such a device requires fixing the power mode, discarding warm-up runs, measuring long enough and reporting percentiles (p50, p95) rather than only the mean.

**TensorRT and quantisation.** TensorRT [@nvidia2026tensorrt] compiles a model into an engine for one specific GPU: it fuses layers, selects the fastest kernels and lowers numerical precision. FP16 (16-bit floating point) usually loses almost no accuracy; INT8 (8-bit integers) is faster still but needs calibration data to measure activation ranges, and can hurt small objects most because their weak signals are quantised coarsely. Engines are not portable by default: an engine is compatible only with the type of device and the TensorRT version used to build it, so an engine built on a T4 GPU does not run on a Jetson. During this work, TensorRT 11 changed INT8 quantisation (explicit quantisation only) and INT8 export no longer built on the T4; the thesis uses TensorRT 10 (Chapter 6, Section 6.5).

**Measuring without the target device.** When the target device is not available, publications usually report speed on another GPU and compare only in relative terms, or cite the vendor's benchmark tables. The thesis does both and adds a device timing simulation (Chapter 4, Section 4.8.3), always labelled as an estimate.

## 2.6 Research Gap

[PENDING #19: written according to the current proposal. @messmer2022adaptive and @ahmed2025altitude read in full on 10/11; @wang2025middtd read in full on 26/11 (Sections 3.3 and 4.1, Tables 1 and 2).]

The sections above leave three gaps that this thesis addresses:

1. **No size-aware evaluation of person detection in UAV flood imagery.** Existing rescue datasets show urban scenes, open sea, or disasters with pasted people; there is no labelled set of real flood images, and results are usually reported as overall AP rather than by person size, although misses concentrate on people of a few pixels.
2. **Confirming people when only a few frames per second are processed.** Common trackers are designed for full frame rates. On an edge device that processes only a few frames per second while the UAV flies fast, a person moves hundreds of pixels between two processed frames. Association in world coordinates has been used for tracking vehicles from drones at full frame rate, but no work was found that measures it against image-space association at such low rates, for confirming people before a rescue alert.
3. **Using flight data at several stages of one edge system.** Altitude-based resizing has been proposed and measured for detection accuracy and speed. The thesis places it in a pipeline driven by per-frame telemetry, measures its effect on accuracy by person size and on the number of tiles a weak device must process at the same time, and uses the same telemetry for geolocation and confirmation.
