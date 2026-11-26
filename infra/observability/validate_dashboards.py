#!/usr/bin/env python3
"""Validate the Grafana dashboards provisioned as code (ADR 0028).

Every ConfigMap in infra/observability/dashboards/ must carry the
grafana_dashboard=1 label (the sidecar's selector) and live in the
observability namespace. Every *.json key in its data must be valid JSON
with the fields Grafana needs: schemaVersion (int), a unique uid, a title,
and a panels list.
"""
import json
import sys
from pathlib import Path

import yaml

DASHBOARDS_DIR = Path(__file__).resolve().parent / "dashboards"
LABEL = "grafana_dashboard"
NAMESPACE = "observability"


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    files = sorted(DASHBOARDS_DIR.glob("*.yaml")) + sorted(DASHBOARDS_DIR.glob("*.yml"))
    configmaps = []
    for f in files:
        for doc in yaml.safe_load_all(f.read_text()):
            if doc and doc.get("kind") == "ConfigMap":
                configmaps.append((f, doc))

    if not configmaps:
        fail(f"no ConfigMap found in {DASHBOARDS_DIR}")

    seen_uids = set()
    for f, cm in configmaps:
        meta = cm.get("metadata", {})
        labels = meta.get("labels", {})
        if labels.get(LABEL) != "1":
            fail(f"{f.name}: missing label {LABEL}=1 (sidecar selector)")
        if meta.get("namespace") != NAMESPACE:
            fail(f"{f.name}: namespace must be {NAMESPACE!r} (sidecar searchNamespace)")
        data = cm.get("data") or {}
        json_keys = [k for k in data if k.endswith(".json")]
        if not json_keys:
            fail(f"{f.name}: no *.json key under data")
        for key in json_keys:
            raw = data[key]
            try:
                dash = json.loads(raw)
            except json.JSONDecodeError as e:
                fail(f"{f.name}:{key}: invalid JSON ({e})")
            if not isinstance(dash, dict):
                fail(f"{f.name}:{key}: dashboard must be a JSON object")
            if not isinstance(dash.get("schemaVersion"), int):
                fail(f"{f.name}:{key}: missing integer schemaVersion")
            uid = dash.get("uid")
            if not uid or not isinstance(uid, str):
                fail(f"{f.name}:{key}: missing uid")
            if uid in seen_uids:
                fail(f"{f.name}:{key}: duplicate uid {uid!r}")
            seen_uids.add(uid)
            if not dash.get("title"):
                fail(f"{f.name}:{key}: missing title")
            if not isinstance(dash.get("panels"), list):
                fail(f"{f.name}:{key}: panels must be a list")
            print(f"OK: {f.name}:{key} — uid={uid} title={dash['title']!r} panels={len(dash['panels'])}")
    print(f"{len(configmaps)} ConfigMap(s), {len(seen_uids)} dashboard(s) valid")


if __name__ == "__main__":
    main()
