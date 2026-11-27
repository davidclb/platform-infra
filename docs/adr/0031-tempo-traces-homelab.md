# ADR 0031: Traces on the homelab — Tempo (single-binary) + Alloy OTLP, deployed by Flux

## Status

Accepted

## Context

The ADR 0027 amendment (2026-11-24) moved traces for Ghamr into scope, after
metrics and logs: Ghamr's slow requests spend their time in external calls
and subprocesses (yt-dlp, ffmpeg, LLM providers, SQLite), which is exactly
what distributed traces measure. Metrics say *that* a route is slow, logs
say *what* happened, a trace says *where* the time went inside one request
(the 504 incident, Ghamr ADR 0021, would have shown the Speechmatics span in
one trace). The app side is ready: `otlptracehttp` in go.mod, server spans +
per-external-call spans, `trace_id` in every log line, exemplars on the
latency histogram (OpenMetrics).

## Decision

1. **Tempo single-binary** (chart `grafana/tempo` 1.24.4, app 2.9.0, image
   pinned by digest `sha256:65a57897…` verified on Docker Hub): local PVC
   10 Gi, retention bounded at **7 days** (`tempo.retention: 168h`, same as
   Loki) — traces are the biggest signal per byte, cap the disk. OCI object
   storage later, same as Loki/Prometheus (values change only).
2. **Alloy receives OTLP and forwards to Tempo**: `otelcol.receiver.otlp`
   on 4317 (gRPC) / 4318 (HTTP) → `otelcol.exporter.otlp` →
   `tempo.observability.svc:4317` (insecure, cluster-internal). Ghamr sends
   to Alloy `:4318` (HTTP, no sidecar needed in the pod). Config in the
   Alloy HelmRelease values (River), per the official Alloy otelcol docs.
3. **Flux layout** (ADR 0023): `infra/observability/tempo/` +
   `flux/TempoKustomization.yml` (`dependsOn: observability-sources`);
   `alloy` now `dependsOn: [loki, tempo]`.
4. **Grafana data source Tempo as code**: `additionalDataSources` entry
   (`uid: tempo`, `http://tempo.observability.svc.cluster.local:3100`) next
   to Loki in the kube-prometheus-stack release.yaml.
5. **Correlation**: Grafana links traces ↔ logs via `trace_id` (in the log
   lines) and metrics ↔ traces via exemplars on the latency histogram —
   one dashboard can jump from a slow route to its trace to its error logs.
6. **CI**: the `observability:helm-template` job (added with Loki) render-
   checks the tempo release automatically — no extra wiring.

## Alternatives considered

- **Tempo distributed (ingester/distributor/querier/…) with object storage** —
  rejected for a 2-node homelab: single-binary is Tempo's own recommended
  small-install mode; the distributed mode is the later scale-up, a values
  change.
- **Jaeger** — rejected: Tempo is the Grafana-native stack (same project as
  Loki/Alloy/Grafana), one datasource in Grafana, exemplars already emitted.
- **Traces to Grafana Cloud** — rejected: third-party data, less skill
  (same reasoning as ADR 0026/0030).

## Consequences

- Traces queryable in Grafana (Explore → Tempo), correlatable with logs
  (`trace_id`) and metrics (exemplars) — the full three-signal picture on
  the homelab: Prometheus (metrics) + Loki (logs) + Tempo (traces), all in
  one Grafana, all as code.
- 10 Gi PVC + 7d retention bounds disk; watch the USE dashboard (01).
- Rollback: delete the tempo Kustomization (prune) + remove the OTLP
  blocks from Alloy + the Tempo datasource from release.yaml.

## References (official)

- Tempo Helm chart (single binary mode) — https://grafana.com/docs/tempo/latest/setup/helm-chart/
- Tempo retention — https://grafana.com/docs/tempo/latest/configuration/#retention
- Alloy otelcol receiver/exporter — https://grafana.com/docs/alloy/latest/reference/components/otelcol/
- OpenTelemetry traces — https://opentelemetry.io/docs/concepts/signals/traces/
- ADR 0027 (+ amendment 2026-11-24: traces for Ghamr), ADR 0030 (Loki/Alloy), ADR 0023 (flux/ layout)
