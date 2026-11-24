# Appendix D. Automated Tests

> **Draft note (remove in the final document).** Compiled 25/11/2026. Test counts are copied from `runs/qa/test_files.csv`, which `tools/qa_snapshot.py --only-test-files` derives from the same snapshot that Chapter 5 cites (`runs/qa/pytest.xml`, 21/11/2026: 290 tests in 41 files). At code freeze (28/11), run `tools/qa_snapshot.py`, then update this appendix, Section 5.5 and Tables 5.2 and 5.3 together **[UPDATE AT CODE FREEZE]**.

The whole suite needs no model, GPU or dataset and runs in seconds (Chapter 5, Section 5.5). Table D.1 lists every test file by the component it checks; Table 5.3 in Chapter 5 describes the main ones in more detail.

**Table D.1.** Test files, number of tests and what they check (`runs/qa/test_files.csv`).

| Component | Test file | Tests | What is checked |
|---|---|---|---|
| Edge: detection | `test_detector` | 5 | Tiling and mapping boxes back to the original frame, without loading a model |
| | `test_gpu_resize` | 10 | Frame resizing with PyTorch on the CPU stays close to OpenCV; option off gives identical results |
| | `test_tile_cache` | 5 | Reusing results of unchanged tiles; option off gives identical results |
| Edge: geolocation | `test_georef` | 79 | Pixel → GPS → pixel round trips for nadir and tilted cameras, hand-computed cases, footprint, error propagation |
| Edge: telemetry and rate | `test_telemetry` | 10 | Telemetry interpolation (angles along the shortest path), DJI subtitle parsing, synthetic flights |
| | `test_sampler_fps` | 1 | Processing rate computed from altitude and speed |
| Edge: confirmation | `test_confirm` | 15 | Ground-plane grouping on scripted detection sequences |
| Edge: delivery | `test_alerts` | 10 | Outbox: coordinates before crops, resending after an outage, no alert lost after a restart |
| | `test_status` | 7 | Status messages: sending rate, passage through the network simulator, reception at the ground station |
| Ground station | `test_ground` | 14 | Duplicate alerts stored once, crop requires coordinates, unsafe input rejected, incident merging, offline map, GPX export |
| | `test_priority` | 3 | Incident priority score computed by hand, operator tags, closed incidents last |
| Shared | `test_config` | 2 | Reading options together with a YAML file; command-line values take precedence |
| Evaluation metrics | `test_metrics` | 8 | Matching and AP by size group against hand-computed examples, ignore regions, bin edges |
| | `test_conf_by_size` | 3 | Confidence distribution by person size |
| | `test_recall_by_tag` | 3 | Recall by nuisance tag against a hand-computed example |
| | `test_track_confirm_eval` | 3 | Scoring track-based confirmation against a hand-computed example |
| | `test_timing_summary` | 2 | Summary of stage timings against a hand-computed example |
| | `test_flood_tables` | 2 | Flood test set tables built from synthetic results |
| | `test_eval_flood` | 2 | Grouping flood frames into video clusters for the bootstrap |
| Speed (RQ2) | `test_rq2_report` | 8 | Report tables of the T4 measurements |
| | `test_rq2_tradeoff` | 1 | Joining accuracy and timing results |
| | `test_fit_device_profile` | 2 | Calibrating a device profile from measured timings, by hand example |
| Simulation | `test_rq3` | 12 | Flight, network and confirmation simulation; system metrics on a hand example |
| | `test_sim_scenario` | 7 | Simulated detector following recall by person size; GPS noise statistics |
| | `test_device_sim` | 8 | Device timing simulation and real-time pacing, by hand example |
| | `test_render` | 4 | Synthetic images place people where the projection puts them, for every heading |
| | `test_truth_layer` | 2 | Ground-truth overlay for the demonstration map |
| Data tools | `test_convert_cvat` | 7 | Converting CVAT labels; unknown labels, attributes or tags are rejected |
| | `test_extract_frames` | 8 | Frame extraction: minimum gap, near-duplicate removal, frame limit, file names |
| | `test_check_leakage` | 1 | Leakage check: images with the same name in two training sets do not overwrite each other |
| | `test_splits` | 5 | Splitting by video and finding near-duplicate images |
| | `test_relabel_agreement` | 1 | Agreement between two labelling passes, by hand example |
| | `test_convert_yolo_subset` | 3 | Reducing a multi-class YOLO dataset to the person class |
| | `test_prepare_afo` | 3 | Rebuilding the AFO dataset layout |
| | `test_make_tiles` | 2 | Cutting labelled tiles with the same grid as the detector |
| | `test_rescale_dataset` | 2 | Downscaling a dataset: image size divided by the factor, normalised labels unchanged |
| Training | `test_p2_transfer` | 9 | Mapping pretrained weights onto the model with a P2 head |
| Demonstration and console | `test_demo_panels` | 2 | Fixed rules for choosing flood frames to show |
| | `test_draw_text` | 4 | Drawing Vietnamese text on images, with a fallback when the font is missing |
| | `test_console` | 8 | Experiment console: per-image error matching, error browser, limits on trial runs |
| | `test_sandbox` | 7 | Sandbox: parameter limits, command building, comparison table |
