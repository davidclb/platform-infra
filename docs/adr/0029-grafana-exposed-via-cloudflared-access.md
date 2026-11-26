# ADR 0029: Grafana exposed publicly via the cloudflared tunnel + Cloudflare Access

## Status

Accepted

## Context

Grafana (kube-prometheus-stack, namespace `observability`) runs as
`ClusterIP` and was reachable only via `kubectl port-forward` (ADR 0027).
For day-2 work (viewing dashboards away from the LAN, e.g. on the phone)
a stable public URL is wanted. ADR 0021 already established the lab
exposure pattern: dedicated domain `ghamrr-lab.site`, cloudflared tunnel
(GitOps, token mode), routing through in-cluster Traefik, and Cloudflare
Access (email OTP) protecting everything on the domain. ADR 0027 left
"Grafana exposure" as an open follow-up.

## Decision

- **Expose Grafana as `grafana.ghamrr-lab.site` through the existing
  tunnel**, following the ADR 0021 pattern exactly:
  cloudflared → Traefik (`traefik.kube-system.svc.cluster.local:80`) →
  a new Traefik `Ingress` (`grafana-ingress`, host `grafana.ghamrr-lab.site`)
  in the `observability` namespace → `kube-prometheus-stack-grafana:80`.
- The Ingress lives in Git, deployed by Flux: `infra/observability/grafana/`
  + Kustomization `observability-grafana` (`dependsOn: observability`).
- **Grafana stays `ClusterIP`** — no NodePort, no `externalIPs`, nothing
  exposed on the LAN (the earlier idea of `192.168.1.111:3000` was
  rejected: LAN exposure with only the Grafana login as protection, and a
  hardcoded IP in values).
- **Cloudflare Access protects the subdomain**: `grafana.ghamrr-lab.site`
  is added to the `Owner access` application (email OTP), so the tunnel
  never serves Grafana to an unauthenticated visitor. The Grafana login
  remains as a second factor (defense in depth).
- One-time manual steps in the Cloudflare dashboard (the tunnel runs in
  token mode, its routes are not in Git): DNS CNAME `grafana` →
  `<tunnel>.cfargotunnel.com`, a Public Hostname entry
  `grafana.ghamrr-lab.site` → Traefik, and the Access application entry.
  Documented in `infra/observability/grafana/README.md`.

## Alternatives considered

- **NodePort / `externalIPs: [192.168.1.111]` on the Grafana Service**
  (http://192.168.1.111:3000 or :30080) — rejected: exposes Grafana on the
  LAN (reachable by VPN guests too, ADR 0018) with only the Grafana login;
  hardcodes a host IP in values; NodePort can't use port 3000 anyway
  (range 30000–32767).
- **Direct cloudflared ingress rule to the Grafana Service** (bypassing
  Traefik) — rejected: with token-mode tunnels the rule would live only in
  the Cloudflare dashboard, not in Git — unversioned, against the GitOps
  rule. Going through Traefik keeps the routing in the cluster, in Git.
- **Port-forward** — rejected: not durable, not shareable.

## Consequences

- `https://grafana.ghamrr-lab.site` → Cloudflare Access OTP → Grafana
  login → dashboards (including the as-code dashboards of ADR 0028).
- The Ingress is pruned by Flux if removed from Git; the Cloudflare-side
  entries (DNS, hostname, Access app) are deleted manually (README).
- oauth2-proxy in front of Grafana (roadmap, January) can later replace
  or complement the Access layer, still via the same Ingress.
- Local routing test without Cloudflare:
  `curl -sk --resolve grafana.ghamrr-lab.site:443:192.168.1.111 https://grafana.ghamrr-lab.site/api/health`

## References (official)

- ADR 0021 (lab domain, tunnel, Access), ADR 0027 (Grafana ClusterIP), ADR 0028 (dashboards as code)
- Cloudflare Tunnel public hostnames — https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/configure-tunnels/local-management/
- Cloudflare Access applications — https://developers.cloudflare.com/cloudflare-one/applications/
- Traefik Kubernetes Ingress — https://doc.traefik.io/traefik/routing/providers/kubernetes-ingress/
