# ADR 0005: stop_on_destroy to avoid VM shutdown lock timeouts

## Status
Accepted

## Context
A manual `tofu destroy` failed with:
```
Error: VM shutdown
task "...:qmshutdown:<vmid>:..." failed to complete with exit code:
can't lock file '/var/lock/qemu-server/lock-<vmid>.conf' - got timeout
```
This is a known upstream issue with the `bpg/proxmox` provider's default
destroy behavior: it requests a clean ACPI/agent-driven shutdown
(`qmshutdown`), which can hang and hold a lock on the VM's config file,
blocking further operations until Proxmox's own timeout expires
(github.com/bpg/terraform-provider-proxmox/issues/1620, /995 report the
same symptom, in some cases even with `stop_on_destroy` already set).

## Decision
Set `stop_on_destroy = true` on every VM resource in this repo — forces a
hard stop instead of a clean shutdown on destroy/replace.

## Verification
Tested directly on this repo: with `stop_on_destroy = true`, a full
`tofu destroy` of both `k3s-master` and `k3s-worker` completed in ~2s per
VM, no lock timeout. A subsequent `tofu apply` recreated both cleanly.
The upstream issue exists, but this flag resolves it for our setup.

## Consequences
- Any new VM resource added to this repo must include
  `stop_on_destroy = true` to get the same reliable destroy behavior.
- If a lock timeout resurfaces despite this flag (matching the upstream
  issue), the manual recovery is:
  ```bash
  qm unlock <vmid>       # or: rm /var/lock/qemu-server/lock-<vmid>.conf
  qm stop <vmid>
  ```
  followed by `tofu plan` to confirm state consistency before retrying.
