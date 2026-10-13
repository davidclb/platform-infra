# ADR 0012: `creates:` idempotence guard silently hides environment variable changes

## Status
Accepted

## Context
`install-k3s-master.yaml` originally ran the K3s install script without a
pre-shared `K3S_TOKEN`, letting K3s auto-generate one on first install
(`ansible.builtin.command: /tmp/k3s-install.sh`, guarded by
`args: creates: /usr/local/bin/k3s`). A pre-shared token (stored in
Ansible Vault, `k3s_token`) was added later, passed via
`environment: K3S_TOKEN: "{{ k3s_token }}"` on the same task, with the
intent of using the same token on `install-k3s-worker.yaml` to join the
cluster without ever reading the auto-generated token.

Re-running the playbook after this change did **not** re-run the install
script: `/usr/local/bin/k3s` already existed from the first run, so
`creates:` correctly judged the task "already done" and skipped it —
exactly as idempotence is supposed to work (see ADR-equivalent discussion
of idempotence and `changed_when` earlier in this repo's Ansible work).
The consequence: the K3s server kept running with its original
auto-generated token, while the worker was later configured with the
*vault* token — a mismatch invisible until the worker's `k3s-agent`
service logged `not authorized` trying to join.

This is not a bug in `creates:` — it did exactly what it's documented to
do. The mistake was assuming `creates:`-guarded idempotence stays valid
when an environment variable that affects the *outcome* of the guarded
command changes, without the guard being aware of that variable at all.

## Decision
When a task installs software using `environment:`-provided
configuration that materially affects the installed state (a token, a
version pin, a config flag baked in at install time), a bare
`creates: <binary path>` guard is not sufficient once that configuration
can change across runs. For K3s specifically: if `K3S_TOKEN` (or similar)
changes after first install, the fix is to fully uninstall
(`k3s-uninstall.sh` / `k3s-agent-uninstall.sh`) and re-run the playbook,
not to just re-run `ansible-playbook` and expect the change to apply.

## Consequences
- Any future change to `k3s_token` (rotation, compromise) requires an
  explicit uninstall step on both master and worker before re-running the
  install playbooks — this is not automatic and must be a deliberate,
  documented operation, not just "run the playbook again."
- More generally on this repo: before relying on `creates:` (or any
  simple idempotence guard) for a task, ask whether any `environment:` or
  `vars:` value that affects the guarded command's outcome could change
  between runs. If yes, the guard needs to account for that (e.g. check a
  marker file that encodes the relevant config, or accept that a manual
  reset step is required — as decided here).
- The debugging signal that surfaced this (`not authorized` in
  `journalctl -u k3s-agent`, then comparing the vault token against
  `/var/lib/rancher/k3s/server/node-token` on the master) is the fast path
  to this diagnosis if it resurfaces: a node join failure with
  `not authorized` almost always means a token mismatch between the two
  sides, worth checking before anything else (network, DNS, firewall).
