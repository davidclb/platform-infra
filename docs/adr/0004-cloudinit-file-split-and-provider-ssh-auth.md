# ADR 0004: Split cloud-init files (vendor/meta/user_account) and provider SSH auth for snippet uploads

## Status
Accepted

## Context
After fixing the cloud-init disk bus (ADR 0003), a new requirement surfaced:
each VM needs a unique hostname, and the QEMU guest agent needs to be
installed at boot — both via cloud-init.

The first attempt combined everything (hostname, user, SSH key, package
install) into a single file passed via `initialization.user_data_file_id`.
This failed for two separate reasons:

1. `user_data_file_id` conflicts with `user_account` — the provider will
   not let a VM resource use both, so `user_account` had to be dropped and
   its content (username, SSH key) duplicated into the raw YAML instead.
2. Retyping the agent-install packages/runcmd into every per-VM file is
   repetitive and error-prone — a first pass on this even forgot the
   `qemu-guest-agent` package entirely on a hostname-only rewrite, which
   silently broke the agent on the next apply.

Separately, uploading any `snippets`-type file via
`proxmox_virtual_environment_file` turned out to require two things not
needed for VM/clone operations alone:
- The Proxmox API token's role needs `Datastore.Allocate`, not just
  `Datastore.AllocateSpace` (the latter only covers allocating disk space
  for VM disks, not uploading arbitrary files to a datastore).
- The provider uploads snippets over **SSH to the Proxmox node itself**,
  independently of the API token. It only supports `ssh { agent = true }`
  (key-based, via the local `ssh-agent`) or an explicit `password`/
  `private_key` — it does **not** read `~/.ssh/config`, and password-only
  SSH access to the node (this homelab's prior setup) does not satisfy it.

## Decision
1. Split cloud-init content across the three independent channels the
   provider exposes, instead of cramming everything into one:
   - `vendor_data_file_id`: one shared file (`vendor-data-agent.yaml`)
     across all VMs, installing and enabling `qemu-guest-agent`. Defined
     once in `cloud-init.tf`, referenced by every VM resource.
   - `meta_data_file_id`: one small file per VM, containing only
     `local-hostname: <name>`.
   - `user_account` (native provider block): username + SSH key, kept as
     a normal attribute rather than folded into a raw file.

   `vendor_data_file_id` and `meta_data_file_id` do not conflict with
   `user_account` — only `user_data_file_id` does.

2. Grant the Proxmox API token role (`TofuProv`) the `Datastore.Allocate`
   privilege in addition to `Datastore.AllocateSpace`.

3. Add an `ssh { agent = true; username = "root" }` block to the
   `proxmox` provider, and switch this homelab's root SSH access from
   password-only to a key added via `ssh-copy-id` — required for the
   provider to upload snippet files at all.

## Consequences
- Adding a new package to install on every VM's first boot means editing
  one shared file (`vendor-data-agent.yaml`), not every VM's cloud-init
  block — reduces the risk of the "forgot the agent on one VM" mistake
  that happened during this session.
- Root SSH access to this Proxmox host is now key-based, not
  password-only. This is a net security improvement for the homelab, not
  just a workaround for OpenTofu.
- Any future VM resource added to this repo must set `wait_for_ip.disabled
  = true` in its `agent` block (see also the 15-minute timeout trap this
  avoids) and reference the shared `vendor_data_file_id`, rather than
  reinventing per-VM agent installation.
- If a future Proxmox role/permission set is rebuilt from scratch, all
  three of `Datastore.AllocateSpace`, `Datastore.Allocate`, and
  `Datastore.AllocateTemplate` must be included, or file-/template-upload
  resources (snippets, ISOs, LXC/VM templates downloaded via
  `proxmox_download_file`) will fail with a misleading 403 that looks like
  a broader permissions problem.
  - `Datastore.AllocateSpace`: allocating disk space for VM/container disks.
  - `Datastore.Allocate`: uploading arbitrary files to a datastore
    (snippets, in ADR 0004's original case).
  - `Datastore.AllocateTemplate`: downloading/registering a VM or LXC
    template on a datastore via `proxmox_download_file` — discovered when
    provisioning the `pihole`/`vpn` LXC containers (platform-infra), which
    failed with `403 ... Datastore.AllocateTemplate` despite already
    having the other two privileges.
