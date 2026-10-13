# ADR 0019: Vault dev mode first — ephemeral data accepted as a learning step

## Status
Accepted

## Context
HashiCorp's own documentation is explicit: *"Never, ever, ever run a
'dev' mode server in production. It is insecure."* Dev mode differs from
a real Vault deployment in every dimension that matters for actually
storing secrets:

| Aspect | Dev mode | Production mode |
|---|---|---|
| Storage | In-memory only | Persistent (Raft, or Consul) |
| TLS | None (`http://127.0.0.1:8200`) | Required |
| Seal/unseal | Auto-unsealed at boot | Manual unseal key process |
| Root token | Auto-generated, printed at boot | Controlled distribution |
| Data on restart | **Lost entirely** | Persisted |

The roadmap (`DevSecOps-IDP-Roadmap-6mois.md`, Phase 2.2) already planned
for this as a two-step path: *"Vault (dev mode d'abord, puis prod mode)"*.

## Decision
Install and run Vault in dev mode first, on `vault-01` (ADR 0010), via a
systemd service wrapping `vault server -dev`. This is accepted as a
deliberate learning/integration step — not a shortcut mistaken for the
real thing.

## Consequences
- **No secret stored in this dev-mode Vault should be treated as durable.**
  A VM reboot, a service restart, or a crash erases everything — this is
  expected behavior, not a bug to work around.
- Dev mode is useful for: learning Vault's CLI/API, standing up and
  testing External Secrets Operator's integration with Vault (the
  Kubernetes-side plumbing), and validating the overall secrets-flow
  design — none of which require durable storage yet.
- **Before any real secret is stored** (e.g. Ghamr's LLM API key, once
  Ghamr is deployed to the homelab per ADR 0008), this ADR must be
  revisited and Vault migrated to production mode: Raft integrated
  storage, TLS, and a real unseal process. Treat "Vault is running" and
  "Vault is ready to hold real secrets" as two different milestones —
  don't conflate them.
- Update this ADR's status to Superseded once the production-mode
  migration happens, noting what the final storage/TLS/unseal setup
  looks like.
