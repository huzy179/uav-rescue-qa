# Appendix B. Reproducing the Tables

> **Draft note (remove in the final document).** Compiled 25/11/2026 from the "Tái lập" section of each file in `docs/results/`. Commands are copied, with comments translated; when a result file changes its commands, this appendix follows it. The commit to quote is the code-freeze commit (28/11/2026) **[ADD COMMIT HASH AT CODE FREEZE]**.

Every number in Chapters 6 and 7 is read from a file under `runs/`, written by one of the commands below. Each run also writes a `run_config.json` with the full command, parameters, library versions, device, the SHA-256 hash of the model weights and the git commit (Chapter 5, Section 5.4). All commands are run from the repository root with the project's virtual environment (`.venv/bin/python`, shortened to `python` below). Installation and data preparation are described in the repository README. Model training ran on Kaggle (`notebooks/kaggle_train.ipynb`, which clones a fixed commit and calls `training/train.py`); the trained weights are not part of the repository.

## B.1 Where Each Table Comes From

**Table B.1.** Source of each results table. Result files are in `docs/results/`; configuration files in `configs/experiments/`.

| Table | Result file | Produced by (Section) |
|---|---|---|
| 1.1 | — (`runs/gsd/m4t_diag82/gsd_table.csv`) | B.2 |
| 4.2 | `rq2_t4.md` | B.6 |
| 5.2, 5.3 | — (`runs/qa/`) | B.9 |
| 6.4 | `flood.md` | B.4 |
| 7.1 | `visdrone_baseline.md` | B.3 |
| 7.2 | `e6_sds_pilot.md` | B.3 |
| 7.3, 7.4, 7.11 | `flood.md` | B.4 |
| 7.5 | `visdrone_E2.md` | B.3 |
| 7.6 | `afo_E1_E2.md`, `E2c.md`, `sds_det.md` | B.3 |
| 7.7 | `E2e.md` | B.3 |
| 7.8 | `visdrone_tiled_vs_sahi.md` | B.3 |
| 7.9 | `E3.md` | B.3 |
| 7.10 | `scale_by_altitude.md` | B.5 |
| 7.12 | `E2c.md`, `E3.md`, `sds_det.md`, `flood.md` | B.3, B.4 |
| 7.13–7.16 | `rq2_t4.md` | B.6 |
| 7.17 | `rq3_altitude.md` | B.7 |
| 7.18 | `rq3_adaptive.md` | B.7 |
| 7.19 | `sds_mot_confirm.md` | B.8 |
| 7.20 | `rq3_cmc_cause.md` | B.7 |
| 7.21 | `rq3_geoerr.md` | B.7 |
| 7.22 | `rq3_network.md` | B.7 |
| 7.23 | `rq3_burst.md` | B.7 |
| 7.24 | `alert_memory.md` | B.8 |

## B.2 Person Size by Altitude

```bash
python scripts/gsd_calc.py        # default: 82° diagonal field of view (Matrice 4T), 4K video
```

## B.3 Detection on Public Sets (Research Question 1)

Each experiment has one configuration file per evaluation set, named `<code>_<set>.yaml` (the codes are defined in Chapter 6, Table 6.6). Prediction uses `scripts/run_baseline.py` for full-image inference, `scripts/run_sahi.py` for SAHI and `scripts/run_tiled.py` for the thesis's own tiler. Evaluation is always at IoU 0.5 and 0.3, by size group, with paired bootstrap for comparisons.

```bash
# Prediction, for example the main model on VisDrone val and test-dev, AFO test and SeaDronesSee
for t in visdrone visdrone-testdev afo sds; do python scripts/run_baseline.py --config configs/experiments/E2c_$t.yaml; done
python scripts/run_sahi.py  --config configs/experiments/E4_visdrone.yaml
python scripts/run_tiled.py --config configs/experiments/E4tiled_visdrone.yaml

# Evaluation by size and paired comparison, VisDrone val
D=data/processed/visdrone
for iou in 0.5 0.3; do
  python eval/eval_by_size.py --runs runs/visdrone/E2c --images $D/images/val --labels $D/labels/val \
      --ignore $D/ignore/val --iou $iou --output runs/visdrone/eval_E2c_iou$iou
  python eval/compare_runs.py --a runs/visdrone/E2 --b runs/visdrone/E2c --images $D/images/val --labels $D/labels/val \
      --ignore $D/ignore/val --iou $iou --output runs/visdrone/compare_E2_E2c_iou$iou
done
# SeaDronesSee: add --cluster-pattern '^(v\d+)_' to resample whole videos
```

Two runs with the same method and input size (for example two models both at 1280 px on the full image) are evaluated separately, because `eval_by_size.py` identifies a configuration by method and input size.

**Recall by pixels on the person (Table 7.2).** SeaDronesSee images are downscaled by several factors and both models are run with tiling at each factor:

```bash
python tools/rescale_dataset.py --images data/processed/sds_det/images/val \
    --labels data/processed/sds_det/labels/val --dst data/processed/sds_rescale --factors 1 2 3 4 6
for f in 1 2 3 4 6; do
  for m in E1:yolo26s.pt E2c:runs/train/E2c_s0/weights/best.pt; do
    python scripts/run_tiled.py --source data/processed/sds_rescale/x$f/images/val --model ${m#*:} \
        --tile 640 --overlap 0.2 --imgsz 640 --conf 0.001 --max-det 1000 --no-images --output runs/e6_sds/x$f/${m%%:*}
  done
done
python eval/recall_by_pixels.py --data data/processed/sds_rescale --runs runs/e6_sds --models E1 E2c \
    --factors 1 2 3 4 6 --cluster-pattern '^(v\d+)_' --output runs/e6_sds/eval
```

