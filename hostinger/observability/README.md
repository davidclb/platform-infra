# Hostinger observability stack

Prometheus and Alertmanager for every app on the Hostinger VPS (tier 3).
[ADR 0026](../../docs/adr/0026-hostinger-shared-observability-stack.md)
explains why there is one shared stack and why targets are files.
Grafana, node-exporter and cAdvisor come in a later change.

| Path | What |
|---|---|
| `compose.yaml` | The two services, images pinned by digest, UIs on `127.0.0.1` only |
| `prometheus/prometheus.yml` | Scrape config: the stack itself, plus one `apps` job fed by `targets/` |
| `prometheus/targets/<app>.yml` | One file per app: its `/metrics` address and its `app` label |
| `prometheus/rules/*.rules.yml` | Recording and alerting rules, each commented with what it answers |
| `prometheus/tests/rules.test.yml` | Unit tests of the rules: each alert fires and stays quiet as intended |
| `alertmanager/alertmanager.yml` | Routing to Telegram: `page` with sound, `ticket` silent |
| `ci.yml` | `promtool` / `amtool` checks, to include in `.gitlab-ci.yml` |

## Checks, locally

```sh
P=prom/prometheus:v3.16.0@sha256:e04987641b57704f408e31f6373ba4138ecf27cb4a165d24aabb6c38fddd0f06
A=prom/alertmanager:v0.35.1@sha256:4e3d029e69c7f61dd53a2b31a3dc427a2b81736cffca185c0854075e07969e36
docker run --rm --entrypoint promtool -v "$PWD/prometheus:/p:ro" "$P" check config /p/prometheus.yml
docker run --rm --entrypoint promtool -v "$PWD/prometheus:/p:ro" -w /p/tests "$P" test rules rules.test.yml
docker run --rm --entrypoint amtool -v "$PWD/alertmanager:/a:ro" "$A" check-config /a/alertmanager.yml
```

## First deployment

1. **The Telegram bot.**
   - Create the bot with @BotFather: it gives the token.
   - Send the bot any message, then read `chat.id` from `https://api.telegram.org/bot<token>/getUpdates`.
   - Store both values encrypted with SOPS, like the other secrets in `secrets/`.
2. **The shared network**, once per host: `docker network create observability`.
3. **Copy the stack** to `~/infra/observability` on the VPS. Then decrypt the two values into `secrets/telegram_bot_token` and `secrets/telegram_chat_id`: one value per file, no newline.
   - Alertmanager runs as `nobody` (65534) and reads them through a bind mount, so: `chown 65534 secrets/* && chmod 400 secrets/*`.
   - `secrets/` is in `.gitignore`.
4. `docker compose up -d`.
5. **Each app joins the network.** In its compose file, the service that serves `/metrics` gets `networks: [default, observability]`, and `observability` is declared `external: true`. The app's file in `targets/` then becomes reachable.

## Checking it end to end

- Through the SSH tunnel, http://localhost:9090/targets shows each app `UP`.
- http://localhost:9090/alerts lists the rules.
- **A test alert, straight to Alertmanager**, to prove the Telegram delivery:

  ```sh
  docker compose exec alertmanager amtool alert add TestAlert severity=ticket app=test \
    --annotation=summary="Test from amtool" --alertmanager.url=http://localhost:9093
  ```

  The message comes silently (`ticket`) within `group_wait` (30 s).

## Adding an app

1. A `/metrics` endpoint that the internet can't reach.
2. Its service on the `observability` network.
3. A `targets/<app>.yml` here, with its `app` label.
4. Optionally, its rules in `rules/<app>.rules.yml` and their tests.

Nothing else changes.
