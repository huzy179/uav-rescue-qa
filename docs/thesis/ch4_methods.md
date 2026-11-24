# Chapter 4. Methods

> **Draft note (remove in the final document).** English version of `docs/luan_van/chuong3.md` §3.2–3.8 (21/11/2026); the architecture of the old §3.1 is now Chapter 3. Section numbers 4.2–4.8 match the old 3.2–3.8. Sources: `docs/TECHNICAL.md` §2, 4, 7–12, 14.6; `docs/THUAT_TOAN.md`; code in `edge/`, `ground/`, `sim/`. Numbers come from the `docs/results/` file named next to them; parameters are the defaults in `configs/edge.yaml`. Table and figure numbers are finalised at layout. Section 4.3.4 follows decision #19 **[PENDING #19]**.

This chapter describes how the system detects and geolocates people in flooded areas from a UAV: the design principles that shape all components (4.1), camera geometry and the mapping from image to ground coordinates (4.2), detection (4.3) and altitude-based frame downscaling (4.4), the processing rate (4.5), ground-plane confirmation (4.6), and alert delivery with the ground station (4.7). Section 4.8 describes the simulators used to evaluate the parts that could not be measured on a real device and flight.

## 4.1 Overview and Design Principles

The five on-board stages and the ground station were introduced in Chapter 3 (Figure 3.1). One idea runs through this chapter: **the flight data the UAV already has (altitude, GPS, heading) is fed into detection, computation and confirmation**, instead of fixed assumptions.

Three design principles matter for the evaluation in Chapter 6:

- **Every stage is an interface with a fake.** Detection, the telemetry source and the transport all have fake implementations for testing and simulation. The same confirmation, delivery and ground-station code therefore runs with the real model, with detections replayed from an earlier run, or with a simulated detector in a simulated flight.
- **Time comes from the frame, not from the computer clock.** A frame's time is its index divided by the video frame rate. Re-running the same data gives exactly the same result, including the simulated network (fixed seed), and simulations can run faster than real time. Real processing time is measured separately and only logged.
- **Every stage writes a log; metrics are computed afterwards.** The pipeline does not compute accuracy. All metrics in Chapter 7 are recomputed from the logs by separate evaluation scripts, so a metric can change without re-running the pipeline.

## 4.2 Camera Geometry and Geolocation

### 4.2.1 Camera Model

A pinhole camera **looking straight down** (nadir) at altitude h above the water is assumed. The focal length in pixels follows from the horizontal field of view (HFOV) and the image width W:

```
f = (W / 2) / tan(HFOV / 2)
```

Camera makers usually state the diagonal field of view (DFOV); for a W × H image the horizontal angle follows from `tan(HFOV/2) = tan(DFOV/2) · W / √(W² + H²)`. For an 82° diagonal camera and 3840 × 2160 video, HFOV is about 74.3° and f about 2,534 px.

The ground sampling distance (GSD) is `h / f`, so a person about 0.5 m wide covers

```
px_person = 0.5 · f / h
```

pixels: about 42 px at 30 m, 25 px at 50 m and 13 px at 100 m (Table 1.1). This number links flight altitude to detection in Section 4.4.

### 4.2.2 From Pixel to Ground Coordinates

For an image point (u, v) (u to the right, v downwards), image centre (c_x, c_y), altitude h and heading ψ of the top of the image (clockwise from north):

```
forward = −(v − c_y) · h / f          right = (u − c_x) · h / f
north   = forward · cos ψ − right · sin ψ
east    = forward · sin ψ + right · cos ψ
latitude  = UAV latitude  + north / R · 180/π
longitude = UAV longitude + east / (R · cos(UAV latitude)) · 180/π        (R = 6,378,137 m)
```

The last step is a local flat-earth approximation, accurate within a few kilometres of the UAV. The point taken from a box is the **centre of its bottom edge** (the feet of a standing person; seen from above it is close to the box centre).

The **inverse** (GPS → pixel) reverses these steps. It serves two purposes: testing (pixel → GPS → pixel must return the original point to within 0.01 px) and simulation (a person placed at known coordinates appears at a known pixel in each frame, Section 4.8).

Telemetry is usually recorded at a different rate from the video, so the value at a frame's time is **interpolated** from the two nearest samples; heading is interpolated along the shortest arc (from 359° to 1° is an increase of 2°).

