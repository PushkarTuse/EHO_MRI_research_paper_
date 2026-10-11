# External image-only stress studies

Registration is a known synthetic rigid perturbation of anatomical MRI slices; geometric grid-landmark RMSE is in pixels and is not clinical TRE. Noise references are the known normalized uncorrupted images. Gaussian corruption is not a clinical noisy/clean pair. Segmentation labels are never read.

The primary histogram contrast objective and optimizer defaults were frozen. Clean-reference PSNR/SSIM are independent postprediction endpoints; lower quality after contrast adjustment must be reported without selecting favorable subjects or noise realizations. Noisy identity and fixed Gaussian sigma1 are separately named controls.

runs.csv retains individual measurements. Per-subject tables summarize repeated RNG runs first; across-subject tables use three distinct subjects as observational units. Full histories, prediction arrays, corruption arrays and static panels are retained. These small controlled studies support no clinical accuracy or optimizer superiority conclusion.
