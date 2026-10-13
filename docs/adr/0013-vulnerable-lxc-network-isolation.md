# ADR 0013: Isolate the deliberately-vulnerable pentest target on its own bridge

## Status
Accepted

## Context
`vulnerablelxc` (LXC 106) is a deliberately vulnerable container
(WebGoat-like) used to practice offensive security — the opposite of
every other workload in this homelab, which is meant to be hardened.
Running it on the same network as trusted infrastructure (K3s nodes,
`pihole`, the VPN, and later `vault-01`) would create a real lateral
movement risk if it were ever actually compromised during an exercise,
not just theoretically exploited.

## Decision
`vulnerablelxc` runs on `vmbr100` (`10.100.0.0/24`), a Proxmox bridge
entirely separate from `vmbr0` (`192.168.1.0/24`), which carries every
other VM/LXC in the homelab (K3s nodes, `pihole`, `vpn`, and future
`vault-01`/`monitoring`).

## Consequences
- No routing is configured between `vmbr100` and `vmbr0` by default —
  a compromise of `vulnerablelxc` does not have a direct network path to
  the rest of the homelab's trusted infrastructure.
- Accessing `vulnerablelxc` for exercises requires connecting through
  Proxmox itself (or a deliberately-configured jump path), not through
  the regular LAN — this is intentional friction, not an oversight to fix.
- If a future exercise needs `vulnerablelxc` to interact with a specific
  trusted service (e.g. testing an attack against Ghamr-in-K3s), that
  requires an explicit, temporary, documented routing/firewall rule —
  never a permanent bridge between `vmbr100` and `vmbr0`.
- This isolation was already in place before this ADR was written
  (discovered mid-session via `ip a` output showing `vmbr100` as a
  distinct bridge); this ADR formalizes it as a deliberate decision worth
  defending in an interview, not an accidental side effect.
