# Appendix A. Labelling Guidelines for the Flood Test Set

> **Draft note (remove in the final document).** Condensed English version of `docs/LABELING.md` (25/11/2026). Statistics of the locked set are in Chapter 6, Table 6.4; the labelling-consistency check and the known unlabelled frame are in Chapter 6 and Chapter 7, Section 7.1.1. This appendix states the rules as they were applied, including where practice departed from the plan.

## A.1 Selecting Videos and Frames

- **Sources.** UAV videos of flooded areas with people, seen from above or obliquely, at 1080p or higher. Four of the ten videos are below this resolution and were kept, because dropping them would leave fewer frames than the planned minimum (Section A.5). Videos come from different places and different floods; at most 30 frames are taken from one video.
- **Provenance.** Each video has one row in a source list: identifier, URL, download date, resolution and licence or copyright note. The images are not redistributed; only labels and sources are published.
- **Frame extraction** (`tools/extract_frames.py`). One frame every 2 seconds; a frame is dropped if its perceptual hash (dHash) differs by fewer than 10 bits from any frame already kept from the same video; black or uniform frames are dropped; at most 30 frames are kept per video, spread evenly in time. Every kept frame was then checked by eye, and blurred frames or frames that are not flood scenes were removed.
- **Frames without people** (water, debris, roofs) are kept, so that false alarms can be measured.
- Videos in the test set are never used for training or for choosing parameters.

## A.2 Tool and Labels

Labelling was done in CVAT with two rectangle labels and four image tags (Table A.1). Labels are exported in the CVAT XML format, because the YOLO format drops attributes and tags, and converted with `tools/convert_cvat.py`, which rejects any label, attribute or tag not in Table A.1 so that a typing error in CVAT cannot silently become a missing label.

**Table A.1.** Labels, attributes and tags.

| Name | Level | Used when |
|---|---|---|
| `person` | box | One person |
| `ignore` | box | A region that cannot be labelled (an object that may or may not be a person; a crowd that cannot be split into individuals). Predictions inside it count neither as correct nor as false alarms |
| `partly_submerged` | box attribute | Water covers the person from the knees up |
| `occluded` | box attribute | Another object (tree, roof, boat, another person) hides about one third of the body or more |
| `glare` | image tag | Sun glare on the water large enough to hide a person |
| `weather` | image tag | Rain, fog or darkness clearly reduces contrast |
| `blur` | image tag | Motion blur or defocus; object edges are no longer sharp |
| `floating_debris` | image tag | Floating rubbish, plants or objects about the size of a person |

When in doubt between setting an attribute or tag and not setting it, it is not set: tags are useful only when they separate clear cases.

## A.3 What Counts as a Person

A `person` box is drawn when the annotator is sure it is a person, even if only part of the body is visible: people wading, swimming, clinging to floating objects, standing on roofs or balconies, sitting in boats or on vehicles; and very small people (a few pixels) when they can be recognised from shape, shadow or motion in neighbouring frames.

Not labelled: reflections of people on the water and cast shadows; people inside vehicles or buildings whose body cannot be seen; figures on billboards, mannequins and scarecrows. An object that may or may not be a person gets an `ignore` box, not a `person` box.

## A.4 Drawing Boxes

- The box encloses the **visible part** of the person tightly; parts under water or hidden behind objects are not guessed.
- People below 16 px are drawn at 300–400% zoom, because an offset of 1–2 px at this size is enough to push the IoU below the threshold.
- Objects the person holds or clings to (life rings, plastic cans, poles) are outside the box, except where they overlap the body.
- A person cut by the image border is boxed inside the image.
- Two overlapping people get one box each if they can be separated; a crowd that cannot be separated gets one `ignore` region covering it.

## A.5 Decisions Made During Labelling

Cases not covered by the rules above were decided once, recorded with the date and applied to all later frames.

**Table A.2.** Additional decisions.

| Date | Case | Decision |
|---|---|---|
| 4/11/2026 | Four videos below 1080p (two at 854 × 480, two at 1280 × 720); 74 of the 188 frames | Kept and labelled at their own resolution without upscaling. Without them only 114 frames would remain, below the planned minimum of 150. Stated as a limitation: people in these videos have fewer pixels than at the same altitude in 1080p |
| 4/11/2026 | Two videos are footage of the same police department during the same flood (same logo on every frame): 54 frames from one source, above the limit of 30 | Merged into one source: 15 frames kept per video, chosen evenly by frame order without looking at content; the other 24 frames removed. In the cluster bootstrap the two videos form one cluster. The set has 188 frames after this step |
| 4/11/2026 | One video shows a sheriff's camera overlay with speed and altitude readings, most likely filmed from a helicopter, during the same flood as another video filmed by a drone | Kept as its own cluster (different camera and time). Stated as a limitation: the source is a crewed aircraft with an oblique view similar to a UAV |

## A.6 Quality Control and Locking

- After every 50 frames, all frames were reviewed at 100% zoom to look for missed people, especially near the image border and in glare.
- The plan called for relabelling 20 of the first 50 frames at least two days later, without looking at the original labels, and comparing the two passes with `tools/relabel_agreement.py`. **This was not done.** Two videos were, by chance, labelled twice on the same day, in separate CVAT tasks; that comparison is reported in Chapter 6 as the only indication of labelling consistency.
- Before locking, every frame either has labels or was confirmed to contain no person, and every video has a row in the source list.
- **Locking** (Chapter 6): labels are converted, every test image is checked against all training sets for exact and near duplicates (`tools/check_leakage.py`), and a SHA-256 hash of every image, label file, ignore region file and the attribute and tag tables is written to `MANIFEST.sha256`. The evaluation script stops if any file differs from the manifest. After locking, no label is changed and no frame is added or removed.
- **Known error after locking.** One frame with a clearly visible crowd has no labels and no `ignore` region. It was found after locking and was not corrected; Chapter 7, Section 7.1.1 reports the results with and without that frame. The lesson is the rule already stated in Section A.4: a crowd that cannot be split must receive an `ignore` region, never be left empty.
