# ADR 0006: OpenTofu instead of Terraform

## Status
Accepted

## Context
This repo starts greenfield — no existing Terraform state, no legacy
HCP-specific features to preserve. Two engines were on the table for
provisioning the homelab (Proxmox now, Oracle ARM / AWS later per the
roadmap): HashiCorp Terraform and OpenTofu (the Linux Foundation fork,
HCL- and provider-compatible).

Terraform moved to the BUSL license in 2023; OpenTofu remained under the
OSI-approved MPL-2.0. For a solo homelab with no HCP Terraform Cloud/
Enterprise dependency planned, the licensing question was the main
differentiator — the tool itself (HCL syntax, workflow, provider
ecosystem) is otherwise the same skill either way.

## Decision
Use OpenTofu (pinned `1.12.6` in `mise.toml`) as the IaC engine for this
repo, not Terraform.

## Consequences
- No `terraform` binary anywhere in this repo's toolchain — `opentofu`
  is the only engine declared in `mise.toml`. Commands are `tofu plan` /
  `tofu apply`, not `terraform plan` / `terraform apply` (see ADR 0005
  for `tofu destroy` behavior).
- Provider compatibility is not 100% guaranteed to stay in lockstep with
  Terraform forever — each provider release should be checked against
  OpenTofu compatibility, not assumed automatically. So far `bpg/proxmox`
  (0.113.1) works without issue.
- If a future employer or environment mandates HashiCorp Terraform
  specifically (e.g. Terraform Cloud/Enterprise features), the switch
  back is low-cost: same HCL, same state format, same provider blocks —
  this decision is reversible without relearning the tool.
- Revisit if OpenTofu's provider registry sync with Terraform's degrades
  meaningfully for a provider this repo depends on.
