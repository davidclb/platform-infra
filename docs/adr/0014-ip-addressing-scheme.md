# ADR 0014: LAN IP addressing scheme, and single DHCP authority

## Status
Accepted

## Context
IPs were assigned to homelab VMs (`k3s-master` on `.10`, `k3s-worker` on
`.11`) without first checking the router's actual DHCP range — the wrong
gateway (`.1` assumed instead of the real `.254`) was one direct
consequence, already covered in ADR 0011.

Once the real network was inspected further, two more issues surfaced:
- The router's DHCP range is `192.168.1.1`–`192.168.1.100` — meaning
  `k3s-master`/`k3s-worker`'s static IPs (`.10`/`.11`) sit *inside* the
  DHCP pool, a real (if not yet triggered) collision risk with any device
  that joins the network and gets leased one of those addresses.
- Pi-hole's own DHCP server was also enabled, serving `.150`–`.250` — a
  second, independent DHCP authority on the same network as the router's.
  Even with non-overlapping ranges, running two DHCP servers is a classic
  race-condition source: a new device's DHCP Discover broadcast can be
  answered by either server, non-deterministically, and if the router
  answers first the device gets the router's DNS (not Pi-hole's),
  silently defeating Pi-hole's ad-filtering for that device.

## Decision
**Single DHCP authority**: Pi-hole becomes the only DHCP server; the
router's built-in DHCP server is disabled.

This was not the first option considered — pushing Pi-hole as the DNS
server via the router's own DHCP settings while keeping the router as
DHCP authority was tried first, but this router model (a Bouygues Bbox)
does not support setting a custom primary DNS for DHCP clients: it always
hands out itself as the primary DNS, with any custom DNS only usable as a
secondary/tertiary entry that devices are free to ignore — which does not
reliably route all LAN traffic through Pi-hole's filtering. Disabling the
router's DHCP and letting Pi-hole be the sole DHCP+DNS authority is the
standard, documented workaround for this specific router limitation.

**Static IP ranges**, none of them inside the router's DHCP pool:

| Range | Usage |
|---|---|
| `.1`–`.100` | Formerly the router's DHCP pool; router DHCP now disabled, range kept reserved (unused) rather than reassigned, in case DHCP authority ever moves back to the router |
| `.101`–`.109` | Reserved / unallocated |
| `.110` | `pihole` (kept as-is; predates this scheme) |
| `.111`–`.149` | Homelab static infrastructure (VMs/LXC) |
| `.150`–`.250` | Pi-hole DHCP pool — never assign a static IP here |
| `.251`–`.253` | Reserved / future use |
| `.254` | Router (gateway) |

Static assignments as of this ADR:

| Host | IP | Notes |
|---|---|---|
| Proxmox host | `.3` | Predates this scheme, outside `.111`-`.199` but not in the DHCP pool's actively-leased tail — left as-is |
| `pihole` | `.110` | |
| `k3s-master` | `.111` | Migrated from `.10` (was inside the DHCP pool) |
| `k3s-worker` | `.112` | Migrated from `.11` (was inside the DHCP pool) |
| `vault-01` | `.113` | Not yet provisioned |
| `wireguard-vpn` | `.114` | Not yet provisioned via IaC (currently a hand-made LXC, IP to reconcile when migrated) |
| ~~`monitoring`~~ | ~~`.115`~~ | Freed — monitoring runs inside K3s instead, see ADR 0016; `.115` available for the next host |

## Consequences
- `k3s-master.tf` and `k3s-worker.tf`'s `ip_config` must be updated to
  `.111`/`.112`, followed by the same `cloud-init clean` + reboot
  procedure as ADR 0011 (a plain `tofu apply` alone does not make a
  running VM re-read a changed static IP any more than it did for the
  gateway).
- SSH `known_hosts` entries for the old IPs (`.10`/`.11`) will need
  clearing, same as every previous IP/gateway change in this repo.
- Ansible inventory (`ansible/homelab/hosts.yaml`) must be updated to
  match — it currently has provisional IPs (`.12`/`.13`/`.14`) for
  `vault`/`wireguard_vpn`/`pihole` that don't match this scheme's `.110`,
  `.113`, `.114` and were never reconciled with reality.
- Any future VM/LXC added to this homelab is assigned from `.111`-`.199`,
  never from the DHCP pool, and this table is updated at the same time —
  not after the fact.
