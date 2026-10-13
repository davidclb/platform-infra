# ADR 0008: Ghamr as the three-environment promotion path (homelab/test → Oracle/staging → Hostinger/prod)

## Status
Accepted

## Context
The homelab K3s cluster (provisioned in ADR 0006/0007) needs a real
application deployed through ArgoCD to be useful for learning — an empty
cluster teaches nothing about GitOps, Kyverno, or observability.

Two families of candidate apps were considered:
- **Morgoth / vuln-server**: single-process Go services, stateless,
  no real multi-component topology. Easy to containerize, but too
  simple to exercise a real promotion chain — there's only one
  meaningful environment for them ("does it run").
- **Ghamr**: an actual multi-tier SaaS already in production (Fiber
  API, SQLite in WAL mode, external LLM provider calls, rate limiting).
  It already has a real prod (Hostinger) and a planned staging
  environment (Oracle ARM, per the roadmap) that it needs to migrate to.

Deploying Ghamr onto the homelab as well raises the question of what
role each of its three potential environments (homelab, Oracle, current/
future prod) actually plays, since none of them should be casually
conflated — corrupting Ghamr's real users' data is not an acceptable
side effect of learning Kyverno.

## Decision
Treat the homelab as Ghamr's **`test`** environment, not a second
staging or a prod replica:

| Environment | Role | Behavior |
|---|---|---|
| **Homelab (Proxmox/K3s)** | `test` | Continuous, aggressive deploys on every merge to `main`. Deliberately broken here — this is where Kyverno/ArgoCD/Falco/Prometheus get exercised against a real, if disposable, workload. |
| **Oracle ARM** | `staging` | Prod-like, stable. Last filter before production — not touched by every commit, only by deliberate promotion. |
| **Hostinger (→ later Oracle prod)** | `prod` | Never deployed to directly. Only reached by promoting an already-validated, staging-tested image tag. |

Concretely: `main` merges trigger CI (build, scan, sign, push to GHCR)
and an automatic deploy to homelab/test. Promotion to staging and then
to prod are both manual, tag-based steps (see ADR 0006-adjacent tagging
convention: `sha-<commit>` + `latest` on every build; a fixed semver tag
only on deliberate promotion) — never automatic, never branch-based
(see ADR 0007 on avoiding branch-per-environment).

Morgoth, vuln-server, and the portfolio site still get deployed to the
homelab too, but as simpler, single-environment workloads run in
parallel — not as the app driving the promotion-chain design.

## Consequences
- The homelab is explicitly allowed to be broken. A failed deploy or a
  Kyverno policy rejecting a homelab release is expected, useful signal
  — not an incident.
- Ghamr's real users (on Hostinger today) are never exposed to
  homelab-stage experiments; only a tag that has already survived
  homelab + staging reaches prod.
- Yoshu and other apps can follow a lighter version of this pattern
  (e.g. homelab/test → prod directly, no staging tier) if their
  criticality doesn't justify a three-environment chain — this ADR sets
  the pattern for apps that need it, not a blanket requirement.
- If Ghamr's Hostinger → Oracle migration (tracked separately in the
  roadmap) completes, this ADR's "prod" row should be updated to point
  at Oracle prod, and "staging" reconsidered — revisit at that point.
