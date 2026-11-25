# Chapter 5. Implementation and Quality Assurance

> **Draft note (remove in the final document).** New chapter written for the English thesis (decision #21, 21/11/2026). Sources: `pyproject.toml`, `.github/workflows/tests.yml`, `docker/`, `compose.yaml`, `.claude/rules/pipeline.md` and `experiments.md`, `docs/TECHNICAL.md` §6, 10, 12, 16, `docs/LABELING.md` §8. Test and code counts come from `runs/qa/` (`pytest.txt`, `pytest.xml`, `code_lines.csv`, `commit.txt`, generated 21/11/2026, commit in `commit.txt`); regenerate them at code freeze (28/11) and update Tables 5.2 and 5.3 **[UPDATE AT CODE FREEZE]**. Screenshots of the dispatch screen are added at layout **[FIGURE]**.

This chapter describes how the system of Chapter 3 is implemented and how its quality is assured. Section 5.1 lists the technology, Section 5.2 the code organisation, Section 5.3 the architectural rules, Section 5.4 configuration and provenance, Section 5.5 the testing strategy, Section 5.6 the measures that protect the integrity of the evaluation data, Section 5.7 deployment, and Section 5.8 the user interfaces.

## 5.1 Technology

**Table 5.1.** Main technologies and pinned versions (`pyproject.toml`).

| Concern | Technology | Version | Used in |
|---|---|---|---|
| Language | Python | ≥ 3.10 (3.12 locally, 3.13 on Kaggle and in CI) | Everywhere |
| Detection | Ultralytics (YOLO26) | 8.4.174 | UAV side, training |
| Deep learning runtime | PyTorch; TensorRT for FP16/INT8 engines | torch 2.14.1 (CI); TensorRT 10.16 (Kaggle) | UAV side, speed measurement |
| Image processing | OpenCV | 5.0.0.93 | UAV side |
| Message schema, configuration | Pydantic, PyYAML | 2.14.0, 6.0.3 | Both sides |
| Ground station | FastAPI, Uvicorn, SQLite, Leaflet | 0.143.0, 0.54.0, —, 1.9.4 (bundled) | Ground station |
| Evaluation | pandas, matplotlib, SAHI (baseline) | 3.0.6, 3.11.2, 0.12.8 | Evaluation tools |
| Testing, CI | pytest, GitHub Actions | 9.1.1 | Quality assurance |
| Labelling | CVAT (CVAT for images 1.1 export) | — | Flood test set |

Dependencies are pinned to exact versions and split into three install groups: `edge` (installable on an NVIDIA Jetson), `ground` (no PyTorch or OpenCV), and `dev` (both, plus evaluation and testing tools).

## 5.2 Code Organisation

**Table 5.2.** Packages, number of Python files and lines of code (`runs/qa/code_lines.csv`).

| Package | Role | Files | Lines |
|---|---|---|---|
| `edge/` | On-board pipeline | 13 | 2217 |
| `ground/` | Ground station | 4 | 558 |
| `shared/` | Message schema, configuration, provenance | 4 | 235 |
| `sim/` | Flight, scenario and network simulators | 7 | 944 |
| `eval/` | Metrics computed from logs | 22 | 3053 |
| `tools/` | Data conversion and checks | 21 | 2321 |
| `scripts/` | Experiment runners | 7 | 931 |
| `console/` | Experiment console (web) | 9 | 1407 |
| `training/` | Fine-tuning entry point | 1 | 193 |
| `tests/` | Automated tests | 41 | 3077 |

Each experiment is one YAML file in `configs/experiments/`, named after the experiment and the dataset; its outputs go to `runs/<dataset>/<experiment>/`. Device timing profiles live in `configs/devices/`, demonstration scenarios in `configs/demo/`.

## 5.3 Architectural Rules

The following rules keep the design of Chapter 3 intact as the code grows. They are written down in the repository and checked in code review; several are also enforced by tests.

1. **The detection library is imported in one module only.** Every other component receives detections in the shared `Detection` type, so the pipeline runs with a fake detector in tests.
2. **No wall-clock time inside the pipeline.** Time comes from the frame timestamp; the network simulator follows the same clock with a fixed seed. Processing time is measured separately and only logged.
3. **Each component is an interface with a fake implementation** (detector, telemetry source, transport). The main loop only wires components and contains no logic.
4. **The detector always returns boxes in original image coordinates**, even after downscaling or tiling; geolocation and confirmation never know that the frame was resized.
5. **Every stage writes a JSON Lines log; metrics are computed afterwards** by separate evaluation scripts.
6. **Geolocation is a pure function with an inverse**; any change to the projection requires a pixel → GPS → pixel round-trip test.
7. **Alerts go through the outbox**: coordinates first, crop second, same alert ID; the ground station ignores IDs it already has.
8. **Incident merging is a pure function**; the web application only reads and writes the database, and merging runs inside one `BEGIN IMMEDIATE` transaction.
9. **The ground station never imports PyTorch, Ultralytics or OpenCV**; the shared package uses only Pydantic and PyYAML.
10. **Every new configuration is read through Pydantic**, so a misspelled key or a wrong type fails at start-up.

New features are added as options that are **off by default**, with a test showing that the old behaviour is unchanged when the option is off. Earlier results therefore stay reproducible after every change. Chapter 7 reports several such options that were measured and kept off because they did not help (negative results).

## 5.4 Configuration and Provenance

Every command-line tool accepts a `--config` YAML file whose keys match the command-line options; options typed on the command line take precedence, and an unknown key is an error. Every run writes a `run_config.json` with the command, all parameters, the versions of Python and the main libraries, the device, the operating system and machine architecture, the **SHA-256 hash of the model weights** and the **git commit with a flag telling whether the working tree had uncommitted changes**. A result used in the thesis must come from a run without uncommitted changes, so the exact code that produced each number is known. The weight hash matters because a model file can be updated upstream under the same name.

## 5.5 Testing Strategy

The test suite runs in seconds and needs **no model, GPU or dataset**; at the time of writing it contains 290 tests in 41 files, all passing (`runs/qa/pytest.txt`). GitHub Actions runs the whole suite on every push and pull request, on Ubuntu with the CPU build of PyTorch.

**Table 5.3.** Test files by component, with the number of tests in each (`runs/qa/pytest.xml`; selected files).

| Component | Test file (tests) | What is checked |
|---|---|---|
| Geolocation | `test_georef` (79) | Pixel → GPS → pixel round trips for nadir and tilted cameras, hand-computed examples, footprint, error propagation |
| Confirmation | `test_confirm` (15), `test_track_confirm_eval` (3) | Ground-plane grouping on scripted detection sequences; ByteTrack on hand-built scenes |
| Delivery | `test_alerts` (10), `test_status` (7) | No alert lost and none duplicated across an outage; coordinates before crops; status trail resent after an outage |
| Telemetry, sampling | `test_telemetry` (10), `test_sampler_fps` (1) | Interpolation of angles along the shortest path, DJI `.SRT` parsing, frame timing |
| Detector | `test_detector` (5), `test_gpu_resize` (10), `test_tile_cache` (5) | Tiling and box mapping back to the original frame; GPU resizing close to OpenCV; options off give identical results |
| Ground station | `test_ground` (14), `test_priority` (3) | Duplicate alerts stored once, crop requires coordinates, unsafe input rejected, incident merging, offline map, GPX export |
| Metrics | `test_metrics` (8), `test_rq3` (12) | AP against a hand-computed example, size bins, ignore regions, bin-edge rounding, paired and cluster bootstrap, system metrics on a hand example |
| Simulation | `test_sim_scenario` (7), `test_device_sim` (8), `test_render` (4) | Simulated detection rates, GPS noise statistics, device busy time and dropped frames |
| Data tools | `test_convert_cvat` (7), `test_extract_frames` (8), `test_check_leakage` (1), `test_relabel_agreement` (1) | Label conversion rejects unknown labels, frame selection, leakage detection, annotator agreement |

The tests follow five patterns:

- **Hand-computed examples** for every metric, so that the evaluation code is checked against numbers computed by hand rather than against itself. The AP implementation was additionally checked against the evaluator built into Ultralytics.
- **Round-trip properties** for invertible functions, such as geolocation.
- **Fault injection** with the fake transport: the link is cut and restored, and the test asserts that every alert arrives exactly once.
- **Determinism**: simulations with a fixed seed must give identical results.
- **Regression guards for optional features**: with the option off, the output must equal the output of the code before the option existed.

## 5.6 Integrity of the Evaluation

Software quality also covers the evaluation itself, since a wrong number in the thesis is a defect.

- **Leakage check.** Before the flood test set is locked, every frame is compared with all training images using a perceptual hash; near-duplicates stop the process.
- **Hash-locked test set.** The images, labels, ignore regions, attributes and tags of the flood test set are listed in a SHA-256 manifest. The evaluation script refuses to run if any file differs from the manifest or if a file was added or removed.
- **Parameters chosen elsewhere.** Every threshold and parameter is chosen on other datasets; each final configuration runs once on the flood test set. No model is used to pre-label the flood set, so the labels are not biased towards what a model already sees.
- **Pre-registered presentation rules.** The flood frames shown in the thesis and at the defence are selected by fixed rules written down before the test set was locked (Chapter 7), not chosen by hand.
- **Numbers traced to files.** Every number in the thesis is copied from a result file produced by a script, and every table names its source.

## 5.7 Deployment

- **Ground station.** A Docker image based on a slim Python image with only the `ground` dependencies (no PyTorch); `docker compose up ground` starts it. The map library is bundled and map tiles viewed once are cached on disk, so the dispatch screen works without internet.
- **UAV side.** Installed with the `edge` dependencies. On a Jetson, the vendor build of PyTorch is installed first; a TensorRT engine must be built on the device itself, because engines are tied to one GPU. The default on-board configuration (`configs/edge.yaml`) sets tiling with 640 px tiles and 20% overlap, ground-plane confirmation (3 detections within 5 s, 3 m radius), 2 processed frames per second, GPU resizing and link probing; the model file and the altitude-based downscaling target are set per deployment (the demonstration flight uses the fine-tuned model and a 10 px target, `configs/demo/sds_v21_px10.yaml`). The TensorRT FP16 engine recommended by Chapter 7 is built on the target device. Running on a real Jetson was not possible in this work (Chapter 1, Section 1.5).
- **Training and speed measurement.** Kaggle notebooks clone the repository at a fixed commit, install the pinned packages and call the same scripts; no logic lives in the notebooks.

## 5.8 User Interfaces

**Dispatch screen.** The ground station serves one web page designed for a projector or a laptop in the field (Figure 5.1). The left column shows the on-board video when available and one card per UAV: altitude, speed, achieved frame rate, simulated device, whether telemetry is real, and how many alerts are still waiting on board. The centre shows the map with each UAV and its heading, the area the camera currently sees, the area already scanned, the flight path, and the incidents with their 95% search areas. A red banner appears when a UAV has been silent for more than three seconds, stating that its alerts are kept on board. The right column lists incidents with their crops and priority reasons.

**Rescue-team tools.** The operator places the boat on the map; each open incident then shows distance, bearing and travel time. A suggested visiting order takes incidents by priority level and, within each level, always the nearest next one; it is simple and explainable, not an optimal route. Coordinates can be copied, opened in a map application on a phone, or exported as GPX for a handheld navigation device.

**Experiment console.** A separate local web application lets the researcher run the pipeline on a listed source, compare two runs side by side, and generate an error-analysis report whose examples are selected automatically (largest misses per size group, most confident false alarms). The flood test set appears in the console only after it has been locked.

![**Figure 5.1.** Dispatch screen during a simulated link outage: the status pill and the UAV card show the lost link and the time since the last message, while alerts wait on board to be resent. Captured from `scripts/demo_bao_ve.sh chay hotay_quet orin_nano_super 60 90` (simulated flight over a synthetic flood scene, outage from 60 s to 90 s of flight time); the interface is in Vietnamese for local operators.](figures/fig5_1_dispatch_outage.png){width=100%}

## Chapter Summary

The system is implemented in Python with pinned dependencies split into on-board, ground and development groups. Ten architectural rules keep the two sides independent, the pipeline deterministic and every component testable with a fake. Quality is assured by a fast test suite that needs no model or data, run on every push, built on hand-computed examples, round trips, fault injection, determinism checks and regression guards, and by measures that protect the evaluation itself: leakage checks, a hash-locked test set, parameters chosen elsewhere and provenance for every run. Chapter 6 describes the data and the experimental setup.
