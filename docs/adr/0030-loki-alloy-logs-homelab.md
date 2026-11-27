# ADR 0030: Logs on the homelab — Loki (monolithic) + Alloy (DaemonSet), deployed by Flux, local storage, bounded retention

## Status

Accepted

## Context

ADR 0027 scoped the homelab observability stack to metrics + logs now,
traces later, one isolated stack per environment, deployed by Flux, local
PVC storage first. Metrics landed with `kube-prometheus-stack` (ADR 0028 for
the dashboards). Logs now: Loki + Alloy. Ghamr already writes structured
logs with a `request_id` (and will add `trace_id` for the traces step).

## Decision

1. **Loki, deployment mode `Monolithic`** (chart `grafana/loki` 7.7.0, app
   3.6.20, image pinned by digest `sha256:be040ec9…` verified on Docker
   Hub): one replica, filesystem storage on a local PVC (10 Gi).
   SimpleScalable (read/write/backend/gateway) is overkill on a 2-node
   homelab; monolithic is Loki's own recommendation for small installs.
   `auth_enabled: false` — ClusterIP only, same trust zone as Grafana.
2. **Bounded retention: 7 days** (`tableManager.retention_period: 168h`,
   deletes enabled). Logs are bigger than metrics (Prometheus is at 15d);
   disk use stays capped on the homelab. OCI object-storage backend is the
   later migration (same as ADR 0027's Loki note), a values change only.
3. **Alloy in DaemonSet** (chart `grafana/alloy` 1.16.0, app v1.22.0,
   digest `sha256:9acc2529…`): collects `/var/log/pods` of every pod
   (`loki.source.kubernetes`, labels pod/namespace/container/app) and
   pushes to `http://loki.observability.svc:3100`. Config River in the
   HelmRelease values, following the official Alloy Kubernetes guide.
4. **Deployed by Flux** (ADR 0023 layout): `infra/observability/sources/`
   (HelmRepository grafana-charts) → `loki/` → `alloy/`, chained with
   `dependsOn` (ns → sources → loki → alloy: Alloy pushes to Loki, so Loki
   first). Kustomizations: `observability-sources`, `loki`, `alloy`.
5. **Grafana data source Loki as code**: `grafana.additionalDataSources` in
   the kube-prometheus-stack `release.yaml` (`uid: loki`, url
   `http://loki.observability.svc.cluster.local:3100`). Tempo's data source
   is added here too at the traces step.
6. **Traces next (not here)**: Tempo monolithic + Alloy OTLP receiver
   (4317/4318) → Tempo, `trace_id` in logs, exemplars on the latency
   histogram — per the ADR 0027 amendment.

## Alternatives considered

- **SimpleScalable Loki** (separate read/write/backend + gateway) — rejected:
  4+ components on a 6 Gi master for no benefit at this scale.
- **Loki on object storage (OCI) from day one** — deferred (ADR 0027):
  prove the pipeline on local PVC first, migrate the backend after — a
  values change, not a re-architecture.
- **Grafana Agent / Fluent Bit instead of Alloy** — rejected: Alloy is
  Grafana's unified OTel collector (logs + traces + metrics later), one
  agent for the whole pipeline; the ADR 0027 amendment already names Alloy.
- **Hosted logging (Grafana Cloud)** — rejected: sends data to a third party,
  builds less of the skill (same reasoning as ADR 0026).

## Consequences

- Logs of every pod (incl. Ghamr) queryable in Grafana via Loki
  (`{app="ghamr"} | json`), correlatable with metrics by time, and soon by
  `trace_id`.
- 10 Gi PVC + 7d retention bounds the disk; watch `node_filesystem` on the
  "01 — cluster overview (USE)" dashboard.
- Rollback: remove the two Kustomizations (prune deletes Loki/Alloy); the
  Loki data source stays but has no backend until re-added.

## References (official)

- Loki Helm chart (deployment modes, monolithic) — https://grafana.com/docs/loki/latest/setup/install/helm/
- Loki retention — https://grafana.com/docs/loki/latest/storage/#retention
- Alloy, collect Kubernetes logs — https://grafana.com/docs/alloy/latest/collect-logs/kubernetes/
- ADR 0027 (stack by Flux, local storage first), ADR 0023 (flux/ layout), ADR 0028 (dashboards as code)
