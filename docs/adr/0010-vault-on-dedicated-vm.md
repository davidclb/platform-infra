# ADR 0010: Run HashiCorp Vault on a dedicated VM, not inside K3s

## Status
Accepted

## Context
The 6-month DevSecOps roadmap (`DevSecOps-IDP-Roadmap-6mois.md`, Phase 2.2)
originally planned Vault running *inside* the homelab K3s cluster
(`Vault (dev mode d'abord, puis prod mode)`). The homelab inventory
(`ansible/homelab/hosts.yaml`) already anticipates a `vault-01` host under
a `service` group, separate from `k3s_cluster` — which prompted revisiting
this placement decision before actually deploying Vault.

HashiCorp's own guidance
(developer.hashicorp.com/vault/tutorials/kubernetes-introduction/kubernetes-external-vault)
recommends running Vault outside the cluster it serves when possible,
citing centralized secret management and avoiding coupling Vault's
availability to cluster health. For a single-cluster homelab (no
dedicated cluster available), the same guidance accepts running Vault
in-cluster with strict namespace isolation (RBAC, NetworkPolicies) as a
reasonable fallback — which is what the original roadmap assumed.

## Decision
Run Vault on its own dedicated VM (`vault-01` in the homelab inventory),
outside the K3s cluster — diverging from the roadmap's original
in-cluster plan.

This follows the same reasoning already applied to GitLab hosting
(ADR-equivalent decision in this repo's `CLAUDE.md`, "Technical context"
section): the homelab is the DEV/LAB where it's fine to break things while
experimenting (Kyverno policies, NetworkPolicies, etc.) — a control-plane
service should not go down together with the infrastructure it's meant to
help recover. If Vault ran inside K3s and the cluster broke during
experimentation, Vault-stored credentials needed to diagnose/rebuild would
be unreachable at the exact moment they're needed most.

## Consequences
- One more VM to provision, patch, and secure independently — real
  operational cost accepted in exchange for resilience.
- Diverges from `DevSecOps-IDP-Roadmap-6mois.md` Phase 2.2 as originally
  written; the roadmap's own guidance doesn't need to be rewritten, but
  this repo's actual implementation will not match it on this point.
- Namespace-level isolation inside K3s (the alternative HashiCorp accepts
  for single-cluster setups) is not used here — if a future need arises to
  demonstrate that pattern specifically (e.g. for interview practice), it
  should be a separate, explicitly-scoped exercise, not a silent deviation
  from this decision.
- Any Kubernetes workload needing Vault secrets will authenticate to this
  external VM over the network (Vault's Kubernetes auth method), rather
  than to an in-cluster service — network reachability from K3s to
  `vault-01` becomes a hard dependency to keep working.
