# ADR 0026: Hostinger (tier 3) — one shared observability stack for every app, multi-host over WireGuard

## Status
Accepted — refines tier 3 of ADR 0016. Implemented in
`hostinger/observability/` (Prometheus + Alertmanager; Grafana,
node-exporter and cAdvisor to follow).

## Context

ADR 0016 splits observability into three tiers. For tier 3 (production on
the Hostinger VPS) it says: Prometheus + Grafana + Node Exporter + cAdvisor
"added as extra services in Ghamr's existing docker-compose.yml".

The VPS no longer runs only Ghamr. In November 2026 it hosts Ghamr, Yoshu,
FamilyTree, Yukionigiri, plus shared infrastructure (Nginx Proxy Manager,
wg-easy) under `~/infra`. More apps are planned, possibly on a second VPS.

What exists today:

- Yoshu ships its own `yoshu_prometheus` + `yoshu_grafana` inside Yoshu's
  compose project. Its `prometheus.yml` is a copied template: it scrapes a
  `cv-generator` that does not exist, its own port wrongly (9091), and
  exporters that are not running; it joins no application network; images
  are `:latest`. It observes nothing useful — there is nothing to migrate.
- Yoshu's backend already exposes application metrics on `/metrics`
  (request count, duration, in-flight), not published on the internet
  (NPM forwards only `/api/`).
- Ghamr exposes no `/metrics` yet.

Following ADR 0016 literally would mean one stack per app (Ghamr's, then
Yoshu's, then each new app's): N Prometheus and N Grafana on one host, the
host metrics (node-exporter, cAdvisor) collected N times, and monitoring
that disappears whenever the app that owns it is stopped or redeployed.

## Decision

1. **One observability stack per tier-3 environment, owned by no app.**
   Prometheus, Grafana, node-exporter and cAdvisor run as their own compose
   project on the Hostinger VPS, next to NPM and wg-easy in `~/infra`. Its
   configuration lives in this repo (the `hostinger/observability/`
   layout is to be confirmed), not in an application repo.
   ADR 0016's separation still holds: this stack is independent of the
   homelab's (tiers 1–2) and is not federated with it.

2. **Apps opt in with two things, nothing else:** expose `/metrics`
   (application code, in the app's repo) and join an external Docker
   network, `observability`. Prometheus pulls from them over that network
   (the pull model Prometheus recommends — FAQ, "Why do you pull rather
   than push?").

3. **Scrape targets are declared as files** (`file_sd_configs`, one file
   per app), not discovered through the Docker socket (`docker_sd_configs`).
   Docker discovery would need `/var/run/docker.sock` mounted in
   Prometheus, which is root-equivalent access to the host. Prometheus's
   security model presumes that "only trusted users have the ability to
   change the … configuration file", and "which targets Prometheus scrapes
   … is determined entirely via the configuration file": the target list
   stays a reviewed file in git.

4. **A second host is scraped over WireGuard**, never over the internet:
   node-exporter (and the apps' `/metrics`) listen on the host's WireGuard
   address only, and the same Prometheus scrapes them. No `/metrics` and
   no exporter port is published publicly.

5. **Nothing is published publicly by the stack itself.** Grafana and
   Prometheus bind to `127.0.0.1` (reached through the existing
   `hostinger-grafana` / `hostinger-prometheus` SSH tunnels), as today.

6. **Same rules as the rest of the repo:** images pinned (version +
   digest, no `:latest`); data sources and dashboards provisioned from files
   (ADR 0016: dashboards as code); a retention limit set explicitly
   (`--storage.tsdb.retention.time`) so disk use is bounded on a shared VPS.

## Consequences

- Adding an app = one `/metrics` endpoint, one network line in its compose
  file, one target file here. No change to Prometheus itself.
- Host metrics are collected once. node-exporter needs the host
  namespaces and a read-only bind mount of `/` (node_exporter README,
  "Docker" section: containerised deployment "requires extra care in order
  to avoid monitoring the container itself"); cAdvisor needs read access to
  the Docker and cgroup directories. Both are privileged in the sense of
  seeing the whole host — accepted, they are read-only and not exposed.
- Monitoring outlives app redeploys and app removals; a stopped app shows
  as `up == 0` instead of taking its own monitoring down with it.
- One shared Grafana: its admin account and data sources must be managed
  centrally (provisioning), not per app.
- Yoshu's current `yoshu_prometheus` / `yoshu_grafana` are removed together
  with Yoshu's old Supabase stack after the Yoshu production reset (Yoshu
  repo, `deploy/prod/README.md`); Yoshu's new compose only adds the
  `observability` network to its backend.

## Alternatives considered

- **Per-app stacks (ADR 0016 as written).** Rejected for the reasons in
  Context: duplicated host metrics, N Grafanas, monitoring tied to app
  lifecycle.
- **Docker service discovery** (`docker_sd_configs` + labels). Zero config
  per app, but requires the Docker socket in Prometheus (root-equivalent).
  Revisit only with a read-only socket proxy in front of it.
- **Prometheus Agent mode + `remote_write`** from each host to the central
  one. The standard answer when the central server cannot reach the
  targets (NAT, many hosts); with two hosts on a WireGuard network, plain
  scraping is simpler and keeps the "target is down" signal. Revisit if
  hosts multiply or cannot be reached from the central host.
- **A hosted service (e.g. Grafana Cloud free tier).** Less to run, but
  sends production metrics to a third party and builds less of the skill
  this repo is for.

## Follow-ups (not decided here)

- Ghamr: add a `/metrics` endpoint (application code, Ghamr repo).
- Alerting (Alertmanager, notification channel).
- Logs (Loki), which ADR 0016 already keeps separate from metrics
  (Prometheus FAQ: "How to feed logs into Prometheus? Short answer: Don't!").

## References (official)

- Prometheus FAQ — https://prometheus.io/docs/introduction/faq/
- Prometheus security model — https://prometheus.io/docs/operating/security/
- Prometheus configuration (`file_sd_configs`, `docker_sd_configs`) —
  https://prometheus.io/docs/prometheus/latest/configuration/configuration/
- Prometheus Agent mode — https://prometheus.io/docs/prometheus/latest/prometheus_agent/
- Prometheus instrumentation practices — https://prometheus.io/docs/practices/instrumentation/
- Prometheus guides: file-based service discovery — https://prometheus.io/docs/guides/file-sd/ ;
  cAdvisor — https://prometheus.io/docs/guides/cadvisor/ ;
  Node Exporter — https://prometheus.io/docs/guides/node-exporter/
- Grafana provisioning — https://grafana.com/docs/grafana/latest/administration/provisioning/
- node_exporter README, "Docker" — https://github.com/prometheus/node_exporter
- cAdvisor — https://github.com/google/cadvisor
