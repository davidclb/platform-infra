# ADR 0016: Observability strategy — three tiers, no separate monitoring VM

## Status
Accepted

## Context
`monitoring.tf` had already been written (VM at `.115`, following the
same pattern as `k3s-master`/`vault-01`), intending to install Prometheus,
Grafana, and Loki as standalone packages/binaries on a dedicated VM —
mirroring the reasoning already applied to Vault (ADR 0010): keep a
service available even if K3s itself breaks during experimentation.

That reasoning doesn't transfer cleanly to monitoring. Vault must survive
a cluster outage because it's needed to *recover* the cluster (secrets,
diagnostics). Monitoring's job is to *observe* the cluster — a monitoring
stack that lives outside K3s can still observe it externally, but the
roadmap's own target (`kube-prometheus-stack`) is a Kubernetes-native
Helm chart, not a standalone binary install, and industry practice
confirms this is the standard approach: it deploys Prometheus, Grafana,
Alertmanager and the Prometheus Operator together, discovers scrape
targets automatically via `ServiceMonitor`/`PodMonitor` CRDs, and is
designed to be managed as Kubernetes YAML — which fits this repo's
GitOps/ArgoCD strategy directly, unlike a hand-configured external stack.

## Decision
Deploy `kube-prometheus-stack` via Helm, inside the K3s cluster —
eventually through ArgoCD like other cluster workloads. `monitoring.tf`
(the dedicated VM) is removed; no separate monitoring VM is provisioned.

## Consequences
- Monitoring config becomes Kubernetes YAML/Helm values managed in this
  repo, consistent with how Ghamr and other apps will be deployed (ADR
  0008) — not a separately-maintained Ansible playbook targeting a VM.
- Adding a new scrape target later means adding a `ServiceMonitor`
  resource, not editing a Prometheus config file on a VM by hand — this
  is deliberately the K8s-native workflow, and the reason it was chosen:
  it's what the pattern actually tests in an interview context.
- If K3s itself goes down, monitoring goes down with it — accepted here,
  unlike Vault, because observing a dead cluster from outside it isn't
  meaningfully more useful than an already-known outage, and the roadmap
  doesn't call for cross-cluster/federated monitoring at this stage.
- IP `.115` (reserved for `monitoring` in ADR 0014) is freed up; ADR 0014
  should be updated to reflect this if a future host needs that address.

## Addendum: the three observability tiers

This repo spans three genuinely different things to observe, each with
its own stack — not one unified solution, because each tier has a
different failure domain and a different native tool for it.

```
┌─────────────────────────────┐  ┌─────────────────────────────┐  ┌─────────────────────────────┐
│ 1. HOMELAB / PROXMOX HOST    │  │ 2. K3S CLUSTER + NETWORK     │  │ 3. HOSTINGER / GHAMR (prod)  │
│                              │  │                              │  │                              │
│ What: the hypervisor itself  │  │ What: pods, nodes, cluster   │  │ What: Ghamr the app, its     │
│ — VMs/LXC up or down, host   │  │ network, k8s-native workloads│  │ host VM, and its own network │
│ CPU/RAM/disk, hardware       │  │                              │  │ exposure (errors, latency,   │
│ sensors                      │  │                              │  │ client geolocation)          │
│                              │  │                              │  │                              │
│ Tool: pve-exporter (on the   │  │ Tool: kube-prometheus-stack  │  │ Tool: Prometheus + Grafana + │
│ Proxmox host) → scraped by   │  │ (Helm, in-cluster) — Prom-   │  │ Node Exporter + cAdvisor,    │
│ the SAME Prometheus as tier 2│  │ etheus + Grafana + Alert-    │  │ added as extra services in   │
│                              │  │ manager + Operator, targets  │  │ Ghamr's existing              │
│ Dashboard: Grafana community │  │ via ServiceMonitor/PodMonitor│  │ docker-compose.yml (no K8s   │
│ dashboard #10347             │  │                              │  │ on Hostinger)                │
│                              │  │ Dashboard: same Grafana      │  │                              │
│                              │  │ instance as tier 1           │  │ Ghamr itself must expose a   │
│                              │  │                              │  │ Prometheus /metrics endpoint │
│                              │  │                              │  │ (application-level: request  │
│                              │  │                              │  │ counts, error codes, latency)│
│                              │  │                              │  │ — that's app code, done in   │
│                              │  │                              │  │ the Ghamr repo, not here     │
│                              │  │                              │  │                              │
│                              │  │                              │  │ Client IP geolocation is NOT │
│                              │  │                              │  │ a metrics concern — handled  │
│                              │  │                              │  │ via Loki + log enrichment,   │
│                              │  │                              │  │ separately from Prometheus   │
└─────────────────────────────┘  └─────────────────────────────┘  └─────────────────────────────┘
        one Prometheus scrapes both tier 1 and 2                    a SEPARATE Prometheus/Grafana
        (same K3s cluster, two scrape targets)                      stack, independent of the
                                                                      homelab's — different failure
                                                                      domain, different host
```

Key design choices this implies:
- Tiers 1 and 2 share **one** Prometheus/Grafana (the homelab's), because
  they're the same failure domain — if the homelab is up, both are
  observable together.
- Tier 3 is a **fully separate** Prometheus/Grafana stack living on
  Hostinger itself, in Docker Compose — not connected to or federated
  with the homelab's stack. Ghamr's production observability must not
  depend on the homelab being up, and vice versa.
- No cosmetic "homelab portal" dashboard (Homarr/Homepage/Dashy-style)
  is used anywhere — those solve link/status aggregation, not metrics,
  and don't build the Prometheus/Grafana skill this repo is optimizing
  for. Grafana alone covers what's needed.
- Dashboards are managed as code (JSON provisioning, loaded by Grafana
  from files/Helm values — not hand-clicked and left unversioned), so the
  same authoring skill and even the same dashboard *patterns* (RED
  metrics for an API, USE metrics for infra) carry over between all three
  tiers and to a future employer's stack.
- `k9s` is a separate, complementary tool — interactive terminal
  exploration/debugging of the live cluster state, no history. It doesn't
  replace Grafana's persistent, historical view, and isn't part of the
  "observability stack" proper; it's a local CLI tool on the operator's
  laptop.
