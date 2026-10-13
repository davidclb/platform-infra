# ADR 0015: GHCR for all container images, no local/self-hosted registry

## Status
Accepted

## Context
The original homelab plan (roadmap Phase 2.1) allocated a VM for
"vault + registry locale" — a self-hosted container registry alongside
Vault. Ghamr's CI (ADR 0009) already pushes to GHCR (GitHub Container
Registry). The question was whether homelab-only images (Yoshu, Morgoth,
future apps never meant for Hostinger/Oracle) should go through a
separate, self-hosted registry instead.

Options considered:
- **GHCR** (already used for Ghamr) — free, generous quota, same
  ecosystem as this project's GitHub-hosted repos and CI.
- **Self-hosted registry (Harbor, or the Docker `registry:2` image)** —
  runs on the homelab itself; the "registry locale" originally planned.
- **Docker Hub** — functionally equivalent to GHCR, but a separate
  account/service with no integration benefit over GHCR here.
- **AWS ECR** — only relevant if a workload specifically targets AWS/EKS
  (roadmap Phase 4); neither the homelab nor Oracle run on AWS today.

The one real argument for a self-hosted registry — resilience if GitHub/
GHCR has an outage — was judged a low-probability, low-impact case for a
learning homelab: Kubernetes doesn't re-pull an already-cached image
unless the tag changes, so an existing deployment keeps running through a
GHCR outage; only *new* deploys would be blocked until GHCR recovers.

## Decision
Use GHCR for every container image in this project — Ghamr, Yoshu,
Morgoth, and any future app — regardless of which environment
(homelab/test, Oracle/staging, Hostinger/prod) it's deployed to. No
self-hosted registry is provisioned.

This removes "registry locale" from the original VM3 plan — that VM now
hosts only Vault (see ADR 0010, already deciding Vault gets its own
dedicated VM regardless).

## Consequences
- One registry, one set of credentials, one place to look for any image
  used across this project — simpler than operating a second registry.
- A GHCR outage blocks new deployments cluster-wide until it recovers;
  accepted as a low-probability risk for a homelab, not something this
  repo builds redundancy against.
- If a real need for a self-hosted registry ever appears (e.g. wanting to
  practice operating Harbor specifically, or genuinely needing
  registry independence from GitHub), that becomes a new, explicitly
  scoped decision — not a silent reintroduction of the original plan.
