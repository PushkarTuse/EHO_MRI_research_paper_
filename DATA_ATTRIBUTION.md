# Dataset and derived-output attribution

Dataset: Medical Segmentation Decathlon **Task01_BrainTumour** / BraTS.
The metadata of the local input release specifies version2.0 (04/05/2018),
licence **CC-BY-SA4.0**, and the reference
<https://www.med.upenn.edu/sbia/brats2017.html>.

Official project: <https://medicaldecathlon.com/>.
Licence text: <https://creativecommons.org/licenses/by-sa/4.0/>.

`data/dataset_metadata.json` preserves that input metadata. Raw images and labels
are obtained separately and are not included in this repository.

Dataset-derived outputs in `results/run_20261005/imaging/` include transformed
FLAIR volumes, image-only predicted masks, reference whole-tumour masks formed
from label>0, slice illustrations and physical-coordinate surface meshes. Their
transformations and evaluation are documented in `reports/imaging_method_notes.md`.
These derived data outputs are shared with the source dataset's CC-BY-SA4.0
attribution and share-alike notice. Reference masks remain labelled as given
annotations; they are not described as algorithmic detections.

The video is a recording supplied by Pushkar Tuse showing a derived viewer.
Third-party scientific algorithms and libraries remain subject to their own
references and licences. This notice does not assign a new licence to the
authors' original code or manuscript text.

## MSLesSeg external validation

Official dataset: [MSLesSeg, Figshare record 27919209](https://doi.org/10.6084/m9.figshare.27919209).
Dataset paper: https://doi.org/10.1038/s41597-025-05250-y.
The deposit declares [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
The recorded official author metadata is retained in `data/MSLesSeg/source_metadata.json`;
cite the dataset and its authors. Raw images and expert masks are acquired separately.
Release assets contain modified contrast volumes, threshold predictions, given reference
lesion masks, illustrations and physical-coordinate meshes, with this attribution.
These are MS lesions, not brain tumours. The registered-grid outputs are adaptations
of the supplied processed dataset, not native clinical volume measurements.
