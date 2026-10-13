# ADR 0017: wg-easy on the homelab — bind mount and INSECURE=true accepted

## Status
Accepted

## Context
`wireguard-vpn` (homelab LXC, `.114`, ADR 0014) runs wg-easy via Docker
Compose, deployed with a custom Ansible `template` (not the official
docker-compose.yml downloaded as-is) so storage and reproducibility can
be controlled explicitly.

Two deviations from the user's own existing production wg-easy setup
(a separate, already-running deployment, unrelated to this repo) were
considered:

1. **Storage: named Docker volume (prod) vs bind mount (homelab).**
   Prod uses a named volume (`etc_wireguard:/etc/wireguard`) — wg-easy's
   own documented default. A named volume is opaque to the host
   filesystem: backing it up requires running a temporary container with
   `docker run --rm -v etc_wireguard:/data ...` to extract its contents,
   rather than a plain file copy.
2. **`INSECURE=true`** — disables the HTTPS requirement for wg-easy's web
   UI login, so the admin password can travel over plain HTTP. Official
   wg-easy guidance explicitly warns this is unsafe unless the UI is kept
   LAN-only (never exposed to the internet).

## Decision
For the homelab deployment specifically:
- Use a **bind mount** (`./data:/etc/wireguard`) instead of a named
  volume. This makes backup/restore a plain directory copy
  (`ansible.builtin.copy`/`synchronize`), consistent with how this repo
  already treats reproducibility (everything should come up/go down
  cleanly, per CLAUDE.md) — worth the minor cost of diverging from the
  user's existing production pattern, which is a separate, independently
  managed deployment anyway.
- Keep **`INSECURE=true`**, because the wg-easy web UI (port `51821`) is
  not port-forwarded on the router — only reachable from inside the LAN.
  The VPN data-plane port itself (`51820/udp`) is the only one exposed
  externally. This is the same category of decision as ADR 0002 (Proxmox
  self-signed TLS accepted for a LAN-only service) — accepted here for the
  same reason, not a default copied without thought.

## Consequences
- If the wg-easy UI's exposure ever changes (e.g. port-forwarding `51821`
  for remote admin access), `INSECURE=true` must be revisited immediately
  — at that point a reverse proxy with HTTPS (Traefik/Caddy, per wg-easy's
  own docs) becomes mandatory, not optional.
- Backup/restore of `/etc/wireguard`'s bind-mounted `./data` directory
  (containing `wg0.json`, `wg0.conf`, server and peer keys) should be
  automated in Ansible before this LXC is ever destroyed/recreated —
  otherwise all configured peers are lost, same risk wg-easy's own docs
  warn about for the named-volume case.
- This repo's wg-easy config intentionally diverges from the user's
  existing production WireGuard setup; the two are not meant to be kept
  in sync, and neither should be copied into the other without re-checking
  this ADR's reasoning first.
