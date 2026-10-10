# Dataset setup

Obtain Medical Segmentation Decathlon **Task01_BrainTumour** through its official
dataset distribution: [Medical Segmentation Decathlon](https://medicaldecathlon.com/).
Read the supplied dataset terms and metadata. The completed run used an existing
local copy; this repository does not redistribute the raw training/test images.

Point `--dataset` or environment variable `EHO_DATASET_PATH` to the folder containing:

```text
Task01_BrainTumour/
  dataset.json
  imagesTr/BRATS_001.nii.gz ...
  labelsTr/BRATS_001.nii.gz ...
  imagesTs/ ...
```

The supplied release lists 484 training pairs and266 test images. Modality index0
is FLAIR,1 T1w,2 t1gd and3 T2w. Label values are0 background,1 oedema,
2 non-enhancing tumour and3 enhancing tumour. Whole-tumour evaluation uses label>0.
Do not substitute a label4 convention from another BraTS release.

Default MRI selection is the first three sorted training cases; `--cases` changes
the count. The published measured run covers001–003, not all484 cases. Native masks
are evaluated at their original geometry. Raw images and labels are ignored by Git;
metadata and dataset-derived research outputs are documented separately.