### 4.2.3 Position Error

Each alert carries an **estimated position error** (1σ), computed from the person's position in the image and the altitude as the root sum of squares of independent sources (Table 4.1).

**Table 4.1.** Sources of geolocation error, where d is the ground distance from the point below the UAV to the person.

| Source | Position error | Default (standard GPS assumed) |
|---|---|---|
| UAV GPS, σ_GPS | σ_GPS | 3 m |
| Altitude, δh | d · δh / h | 2 m |
| Heading, δψ (radians) | d · δψ | 2° |
| Camera tilt, δθ | h · (1 + d²/h²) · δθ | 1° |

With standard GPS, the GPS term dominates. The ground error is two-dimensional: if each axis is normal with standard deviation σ, the distance to the true position follows a Rayleigh distribution, and a circle of radius 1σ contains only about 39% of cases. The ground station therefore draws a **95% search area** of radius

```
r_95 = √(−2 ln 0.05) · σ ≈ 2.448 σ
```

The simulation in Chapter 7 confirms this: when GPS σ is 3 m as assumed, only 0.278 of people lie within the 1σ circle, while the 95% area contains 1.000 (`rq3_geoerr.md`).

Two optional extensions use the telemetry to correct the telemetry (simulation results in Chapter 7, Section 7.3.3):

- **GPS error from the receiver's own accuracy estimate:** when the telemetry carries the receiver's horizontal accuracy, σ_GPS of an alert is taken from its value at detection time instead of a constant, so the search area grows and shrinks with GPS quality.
- **Self-calibration of compass bias:** when the UAV flies straight fast enough, the direction of travel computed from two GPS fixes is an independent measurement of the heading; the median difference (compass heading − direction of travel) over several straight segments estimates a fixed compass bias, which is subtracted before geolocation.

The nadir assumption remains the default. A general projection for a tilted gimbal is implemented (a ray from the camera centre through the pixel, rotated by the tilt angle and intersected with the water surface), with an inverse and round-trip tests, but on real video it did not give more stable positions overall (`georef_pitch.md`), so it remains optional.

## 4.3 Person Detection: Fine-Tuning and Tiling

### 4.3.1 Model and Fine-Tuning Data

The model is YOLO26s (Ultralytics 8.4.174). YOLO26 has two prediction heads: a one-to-many head that needs non-maximum suppression (NMS) and a one-to-one head whose output needs none; the thesis uses the library default, the one-to-many head with NMS, for both PyTorch and TensorRT runs, so the two are directly comparable. The model is **fine-tuned** from COCO weights with a single class, person, at an input size of 1280 px. The fine-tuning data combines two complementary sources: VisDrone (very small people seen from above, urban scenes) and AFO (people in water). This model (experiment E2c) is the main model of the thesis; the reasons and the alternatives tried (a P2 head, adding the C2A disaster images) are in Chapter 7, Section 7.1.2.

### 4.3.2 Batched Tiling

A YOLO model resizes the image to its input size before processing. Reducing a 3840 px frame to 640 px divides it by 6: a 25 px person shrinks to about 4 px and nearly disappears. **Tiling** keeps the native resolution: the frame is cut into 640 × 640 tiles overlapping by 20%, and the model runs at an input size of 640 so that one image pixel is one network input pixel. The number of tiles along a side of length L is

```
n = ⌈(L − 640) / 512⌉ + 1
```

so a 3840 × 2160 frame has 8 × 4 = 32 tiles. The last tile in each row and column is aligned with the image border.

Unlike the SAHI library, which runs the model on one tile at a time, the thesis uses **its own tiler that runs all tiles in one batch**: the GPU processes many tiles at once, and the model can be exported to TensorRT with a dynamic batch size (the number of tiles changes when the frame is downscaled, Section 4.4).

### 4.3.3 Merging Boxes Across Tiles

A person in the overlap between two tiles yields two near-identical boxes; a person at a tile edge may yield a full box in one tile and a half box in the neighbouring tile. Boxes are mapped back to original image coordinates and merged:

```
sort boxes by confidence, highest first;
repeat: keep the highest remaining box; drop every remaining box whose IoS with it > 0.5
IoS = intersection area / area of the smaller box
```

