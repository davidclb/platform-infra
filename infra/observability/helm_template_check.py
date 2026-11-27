#!/usr/bin/env python3
"""Render-check every HelmRelease under infra/observability/*/release.yaml.

For each release.yaml: extract spec.values, run `helm template` for the
chart@version from its HelmRepository, and parse the rendered YAML.
This catches bad values and chart-side validation errors (validate.yaml)
WITHOUT a cluster — the same local loop: extract -> helm template -> read
the error -> fix -> re-render -> inspect the rendered objects.

Used by the CI job `observability:helm-template` (infra/observability/ci.yml)
and runnable locally:
    mise exec -- helm repo add grafana https://grafana.github.io/helm-charts
    python3 infra/observability/helm_template_check.py
"""
import pathlib
import subprocess
import sys

import yaml

# HelmRepository metadata.name -> helm repo name used by `helm template`
REPO_MAP = {
    "grafana-charts": "grafana",
    "prometheus-community": "prometheus-community",
}


def main() -> None:
    root = pathlib.Path(__file__).resolve().parent
    releases = sorted(root.glob("*/release.yaml"))
    if not releases:
        print(f"FAIL: no release.yaml under {root}")
        sys.exit(1)
    failures = 0
    vfile = pathlib.Path("/tmp/helm-check-values.yaml")
    for rel in releases:
        # a release.yaml may hold several documents (HelmRepository + HelmRelease)
        docs = [x for x in yaml.safe_load_all(rel.read_text()) if x]
        d = next((x for x in docs if x.get("kind") == "HelmRelease"), None)
        if d is None:
            print(f"FAIL {rel}: no HelmRelease document")
            failures += 1
            continue
        cs = d["spec"]["chart"]["spec"]
        chart, version = cs["chart"], cs["version"]
        repo = REPO_MAP.get(cs["sourceRef"]["name"], cs["sourceRef"]["name"])
        name = rel.parent.name
        vfile.write_text(yaml.safe_dump(d["spec"].get("values") or {}))
        print(f"== {name}: {repo}/{chart}@{version}")
        r = subprocess.run(
            ["helm", "template", name, f"{repo}/{chart}", "--version", version,
             "--namespace", "observability", "--values", str(vfile)],
            capture_output=True, text=True,
        )
        if r.returncode != 0:
            err = r.stderr.strip().splitlines()
            print(f"FAIL {name}: {err[-1] if err else 'helm template failed'}")
            failures += 1
            continue
        docs = [x for x in yaml.safe_load_all(r.stdout) if x]
        kinds = sorted({x.get("kind", "?") for x in docs})
        print(f"OK {name}: {len(docs)} objects rendered ({', '.join(kinds)})")
    print(f"{'FAIL' if failures else 'OK'}: {len(releases) - failures}/{len(releases)} releases render")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
