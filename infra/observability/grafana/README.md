# Grafana public exposure — cloudflared tunnel (ADR 0029, ADR 0021)

Grafana stays `ClusterIP` internally. It is published on
**https://grafana.ghamrr-lab.site** through the existing cloudflared
tunnel: `grafana.ghamrr-lab.site` → cloudflared → Traefik
(`traefik.kube-system.svc.cluster.local:80`) → the `grafana-ingress`
Ingress in this folder → `kube-prometheus-stack-grafana:80`.

## In Git (this repo, deployed by Flux)

- `ingress.yaml` — the Traefik Ingress for `grafana.ghamrr-lab.site`
- deployed by the Flux Kustomization `observability-grafana`
  (`flux/ObservabilityGrafanaKustomization.yml`, dependsOn `observability`)

## One-time manual steps in the Cloudflare Zero Trust dashboard
(the tunnel runs in token mode: its routes live in the dashboard, not Git)

1. **DNS** (zone `ghamrr-lab.site`): CNAME `grafana` →
   `<tunnel-id>.cfargotunnel.com`, proxied (orange cloud).
2. **Zero Trust → Networks → Tunnels → (your tunnel) → Public Hostnames**:
   add `grafana.ghamrr-lab.site` → service
   `http://traefik.kube-system.svc.cluster.local:80`
   (same backend as `ghamrr-lab.site`).
3. **Zero Trust → Access → Applications**: add `grafana.ghamrr-lab.site`
   to the `Owner access` application (email OTP policy) so the subdomain
   is protected like the rest of the lab domain.

## Verify

- Cluster: `kubectl -n observability get ingress grafana-ingress`
- Routing through Traefik without Cloudflare (from the laptop):
  `curl -sk --resolve grafana.ghamrr-lab.site:443:192.168.1.111 https://grafana.ghamrr-lab.site/api/health`
  → `{"message":"..."}`-style Grafana health JSON (Traefik answers, TLS is
  Cloudflare's in production; locally Traefik serves its default cert).
- Publicly: open https://grafana.ghamrr-lab.site → Cloudflare Access OTP
  email → Grafana login → dashboards.

## Rollback

Remove this folder + the `observability-grafana` Kustomization (prune
deletes the Ingress), and delete the DNS record / public hostname /
Access app entry in the dashboard. Grafana was never exposed otherwise.