## B.4 Flood Test Set

Run once, after locking. The script checks every label file against `MANIFEST.sha256` and stops if anything differs; it evaluates each named model, compares pairs with the cluster bootstrap by source, and writes all tables to `runs/flood/bang.md`.

```bash
python tools/convert_cvat.py --xml exports/*.zip --images data/raw/flood/frames --dst data/processed/flood --split test
python tools/check_leakage.py --train data/processed/visdrone/images/train data/processed/afo/images/train \
    data/processed/hydrovigilance/images/train data/processed/hydrovigilance/images/val data/processed/c2a/images/train \
    --eval data/processed/flood/images/test --output runs/leakage/flood_test
(cd data/processed/flood && find -L images/test labels/test ignore/test boxes_test.csv tags_test.csv -type f | sort \
    | xargs sha256sum > MANIFEST.sha256)
scripts/eval_flood.sh exports/ E1 E2 E2c E3 E4tiled
python tools/relabel_agreement.py --orig exports/04-10_con_lai.zip \
    --relabel exports/hai_lan_gan_2311/05_texas_task_rieng.zip exports/hai_lan_gan_2311/06_hue_task_rieng.zip \
    --output runs/flood/hai_lan_gan
```

The sensitivity analysis without the unlabelled frame (Table 7.4) removes that frame from the images and from the stored predictions, then repeats exactly the same evaluation and comparisons into `runs/flood/nhay_bo_003120/`; the full command block is in `docs/results/flood.md`.

## B.5 Altitude-Based Downscaling

```bash
python tools/make_sds_det.py --src data/raw/seadronessee_mot --dst data/processed/sds_det --split val --every 15
C="--source data/processed/sds_det/images/val --model runs/train/E2c_s0/weights/best.pt --tile 640 --overlap 0.2 --imgsz 640 --conf 0.001 --max-det 1000 --no-images"
python scripts/run_tiled.py $C --output runs/sds_det/E2c_tiled
for p in 20 10; do
  python scripts/run_tiled.py $C --altitude-csv data/processed/sds_det/meta_val.csv --target-person-px $p \
      --output runs/sds_det/E2c_tiled_px$p
done
for r in E2c_tiled E2c_tiled_px20 E2c_tiled_px10; do
  python eval/eval_by_size.py --runs runs/sds_det/$r --images data/processed/sds_det/images/val \
      --labels data/processed/sds_det/labels/val --iou 0.5 --cluster-pattern '^(v\d+)_' --output runs/sds_det/eval_${r}_iou0.5
done
python eval/compare_runs.py --a runs/sds_det/E2c_tiled --b runs/sds_det/E2c_tiled_px20 \
    --images data/processed/sds_det/images/val --labels data/processed/sds_det/labels/val \
    --cluster-pattern '^(v\d+)_' --output runs/sds_det/compare_E2c_tiled_E2c_tiled_px20   # likewise for the other pairs
```

## B.6 Speed on the T4 and Weak Devices (Research Question 2)

The T4 measurements run in a Kaggle notebook (`notebooks/kaggle_rq2.ipynb`, fixed commit), which exports the models with TensorRT and times the whole pipeline. Its output is downloaded into `runs/rq2/`; the rest runs locally.

```bash
python scripts/after_rq2.py --rq2 runs/rq2      # paired comparisons, device profile calibration, tables
python -m sim.sweep_rq3 --config configs/experiments/rq3_device.yaml --jobs 12   # weak devices (Table 7.16), simulation
```

## B.7 Simulations (Research Question 3)

Each simulation is one configuration file; the sweep runs every combination of its grid over several seeds and writes a CSV next to the configuration's output directory.

```bash
for c in rq3_altitude rq3_adaptive rq3_cmc_cause rq3_geoerr rq3_network rq3_burst; do
  python -m sim.sweep_rq3 --config configs/experiments/$c.yaml --jobs 12
done
```

Table 7.17 also uses the recall-by-pixels curve of Section B.3 (`runs/e6_sds/eval/recall_by_pixels.csv`).

## B.8 Confirmation and Incident Merging on Real Video

```bash
kaggle datasets download rameezakther/seadronessee-mot-sampled-dataset -p data/raw/seadronessee_mot --unzip
python tools/convert_seadronessee_mot.py --src data/raw/seadronessee_mot --dst data/processed/sds_mot
V=val-m100-DJI_0001-v21; D=data/processed/sds_mot/$V
python -m edge.main --config configs/edge.yaml --source $D/frames --source-fps 30 --fps 2 \
    --model runs/train/E2c_s0/weights/best.pt --telemetry $D/telemetry.csv --confirm geo --output runs/sds/$V/geo --drain-s 0
python -m edge.main --config configs/edge.yaml --source $D/frames --source-fps 30 --fps 2 --replay runs/sds/$V/geo/detections.jsonl \
    --telemetry $D/telemetry.csv --confirm bytetrack --track-thresh 0.1 --output runs/sds/$V/bytetrack_t01 --drain-s 0
python eval/track_confirm_eval.py --run runs/sds/$V/geo --truth $D/truth.json

# Incident merging at the ground station (Table 7.24)
python eval/incident_merge_eval.py --videos val-m100-DJI_0001-v21 val-mavic-DJI_0065-v5 train-mavic-DJI_0064-v13 \
    --mot data/processed/sds_mot --runs runs/sds --confirm geo --output runs/sds/incident_merge.csv
```

The second command replays the detections stored by the first (`--replay`), so both confirmation methods see exactly the same detections.

## B.9 Test Suite and Code Size

```bash
python -m pytest --junitxml=runs/qa/pytest.xml | tee runs/qa/pytest.txt
git rev-parse HEAD > runs/qa/commit.txt
```
