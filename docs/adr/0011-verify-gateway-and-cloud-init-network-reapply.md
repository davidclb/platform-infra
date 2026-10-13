# ADR 0011: Verify the real LAN gateway, and force cloud-init to reapply network config

## Status
Accepted

## Context
Both `k3s-master.tf` and `k3s-worker.tf` were written with
`gateway = "192.168.1.1"`, assumed by convention (most consumer routers
default to `.1`) rather than verified against this homelab's actual box.
The real gateway is `192.168.1.254`.

This produced a long, misleading debugging chain: SSH into the VMs worked
fine (inbound traffic), so the VMs appeared reachable. But `ping`/`curl` to
the gateway, to `192.168.1.1`, and to public IPs all failed with
"Destination Host Unreachable" — first suspected as a Proxmox
bridge/firewall issue, then as an ARP cache issue, before the real cause
(wrong gateway) surfaced. The same symptom reproduced on `pihole` (an
already-working LXC container unrelated to this session's changes),
which was the key signal ruling out anything specific to the new VMs.

A second, separate issue compounded this: after fixing `gateway` in the
`.tf` files and running `tofu apply`, `qm config <vmid> | grep ipconfig`
confirmed Proxmox had the correct value (`gw=192.168.1.254`) — but the
VM's own `ip route` still showed the old gateway (`.1`). Cloud-init
applies network configuration from the cloud-init disk primarily on the
**first boot** of a VM; a config change pushed to an already-provisioned
VM's cloud-init metadata is not automatically re-read on a plain reboot.

## Decision
1. Never assume a LAN gateway by convention — verify it (`ip route` on
   the Proxmox host, or the router's own admin interface) before writing
   it into any `.tf`/inventory file.
2. When a VM's cloud-init network config changes after the VM already
   exists (e.g. correcting a wrong gateway), force cloud-init to reapply
   it rather than just rebooting:
   ```bash
   sudo cloud-init clean
   sudo reboot
   ```
   A plain `sudo reboot` alone is not sufficient and can silently leave
   the VM running with stale network config while both the `.tf` file and
   Proxmox's own stored config already show the corrected value —
   `tofu plan` will report "No changes" in this state, which does NOT mean
   the VM's actual runtime config matches.

## Consequences
- Any future gateway/IP config change on an existing VM (not just at
  creation) must be followed by `cloud-init clean` + reboot on that VM,
  not just `tofu apply`.
- When network connectivity looks broken from a specific VM, checking a
  second, unrelated, already-working host (like `pihole` here) on the same
  bridge is a fast way to tell "problem specific to this VM" from
  "problem with the network/gateway itself" — worth doing early next time,
  not after several other hypotheses.
- `tofu plan` reporting "No changes" only confirms OpenTofu's state matches
  the provider's API-reported config (Proxmox's stored VM config here) —
  it says nothing about whether the guest OS has actually re-read and
  applied that config yet.
