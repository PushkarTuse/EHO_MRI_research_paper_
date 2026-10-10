# MRI enhancement, exploratory segmentation and 3D reconstruction

## Provenance and relationship to the draft

`src/imaging.py` is a new, documented reconstruction of the manuscript's general intensity-processing and surface-rendering ideas. It is **not recovered historical MRI implementation**. The supplied notebooks and both code PDFs contain manually entered MRI plotting scores and surface illustrations, but no executable source specifying the original enhancement objective, segmentation rule, reference image or image-to-surface transformation. The added `code_snippets.txt` contains TSP comparisons rather than MRI source. Consequently this implementation produces new measurements; it cannot retrospectively authenticate the plotted PSNR, SSIM or execution-time constants.

The draft mentions an MRI slice numbered 71. It does not provide an unambiguous patient identifier, modality, normalization range or reference image for that illustration. Index 71 is included as an image-only representative slice when available, but a different patient at index 71 is not an exact reproduction of the draft figure. No draft numerical result is silently relabelled as a rerun result.

The existing files named EHO and PSO STL are byte-identical within each saved pair. Their z extent is three coordinate units and their associated case, units and generating pipeline are unrecorded. They therefore supply neither independent evidence of optimiser-dependent geometry nor a validated full-volume tumour prediction. New meshes below are derived from newly saved three-dimensional masks with recorded affines.

## Inputs and data selection

The local Medical Segmentation Decathlon Task01 dataset is available at `D:/MInor Project/datasets/New folder/Task01_BrainTumour`. Its own metadata lists 484 training image/label pairs, four modalities (0 FLAIR, 1 T1w, 2 t1gd and 3 T2w), and label values 0 background, 1 oedema, 2 non-enhancing tumour, 3 enhancing tumour. The training volumes are an available retrospective evaluation cohort; this is not an evaluation on withheld challenge-test labels. The dataset's label encoding must not be confused with a different BraTS release that uses label 4.

Default case selection is the lexically first three image paths in the supplied training manifest, giving BRATS_001, BRATS_002 and BRATS_003. The count can be increased with `--cases`. Predictions operate on the complete native-resolution volume; no tumour-dependent slice selection or image cropping is performed. Three cases are a functional rerun and exploratory evaluation, not a claim of generalisation across all 484 patients.

For a case, every requested optimiser/seed prediction and the deterministic Otsu prediction are saved before its reference label is opened. Label geometry and allowed values are subsequently checked for evaluation. Reference labels never enter normalization, enhancement, objective evaluation, threshold selection, connected-component selection or representative-slice selection.

## Enhancement objective and output interpretation

The finite, nonzero FLAIR voxels define the image ROI. The first and 99th percentiles of these intensities provide a fixed image-only normalization to [0,1]. The enhancement transform has two parameters: gamma in [0.7,1.5] and contrast in [0.8,1.3]. For a normalized intensity x it computes

`y = clip((x**gamma - 0.5) * contrast + 0.5, 0, 1)`.

Its objective, evaluated on a 256-bin ROI histogram, is

`J = -RMS_contrast(y) + 0.5 * weighted_MSE(y,x) + 0.05 * saturation_mass(y)`.

The constants and bounds are exposed in the source and committed to the run manifest before predictions. They were selected to define a complete reproducible hypothesis; they are not claimed to be the original unpublished settings. This is a contrast transform without a denoising model or ground-truth clean reference. PSNR against the normalized input measures intensity departure, and SSIM against that same input measures appearance similarity. Neither establishes denoising, fidelity to unknown clean anatomy, tumour-detection accuracy or clinical benefit. Higher input similarity can simply mean the image was changed less. The unchanged deterministic baseline has identity SSIM of 1 and mathematically infinite PSNR; JSON represents that infinite PSNR as `null` together with an explicit identity flag.

PSNR uses only ROI voxels with an explicit normalized range of one. SSIM is reported both for selected whole slices and as the average SSIM map over ROI pixels whose complete local window is within the ROI. The whole-slice result includes zero background and must not be compared as though it were a tissue-only metric. Representative slices are index 71 and the slice with maximum nonzero ROI area, selected without reference labels. The first requested seed's complete enhanced FLAIR volume is retained for each method and case as float32 normalized intensities, with its original affine, qform, sform and spatial units.

## Segmentation hypothesis

After enhancement, each optimiser minimizes the negative between-class variance of a three-class multilevel Otsu histogram partition. Two optimized normalized thresholds are sorted, quantized to the shared 256-bin grid, and required to define nonempty classes. The highest-intensity class is taken as a candidate abnormal-hyperintensity region. A fixed largest six-connected-component rule gives the final binary prediction. This rule is an unsupervised exploratory whole-tumour proxy. It does not classify the tumour subregions, learn from labels, establish a diagnostic detection model or guarantee that the selected component is a tumour. Its suitability is tested by the measured overlap, including any substantial failure.

A deterministic `skimage.filters.threshold_multiotsu` baseline is applied to the unenhanced normalized volume with the same highest-class and largest-component selection. It is retained so that computationally heavier stochastic search is not assessed only against other optimisers. Its boundaries use the library-returned histogram-center convention, which is recorded and slightly differs from the optimiser's bin-edge convention. The stochastic comparison's processing objective is shared across methods; the direct baseline also differs by omitting contrast optimisation.

