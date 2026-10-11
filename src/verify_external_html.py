"""Verify saved local viewer data, dashboard links and JavaScript syntax.

This is a file audit, not a browser test. It never executes the HTML or contacts
a network service. Quantitative overlap is checked separately from saved masks.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import shutil
import subprocess
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

import numpy as np


class Page(HTMLParser):
    """Collect script text and linked local artifacts without executing a page."""
    def __init__(self):
        super().__init__()
        self.scripts, self.links, self.external_scripts = [], [], []
        self.current = None

    def handle_starttag(self, tag, attributes):
        attributes = dict(attributes)
        if tag == "script":
            if attributes.get("src"):
                self.external_scripts.append(attributes["src"])
            self.current = []
        if tag == "a" and attributes.get("href"):
            self.links.append(attributes["href"])

    def handle_data(self, text):
        if self.current is not None:
            self.current.append(text)

    def handle_endtag(self, tag):
        if tag == "script" and self.current is not None:
            self.scripts.append("".join(self.current))
            self.current = None


def numeric_array(value):
    """Decode Plotly's JSON list or typed binary array representation."""
    if isinstance(value, dict):
        result = np.frombuffer(base64.b64decode(value["bdata"], validate=True),
                               dtype=np.dtype(value["dtype"]))
    else:
        result = np.asarray(value)
    if result.ndim != 1 or not np.isfinite(result).all():
        raise ValueError("Trace arrays must be finite one-dimensional values")
    return result


def trace_data(scripts):
    """Read the generated Plotly call's JSON payload, never evaluating JavaScript."""
    pattern = r'Plotly\.newPlot\(\s*[\"\'][^\"\']+[\"\']\s*,\s*'
    for script in reversed(scripts):
        match = re.search(pattern, script)
        if match:
            result, _ = json.JSONDecoder().raw_decode(script[match.end():])
            if not isinstance(result, list):
                raise ValueError("Plotly figure data must be a JSON trace list")
            return result, script
    raise ValueError("Generated Plotly JSON call not found")


def verify(run):
    run = Path(run).resolve()
    reports = run.parent / "reports"
    reports.mkdir(exist_ok=True)
    dashboard = reports / "VIEW_EXTERNAL_RESULTS.html"
    index = Page()
    index.feed(dashboard.read_text(encoding="utf-8"))
    failures, checks = [], 0

    def check(condition, detail):
        nonlocal checks
        checks += 1
        if not condition:
            failures.append(detail)

    local_links = []
    for link in index.links:
        parsed = urlsplit(link)
        if parsed.scheme or parsed.netloc or not parsed.path:
            continue
        target = (dashboard.parent / unquote(parsed.path)).resolve()
        local_links.append(str(target))
        check(target.is_file(), "Missing dashboard artifact: " + str(target))
    metadata = json.loads((run / "run_manifest.json").read_text(encoding="utf-8"))
    check(metadata["status"] == "completed", "Cohort is not completed")
    check(len(metadata["cases"]) == 115, "Expected all 115 case viewers")
    viewer_paths, vendor_hashes, first_plot_script = [], set(), None
    for case in metadata["cases"]:
        directory = run / case["case_id"] / "meshes"
        path = directory / "interactive_prediction_reference.html"
        viewer_paths.append(str(path))
        try:
            parser = Page()
            parser.feed(path.read_text(encoding="utf-8"))
            check(not parser.external_scripts, case["case_id"] + ": viewer depends on external script")
            traces, plot_script = trace_data(parser.scripts)
            if first_plot_script is None:
                first_plot_script = plot_script
            vendor = [script for script in parser.scripts if "plotly.js" in script[:1000].lower()]
            check(bool(vendor), case["case_id"] + ": bundled Plotly runtime absent")
            vendor_hashes.update(hashlib.sha256(script.encode("utf-8")).hexdigest() for script in vendor)
            meshes = json.loads((directory / "mesh_manifest.json").read_text(encoding="utf-8"))
            expected = {"Brain context (nonzero FLAIR foreground)": "image_foreground",
                        "Expert reference lesions (given labels)": "reference_lesion"}
            expected.update({method + " predicted threshold mask": method + "_prediction"
                             for method in metadata["methods"] + ["direct_otsu"]})
            expected = {name: slug for name, slug in expected.items() if meshes[slug]["status"] == "exported"}
            check(len(traces) == len(expected), case["case_id"] + ": trace count differs from saved meshes")
            check({trace["name"] for trace in traces} == set(expected), case["case_id"] + ": reference/prediction names mismatch")
            for trace in traces:
                detail = meshes[expected[trace["name"]]]
                check(trace["type"] == "mesh3d", case["case_id"] + ": wrong 3D trace type")
                coordinates = [numeric_array(trace[axis]) for axis in ("x", "y", "z")]
                triangles = [numeric_array(trace[axis]) for axis in ("i", "j", "k")]
                check(all(len(array) == detail["vertices"] for array in coordinates), case["case_id"] + ": HTML vertex count mismatch")
                check(all(len(array) == detail["faces"] for array in triangles), case["case_id"] + ": HTML face count mismatch")
                check(all(np.equal(array, np.floor(array)).all() and np.all((array >= 0) & (array < detail["vertices"]))
                          for array in triangles), case["case_id"] + ": invalid triangle vertex index")
        except Exception as error:
            failures.append(case["case_id"] + ": " + repr(error))
    check(len(vendor_hashes) == 1, "Bundled Plotly version differs across viewers")
    linked = set(local_links)
    check(set(viewer_paths).issubset(linked), "Dashboard does not link every completed case viewer")
    javascript_checks = []
    node = shutil.which("node")
    if node:
        snippets = [("dashboard", "\n".join(index.scripts)), ("viewer_setup", first_plot_script)]
        for name, snippet in snippets:
            path = reports / (name + "_syntax_checked.js")
            path.write_text(snippet or "", encoding="utf-8")
            result = subprocess.run([node, "--check", str(path)], capture_output=True,
                                    text=True, timeout=60)
            javascript_checks.append({"name": name, "exit_code": result.returncode, "stderr": result.stderr})
            check(result.returncode == 0, name + ": JavaScript syntax failure " + result.stderr)
    report = {"status": "passed" if not failures else "failed", "checks": checks,
              "case_viewers": len(viewer_paths), "local_dashboard_links": len(local_links),
              "plotly_vendor_sha256": sorted(vendor_hashes), "javascript_syntax_checks": javascript_checks,
              "failures": failures, "scope": "Saved HTML, JSON trace arrays, links and syntax; no browser interaction or rendering test"}
    (reports / "external_html_validation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("status", "checks", "case_viewers", "local_dashboard_links", "failures")}))
    return 0 if not failures else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, type=Path)
    raise SystemExit(verify(parser.parse_args().run))
