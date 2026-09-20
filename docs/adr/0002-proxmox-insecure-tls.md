# ADR 0002: Accept Proxmox's self-signed certificate (insecure = true)

## Status
Accepted

## Context
The homelab Proxmox host (192.168.1.3) serves its API over HTTPS with the
default self-signed certificate — standard behavior for Proxmox VE on a
local network with no internal CA yet. The `bpg/proxmox` provider refuses
TLS verification against this certificate unless explicitly told not to
verify it (`insecure = true`).

## Decision
Set `insecure = true` on the `proxmox` provider block for this homelab.

## Consequences
- Acceptable here: the API is only reachable on a closed local network
  (192.168.1.0/24), not exposed to the internet. Risk is limited to
  someone already on the local network being able to MITM the connection.
- This is NOT a pattern to carry over to any environment reachable from
  outside the local network (Oracle staging, AWS) — those must use a
  real certificate (e.g. Let's Encrypt, or an internal CA) and drop
  `insecure = true` entirely.
- Revisit if/when an internal CA or public cert is set up for the
  homelab Proxmox host itself (e.g. via step-ca or similar) — at that
  point this ADR should be superseded.
