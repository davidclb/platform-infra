# ADR 0021: Cloudflare Tunnel + Access for exposing Ghamr-lab publicly

## Status
Accepted

## Context

Ghamr (backend + frontend) was validated locally on the homelab K3s
cluster via `kubectl port-forward` and direct LAN access through
Traefik (`http://192.168.1.111/`). Testing real integrations — Stripe
checkout/webhooks, Google OAuth — requires a publicly reachable HTTPS
URL: Stripe needs to call a webhook endpoint from its own servers, and
Google OAuth redirect URIs must be a valid public domain.

Several approaches were considered and discarded before settling on
Cloudflare Tunnel:

- **Direct NAT port-forwarding on the router (80/443)**, the same
  pattern already used for the VPN (ADR 0017, 0020). Not possible on
  this router: external ports are restricted to the 57344–65535 range,
  so 80/443 cannot be forwarded directly. A non-standard external port
  (e.g. `:58443`) would work technically, but Stripe/Google callback
  URLs are expected on standard ports, and the user's own stated goal
  ("site en test exactement comme en prod, pour être fiable dans les
  tests") ruled out a non-standard-port workaround.
- **New subdomain of the existing production domain** (`ghamrr.site`,
  hosted at Hostinger), delegated via NS records to Cloudflare so
  Cloudflare Tunnel could manage just that subdomain. Not possible:
  Hostinger only supports NS delegation for a domain's root, not for
  individual subdomains (A/CNAME only at the subdomain level) —
  confirmed via Hostinger's own documentation.
- **Transferring the entire `ghamrr.site` zone to Cloudflare DNS**,
  which would have unblocked the subdomain approach. Rejected: touches
  the DNS of the actual production app (still on Hostinger, "ne pas
  toucher" per CLAUDE.md / the pilot roadmap), for a lab/test need —
  too much blast radius for the benefit.
- **A new domain on a cheap/unusual TLD** (`.men` was the first pick).
  Rejected after checking: `.men` is one of the most spam-abused TLDs
  (~55% of `.men` domains flagged "bad" by Spamhaus), a reputation
  risk independent of what this domain would actually be used for —
  bad for email deliverability (Ghamr sends verification/reset
  emails) and for Stripe's own risk scoring.

## Decision

- **New dedicated domain**, `ghamrr-lab.site`, bought directly through
  Cloudflare Registrar — isolates the lab entirely from the production
  domain's DNS, no transfer/delegation risk on `ghamrr.site`.
- **Cloudflare Tunnel** (`cloudflared`, deployed as a Kubernetes
  Deployment, 2 replicas) connects outbound from the cluster to
  Cloudflare — no inbound port is opened on the home router at all,
  for any of 80/443/custom. The tunnel routes to Traefik's in-cluster
  Service (`http://traefik.kube-system.svc.cluster.local:80`), not
  directly to the app's own Service — Traefik keeps doing routing
  (path-based `/api` → backend, `/` → frontend, see ingress.yaml).
- **Cloudflare Access** (Zero Trust Free plan) protects the domain
  with two policies:
  - `Owner access` (Allow, Include: Emails = operator's own email) on
    `ghamrr-lab.site` — anything under the domain requires
    authentication (one-time PIN by email), regardless of the
    operator's network/location. No VPN needed to reach the lab.
  - `Webhooks bypass` (Bypass, Include: Everyone) on a **separate**
    Access Application scoped to the specific path
    `ghamrr-lab.site/api/v1/stripe/webhook` — Stripe's servers aren't
    a human and can't complete an email challenge, so this path skips
    Access entirely. Security for this path isn't dropped, it moves
    layer: the backend's own Stripe signature verification
    (`STRIPE_WEBHOOK_SECRET`) is the real control here, not Access.
  - Google OAuth did **not** need a bypass: `HandleGoogleSignin`
    receives the Google `id_token` from the browser (the already
    Access-authenticated user), not a server-to-server call from
    Google itself — the request is routed exactly like any other
    authenticated page load.

## Consequences

- `cloudflared`'s liveness probe must point at its metrics server's
  **actual** port, not an assumed one: in containerized environments
  cloudflared's metrics server (which serves `/ready`) binds to the
  first free port in 20241–20245 by default, not a fixed port — a
  probe on a guessed port (`2000`, unset `--metrics`) causes a
  `connection refused` → `CrashLoopBackOff` loop that looks like a
  tunnel problem but isn't. Fix: pass `--metrics 0.0.0.0:2000`
  explicitly so the probe's assumption holds.
- Routing two paths (`/api`, `/`) to two different backends must be
  **one** Ingress object with two `paths:` entries, not two separate
  Ingress resources on the same host — Traefik's routing priority
  across separate Ingress objects on one host isn't reliably
  deterministic (confirmed via Traefik community reports), and was
  observed directly here: `/api/v1/ping` resolved to the frontend
  instead of the backend until the two were merged into one Ingress.
- This lab domain is intentionally decoupled from production
  (`ghamrr.site`/Hostinger) — the two are not meant to be kept in
  sync, and this ADR's Cloudflare-specific choices (Tunnel, Access)
  should not be assumed to apply if/when production itself is
  migrated (see ADR 0009, Hostinger → Oracle).
- Branch protection on `main` in GitLab had to be temporarily lifted
  to force-push a history rewrite unrelated to this ADR's content
  (commit trailer cleanup) — re-protecting `main` after any such
  rewrite is a standing requirement (CLAUDE.md), not specific to this
  change.