IoS (intersection over the smaller box) is used instead of IoU because a half box lies entirely inside the full box, giving an IoS close to 1 but an IoU of only about 0.5. Merging **keeps the highest-scoring box** rather than fusing coordinates as SAHI does: coordinate fusion was tried and dropped, because one large low-score box covering a crowd turned each person's box into a box of the whole group. In a paired bootstrap on VisDrone val, the tiler is 0.006 AP50 below SAHI (confidence interval −0.011 to −0.003) but slightly better for people below 8 px (`visdrone_tiled_vs_sahi.md`; Chapter 7, Table 7.8).

### 4.3.4 Confidence Threshold

The pipeline keeps boxes with conf ≥ 0.1, lower than the 0.25 used for operating recall in Chapter 7. The low threshold reduces misses; the extra false alarms are filtered by confirmation (Section 4.6), because false alarms rarely recur at the same ground position over several frames. A separate threshold per box size was tried and did not help (`conf_by_size.md`).

## 4.4 Altitude-Based Frame Downscaling

### 4.4.1 Motivation

The fine-tuned model has learned mostly small people: on SeaDronesSee downscaled to several levels, it detects people of about 6–23 px well but drops sharply for people above 45 px (`e6_sds_pilot.md`; Chapter 7, Table 7.2). When the UAV flies low, people grow into exactly the range where the model is weak, and tiling at native resolution makes them even larger. On 4K SeaDronesSee, native-resolution tiling gives a much lower AP50 than running on the full image (0.235 versus 0.468, `scale_by_altitude.md`).

### 4.4.2 Method

Before tiling, the expected person size in pixels is estimated from the altitude in the telemetry (Section 4.2.1), and the frame is downscaled so that people reach a target size p* at which the model performs well:

```
px_expected = 0.5 · f / h
s = max(1, px_expected / p*)
downscale the frame by s → tile → detect → multiply box coordinates by s to return to the original image
```

Boxes are always mapped back to original image coordinates, so geolocation and confirmation never need to know that the frame was downscaled. Frames are never upscaled (s ≥ 1): upscaling when people are expected below 8 px was tried as an extension and gave no significant improvement (`upscale_small.md`). The target p* = 10 px was chosen on SeaDronesSee (10 and 20 px were tried), not on the flood test set. This is the **expected** size under the 0.5 m person assumption; boxes of swimmers in the SeaDronesSee labels are about 1.8–2.6 times larger in nadir frames, so on that dataset people end up at about 18–26 px after downscaling (`person_px_check.md`).

### 4.4.3 Two Effects

Altitude-based downscaling has two effects, matching two research questions:

- **Accuracy (research question 1):** people are brought to the size the model handles best. On SeaDronesSee, tiling AP50 rises from 0.235 to 0.531 with p* = 10 px (`scale_by_altitude.md`; Chapter 7, Section 7.1.4).
- **Computation (research question 2):** a smaller frame has fewer tiles, decreasing with the square of s. For example, at 30 m a person is about 42 px; with p* = 10 px, s = 4.2 and the 3840 × 2160 frame shrinks to about 914 × 514, needing only 2 tiles instead of 32. On a weak device this is how the required rate can be approached when flying low (Section 4.8.3; Chapter 7, Section 7.2).

### 4.4.4 Relation to Prior Work

