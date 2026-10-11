# Complete external snapshot publication

Release: https://github.com/PushkarTuse/EHO_MRI_research_paper_/releases/tag/external-mslesseg-2026-10-11

Normal Git contains runnable external additions, tests, the complete statistical
and audit reports, compact plots, download metadata and the source case inventory.
The release ZIPs contain **every file** from the completed full-cohort experiment,
the separate pilot, controlled registration/noise studies, both preserved post hoc
diagnostics, and a byte-exact source snapshot. No completed prediction or viewer
is omitted. Original numerical JSON/CSV records are byte-preserved. Markdown link
destinations are adapted only in the publication copy.

Each `mslesseg-cases-XX.zip` holds a disjoint part of the 115 cases; the support
ZIP holds cohort reports/manifests, pilot, ancillary studies and frozen sources.
Extract **all ZIPs into the repository root**. They share a directory structure
and contain no traversal paths. `EXTERNAL_RELEASE_MANIFEST.json` records per-file
SHA256s and the archive hashes/sizes. Verify it before opening or analysing files.
Optional: use `tools/restore_external_release.py --assets YOUR_DOWNLOAD_FOLDER`
to verify every ZIP and safely restore the published tree. It checks SHA256s,
refuses traversal paths and never silently replaces a modified existing file.
`--verify-only` checks archives without extracting. Download the thirteen ZIPs
and their manifest from the release page first; the helper performs no network
or credential access.

The raw official dataset is deliberately obtained from Figshare rather than
duplicated in GitHub; download code, URLs, licence and official checksums are
published. Run `src/download_external.py --manifest reports/mslesseg_case_manifest_local.json`
to generate a manifest for your machine without overwriting the frozen historical
manifest. Use a fresh output directory for any rerun.

Saved historical JSON records and source manifests retain their original absolute
machine paths as provenance. Opening the relative-link dashboard requires only
the extracted release. Original saved-run validation was performed on the original
workspace; the recorded 155,498 checks are not a claim that unchanged absolute-path
validation works on an arbitrary clone. For new experiments, use the newly generated
local manifest. Frozen sources are preserved in `sources/external_validation_frozen/`
within the support ZIP to interpret original source hashes despite Git EOL handling.

The 127-test canonical result precedes packaging. Repository portability tests are
run separately after adding the external modules. Functional tests and file checks
do not establish clinical accuracy or historical result authenticity.

MSLesSeg expert annotations concern **MS lesions, not tumours**. See
`DATA_ATTRIBUTION.md`. The original and rewritten manuscript drafts remain in the
repository; the commented-review DOCX, environments, caches and credentials remain
excluded. No new scientific experiment is part of this publication snapshot.
