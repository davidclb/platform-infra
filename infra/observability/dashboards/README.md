# Grafana dashboards as code (ADR 0028)

The Grafana sidecar (from kube-prometheus-stack, namespace `observability`)
imports every ConfigMap labelled `grafana_dashboard: "1"` in that namespace:
each `*.json` key under `data` becomes a dashboard. `allowUiUpdates: false`
makes provisioned dashboards read-only in the UI — Git is the source of truth.

## Add a dashboard

1. Drop `<name>.yaml` here: ConfigMap, `namespace: observability`,
   label `grafana_dashboard: "1"`, annotation `grafana_folder: "Homelab"`
   (folders are flat in Grafana OSS — one folder "Homelab" for everything,
   order comes from the title prefix, see below), dashboard JSON under a
   `*.json` data key.
2. Naming rules (as-code organisation):
   - `uid`: stable, kebab-case, never change it (changing uid = Grafana
     creates a NEW dashboard instead of updating)
   - `title`: prefix with `NN — ` (Grafana sorts alphabetically by title):
     `01 — Homelab — cluster overview (USE)`, `02 — Ghamr RED`, …
   - `tags`: e.g. ["homelab", "kubernetes", "use"] for search filters
3. CI (`observability:dashboards` job) validates the JSON (schemaVersion,
   unique uid, title, panels). Commit, push, MR.
4. Flux (`observability-dashboards`, prune: true) applies it; removing the
   file from Git removes the dashboard from Grafana.

Panels are written by hand (USE for infra/cluster, RED for apps, tier-1
Proxmox via pve-exporter later) — Grafana best practices, never clicked in
the UI.

Official docs:
- Provisioning dashboards — https://grafana.com/docs/grafana/latest/administration/provisioning/#dashboards
- Dashboard best practices (RED/USE) — https://grafana.com/docs/grafana/latest/dashboards/build-dashboards/best-practices/
- grafana chart sidecar values — https://github.com/grafana/helm-charts/tree/grafana-14.5.0/charts/grafana
