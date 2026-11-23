# ADR 0027: Homelab observability (tiers 1–2) — metrics + logs, deployed by Flux, local storage first

## Status
Proposed — refines ADR 0016 (observability tiers) for the homelab, and
updates its "eventually through ArgoCD" note to Flux.

## Context

ADR 0016 accepted `kube-prometheus-stack` inside the K3s cluster for the
homelab (tiers 1–2), removed the dedicated monitoring VM, and said it
would be deployed "eventually through ArgoCD like other cluster
workloads". Two things have since become clearer and need to be recorded
before the first chart is deployed:

1. The repo's actual GitOps split is **Flux = cluster tooling / ArgoCD =
   developers' apps** (ADR 0023). ArgoCD itself, CloudNativePG and the
   SOPS secrets are all deployed by Flux today; ArgoCD only manages
   application workloads (Ghamr).
2. ADR 0016's three tiers are isolated and not federated. This ADR only
   covers tiers 1–2 (the homelab). Tier 3 (Hostinger, docker-compose) is
   ADR 0026.

The three signals of observability (metrics, logs, traces) do not have
the same value or cost on this homelab today. Ghamr/Yoshu are not yet
microservices, so distributed traces would mostly record a single-process
path — low return for the cost of instrumenting application code by hand
(zero-AI rule on the app repos). Metrics and logs, by contrast, give both
"what is wrong" (metrics, and the DORA basis) and "why" (logs, including
what happens when a security brick is attacked in the lab — Rule #0.5).

## Decision

1. **Deploy the homelab observability stack with Flux, not ArgoCD.**
   This updates ADR 0016's "eventually through ArgoCD" note. Rationale:
   `kube-prometheus-stack` is cluster tooling — it ships the Prometheus
   Operator and CRDs (`ServiceMonitor`/`PodMonitor`), not an application.
   ArgoCD is itself deployed by Flux; making observability depend on the
   app-layer (ArgoCD) would invert the dependency. Flux `HelmRelease` +
   `HelmRepository`, consistent with how Postgres and ArgoCD are managed.

2. **Scope: metrics + logs now, traces later.** Metrics via
   `kube-prometheus-stack` (Prometheus, Grafana, Alertmanager, Prometheus
   Operator, node-exporter, kube-state-metrics). Logs via Loki + Alloy
   (Alloy as the log collector / Grafana's unified agent). Traces (Tempo +
   OTLP) are deferred until Ghamr/Yoshu become microservices — revisit
   then, because that is where distributed tracing earns its cost.

3. **One isolated stack per environment (confirms ADR 0016).** This
   homelab stack is independent of tier 3 (Hostinger) and not federated.
   A central/aggregated view (remote write or federation) is a later,
   reversible evolution if it is ever needed.

4. **Local storage (PVC) first; object storage later.** Prometheus and
   Loki persist to homelab PersistentVolumes with an explicitly bounded
   retention (`--storage.tsdb.retention.time` for Prometheus; a retention
   period for Loki), so disk use is capped. Loki's native object-storage
   backend (S3-compatible, e.g. Oracle OCI where the Terraform state
   already lives) is a later migration — a change of Loki `values`, not a
   re-architecture, deliberately kept reversible. Accepted trade-off: data
   is lost on a homelab teardown, consistent with "the homelab is the lab"
   (ADR 0024) and with the external probe being what reports a dead
   cluster from outside.

5. **Layout and naming: `observability`, not `monitoring`.** Manifests
   under `infra/observability/`, Kubernetes namespace `observability`.
   "Observability" is the broader term (asking new questions from
   metrics+logs+traces), vs "monitoring" (watching known thresholds); the
   stack covers more than monitoring. The stray `infra/monitoring/`
   directory (dead duplicate copies of the ArgoCD manifests, reconciled by
   nothing) was removed when this was decided.

## Consequences

- A new scrape target is added as a `ServiceMonitor`/`PodMonitor` CRD, not
  by editing a Prometheus config file — the K8s-native workflow ADR 0016
  chose on purpose (interview-relevant).
- Grafana exposure and auth, and the exact retention windows, are left to
  the deployment step (see Follow-ups) — this ADR fixes the architecture,
  not every value.
- DORA metrics: deployment frequency and lead time come from Git/CI (no
  app instrumentation); time to restore needs failure detection (external
  probe). The app `/metrics` instrumentation (Ghamr) is a separate,
  zero-AI, app-repo task — not a prerequisite to start DORA.
- If K3s goes down, this stack goes down with it (accepted, per ADR 0016):
  a dead cluster observed from outside is not more useful than an
  already-known outage; the external probe covers "is it up".

## Alternatives considered

- **ArgoCD for the stack (ADR 0016 as written).** Rejected: inverts the
  Flux-infra / ArgoCD-apps boundary and makes observability depend on the
  app-layer. Flux is the tooling plane here.
- **Traces/Tempo/OTLP now.** Rejected for a non-microservices app: low
  value on a monolith, and would require hand-instrumenting Ghamr/Yoshu
  (zero-AI) for little return. Revisit at the microservices switch.
- **Loki on object storage from day one.** Deferred, not rejected: it is
  Loki's normal production backend and a good interview point, but adds a
  bucket + credentials (another SOPS secret) and a second thing to debug
  alongside the log pipeline. Prove the pipeline locally first, migrate
  the backend after.
- **A hosted service (Grafana Cloud free tier).** Less to run, but sends
  data to a third party and builds less of the skill this repo is for
  (same reasoning as ADR 0026).

## Follow-ups (not decided here)

- Retention windows (days) for Prometheus and Loki.
- Grafana exposure (via the cloudflared tunnel now in GitOps — ADR 0021 /
  the `networking` namespace) vs ingress, and Grafana auth.
- Loki backend migration to OCI object storage.
- Ghamr: add a `/metrics` endpoint (application code, Ghamr repo, by hand).
- Alertmanager routing / notification channel.
- Traces (Tempo + OTLP) at the microservices switch.

## References (official)

- ADR 0016 (observability tiers), ADR 0023 (Flux/ArgoCD repo layout),
  ADR 0024 (homelab-is-the-lab), ADR 0026 (Hostinger tier-3 stack).
- kube-prometheus-stack — https://github.com/prometheus-community/helm-charts/tree/main/charts/kube-prometheus-stack
- Prometheus storage & retention — https://prometheus.io/docs/prometheus/latest/storage/
- Prometheus Operator (ServiceMonitor/PodMonitor) — https://prometheus-operator.dev/docs/user-guides/getting-started/
- Grafana Loki — https://grafana.com/docs/loki/latest/
- Grafana Alloy — https://grafana.com/docs/alloy/latest/
- Flux HelmRelease — https://fluxcd.io/flux/components/helm/helmreleases/

## Assisted-by
Claude Opus 4.8 — ADR drafted from the decisions taken in session;
architecture choices made by the repo owner.
