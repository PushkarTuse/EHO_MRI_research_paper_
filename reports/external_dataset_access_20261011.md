# Brain datasets: verified access and fit — 11 October 2026

Rank measures fit to the existing FLAIR enhancement, lesion-mask evaluation and
physical-coordinate 3D pipeline. It is an assessment of task compatibility,
separate from access convenience or dataset prestige. A classification label is
not a segmentation mask; MS and stroke references do not validate tumour diagnosis.

| Fit rank | Dataset | Download/access now | Modality and reference | License / size | Use for this paper |
|---:|---|---|---|---|---|
| 1 | **MSLesSeg** | Anonymous official downloads verified through [Figshare API](https://api.figshare.com/v2/articles/27919209); [processed images and masks](https://ndownloader.figshare.com/files/52771814) | FLAIR, T1, T2; expert-reviewed MS lesion masks, 115 series / 75 patients | CC BY 4.0; processed 1.473 GB, raw 1.295 GB | Best first external test: matching FLAIR, aligned voxel masks, and multifocal lesions challenge the largest-component rule. **Selected and downloaded by this execution.** |
| 2 | **ISLES'22 v2.3.1** | Anonymous [official Zenodo deposit](https://zenodo.org/records/7960856); [ZIP](https://zenodo.org/records/7960856/files/ISLES-2022.zip?download=1) | DWI, ADC, FLAIR; stroke infarct masks; 250 public training cases, 150 hidden test cases | Deposit CC BY 4.0; 1.693 GB | Strong second pathology/domain-shift cohort. Verify native image/mask geometry; do not assume FLAIR and DWI grids match. DWI and ADC have different lesion-contrast conventions. |
| 3 | **MSSEG / MICCAI 2016** | [Official data page](https://portal.fli-iam.irisa.fr/msseg-challenge/english-msseg-data/) opens complete training/testing access through accepted [Shanoir registration](https://shanoir.irisa.fr/shanoir-ng/challenge-request) | 53 patients, FLAIR/T1/T1-Gd/PD-T2; seven annotators and consensus lesion mask | OFSEP research DUA; noncommercial, nonredistribution; archive size not verified | Good additional MS segmentation cohort after approval. Declare reference-rater/consensus choice before evaluation. |
| 4 | **IXI** | Immediate anonymous [official NIfTI archives](https://brain-development.org/ixi-dataset/); T1 archive HTTP 200 verified | Nearly 600 healthy participants; T1/T2/PD/MRA/diffusion; no standard lesion masks | CC BY-SA 3.0; T1 4.841 GB, other modality archives about 3.6–12 GB | Useful enhancement, controlled-noise and anatomical registration/3D study. Does not test lesion Dice or tumour accuracy; no matching FLAIR in the standard release. |
| 5 | **OASIS-1** | [Current official page](https://sites.wustl.edu/oasisbrains/home/oasis-1/) exposes raw tarballs; [disc1](https://download.nrg.wustl.edu/data/oasis_cross-sectional_disc1.tar.gz) anonymous HTTP 200 verified. Current site also links [access/terms](https://sites.wustl.edu/oasisbrains/request-access/) | T1 MRI, cognitive/clinical variables and anatomical/tissue segmentations; no tumour-lesion references | Noncommercial academic research terms; 12 raw discs about 1.5 GB each | Structural MRI/enhancement only. Technical download availability does not remove applicable data-use terms. |
| 6 | **OASIS-3 / OASIS-4** | [Current access route](https://sites.wustl.edu/oasisbrains/request-access/): research statement, NITRC account, staff approval | MRI sequences vary; OASIS-3 includes T1/T2/FLAIR and other modalities, clinical/cognitive records | Data-use agreement; size depends on selected sessions | Potential enhancement/registration cohort after approval. Clinical diagnoses and FreeSurfer anatomy are not tumour segmentation ground truth. |
| 7 | **ADNI** | [Official application](https://adni.loni.usc.edu/data-samples/adni-data/): affiliation/proposed use, DUA and committee approval, then IDA download | Neurodegeneration MRI; sequences vary by phase including T1/FLAIR; clinical and derived imaging measures | Controlled research access; no single fixed archive size | Useful later for structural/WMH-related questions. Numeric WMH volumes and Alzheimer diagnoses cannot replace voxel-level lesion masks. |
| 8 | **MSSEG-2 / MICCAI 2021** | [Official data page](https://portal.fli-iam.irisa.fr/msseg-2/data/); accepted Shanoir registration and [DUA](https://portal.fli-iam.irisa.fr/files/2021/03/OFSEP_MRI_Data_Access_Agreement_MICCAI_2021.pdf) | Paired FLAIR timepoints, 100 patients (40 train/60 test); references mark **new lesions**, not all lesions | Noncommercial/no redistribution/time-limited DUA; training about 6 GB | Requires a longitudinal change-detection method. A single-image whole-lesion prediction is not an appropriate evaluation against new-lesion masks. |
| 9 | **ISLES'24** | Anonymous [current official Zenodo deposit](https://zenodo.org/records/17652035), full train.7z | Pretreatment CT/CTA/CTP plus follow-up DWI/ADC and infarct masks; 149 public training cases | CC BY-NC-SA 4.0; about 99 GB archive | Follow-up MRI can test infarct segmentation. This differs from the challenge's pretreatment-to-final-infarct prediction task and is less practical than ISLES'22. |
| 10 | **RSNA Intracranial Hemorrhage** | [Kaggle competition data](https://www.kaggle.com/c/rsna-intracranial-hemorrhage-detection/data) requires account/rule acceptance; the [official AWS listing](https://registry.opendata.aws/rsna-intracranial-hemorrhage-detection/) explicitly specifies **Controlled Access** | Head CT DICOM; slice-level five haemorrhage subtypes plus any, not voxel masks | Noncommercial/no redistribution terms; Kaggle listing about 458.97 GB | A separate CT classification study, not a direct MRI lesion-segmentation validation. |
| 11 | **CQ500** | [Official Qure release description](https://www.qure.ai/us/blog/challenges-of-development-validation-of-deep-learning-for-radiology); original headctstudy.qure.ai download host was unreachable in this check | 491 head CT scans, three-reader scan-level findings, not original voxel masks | CC BY-NC-SA; live original download size/access not confirmed | Poor fit to the current MRI segmentation task. Do not label unverified third-party mirrors as verified official downloads. |

## Immediate-download shortlist

**MSLesSeg and ISLES'22** have matching pathology-mask references for an external
lesion evaluation. **IXI** is immediately downloadable for MRI enhancement and
registration without lesion-mask evaluation. **OASIS-1** exposes direct archives,
but its current terms/access route must also be followed. Other cohorts require
approved access, different task definitions, substantial download resources or
a working official download route that could not be verified here.

Only MSLesSeg is downloaded in this task. The complete release is preserved
locally; original BraTS data and previous measured runs remain unchanged.

## Evidence notes

- The [MSLesSeg repository README](https://ndownloader.figshare.com/files/54605609)
  explicitly identifies processed images **with masks**, raw MRI, preprocessing
  source and transforms. Its [dataset paper](https://www.nature.com/articles/s41597-025-05250-y)
  documents 1 mm MNI152 registration and brain extraction.
- ISLES'22 Zenodo metadata and original paper specify CC BY 4.0, while its official
  GitHub README inconsistently says CC BY-SA 4.0. Record the deposit's declaration
  and verify any additional redistribution conditions before publishing raw data.
- Availability here means the official route was checked on this date; it does
  not mean every account application has been approved or every dataset downloaded.
- This selection cannot replace a larger tumour-specific BraTS validation. It
  tests the manuscript's broader medical-imaging transfer claims across pathology.