The shared implementations in `optimizers.py` provide original-EHO reference operators, the reconstructed modified-EHO hypothesis, PSO, GA and an ACOR-inspired continuous archive baseline. ACOR is not the original discrete ant-colony-system algorithm and is not the draft's old continuous pheromone-shift implementation. Each stochastic stage consumes the same counted objective-evaluation budget, including initialization. Five methods and five default seeds use 1,500 evaluations per enhancement stage and 1,500 per threshold stage. Original settings and absent local code are not inferred from the newly measured results.

## Independent evaluation and uncertainty

The reference whole-tumour mask is the union `label > 0` on the unchanged native image grid. Evaluation checks shape and affine correspondence and refuses silent resizing/resampling. Outputs include Dice, IoU, precision, recall/sensitivity, specificity, TP/FP/FN/TN and predicted/reference volumes in millilitres. Voxel volume uses the absolute determinant of the image affine divided by 1,000 for millimetre-unit input. Empty-denominator precision/recall are represented as `null`; both-empty Dice and IoU use the declared value of one.

Multiple optimiser seeds represent stochastic variability on one patient's fixed image. Their mean and sample SD are reported within each case. Across-case summaries first average seeds within each case and then summarize case means; 15 seeds across three cases are not treated as 15 independent patients. Convergence plots use the actually recorded incumbents after every counted objective call, with mean and sample SD across seeds. With a three-case initial cohort, these summaries remain descriptive; they cannot support broad claims of significant clinical superiority.

`ResourceMeasurement` reports observed process RSS sampled every 50 ms and stage wall time. RSS is process memory, including imported libraries and allocated image arrays, rather than GPU memory or an exact allocator peak. Stage wall times include histogram processing and array transformations but exclude caller mask/image saving and subsequent reference evaluation. The overall run includes loading, file I/O, metric computation and 3D rendering. Optimiser-only timings are also retained in the detailed JSON, so they must not be conflated with complete volume-processing time. All code is CPU-based and requires no model training; no learned-model comparison has been run by this module.

## Native masks and 3D geometry

Every optimiser/seed prediction is saved as a binary uint8 NIfTI on the original image grid. For each selected case, the first requested seed of each method and the deterministic baseline are used for 3D display. The input's nonzero FLAIR region provides translucent brain context. Supplied reference labels are exported and displayed separately, explicitly named as reference rather than prediction.

Marching Cubes operates at level 0.5 on a padded binary mask. Padding offsets are removed before the retained voxel coordinates are transformed by the original NIfTI affine into world coordinates. This preserves the complete three-dimensional spatial extent and handles axis flips and anisotropic spacing. The requested `--mesh-stride` controls display decimation; the coordinate correction includes that stride. Default stride two reduces the display size and may alter surface topology or lose a tiny component. Full-resolution predictions remain the only masks used for quantitative evaluation. Set `--mesh-stride 1` for native-mask surfaces. PLY and STL are geometry artifacts; STL itself does not encode physical units, so the accompanying manifest identifies millimetre coordinates.

Each case's `interactive_prediction_reference.html` is self-contained and has separate clickable traces for the brain context, each predicted mask and the blue supplied reference. Default display shows the brain and first method; the reference and other methods can be toggled independently. An empty predicted mask is recorded explicitly and produces no misleading surface. Three-dimensional tumour visualization is therefore traceable to a saved mask and its actual measured overlap; reference anatomy is never presented as a successful algorithmic detection.

## Run command and output files

From the project directory, use the isolated Python executable:

```powershell
& 'code_reruns/.venv/Scripts/python.exe' -X utf8 'code_reruns/src/imaging.py' --dataset 'D:/MInor Project/datasets/New folder/Task01_BrainTumour' --output 'code_reruns/results/imaging' --cases 3 --seeds '0,1,2,3,4' --budget 1500 --population 30 --mesh-stride 2
```

Choose a fresh result directory for a new measured run; an existing run manifest blocks accidental overwriting. Output includes protocol/environment manifests, each predicted NIfTI and JSON record, the representative enhanced NIfTI, two per-stage convergence CSVs per stochastic run, evaluated mask metrics, slice panels, three-dimensional meshes and self-contained HTML views for every selected case. Root-level `all_runs.csv`, `per_case_seed_summary.csv`, `across_case_summary.csv`, `all_records.json` and per-case convergence plots consolidate the measured data.

## Tests and remaining empirical scope

`tests/test_imaging.py` checks finite-ROI normalization, seed reproducibility and equal budget accounting, geometry-preserving NIfTI saves, known mask-metric counts and physical volumes, affine-aware Marching Cubes coordinates, identity PSNR semantics and a two-case end-to-end prediction-before-reference-access boundary. These are functional checks rather than evidence of a clinically effective segmentation method. No hypothetical error bars, original manually entered times or manually assigned score constants are used in the new evaluation.

Primary implementation documentation: [NiBabel coordinate systems](https://nipy.org/nibabel/coordinate_systems.html), [scikit-image Marching Cubes](https://scikit-image.org/docs/stable/api/skimage.measure.html#skimage.measure.marching_cubes), and [scikit-image multilevel Otsu](https://scikit-image.org/docs/stable/api/skimage.filters.html#skimage.filters.threshold_multiotsu).
