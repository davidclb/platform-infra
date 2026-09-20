# ADR 0001: Defer OpenTofu state encryption until a real KMS exists

## Status
Accepted

## Context
OpenTofu 1.10+ supports native state encryption (key provider + method
block), stable since our pinned version (1.12.6). The state file will
contain the Proxmox API token used by the provider, in clear text, once
real resources are planned/applied.

Two key provider options were considered for encrypting it now:
- PBKDF2 (self-chosen passphrase, zero external dependency)
- A cloud KMS (AWS/GCP/Azure) key provider

## Decision
Defer state encryption until a real cloud KMS is available (roadmap
Phase 3/4 — Oracle / AWS), rather than using PBKDF2 now.

## Consequences
- Until then, `terraform.tfstate` stays local, gitignored, unencrypted.
  Risk is judged acceptable at this stage: solo homelab, state never
  leaves the laptop, gitignore already prevents it reaching GitLab.
- When Phase 3/4 introduces a real KMS, state encryption must be enabled
  before (or as part of) migrating the state to a remote backend — not
  left for later, to avoid ever writing an unencrypted state to shared
  remote storage.
- Revisit this ADR at that point; update status to Superseded once
  encryption is actually configured.
