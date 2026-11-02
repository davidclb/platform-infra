# ADR 0024: PR previews and staging on the homelab, prod alone on Oracle

## Status
Accepted — target state, rolled out in phases (see below). Amends the
environment table of ADR 0008.

## Context

ADR 0008 set three environments for Ghamr: homelab `test` (deployed on
every merge), Oracle `staging` (tag promotion), and prod (Hostinger, then
Oracle). The roadmap then planned, after the ADR 0009 cutover, to run
`staging` and `prod` as two namespaces of a single Oracle cluster, and to
add ephemeral per-PR previews on the homelab in December.

That raised two questions: is a shared, always-on `test` environment
still worth keeping once per-PR previews exist, and where should
`staging` live.

**A shared long-lived test environment is a known bottleneck.** Everyone
merges into it, someone breaks it, and nobody knows exactly which
version is running. Mature teams replace it with one ephemeral
environment per PR, and keep a single stable, prod-like pre-production
environment for what previews cannot do.

**What previews cannot do: third-party integrations on a stable URL.**
- Google OAuth only accepts redirect URIs registered exactly in advance,
  with no wildcard. A `pr-<n>.preview.<domain>` URL that changes with
  every PR cannot sign in with Google. Working around it needs an
  auth relay (one registered callback, then a redirect to the right
  preview through a signed `state`), which means changing Ghamr's code
  and handling the open-redirect risk that such a relay creates.
- Stripe works in previews in test mode: `success_url`/`cancel_url` are
  sent per request, and webhooks can be forwarded to the preview by a
  Stripe CLI sidecar (`stripe listen --forward-to`), with no public
  endpoint to register.

The current homelab `test` already has a stable public URL
(`ghamrr-lab.site`, ADR 0021), and Google OAuth and Stripe are tested
there.

**Namespaces do not isolate cluster-wide changes.** A K3s upgrade, the
planned Flannel → Cilium migration, a CRD change, an admission webhook
(Kyverno), or an operator upgrade hits every namespace of a cluster at
once. With `staging` and `prod` in the same Oracle cluster, these changes
could not be rehearsed before reaching prod. Today the homelab `test`
cluster plays that rehearsal role.

**Oracle Always Free capacity is not guaranteed.** ADR 0009 already
notes that a free ARM instance may not be recreatable. A second Oracle
VM for staging would consume the free quota and carry the same risk.

### Options considered

1. **Keep the original plan**: homelab `test` + previews, Oracle
   `staging` and `prod` as two namespaces of one cluster. Rejected:
   cluster-wide changes hit staging and prod together.
2. **Two Oracle clusters** (`staging` VM, `prod` VM), homelab for
   previews only. Most prod-like (same ARM architecture, same provider,
   same ingress path). Not chosen for now: consumes the free quota and
   depends on getting a second ARM instance. Kept as the fallback.
3. **Homelab as the non-prod cluster (`staging` + previews), Oracle as
   the prod cluster only.** Chosen.
4. **Previews only, no stable pre-production**, Google OAuth through an
   auth relay. Rejected for now: requires changing Ghamr's auth code and
   building a relay safe against open redirects. Possible later, as a
   project of its own.

## Decision

One non-prod cluster (homelab) and one prod cluster (Oracle). Prod is
alone in its cluster.

| Environment | Cluster | Lifetime | Deployed by | Integrations |
|---|---|---|---|---|
| `pr-<n>` | Homelab | Ephemeral, one per labelled PR | ArgoCD ApplicationSet, Pull Request generator | Stripe test mode (Stripe CLI sidecar), no Google sign-in |
| `staging` | Homelab | Permanent | Automatic, on every merge to `main` | Google OAuth + Stripe, on the stable `ghamrr-lab.site` URL |
| `prod` | Oracle | Permanent | Manual promotion by semver tag | Real Google OAuth + Stripe |

```
PR + label `preview` ──▶ homelab : pr-<n>   (ephemeral)
merge to main        ──▶ homelab : staging  (permanent, stable URL)
semver tag           ──▶ Oracle  : prod     (alone in its cluster)
```

**Previews, minimal version:**
- Created only for PRs carrying the `preview` label (Pull Request
  generator label filter), capped at 2–3 concurrent previews.
- Each `pr-<n>` namespace gets default-deny networking, a
  `ResourceQuota` and a `LimitRange` through Kyverno `generate`.
- Its own SQLite database, seeded with synthetic data, never a copy of
  prod.
- TTL: a scheduled GitHub Action removes the `preview` label after N
  days. The namespace is not deleted directly: while the labelled PR
  exists, ArgoCD (`selfHeal`) would recreate it. The generator stays the
  source of truth, and closing or merging the PR destroys the preview.
- The `web-app` chart serves frontend and backend on the same host, with
  `/api` routed to the backend by the ingress. The frontend calls `/api`
  relatively, so one image works in every environment without baking a
  per-preview API URL at build time.

**Prod:** features that are risky or span several PRs are merged behind
a feature flag (a config boolean or a per-user column, no flag service),
enabled for myself first, then for everyone. Each flag is removed once
the feature is stable.

**Cluster-wide changes** (K3s upgrades, Cilium migration, operator and
CRD upgrades, new admission policies) are always applied to the homelab
cluster first, then to Oracle.

### Rollout

1. **November**: nothing changes. The homelab keeps its `test` role while
   Ghamr moves to Oracle (ADR 0009).
2. **December**: per-PR previews, minimal version above.
3. **Once previews are stable**: rename `test` to `staging`, switch the
   automatic deploy on merge to it, and make Oracle prod-only.

## Consequences

- ADR 0008's table no longer holds: the homelab is `staging` + previews
  instead of `test`, and Oracle carries prod only. The "two namespaces
  with a NetworkPolicy between staging and prod" revision planned for
  ADR 0008 is no longer needed.
- **Architecture gap**: staging runs on x86, prod on ARM. The image is
  multi-arch, but an ARM-only issue would first show in prod. Mitigation:
  check the arm64 image in CI.
- **Ingress gap**: staging is exposed through Cloudflare Tunnel, prod
  through a public IP with cert-manager. The prod entry path and HTTPS
  are not rehearsed exactly; the first prod deploy validates them.
- **Availability**: a power or internet outage at home takes staging
  down. Accepted for a non-prod environment.
- **Resources**: `staging`, previews, Flux, ArgoCD, observability and
  Kyverno share 16 GB. Measure with `kubectl top` before raising the
  preview cap.
- **Cross-forge access**: Ghamr's code is on GitHub, platform-infra on
  GitLab. The Pull Request generator needs a read-only GitHub token in
  the cluster.
- Oracle becomes simpler (one environment) and keeps free quota in
  reserve.
- **Revisit** if the x86/ARM or ingress gap causes a real incident: move
  staging to a second Oracle VM (option 2), without destroying the
  working prod instance first.
