# ADR 0009: Hostinger → Oracle migration path — same image, DNS-only cutover

## Status
Accepted

## Context
Ghamr currently runs in production on Hostinger, deployed by hand as a
simple Docker Compose stack — no Terraform, no CI-driven image
promotion. The roadmap's target is to move production to Oracle ARM
(free-tier, 24GB RAM), but a naive "rebuild Hostinger's setup on Oracle,
then flip a switch" risks two things at once: an untested infra
provisioning path AND an untested cutover, on the app's real users.

The two concerns need to be separated:
1. **What is running** (the Ghamr container image) — already solved by
   the CI pipeline (build → scan → sign → push to GHCR with
   `sha-<commit>` + a promoted semver tag).
2. **Where it's running** (which host serves real traffic) — not yet
   solved; this is what this ADR addresses.

## Decision
Treat the migration as three independent phases, each one fully
reversible before moving to the next:

**Phase A — Formalize Hostinger as-is.**
Write Terraform + Ansible describing Hostinger's current Docker Compose
setup (the VPS, its Docker config) without changing production
behavior. This turns an undocumented snowflake into IaC before touching
anything else — production stays exactly as it is today.

**Phase B — Configure Oracle as a clean pre-prod, in parallel.**
The Oracle ARM instance (24GB, Always Free) already exists — created
once through the OCI console, not something this repo needs to
provision or ever destroy/recreate. Given Always Free capacity
constraints (new A1 instances can fail with "out of host capacity" for
extended periods), treating it as Terraform-managed would risk being
unable to recreate it if ever destroyed, for no real benefit: there is
exactly one instance, its lifecycle isn't changing, and Terraform's
value (repeatable provisioning, safe destroy/recreate) doesn't apply to
a singleton resource never meant to be rebuilt.

So: **Ansible only**, targeting the existing instance by IP — installs
Docker and the deploy tooling, same role as Ansible already plays for
the Proxmox VMs, minus the provisioning step. The same CI pipeline that
already builds/scans/signs/pushes Ghamr's image to GHCR also deploys to
Oracle (pull latest validated tag). Hostinger is untouched and keeps
serving all real traffic during this entire phase.

**Phase C — Validate Oracle over time, then cut over via DNS only.**
Oracle runs the same tagged image as Hostinger, observed over multiple
releases, ideally under synthetic or shadow traffic before real users
ever reach it. The actual production cutover is a DNS/routing change
(point Ghamr's domain at Oracle's IP instead of Hostinger's) — not a new
deployment. Because Oracle is already running the exact image that was
validated, cutover day ships no new code. Rollback is the same DNS
change in reverse.

## Consequences
- The CI pipeline needs no Hostinger-vs-Oracle branching logic: it
  always produces the same tagged image; only the *deploy target* (which
  host pulls it, and later, where DNS points) differs per phase.
- Phase A (formalizing Hostinger) must not silently change what's
  running there — a Terraform/Ansible run against production Hostinger
  is validated with a plan/dry-run first, never applied blind.
- The cutover's blast radius is deliberately minimized: worst case is a
  DNS revert, not a rushed redeploy under real user load.
- Oracle's Ansible inventory targets the existing instance's static
  IP directly — no Terraform state for it, no `oci` provider in this
  repo. If Always-Free capacity constraints ever force rebuilding this
  instance from scratch, that becomes the trigger to reconsider adding
  a Terraform module for it — not before.
- This ADR only covers the Compose-based interim architecture. Once
  Oracle runs K3s + ArgoCD (see ADR 0008's three-environment model:
  homelab/test → Oracle/staging → prod), "Oracle" in this ADR's Phase C
  becomes the staging tier feeding that same promotion chain, and
  "Hostinger" is eventually retired rather than kept as a second prod.
- Revisit this ADR once the DNS cutover has actually happened — update
  status to Superseded and note what, if anything, didn't go as planned.
