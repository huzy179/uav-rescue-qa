# Chapter 3. System Requirements and Architecture

> **Draft note (remove in the final document).** New chapter written for the English thesis (decision #21, 21/11/2026), because the Master of Software Engineering programme assesses requirements, design, implementation and quality assurance. Sources: `docs/luan_van/chuong3.md` §3.1, `docs/TECHNICAL.md` §1, 6, 7, 10, 12, `docs/ROADMAP.md` §2–3, `.claude/rules/pipeline.md`. Requirements are stated as the system was built; the "Verified by" column points to the chapter that tests or measures each one, and no number appears here unless it comes from `docs/results/`. Figures 3.1 and 3.2 are drawn when the document is laid out **[FIGURE]**.

This chapter states what the system must do and under which constraints, and gives the architecture that satisfies these requirements. Section 3.1 introduces the stakeholders and usage scenarios, Section 3.2 the functional requirements, Section 3.3 the non-functional requirements, Section 3.4 the architecture, and Section 3.5 the main design decisions and their alternatives. The algorithms inside each component are described in Chapter 4, and the implementation and its quality assurance in Chapter 5.

## 3.1 Stakeholders and Usage Scenarios

The system serves four kinds of users.

- **The UAV** (on-board software, no human in the loop): processes the video and telemetry of one aircraft and sends alerts.
- **The ground operator** at the ground station: watches the dispatch screen, inspects alerts, tags and closes incidents.
- **The rescue team** in a boat or on foot: receives the positions of people and an order in which to visit them.
- **The researcher** (in this thesis, the author): replays flights, runs experiments and evaluates the system against labels.

Five scenarios describe how they use the system (Table 3.1).

**Table 3.1.** Use scenarios.

| ID | Scenario | Main actor |
|---|---|---|
| UC1 | During a flight, the UAV detects people, confirms them over several frames, geolocates them and sends alerts; while the link is down, alerts are stored and sent later | UAV |
| UC2 | The operator sees incidents appear on a map with an image crop and a search area, tags each one (in water, on a roof), and closes it as rescued or as a false alarm | Ground operator |
| UC3 | The operator places the boat on the map; the system suggests a visiting order and exports the open incidents as GPX for a handheld device | Ground operator, rescue team |
| UC4 | Two UAVs see the same person; the ground station merges their alerts into one incident | UAV, ground operator |
| UC5 | The researcher replays a recorded flight with saved detections, simulated flight, simulated network or a simulated edge device, and computes metrics from the logs | Researcher |

## 3.2 Functional Requirements

**Table 3.2.** Functional requirements by component.

| ID | Requirement | Component | Verified by |
|---|---|---|---|
| FR1 | Read 4K video or a folder of frames together with telemetry (CSV or DJI `.SRT`) and sample frames at a configurable rate, with the telemetry interpolated to each frame's timestamp | UAV | Ch. 5 (tests) |
| FR2 | Detect people with YOLO26 either on the whole frame or on tiles processed in one batch, merge duplicate boxes across tiles, and optionally downscale the frame according to flight altitude | UAV | Ch. 7, RQ1 |
| FR3 | Map each detection from pixel to GPS coordinates and back, for a nadir or tilted camera, and estimate a position error | UAV | Ch. 5 (round-trip tests), Ch. 7, RQ3c |
| FR4 | Confirm a person only after N detections within a time window, issue one alert per person, and offer image-space tracking (ByteTrack, with or without telemetry-based motion compensation) as alternatives | UAV | Ch. 7, RQ3b |
| FR5 | Store every alert on disk before sending; send coordinates before the image crop; retry with exponential backoff; probe the link to resume quickly after an outage | UAV | Ch. 5 (outbox tests), Ch. 7, RQ3d |
| FR6 | Send a periodic status message (position, camera footprint, achieved frame rate, pending alerts) and resend the flight trail missed during an outage | UAV | Ch. 5 |
| FR7 | Accept alerts and crops over HTTP, acknowledge each message, and ignore duplicates | Ground station | Ch. 5 (API tests) |
| FR8 | Merge alerts from one or several UAVs into incidents by distance and time | Ground station | Ch. 7, RQ3e |
| FR9 | Score each incident's priority with an explainable rule (operator tag, confidence, number of UAVs, nearby incidents, waiting time) and show the reasons | Ground station | Ch. 5 |
| FR10 | Show a dispatch screen: map with UAV positions, current camera footprint, area already scanned, incidents with search areas and crops, and a warning when a UAV goes silent | Ground station | Ch. 7, Section 7.6 |
| FR11 | Let the operator tag, close and reopen incidents | Ground station | Ch. 5 (API tests) |
| FR12 | For the rescue team: distance, bearing and travel time from the boat to each incident, a suggested visiting order, copyable coordinates and a GPX export | Ground station | Ch. 5 |
| FR13 | Replay saved detections instead of running the model, and simulate flight, network and edge-device timing with a fixed seed | Evaluation tools | Ch. 4, Section 4.8 |
| FR14 | Compute all metrics afterwards from the logs: AP and recall by person size, paired comparisons, system metrics of research question 3 | Evaluation tools | Ch. 6 |

## 3.3 Non-Functional Requirements

**Table 3.3.** Non-functional requirements.

| ID | Quality | Requirement | How it is met | Verified by |
|---|---|---|---|---|
| NFR1 | Accuracy on small people | Keep native resolution for people of a few pixels; report results by person size | Tiling, altitude-based downscaling, fine-tuning | Ch. 7, RQ1 |
| NFR2 | Throughput on the edge device | Process about 2 frames per second on the target device (proposal) | TensorRT FP16, batched tiles, altitude-based downscaling, GPU resizing | Ch. 7, RQ2 (measured on a T4; Jetson estimated) |
| NFR3 | Robustness to the network | No alert is lost during an outage; the ground station never shows a duplicate | Outbox in SQLite, at-least-once delivery with de-duplication by message ID | Ch. 5 (tests), Ch. 7, RQ3d |
| NFR4 | Bandwidth | Send only small messages; never stream video to the ground | Coordinates first, then a small JPEG crop | Ch. 4, Section 4.7 |
| NFR5 | Offline operation | The ground station works without internet | Bundled map library, cached map tiles | Ch. 5 (test that the page loads nothing from the internet) |
| NFR6 | Portability | The on-board part installs on an NVIDIA Jetson; the ground part installs without PyTorch | Separate install groups; the two parts share only one message schema | Ch. 5 |
| NFR7 | Reproducibility | Re-running the same data gives the same result; every number in the thesis can be traced to a run | Time taken from frame timestamps, fixed seeds, a provenance file per run, pinned dependencies, hash-locked test set | Ch. 5 |
| NFR8 | Testability | Every component can be tested without a model, GPU or dataset | Each component behind an interface with a fake implementation | Ch. 5 |
| NFR9 | Explainability for operators | Every priority and every alert can be explained to the operator | Rule-based priority with reasons; crops and search areas shown | Ch. 4, Section 4.7 |

NFR2 is the requirement the thesis cannot fully verify, because no Jetson device was available; Chapter 7 reports measured speed on a T4 GPU and estimates for Jetson devices, both labelled as such.

## 3.4 Architecture

The system has two sides connected by an unreliable link (Figure 3.1).

**On the UAV (edge device)**, each sampled frame passes through five stages:

1. **Sampling:** take a frame from the video and the telemetry at that exact time.
2. **Detection:** cut the frame into tiles, run YOLO26 on all tiles in one batch, merge duplicate boxes.
3. **Geolocation:** convert each box to a GPS position on the ground.
4. **Confirmation:** group detections by ground position over several frames; a position seen N times within a time window becomes an alert, once per person.
5. **Delivery:** write the alert to an on-disk queue (outbox) and send the coordinates first and the image crop later, retrying on failure.

**At the ground station**, alerts are merged into incidents, prioritised and shown on a map for the operator and the rescue team.

![**Figure 3.1.** Two-sided architecture. On the UAV, five stages turn video and telemetry into alerts stored in an outbox; over an unreliable link, the ground station stores alerts, merges them into incidents, ranks them and shows them on the dispatch screen. Stages 1 and 2 have altitude-based options that are off by default.](figures/fig3_1_architecture.png){width=100%}

![**Figure 3.2.** Packages and their imports, measured from the import statements in the code. `edge/` and `ground/` depend on `shared/` and never on each other; the dashed imports exist only in the main loop, for replaying flights and drawing the saved video.](figures/fig3_2_packages.png){width=100%}

**Table 3.4.** Components and responsibilities.

| Package | Component | Responsibility |
|---|---|---|
| `edge/` | Sampler, telemetry source | Timed frames; telemetry from CSV or DJI `.SRT`, interpolated in time |
| | Detector | Full-frame or batched tiled YOLO26 inference, box merging, altitude-based downscaling; the only module that imports the detection library |
| | Geolocation | Pixel ↔ GPS mapping, camera footprint, expected person size from altitude |
| | Confirmer | Ground-plane grouping, or ByteTrack with or without motion compensation |
| | Outbox and transport | SQLite queue, HTTP transport, retries and link probing |
| | Main loop | Wires the components together and writes logs; contains no logic of its own |
| `ground/` | API and storage | Receives alerts, crops and status; SQLite tables for alerts, crops and incidents |
| | Incident merging, priority | Pure functions for merging alerts and scoring incidents |
| | Dispatch screen | Map, UAV cards, incident list, rescue-team tools |
| `shared/` | Schema, configuration, provenance | Message types shared by both sides, YAML configuration, run provenance |
| `sim/` | Flight, scenario, network | Simulated flights and people, detectors with a given recall, lossy network with outages |
| `eval/` | Metrics | Accuracy by size, bootstrap, system metrics, timing summaries |

**Interfaces between the sides.** The UAV and the ground station share only a message schema (alert, crop, UAV status), each message carrying a schema version. Alerts are sent with an HTTP `POST`; a `200` response carrying the message ID is the acknowledgement. Because an acknowledgement can be lost and the message resent, delivery is at least once; the ground station makes it exactly once in effect by ignoring a message ID it has already stored. Status messages bypass the outbox: an old status is worthless, so a lost one is simply replaced by the next.

## 3.5 Design Decisions

**Table 3.5.** Main design decisions, alternatives and reasons.

| Decision | Alternative considered | Reason |
|---|---|---|
| Process on board and send only alerts | Stream video to the ground and process there | The link in a flood area cannot carry 4K video and drops for tens of seconds (NFR3, NFR4) |
| Confirm on ground coordinates | Image-space tracking (ByteTrack) | At a few processed frames per second a person moves hundreds of pixels between frames; image-space association breaks (Chapter 7, RQ3b) |
| Batched tiling written for this system | SAHI, which runs tiles one by one | One batch per frame suits the GPU and a TensorRT engine with a fixed tile size |
| Outbox in SQLite with HTTP | A message broker (e.g. MQTT with QoS 1) | Same at-least-once guarantee without an extra service to run on board |
| Rule-based priority | A learned priority model | No real rescue data to learn from; the operator must understand each score (NFR9) |
| Time from frame timestamps | Wall-clock time | Replays and simulations give identical results and can run faster than real time (NFR7) |
| Metrics computed from logs afterwards | Metrics computed inside the pipeline | A metric can be changed without re-running the pipeline; the pipeline stays simple |
| Every component behind an interface with a fake | Direct use of the model and network | The whole system can be tested and simulated without a GPU, a model or a network (NFR8) |

## Chapter Summary

The system serves four kinds of users through five scenarios. Fourteen functional requirements cover detection, geolocation, confirmation, delivery, the ground station and the evaluation tools; nine non-functional requirements cover accuracy on small people, throughput on a weak device, robustness to an unreliable network, offline operation, portability, reproducibility, testability and explainability. The architecture separates the UAV side from the ground station, connects them only through a versioned message schema over an at-least-once link, and places every component behind an interface with a fake implementation. Chapter 4 describes the algorithms inside these components.
