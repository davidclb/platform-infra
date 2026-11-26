# ADR 0028: Grafana dashboards as code — sidecar ConfigMaps, deployed by Flux

## Status

Accepted

## Context

ADR 0016 requires dashboards to be "managed as code (JSON provisioning, not
hand-clicked and left unversioned)", and ADR 0027 deployed
`kube-prometheus-stack` (chart 93.9.0, Grafana subchart 14.5.0) via Flux in
the `observability` namespace — but no dashboard mechanism was wired up:
`release.yaml` declared no `grafana.sidecar.dashboards` values and no
dashboard existed in the repo. Without this, Grafana would only show the
chart's default dashboards, and any custom dashboard would be created by
hand in the UI — unversioned, unreviewable.

The chart's Grafana sidecar already supports the standard pattern: it loads
every ConfigMap labelled `grafana_dashboard: "1"` (chart defaults: `label`
`grafana_dashboard`, `labelValue` `"1"`, `searchNamespace: null` = the
sidecar's own namespace) and imports each `*.json` key under `data` as a
dashboard. In grafana chart 14.5.0, `provider.allowUiUpdates` defaults to
`false` — provisioned dashboards are read-only in the UI, which is exactly
"as code".

## Decision

1. **Provision dashboards from ConfigMaps via the built-in sidecar** — no
   extra component. Layout: `infra/observability/dashboards/` holds one
   ConfigMap per dashboard (`label grafana_dashboard: "1"`,
   `namespace: observability`, JSON under a `*.json` data key) plus a
   `kustomization.yaml`.
2. **A dedicated Flux Kustomization** `observability-dashboards`
   (`flux/ObservabilityDashboardsKustomization.yml`, `path:
   ./infra/observability/dashboards`, `prune: true`, `dependsOn:
   observability`) — the same pointer pattern as every other `flux/` entry
   (ADR 0023). `prune: true` + `disableDelete: false` means Git is the
   complete source of truth: removing a file removes the dashboard.
3. **Pin the sidecar values explicitly in `release.yaml`** (they are chart
   defaults) so the mechanism is visible and defensible in review:
   `enabled: true`, `label: grafana_dashboard`, `labelValue: "1"`,
   `searchNamespace: observability`, `provider.allowUiUpdates: false`,
   `disableDelete: false`.
4. **CI guardrail (Rule #0, guardrail 3):** job `observability:dashboards`
   (`infra/observability/ci.yml`, on `changes: [infra/observability/**]`)
   validates every dashboard ConfigMap via `validate_dashboards.py`: label
   present, namespace `observability`, every `*.json` parses as JSON with
   integer `schemaVersion`, unique `uid`, non-empty `title`, `panels` list.
   The full conftest/Kyverno layer over `infra/` remains a separate
   follow-up.
5. **Panels are written by hand** (USE for infra, RED for apps — Grafana
   best practices), never clicked in the UI.

## Alternatives considered

- **Grafana Operator (CRD `GrafanaDashboard`)** — rejected: one more operator
  to run on a 6 Gi master, for a solo lab; the sidecar needs no new component.
- **Inline dashboards in Helm values (`grafana.dashboards`)** — rejected:
  big JSON blobs inside `release.yaml`, hard to review line by line in an MR.
- **Grafana Foundation SDK** (typed builders in Go/TS/Python, `build()` →
  JSON → API/CLI/CI) — rejected *for now*: adds a build step between Git and
  Grafana and is aimed at teams industrializing many dashboards (SDK is
  "public preview"). Re-evaluate when Ghamr exposes many metrics and several
  RED dashboards exist. Source: https://github.com/grafana/grafana-foundation-sdk
- **Hand-made dashboards in the UI** — rejected by ADR 0016: unversioned,
  and `allowUiUpdates: false` makes them read-only anyway.

## Consequences

- Adding a dashboard = one new file + one line in `kustomization.yaml`, then
  MR; Flux applies it and the sidecar imports it within minutes.
- Removing a file prunes the dashboard from Grafana (`prune` +
  `disableDelete: false`).
- Dashboard JSON is validated in CI before merge.
- The first dashboard is a placeholder shell; the real panels (cluster USE,
  then Ghamr RED once `/metrics` exists, then tier-1 Proxmox via
  pve-exporter) are written by the repo owner.

## Follow-ups

- RED dashboard for Ghamr once the app exposes `/metrics` (ServiceMonitor
  via the `feat/web-app-metrics-port` chart work).
- Loki (logs) and Tempo/OTLP (traces) datasources + dashboards when those
  stacks land (ADR 0027, S50) — same provisioning mechanism.
- Tier-1 Proxmox: pve-exporter on the Proxmox host, scraped by the same
  Prometheus (ADR 0016 tier 1).
- Tier-3 (Hostinger) Grafana: dashboards provisioned from files too (ADR 0026).
- `searchNamespace: ALL` if dashboards ever live outside `observability`.
- conftest/Kyverno policy layer over all of `infra/`.

## References (official)

- Grafana — Provision dashboards (file providers) — https://grafana.com/docs/grafana/latest/administration/provisioning/#dashboards
- Grafana — Dashboard best practices (RED / USE / Four Golden Signals) — https://grafana.com/docs/grafana/latest/dashboards/build-dashboards/best-practices/
- grafana Helm chart 14.5.0 values (sidecar defaults) — https://github.com/grafana/helm-charts/tree/grafana-14.5.0/charts/grafana
- kube-prometheus-stack chart 93.9.0 — https://github.com/prometheus-community/helm-charts/tree/kube-prometheus-stack-93.9.0/charts/kube-prometheus-stack
- Grafana Foundation SDK — https://github.com/grafana/grafana-foundation-sdk
- ADR 0016 (dashboards as code requirement), ADR 0023 (flux/ pointer layout), ADR 0027 (stack deployed by Flux)
