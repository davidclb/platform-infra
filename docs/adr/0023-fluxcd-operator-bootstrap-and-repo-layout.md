# ADR 0023: FluxCD via the Flux Operator, and the apps/infra/flux repo split

## Status
Accepted

## Context

GitOps needed a way to get Flux running on the homelab cluster, and a
repo layout that keeps "what Flux watches" separate from "what Flux
is watching" — without duplicating manifests between the two.

**Flux installation method.** Two approaches exist:
- `flux bootstrap github`/`flux bootstrap gitlab` — the classic CLI
  path. One command installs the controllers, generates an SSH deploy
  key, registers it on the repo, and commits the initial sync config.
  Simple to run once, but Flux's own version/upgrade afterwards is
  managed by re-running the CLI by hand.
- **Flux Operator** (`controlplaneio-fluxcd/flux-operator`) + a
  `FluxInstance` CRD — the operator manages Flux's lifecycle as a
  Kubernetes-native resource (declare the desired Flux version/
  components in a CRD, the operator reconciles it), closer to how
  every other piece of this cluster is already managed (CRD +
  controller, cf. the Operator Pattern section of the roadmap).

Chose the **operator**, for consistency with the rest of this
homelab's "everything is a reconciled CRD" approach — at the cost of
one thing `flux bootstrap` does for free: the operator path has no
CLI step that generates the Git deploy key and registers it on
GitLab, so that part had to be done by hand (`ssh-keygen`, the public
half added as a GitLab Deploy Key, the private half encrypted in
Ansible Vault, applied as a Kubernetes `Secret` once via Ansible —
see `install_flux.yaml`). This secret is the one piece in this setup
Ansible touches once at bootstrap and never again; everything after
is Flux reconciling itself from Git.

**Repo layout: `apps/`, `infra/`, `flux/`.** Settled on, after first
getting it wrong by duplicating chart content under `flux/`:
- `apps/<name>/` — one folder per application (`ghamr`, `yoshu`),
  each a thin Helm chart whose only real content is a `dependencies:`
  entry on the shared `web-app` library chart (`helm/web-app/`,
  pushed to `oci://ghcr.io/davidclb/charts`) plus that app's own
  `values.yaml`. ArgoCD is the GitOps tool for this folder.
- `infra/` — shared cluster infrastructure with its own lifecycle,
  independent of any single app: CRDs, operators, monitoring,
  database (Postgres/GoTrue for Yoshu's Supabase pieces), and
  `infra/argocd/` (ArgoCD's own `HelmRepository`+`HelmRelease`).
  Flux is the GitOps tool for this folder.
- `flux/` — holds only Flux's own `Kustomization` resources (e.g.
  `ArgoKustomization.yml`), each one a pointer (`spec.path`) at a
  folder under `infra/` — never a copy of what lives there. This is
  the same "reference, don't duplicate" principle already used for
  `apps/*/Chart.yaml` referencing `web-app` instead of vendoring it.

## Decision

- Flux Operator + `FluxInstance`, not `flux bootstrap`.
- Git deploy key generated manually once, public half as a GitLab
  Deploy Key, private half in Ansible Vault — bootstrapped by
  Ansible, never touched by it again afterwards.
- `FluxInstance.spec.sync.url` must use the full `ssh://git@host/path`
  form — GitLab's short `git@host:path` scp-like syntax fails the
  CRD's schema validation (`should match '^(http|https|ssh)://.*$'`).
- `FluxInstance.spec.sync.path` points at `flux/` (this repo's root,
  as cloned by Flux) — a placeholder value copied from a generic
  example (`clusters/my-cluster`) silently referred to a path that
  never existed in this repo, and failed with a `stat: no such file
  or directory` that gave no hint the value itself was the problem.
- `apps/`, `infra/`, `flux/` as described above — each `Kustomization`
  under `flux/` reconciles one `infra/` subfolder, `sourceRef` always
  points at the `GitRepository` Flux creates for itself
  (`flux-system/flux-system`), never at a `HelmRepository` (a
  different kind of source, for Helm charts, not this Git repo).

## Consequences

- A `HelmRelease`'s `chart.spec.chart` field must be the chart's real
  name inside the Helm repo's index (confirmed on Artifact Hub, e.g.
  `argo-cd` for the `argo-helm` repo) — not the name given to the
  local `HelmRepository` resource (`metadata.name`, e.g. `argo-chart`
  here). Conflating the two produces a misleading `no chart name
  found` error that doesn't point at which field is wrong.
- Fixing a `HelmRelease`/`HelmRepository` by `kubectl apply`-ing a
  corrected file directly on `k3s-master` does **not** fix it
  permanently once a `Kustomization` manages that path: Flux's next
  reconciliation re-applies whatever is committed in Git, silently
  reverting the manual fix. The real fix always has to land in the
  repo file and be pushed, not just applied by hand — confirmed
  directly when a chart-name fix made by hand was reverted by the
  next reconciliation.
- `kubernetes.core.k8s`/`kubernetes.core.helm` Ansible modules need
  the Python `kubernetes` library installed on the **target** host
  (not just the `kubernetes.core` Ansible collection on the
  controller) — installed via `apt: python3-kubernetes`, guarded by
  ADR 0022's apt-lock pattern like every other `apt:` task on a
  homelab VM.
- `KUBECONFIG=/etc/rancher/k3s/k3s.yaml` plus `sudo -E` (not bare
  `sudo`) is needed for any manual `kubectl`/`helm`/`flux` CLI command
  run directly on `k3s-master` — `sudo` alone drops the exported
  environment variable, leaving `helm`/`flux` unable to find the
  cluster at all.
