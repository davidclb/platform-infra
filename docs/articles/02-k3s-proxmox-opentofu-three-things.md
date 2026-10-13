# Provisioning K3s on Proxmox with OpenTofu: three things nobody's tutorial mentioned

*Draft based on [ADR 0004](../adr/0004-cloudinit-file-split-and-provider-ssh-auth.md) and [ADR 0005](../adr/0005-stop-on-destroy.md). Facts only — rewrite in my own voice before publishing.*

---

Once the cloud-init template actually worked (see the [previous
post](01-proxmox-vm-never-got-ip.md) — turns out it was the disk bus, not
the network), the next step was provisioning real K3s master/worker VMs
from it with OpenTofu and the `bpg/proxmox` provider. Here are three
things that cost real debugging time, none of which showed up clearly in
the tutorials I'd read.

## 1. `user_data_file_id` and `user_account` don't mix

Every VM needs a unique hostname and the QEMU guest agent installed at
boot. The first attempt crammed hostname, SSH user, key, and package
install into one file, passed via `initialization.user_data_file_id`.

That fails for a non-obvious reason: `user_data_file_id` conflicts with
the provider's native `user_account` block. You can't use both on the
same VM resource — pick one. So `user_account` had to go, its content
(username, SSH key) duplicated into raw YAML instead. Workable, but
repetitive: retyping the same agent-install packages/runcmd into every
per-VM file is exactly the kind of copy-paste that silently drifts. On a
first hostname-only rewrite, the `qemu-guest-agent` package got dropped
entirely from one file — the VM came up, but the agent never started,
and nothing said why.

**What actually works**: split cloud-init across the three independent
channels the provider exposes instead of merging everything into one
file:
- `vendor_data_file_id` — one file, shared across every VM, installing
  and enabling `qemu-guest-agent`. Defined once, referenced everywhere.
- `meta_data_file_id` — one small per-VM file, just `local-hostname: <name>`.
- `user_account` — kept as a normal provider attribute, not folded into
  a file at all.

`vendor_data_file_id` and `meta_data_file_id` don't conflict with
`user_account` — only `user_data_file_id` does. Adding a new package to
every VM's first boot now means editing one shared file, not N per-VM
ones.

## 2. `Datastore.AllocateSpace` is not `Datastore.Allocate`

Uploading a `snippets`-type file (the vendor-data/meta-data files above)
via `proxmox_virtual_environment_file` needs a specific API token
privilege: `Datastore.Allocate`. Not `Datastore.AllocateSpace` — that one
only covers allocating disk space *for VM disks*, not uploading arbitrary
files to a datastore. The distinction is one word, and the failure mode
(a 403) gives no hint which of the two you're missing.

## 3. Snippet uploads go over SSH to the node — not the API token

Separately: the provider doesn't upload snippet files through the API
token at all. It uploads them over **SSH to the Proxmox node itself**,
and it's picky about how — `ssh { agent = true }` (key-based, via the
local `ssh-agent`) or an explicit `password`/`private_key` block. It does
**not** read `~/.ssh/config`. This homelab's root access was
password-only at the time, which the provider simply doesn't accept for
this operation. Fix: `ssh-copy-id` a real key to the node, add the `ssh`
block to the provider config. Net result — root SSH on this Proxmox host
is now key-based, not password-only. Not just a workaround; a real
security improvement that happened as a side effect of getting Terraform
providers to cooperate.

## Bonus: `tofu destroy` hanging on a VM shutdown lock

Once provisioning worked, tearing it down didn't, cleanly:

```
Error: VM shutdown
task "...:qmshutdown:<vmid>:..." failed to complete with exit code:
can't lock file '/var/lock/qemu-server/lock-<vmid>.conf' - got timeout
```

This is a known issue in the `bpg/proxmox` provider: the default destroy
behavior requests a clean ACPI/agent-driven shutdown, which can hang and
hold a lock on the VM's config file. The fix is a single flag:
`stop_on_destroy = true` on every VM resource — forces a hard stop
instead of waiting on a clean shutdown. Tested directly: with the flag
set, `tofu destroy` on both `k3s-master` and `k3s-worker` completed in
~2 seconds each, no lock timeout. A follow-up `tofu apply` recreated both
cleanly.

## Takeaway

None of these three (or four) issues are hard once you know them. What
made them cost time is that each one *looks* like something else at
first — a YAML conflict looks like a syntax mistake, a 403 looks like a
broader permissions problem, an SSH failure looks like a config-loading
bug, a shutdown timeout looks like a Proxmox flake. Every fix here ended
up being one flag, one privilege, or one file split away — but finding
which one took actually hitting each of them.
