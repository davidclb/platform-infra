# ADR 0020: wg-easy listening port must match the router's NAT internal port

## Status
Accepted

## Context
The router (Bbox) forwards external UDP port `57345` to internal port
`51820` on the `wireguard-vpn` LXC (`.114`) — a deliberate choice (ADR
below's consequences) over forwarding the WireGuard-default `51820`
directly, because external port `51820` was not available to forward on
this router.

wg-easy (v15) exposes **two separate "Port" fields**, easy to conflate:

- **Admin Panel → Connection → Port**: only used to populate the `Endpoint`
  written into generated client `.conf`/QR configs. Purely informational
  for clients — changing it does not touch the running server.
- **Admin Panel → Interface → Port**: the actual port the WireGuard
  process binds to inside the container, persisted in `wg-easy.db` (not
  read from `docker-compose.yml`, and not overridden by a `WG_PORT` env
  var in this version).

During setup, the first-run wizard (which only exposes the "Connection"
style Host/Port fields) was filled with the router's *external* port
(`57345`), on the assumption it would configure the server's listening
port too. It didn't. `docker exec wg-easy wg show` kept reporting
`listening port: 57345` regardless of what `ports:` was set to in
`docker-compose.yml.j2` (tried both `51820:51820` and `57345:57345`) —
because Docker's port mapping controls what the container exposes to the
host, not what the process inside chooses to bind to. The two matched by
coincidence of being the same number was never the actual fix; the
container kept listening on whatever the wizard wrote to `wg-easy.db`.

Symptom while mismatched: tunnel comes up cleanly client-side
(`wg-quick up` succeeds, interface and routes are created), but zero
traffic passes — not even to the internet, since the client's default
route is pulled entirely into the tunnel (`0.0.0.0/0 dev homelab`) with
no working path out. `wg show` on the server never shows a `latest
handshake` line for the peer. `nc -vzu <lxc-ip> 51820` run *from the LXC
itself* returned `Connection refused`, proving nothing was bound to that
port locally — the fastest single check that would have caught this
immediately instead of first suspecting router NAT hairpin.

## Decision
- Router: external `57345` → internal `51820` (unchanged, external port
  constraint on this router).
- `docker-compose.yml.j2`: `ports: - "51820:51820/udp"` (matches the
  router's internal target).
- wg-easy Admin Panel → **Interface → Port**: `51820` (matches Docker's
  exposed port — this is the field that actually matters for the server
  to bind correctly).
- wg-easy Admin Panel → **Connection → Port**: `57345` (external port —
  this is what clients must dial, and what gets written into their
  generated configs).

These two port fields are expected to keep differing by design, since
this router's NAT always will. Setting both to the same number is only
correct if external and internal port happen to match.

## Consequences
- Debug order for "tunnel up, zero connectivity" going forward:
  (1) `docker exec wg-easy wg show` for `listening port` and `latest
  handshake` first, (2) `ss -ulnp | grep <port>` on the LXC to confirm
  something is actually bound locally, (3) `nc -vzu <lxc-ip> <port>` from
  the LXC itself (fastest local-bind check), (4) only then suspect
  router NAT/hairpin and test from a genuinely external network (mobile
  data, not home WiFi — connecting from inside the LAN to the router's
  own public IP can silently fail on routers without hairpin NAT
  support, which looks identical to a server-side misconfiguration).
- If the router's available external port ever changes, only
  **Connection → Port** needs updating (client-facing) — **Interface →
  Port** and the Docker `ports:` mapping stay tied to whatever
  `wireguard_vpn`'s internal NAT target is, independently.
- `community.docker.docker_compose_v2` with `state: present` does not
  reliably recreate a running container on a changed `docker-compose.yml`
  — confirmed here: the file on disk was updated correctly by Ansible,
  but the running container kept its old bound port until the change was
  also applied through the wg-easy UI itself (which owns this particular
  setting via its own persisted DB, not the container's env/args). This
  is specific to settings wg-easy persists internally — not a general
  statement that `docker_compose_v2` never recreates containers on config
  changes.
