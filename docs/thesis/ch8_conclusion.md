# Chapter 8. Conclusion and Future Work

> **Draft note (remove in the final document).** English version of `docs/luan_van/chuong6.md` (24/11/2026). This chapter introduces **no new numbers**: each answer summarises Chapter 7, and any number is copied from a Chapter 7 table, cited by table number. **[PENDING DECISION #19]** marks the contributions paragraph, to be finalised in the form the advisor approves.

## 8.1 Answers to the Research Questions

**Research question 1: how accurately can small people be detected in UAV images of flood areas, and how much does each technique help?**

Training data matter most. Fine-tuning on urban UAV images (VisDrone) strongly improves the detection of small people; adding images of people in water (AFO) keeps swimmers without losing much on small people; mixing in disaster images with pasted large people (C2A) directly costs small people (Chapter 7, Section 7.1.2). On medium-resolution images, changing the architecture (a P2 head) and tiling help very little compared with data (Section 7.1.3). Models fine-tuned for small people are weak with large people; on 4K images with real flight altitude, altitude-based frame downscaling compensates for this weakness (Section 7.1.4). Below about 6–8 px, no model in this thesis detects people reliably; this is the lower limit of detection, and the remaining remedy is to fly lower. On the self-labelled flood test set the result contradicted the prediction: fine-tuning significantly raises recall for people below 16 px but not AP50, because it produces more false alarms; the base model keeps the highest AP50 (0.269 versus 0.148 for the main model; 0.286 versus 0.233 when one unlabelled frame is excluded, Tables 7.3 and 7.4) and is clearly stronger with large people. The ranking on flood images resembles that on the maritime set more than the urban set, so choosing a model on urban images is not enough. The separate effect of glare, blur and floating debris could not be measured on 188 frames (Sections 7.1.1, 7.1.5 and 7.1.6).

**Research question 2: which configuration reaches the required processing rate while keeping the highest recall?**

On a T4 GPU with TensorRT, FP16 compression is 1.833–3.028 times faster than PyTorch with almost no loss in accuracy; INT8 adds little speed and compresses confidence downwards, so at the same threshold it loses half of the operating recall for people below 8 px although AP is almost unchanged (Tables 7.13 and 7.14). The selected configuration is FP16 with altitude-based downscaling: on the Pareto front with the highest recall, and above the ceiling of 8 frames per second from research question 3 on the T4 (Table 7.15). Altitude-based downscaling both increases accuracy and reduces the tiles of a 4K frame from 32 to 6; the most time-consuming stage after that is downscaling the frame on the CPU, not inference. By estimate from the device timing simulation, the Jetson Orin NX and Orin Nano Super process only 4 frames per second at 30–50 m, exactly when the highest rate is needed (Table 7.16); at high altitude, 2 frames per second are enough for every device.

**Research question 3: how many false alarms and misses does the system produce, how long do alerts take to reach the station, and which confirmation method tolerates GPS error and camera motion?**

When only a few frames per second are processed, grouping detections on ground coordinates is more robust than tracking in the image, both on three real sequences with telemetry and in simulation with GPS noise; telemetry-based camera motion compensation only saves image tracking when GPS is very stable between two frames (Section 7.3.2). No single rate is enough for every altitude; computing the rate from altitude and speed reduces misses when flying low and computation when flying high (Section 7.3.1). The 95% search area contains the real person when GPS is no worse than assumed; taking GPS accuracy from the receiver keeps this true when GPS degrades mid-flight, and self-calibration of the compass bias reduces false splits at high altitude (Section 7.3.3, simulation). The outbox with link probing loses no alert in any scenario of packet loss and outage, including burst loss; the remaining delay is the length of the outage itself (Section 7.3.4, simulation). Merging at the ground station reduces duplicate alerts without dropping any (Section 7.3.5). Most results for research question 3 come from simulation; the part on real video rests on three SeaDronesSee sequences.

**Cross-cutting argument.** Flight data the UAV already has help in all three stages: choosing the image scale for detection, reducing the computation on the edge device (from 32 to 6 tiles on a 4K frame), and confirming people when only a few frames per second are processed (Section 7.4). The same dependence is also the system's weak point: when telemetry is poor or absent, as in the flood test set, these benefits shrink or disappear.

## 8.2 Contributions

[PENDING DECISION #19: to be written in the form the advisor approves; the current version follows Chapter 1, Section 1.4.]

1. A self-labelled UAV flood evaluation set and an evaluation by person size with confidence intervals by video: 188 frames from 9 sources, 509 people (88 below 8 px, 205 between 8 and 16 px), locked with a hash before any model was run.
2. Altitude-based frame downscaling in the edge pipeline, measuring accuracy by person size and computational cost together (a direction with prior work, Chapter 2, Section 2.2).
3. An analysis and measurement of ground-plane confirmation versus image-space tracking when few frames are processed, for search and rescue.

In addition: a complete system from video to map, simulators for flight, network and device timing, and open-source code with automated tests.

## 8.3 Limitations

- **Small flood dataset.** The flood test set has 188 frames from 9 sources, so the intervals by source are wide; public flood videos have no flight altitude, so altitude-based downscaling could not be evaluated on flood scenes.
- **Flood labels made by one person, with a known error.** One frame with a clearly visible crowd has no labels; this was found after locking, was not corrected, and is reported with a sensitivity analysis excluding that frame (Section 7.1.1). The planned relabelling was not done; there are only two same-day labelling passes over 37 frames, in which 58 of 72 people match and the glare and floating-debris tags agree poorly. There are no ignore regions, and one source holds almost half of the people.
- **No real flights and no edge device.** Speed was measured on a T4 GPU and is only compared relatively; weak devices are estimated by simulation. Confirmation, geolocation and alert delivery are mostly evaluated in simulation; the real-video part consists of three maritime sequences, with the UAV almost hovering or the camera tilted.
- **The simulation can ignore exactly the phenomenon that decides the result.** An example is in Section 7.3.5: counting people by group is better in simulation but worse on real video, because the simulation does not split one person into several clusters when GPS drifts.
- **One seed** for most training experiments; no comparison across model generations (the YOLO11 experiment was cut).
- **Geometric assumptions:** the camera looks straight down, the water surface is flat and the lens is undistorted; projection with the gimbal angle exists but is not yet more stable on real video.
- **Data licences:** the flood videos are copyrighted, so only labels and sources are published; the AFO licence must be checked again before a model is released.

## 8.4 Future Work

- Measure on a real Jetson device, including power and thermal throttling, and recalibrate the device timing simulation with those measurements.
- Extend the flood set, especially with video that has telemetry, to evaluate altitude-based downscaling on flood scenes.
- Reduce the false alarms of fine-tuned models on flood images (the main reason AP50 did not rise although small-person recall did): choose a confidence threshold for flood scenes on a separate labelled flood set, or add flood images without people to the training data as negative examples.
- Measure frame resizing on the GPU on the edge device itself (implemented and tried preliminarily on the development machine, Section 7.2.1), or decode video at a lower resolution when flying low, because this is the slowest stage of the selected configuration and where weak devices fall short (Section 7.2).
- If INT8 is needed: choose a separate confidence threshold for the compressed model on a validation set, and calibrate INT8 with images containing water.
- Combine thermal and colour images for night time and occluded people.
- Coordinate several UAVs and split the search area; prioritise incidents by urgency.
- The remaining proposals in the improvement list (for example reading GPS accuracy from real flight logs). Two ways of reducing computation were tried and dropped: YOLO26's NMS-free output head (loses recall, not faster in PyTorch) and reusing results of unchanged tiles when the UAV hovers (loses recall because swimmers still move).