Resizing images by capture altitude is not a new idea: @messmer2022adaptive resize UAV images by altitude before detection (Adaptive Resizing), and @ahmed2025altitude combine altitude-based downscaling with a dynamic number of tiles, evaluated on SeaDronesSee itself; the idea of matching object scale during training goes back to TinyPerson [@yu2020scalematch]. Compared with @ahmed2025altitude, the idea and even the target size are nearly the same (about 9 px there, 10 px here), so this is **not a new method** [PENDING #19]. What the thesis adds lies in how the step is used and measured:

- the scale factor is continuous and recomputed for every frame from telemetry, not rounded to a few levels;
- evaluation uses the original SeaDronesSee validation split with real altitude from metadata (Messmer et al. had to infer altitude from labels for VisDrone and UAVDT), by person size and with a paired bootstrap over videos, whereas both papers report a single run without confidence intervals;
- speed is measured with TensorRT on the whole pipeline, with a Pareto frontier and the resizing stage measured separately (Chapter 7, Section 7.2.1);
- the same altitude also sets the processing rate and the confirmation radius (Sections 4.5 and 4.6).

A check of person size on the SeaDronesSee labels also shows that the assumed person size matters a great deal: real boxes are about 1.8–2.6 times larger than the 0.5 m assumption (`person_px_check.md`). Limitation: the flood test set is built from public videos without flight altitude, so this component can be evaluated only on SeaDronesSee (altitude from metadata) and in simulation (decision #13).

## 4.5 Processing Rate by Altitude

The edge device cannot process 30 frames of 4K video per second, and it does not need to. A person stays in the frame for

```
T_dwell = L_v / v,     L_v = 2h · tan(VFOV / 2)
```

(L_v is the along-track length of the footprint, v the ground speed), so at a processing rate of F frames per second the person is seen at most `K_max = ⌊T_dwell · F⌋` times. At 50 m, 10 m/s and 2 frames per second, K_max = 8.

If the detector finds the person in each view with probability r, independently, the probability of at least N detections in K views is

```
P(confirm) = Σ_{k=N..K} C(K, k) · r^k · (1 − r)^(K − k)
```

For example, with K = 8 and r = 0.5, N = 3 gives P ≈ 0.86 and N = 5 gives P ≈ 0.36. This formula links per-frame recall (research question 1) to the confirmation ability of the whole system (research question 3).

A fixed rate does not suit every altitude: at high altitude a person stays in view long and 2 frames per second is more than enough; at low altitude the dwell time is short and 2 frames per second may not give N views. The **altitude-dependent rate** extension sets the rate so that each person is seen about n_views times:

```
F = clamp(n_views · v / L_v, F_min, F_max)
```

recomputed after every frame from altitude and speed in the telemetry; the counting window of the confirmation stage stretches with T_dwell. Simulation results are in Chapter 7, Section 7.3.1.

## 4.6 Contribution: Ground-Plane Confirmation

### 4.6.1 Why Confirmation Is Needed, and Why Common Tracking Breaks

In a single frame, the detector may mistake waves, floating debris or reflections for people. Such mistakes rarely recur at exactly the same place; real people do. The confirmation stage alerts only when a person has been seen N times, and only once per person. This requires knowing that a box in one frame and a box in a later frame belong to **the same person** (the association problem).

The usual way to associate is image-space tracking such as ByteTrack: boxes are matched between frames by overlap (IoU), with a Kalman filter predicting positions. This assumes that a person moves only a few pixels between frames. Here the assumption fails: in the 0.5 s between two processed frames, a UAV flying at 10 m/s covers 5 m, about **254 px** at 50 m, while a person's box is only about 25 px. Two boxes of the same person do not overlap, the IoU is zero, each frame starts a new track, and no person reaches N detections. The Kalman filter cannot help: the motion belongs to the camera, not the person, and in the first frame of a track the velocity is unknown.

One image-space fix is **camera motion compensation** (as in BoT-SORT, but computed from telemetry instead of from the images): the four image corners are projected to the ground with the previous frame's telemetry and back into the image with the current frame's telemetry, an affine transform is fitted, and all tracks are shifted before association. This inherits all the jitter of the telemetry between two frames: GPS jitter of a few tens of centimetres is enough to shift tracks by a few tens of pixels, about the size of a person's box.

### 4.6.2 Grouping by Ground Position

The idea: a person standing still (or drifting slowly) on the water keeps **almost the same ground coordinates from frame to frame**, even though the camera moves. Association therefore happens on the ground instead of in the image.

The system keeps a list of **clusters**; each cluster is a candidate person with a ground position, its sightings (time, confidence) and an alerted flag. Parameters: grouping radius r = 3 m, required sightings N = 3, window T_win = 5 s, expiry T_exp = 6 s.

```
For the detections D of the frame at time t (already geolocated):
1. Remove clusters whose latest sighting is older than T_exp.
2. One-to-one matching: compute the ground distance of every (cluster, detection) pair, sort ascending;
   go through the pairs, matching when the distance ≤ r and neither side is matched yet.
3. Update: a matched detection is added to its cluster, whose position becomes the confidence-weighted
   mean of all sightings; an unmatched detection starts a new cluster.
4. Confirm: a cluster not yet alerted with ≥ N sightings in the last T_win seconds → alert,
   mark as alerted.
```

Matching is **one-to-one** so that two people standing next to each other in the same frame are not merged. The rule "N sightings within T_win seconds" does not require N consecutive frames, so it tolerates misses in a few frames. The radius r is in metres and tolerates GPS errors of a few metres because GPS drifts **slowly**: between two frames 0.5 s apart the error is almost the same, so sightings of the same person stay close to each other even when the absolute position is off. The cost per frame is O(nm log nm) for n detections and m clusters, negligible compared with running the model.

For a fair comparison, all three strategies (ground-plane grouping, ByteTrack, and ByteTrack with camera motion compensation) share the expiry, update and confirmation steps; they **differ only in association**. A complete hand-worked example over four frames for all three strategies is given in Appendix A [APPENDIX: from `docs/THUAT_TOAN.md` §4].

### 4.6.3 Known Limitations

- Two people closer than r may be merged into one alert. In rescue this error is less dangerous than a miss: the team arriving on site still finds the whole group. Each alert also carries an **estimated number of people** within 5 m (the number of detections in the confirming frame around that position), so the team can bring enough buoys and boats; two multi-frame counting methods were tried, better in simulation but worse on real video, and are not used (`rq3_group.md`).
- When GPS drifts, a person may leave the old cluster and be alerted again (a false split). This is handled at the ground station (Section 4.7.3) rather than suppressed on board, because suppressing on board would also suppress a real second person nearby (`alert_memory.md`).
- A person drifting faster than a cluster can follow is split into a new cluster; a fixed compass bias projects the same person to different places as the UAV passes, more so at higher altitude (Section 4.2.3).

## 4.7 Alert Delivery and the Ground Station

### 4.7.1 Send Queue on the UAV

The link between the UAV and the ground station is unreliable, so every alert is **written to an SQLite table on the UAV before it is sent** (the transactional outbox pattern); losing the link or power midway loses no alert. Each alert produces two messages with the same ID:

- **coordinates** (a few hundred bytes, high priority): position, position error, confidence, number of sightings, estimated number of people;
- **an image crop** of 256 × 256 px JPEG around the person (a few tens of kilobytes): sent only **after** the ground station has acknowledged the coordinates.

The send loop runs after every frame and continues for up to 60 s after the last frame:

```
take unacknowledged messages that are due, ordered by (priority, creation time);
send; acknowledged by the ground station → done;
failure → retry after min(30, 2^(attempts − 1)) seconds, plus 0–20% random jitter;
          stop this round (the link is down)
```

Increasing delays avoid flooding the link during an outage; the random jitter keeps several UAVs from retrying at the same moment when the link returns.

**Link probing** (proposed in this thesis, enabled by default since decision #17): with a 30 s cap, a message that failed just before the link returned can wait almost another 30 s. When all pending messages are waiting and nothing has been sent for 2 s, the UAV tries to send the oldest coordinate message; if it succeeds (the link is back), all pending messages become due immediately. A failed probe does not extend the waiting time. Results are in Chapter 7, Section 7.3.4.

### 4.7.2 Delivery Guarantee

This mechanism delivers each message **at least once**: if the ground station's acknowledgement is lost, the UAV resends and the station receives the message twice. The station ignores message IDs it already has, so in effect each alert is recorded **exactly once**.

### 4.7.3 Merging Alerts into Incidents

The station attaches each new alert to the nearest open **incident** within 5 m and 300 s (flight clock), or opens a new incident; an incident's position is the mean of its alerts. Alerts from two different UAVs use a wider radius, the root sum of squares of the two alerts' position errors, because the GPS receivers of two UAVs are independent. The map shows incidents instead of individual alerts; no alert is discarded, so a wrong merge only makes the map less clear and never loses a person. The 5 m radius was chosen on three SeaDronesSee sequences (Chapter 7, Table 7.24). The merging rule is a pure function and runs inside one SQLite transaction.

### 4.7.4 Priority and Rescue-Team Tools

An incident's priority is a weighted sum, each part shown on the map with a one-line reason: the operator's tag after inspecting the crop (in water 3, on a roof 0.5), the highest confidence, the number of UAVs that saw it, the number of other open incidents within 30 m, and the time it has been waiting. The weights are an explainable design choice, not learned, because there is no real rescue data to learn from.

The map draws the 95% search area around each incident (Section 4.2.3), the UAV positions, the area each camera currently sees and the area already scanned. The rescue team sets the boat position and receives the distance and bearing to each incident, a suggested visiting order (higher priority first, nearer first), coordinates to send by text message, and a GPX file for a handheld navigation device. The map works without internet.

## 4.8 Simulators Used for Evaluation

The thesis has no real flight over a flood, no Jetson device and no real network to test on. Three simulators replace them; all three run **the same pipeline code** as the sections above and change only the inputs. Numbers produced this way are labelled **simulation** or **estimate** in Chapter 7 and are never placed next to measurements.

### 4.8.1 Simulated Flight

A simulated flight (straight line or lawn-mower survey) generates telemetry over time; people are placed at known coordinates on the water (individually or in groups, still or drifting). The inverse projection (Section 4.2.2) gives each person's pixel position in every frame. A **simulated detector** detects each person with a given recall and adds random false alarms; recall can follow the person's size in the image, using the recall curve measured on SeaDronesSee (Chapter 7, Table 7.2), so that flight altitude can be swept. Telemetry noise is simulated after real behaviour: GPS drifts slowly as a first-order Gauss–Markov process (correlation time about 30 s) and may degrade mid-flight; altitude is biased; the compass has a fixed bias. Because true positions are known, the simulation measures what cannot be measured on video: miss rate, false alarms per minute, time to alert, position error, and the share of people inside the 95% search area (defined in Chapter 6, Section 6.3.3).

### 4.8.2 Simulated Network

The transport is wrapped in a simulator driven by the simulation clock with a fixed seed: scattered packet loss (each send fails independently with probability p), **burst loss** (the link switches between a good and a bad state with exponentially distributed durations, losing every packet in the bad state; the Gilbert–Elliott model [@gilbert1960burst; @elliott1963burst]), and complete outages. Burst loss can be compared with scattered loss at **the same average loss rate**, differing only in whether losses come together or apart.

### 4.8.3 Edge-Device Timing Simulation

Without a Jetson nothing can be measured directly, and no tool can emulate a Jetson GPU. Instead, the pipeline runs for real on the development machine, but the simulation clock charges each frame the time the target device would take:

```
latency = overhead + n_tiles × t_tile + n_full × t_full + megapixels_original × t_resize
```

where the number of tiles follows from the frame size after altitude-based downscaling (Section 4.4), and the last term applies only when the frame is downscaled. The device is busy until processing ends; frames arriving meanwhile are dropped, as on a real device, and alerts enter the send queue when processing ends. Each device profile takes the times measured on a T4 GPU (Chapter 6, Section 6.4.2) and multiplies them by the device-to-T4 time ratio from Ultralytics' published benchmarks for the same model family (Table 4.2). The resizing term was added after the T4 measurements showed that resizing a 4K frame on the CPU took longer than inference itself (Chapter 7, Section 7.2.1).

**Table 4.2.** Device timing profiles, TensorRT FP16 (`configs/devices/`, `rq2_t4.md`). The T4 row is measured; the Jetson rows are estimates.

| Device | overhead (ms) | t_tile, 640 tile (ms) | t_full, 1280 (ms) | t_resize (ms per megapixel) |
|---|---|---|---|---|
| Tesla T4 (measured) | 0.55 | 3.75 | 23.72 | 5.574 |
| Jetson AGX Orin 64GB | 0.85 | 5.78 | 36.56 | 8.59 |
| Jetson Orin NX 16GB | 1.34 | 9.12 | 57.63 | 13.539 |
| Jetson Orin Nano Super | 1.48 | 10.09 | 63.77 | 14.983 |

The Jetson-to-T4 ratio comes from published YOLO26n inference times and is also applied to the CPU part (frame reading, resizing, box merging), an unverified assumption. Thermal throttling, low-power modes and contention for the memory shared by CPU and GPU are not simulated.

## Chapter Summary

The system detects people at native resolution with batched tiling, maps them to ground coordinates using telemetry, and alerts only when a ground position is seen repeatedly; alerts are stored before sending, coordinates go first, and the ground station merges them into incidents. The two main methodological components both use the flight data the UAV already has: **altitude-based frame downscaling** (prior work exists; the thesis integrates it into an edge pipeline and measures both accuracy and computation) and **ground-plane confirmation** (the main contribution), which associates sightings where people stay still instead of in the image, where association breaks when the UAV flies fast and few frames are processed. Chapter 5 describes the implementation, Chapter 6 the data and measurement, and Chapter 7 the results.
