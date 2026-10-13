# ADR 0018: VPN guest access policy — least privilege per peer

## Status
Accepted

## Context
Granting a third party access to a service behind this homelab's
WireGuard VPN was considered. A naive approach — giving a guest the same
kind of peer config the operator uses personally — grants full LAN
routing (`AllowedIPs = 0.0.0.0/0, ::/0`), not just access to the one
service they're meant to use. A per-service login on that one service
does not change this: the login protects application-level access, not
network-level reachability. A guest peer with full LAN routing could
still probe or reach Proxmox, K3s, Vault, and every other host on
`192.168.1.0/24`, regardless of what they're actually meant to use.

## Decision
Any WireGuard peer created for someone other than the operator follows
least-privilege routing, never the operator's own full-LAN
`AllowedIPs`:

- **Dedicated peer per guest** — never share the operator's own peer
  config. Each guest gets their own peer in wg-easy, independently
  revocable without affecting the operator's own access.
- **Restricted `AllowedIPs`** — scoped to only the specific host(s)/IP(s)
  the guest needs (e.g. `192.168.1.111/32` for one service), never the
  full `192.168.1.0/24` subnet.
- **Host-level firewall as a second layer** — the destination host's own
  firewall should also restrict what's reachable, rather than relying on
  WireGuard routing alone as the only control.
- **Revoke, don't just stop using** — when a guest's access is no longer
  needed, their peer is deleted in wg-easy (and the destination host's
  firewall rule removed if host-level restriction was used), not just
  left configured-but-unused.

## Consequences
- Creating a guest peer is a deliberate, slightly more involved step than
  the operator's own peers (which can reasonably keep full LAN access) —
  this friction is intentional, not an oversight to streamline later.
- Once `kube-prometheus-stack`/Loki are deployed (ADR 0016), guest VPN
  sessions should be visible in logs/metrics — worth checking that a
  guest only reached what they were scoped to, not as a replacement for
  the `AllowedIPs` restriction itself.
- This is a general policy for this repo's VPN, not a one-off decision
  about a specific guest — apply it every time, not just when it's
  top of mind.

## Addendum: client-side `AllowedIPs` is not a real security boundary

A first real guest case (full-internet access via the operator's IP, to
reach a geo-restricted mobile app) surfaced an important gap in the
decision above: wg-easy's "Allowed IPs" field on a peer only sets
client-side routing. It does **not** stop a technically capable guest
from editing their own WireGuard config locally and routing to a
destination this field excludes — it is a convenience default, not an
enforced boundary. Only **server-side** firewall rules (wg-easy's
"Per-Client Firewall" feature, added in v15.3.0, enforced via
iptables/ip6tables and not bypassable from the client) are a real
boundary.

**Decision**: enable Per-Client Firewall (Admin Panel → Interface) and
set the server-side "Firewall Allowed IPs" field on every guest peer —
the client-side "Allowed IPs" field alone is not sufficient for any case
where the guest's trust level doesn't already justify full access.

### Case study: targeting a specific app (Hinge) by IP doesn't work

Per-service least privilege (restricting a peer to one destination
IP/subnet, as the main decision above describes for a single internal
host) was attempted for a guest wanting access to a specific geo-blocked
mobile app. This failed in practice: `dig` against the app's domains
resolved to a Vercel-hosted marketing site and a separate API host on a
different provider — a modern mobile app's real traffic (auth, API,
media, push) spans multiple third-party providers with IPs that are
neither stable nor fully enumerable. Pinning `AllowedIPs`/firewall rules
to specific IPs for this kind of target breaks the moment any of those
providers' infrastructure changes, and can't be made complete to begin
with.

**Decision**: for a guest need that amounts to "general internet access
via this VPN" (not access to one specific internal host), don't attempt
per-IP allowlisting against a public app/service — it doesn't hold up
against CDN-backed, multi-provider traffic. Instead:
- Grant broad routing (the full-internet-minus-LAN `AllowedIPs` set,
  `192.168.0.0/16` excluded) as the realistic option for this case.
- Rely on DNS-level filtering (Pi-hole with a maintained blocklist, e.g.
  Hagezi's anti-piracy list) as a best-effort general safety net — not a
  guarantee, since DNS filtering doesn't cover P2P/BitTorrent traffic
  that doesn't depend on DNS resolution, and doesn't block not-yet-listed
  domains.
- Treat the guest's own intent and a direct conversation about acceptable
  use as the actual primary control, not the technical filtering — the
  operator remains the ISP-identified account for all traffic leaving
  their connection, and no filtering here is airtight.
- Keep the peer's expiration date set (wg-easy's built-in field) to bound
  the exposure window regardless of what's actually accessed during it.
