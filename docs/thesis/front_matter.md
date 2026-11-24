# Front Matter

> **Draft note (remove in the final document).** Written 25/11/2026. The cover pages follow the school template and are filled in when the Word file is built. The abstract (at most 150 words, FSB guidelines) introduces no new numbers: each number is copied from Chapter 7 (Tables 7.3, 7.13, Section 7.1.4) or Chapter 6 (Table 6.4). The acknowledgments are left to the author **[AUTHOR TO WRITE]**. The list of abbreviations follows the "English" column of `docs/THUAT_NGU.md`. Table of contents, list of tables, list of figures and list of appendices are generated when the Word file is built.

## Abstract

Flood victims must be found quickly, but in UAV video from a safe altitude a person covers only a few pixels, the on-board computer is weak and the network is unreliable. This thesis builds FloodEye, which detects people on the UAV, estimates their GPS position, confirms them over several frames and sends alerts to a ground station map. A self-labelled flood test set of 188 frames from 9 sources (509 people) was locked before any model was run. Fine-tuning raised recall for people below 16 px but not AP50, because false alarms increased; the base model kept the highest AP50 (0.269 versus 0.148). On a T4 GPU, TensorRT FP16 ran 1.833–3.028 times faster than PyTorch, and altitude-based downscaling cut a 4K frame from 32 to 6 tiles. In simulation, grouping detections on the ground beat image tracking at low frame rates, and link outages lost no alert.

**Keywords:** small object detection; UAV; flood search and rescue; edge computing; YOLO; multi-frame confirmation.

## Acknowledgments

[AUTHOR TO WRITE]

## List of Abbreviations

| Abbreviation | Meaning |
|---|---|
| AFO | Aerial dataset of Floating Objects |
| AGL | Above ground level |
| AP, AP50 | Average precision; average precision at IoU 0.5 |
| C2A | Disaster image dataset with pasted people (Nihal et al., 2024) |
| CI | Confidence interval |
| CMC | Camera motion compensation |
| COCO | Common Objects in Context dataset |
| CPU, GPU | Central processing unit, graphics processing unit |
| CVAT | Computer Vision Annotation Tool |
| DFOV, HFOV, VFOV | Diagonal, horizontal and vertical field of view |
| FP16, INT8 | 16-bit floating point, 8-bit integer |
| FPS | Frames per second (tables and figures only) |
| GPS | Global Positioning System |
| GPX | GPS Exchange Format |
| GSD | Ground sampling distance |
| IoU | Intersection over union |
| JSONL | JSON Lines (one JSON record per line) |
| MOT | Multi-object tracking |
| NMS | Non-maximum suppression |
| RGB | Red, green, blue (colour image) |
| RQ | Research question |
| SAHI | Slicing Aided Hyper Inference |
| SDS | SeaDronesSee dataset |
| SSE | Server-sent events |
| UAV | Unmanned aerial vehicle |
| YOLO | You Only Look Once (family of object detectors) |
