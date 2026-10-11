"""Add reproducible study-navigation links to the generated local dashboard.

The primary tables and measured results are unchanged. Paths are derived from the
workspace layout, and every linked artifact must exist before this index is saved.
"""
from __future__ import annotations

import argparse
import html
import os
import re
from pathlib import Path
from urllib.parse import quote


def add_studies(run, studies, diagnostic):
    """Read an existing dashboard and append an idempotent artifact index panel."""
    run, studies, diagnostic = (Path(path).resolve() for path in (run, studies, diagnostic))
    workspace = Path(__file__).resolve().parents[1]
    reports = run.parent / "reports"
    dashboard = reports / "VIEW_EXTERNAL_RESULTS.html"
    links = [
        ("Completed execution and interpretation", reports / "COMPLETE_EXTERNAL_VALIDATION.md"),
        ("Dataset access and suitability ranking", workspace / "reports/external_dataset_access_20261011.md"),
        ("Protocol and reporting qualifications", workspace / "reports/external_validation_protocol_20261011.md"),
        ("Source code and reproduction commands", workspace / "EXTERNAL_VALIDATION_README.md"),
        ("Independent saved-mask validation", reports / "external_validation_full.json"),
        ("Saved HTML and JavaScript audit", reports / "external_html_validation.json"),
        ("Registration and noise study definitions", studies / "README.md"),
        ("Registration individual measurements", studies / "registration/runs.csv"),
        ("Controlled-noise individual measurements", studies / "controlled_noise/runs.csv"),
        ("Controlled-noise paired quality differences", studies / "controlled_noise/paired_quality_differences.csv"),
        ("Post hoc objective/localization interpretation", diagnostic / "POSTHOC_OBJECTIVE_LOCALIZATION_CONCLUSIONS.md"),
        ("Post hoc patient objective/Dice values", diagnostic / "patient_seed_means.csv"),
        ("First numeric patient's 3D comparison", run / "P1_T1/meshes/interactive_prediction_reference.html"),
    ]
    images = [
        ("First numeric patient: predicted threshold mask versus supplied expert lesions", run / "P1_T1/preview3D.png"),
        ("Controlled-noise quality; error bars are SD over three patient means", studies / "controlled_noise/quality_summary.png"),
        ("First patient's controlled rigid registration, modified EHO seed 0", studies / "registration/anatomical_P1_T1__modified_eho__seed0.png"),
        ("Post hoc objective/localization diagnostic; one point per patient", diagnostic / "patient_paired_objective_vs_dice.png"),
    ]

    def relative(path):
        if not path.is_file():
            raise FileNotFoundError("Index artifact does not exist: " + str(path))
        return html.escape(quote(os.path.relpath(path, reports).replace(os.sep, "/")), quote=True)

    panel = ['<!-- EXTERNAL_STUDY_NAV_START -->', '<div class="panel"><h2>Additional studies and evidence</h2>',
             '<p class="note">The following studies are separate from the frozen primary lesion analysis. '
             'Expert references are supplied annotations. Successful exports do not imply accurate detection.</p>', '<ul>']
    panel += [f'<li><a href="{relative(path)}">{html.escape(label)}</a></li>' for label, path in links]
    panel += ['</ul>']
    panel += [f'<figure><a href="{relative(path)}"><img src="{relative(path)}" alt="{html.escape(label, quote=True)}" '
              f'style="max-width:100%;height:auto" loading="lazy"></a><figcaption>{html.escape(label)}</figcaption></figure>'
              for label, path in images]
    panel += ['</div>', '<!-- EXTERNAL_STUDY_NAV_END -->']
    document = dashboard.read_text(encoding="utf-8")
    document = re.sub(r'<!-- EXTERNAL_STUDY_NAV_START -->.*?<!-- EXTERNAL_STUDY_NAV_END -->\s*',
                      '', document, flags=re.S)
    if document.count("</html>") != 1:
        raise ValueError("Dashboard must have one closing html tag")
    dashboard.write_text(document.replace("</html>", "\n".join(panel) + "\n</html>"), encoding="utf-8")
    print(f"Added {len(links)} evidence links and {len(images)} figures: {dashboard}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--studies", required=True, type=Path)
    parser.add_argument("--diagnostic", required=True, type=Path)
    arguments = parser.parse_args()
    add_studies(arguments.run, arguments.studies, arguments.diagnostic)
