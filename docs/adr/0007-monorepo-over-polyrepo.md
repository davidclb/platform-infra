# ADR 0007: Monorepo for all infra layers, not one repo per tool

## Status
Accepted

## Context
This repo needs to hold multiple distinct layers: provisioning
(OpenTofu, currently Proxmox VMs for K3s master/worker), configuration
management (Ansible, not yet started), and GitOps deployment config
(ArgoCD manifests for Ghamr/Yoshu, not yet started). A common alternative
is polyrepo — one repo per layer (`terraform-infra`, `ansible-config`,
`argocd-apps`), or even one repo per app's deployment config.

This is a solo homelab, not a multi-team org: there is no team-boundary
reason to split repos, and the layers are tightly coupled in practice —
a change to what OpenTofu provisions (e.g. a new K3s worker) often needs
a corresponding Ansible/ArgoCD change in the same unit of work.

## Decision
Keep a single repo (`platform-infra`) with `terraform/`, `ansible/`,
`argocd/`, `docs/adr/` as top-level directories, rather than splitting by
tool or by app.

## Consequences
- A single PR can touch provisioning and deployment config together when
  they're logically one change (e.g. "add k3s-worker-02": OpenTofu
  resource + its Ansible inventory entry in the same commit/PR) — no
  cross-repo coordination needed for this size of project.
- `docs/adr/` lives at the root, covering decisions across all layers
  (see ADR 0001-0006) rather than being scattered per-repo.
- If this ever grows into a multi-person or multi-team context, the
  coupling that's an advantage now (one PR, one history) becomes a
  liability — that would be the trigger to reconsider polyrepo, not repo
  count alone.
- App source code (Ghamr, Yoshu) stays in its own separate repos — only
  their deployment manifests live here. Kubernetes manifests are never
  placed inside an app's source repo (couples deploy config to code
  releases).
