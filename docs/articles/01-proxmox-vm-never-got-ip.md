# Debugging a Proxmox VM that never got an IP — it wasn't the network

*Draft based on [ADR 0003](../adr/0003-cloudinit-disk-on-scsi-not-ide.md). Facts only — rewrite in my own voice before publishing.*

---

I was building an Ubuntu 24.04 cloud-init template on Proxmox — the base
image every K3s node in my homelab would clone from. The plan was
straightforward: a `#cloud-config` file setting the SSH user, injecting a
key, installing a couple of packages. Nothing exotic.

The VM booted. And then... nothing. No IP address. No SSH access. The
QEMU guest agent never came up. It just sat there, seemingly alive but
completely unreachable.

## The obvious suspect: the network

My first assumption was DHCP. A VM with no IP on a fresh bridge — that's
a networking problem nine times out of ten. So I went there first:
`tcpdump` on the Proxmox bridge interface, watching for any DHCP traffic
coming from the VM at all.

Zero. Not a single DHCPDISCOVER packet leaving the guest.

That redirected the investigation further into cloud-init territory: was
the YAML malformed? Was I using `user=` when I should have used
`vendor=`? Was `--ipconfig0` set correctly? I went through the
cloud-config syntax line by line, cross-checked it against the official
schema, tried variations. Nothing changed the outcome.

At this point I'd spent real time convinced this was a config-syntax or
network-config problem — because that's what the symptom looked like.

## The actual cause: the wrong bus, not the wrong config

The cloud-init drive was attached like this:

```
qm set 9000 --ide2 local-lvm:cloudinit
```

IDE. Which is what nearly every Proxmox cloud-init tutorial shows — it's
the default, boring choice that "just works" in most examples.

Except it doesn't, reliably, on Ubuntu 24.04 cloud images specifically.
The VM boots, the guest reads the IDE cloud-init ISO just enough to find
a filesystem on it — but it does not reliably apply the actual
user-data/network configuration from it. Nothing in the cloud-config
(user, SSH key, network, packages) gets applied. No error. No log entry
screaming "wrong bus." It just silently does nothing.

The fix:

```
qm set 9000 --scsi1 local-lvm:cloudinit
```

SCSI instead of IDE (with `--scsihw virtio-scsi-pci` set, main OS disk on
`scsi0`). Same cloud-config file, same VM — except now it actually got
applied. IP address, SSH access, guest agent — all working within
seconds of boot.

## Why this one was hard to catch

The symptom (no IP) pointed exactly where you'd expect it to: network
configuration. Every diagnostic step I took — `tcpdump`, cloud-init YAML
review, `--ipconfig0` — was a reasonable response to that symptom. None
of them were wrong to check. They just weren't where the actual bug
lived.

The real lesson isn't "IDE bad, SCSI good" — it's that a silent
cloud-init failure can look identical to a dozen other failures further
up the stack, and the fastest way to lose time is to keep investigating
deeper into the symptom's *apparent* domain instead of stepping back and
checking the disk bus the cloud-init drive is attached to.

## Takeaway

If a Proxmox VM boots but cloud-init seems to have done nothing —
no hostname, no user, no network — check the bus the cloud-init disk is
attached on before touching anything else. IDE is the tutorial default.
SCSI is what actually works reliably on Ubuntu 24.04+ images, at least on
this Proxmox host.

---

*Not yet verified whether this is Ubuntu-24.04-specific or affects other
cloud images (Debian 12, etc.) — will update if a later template on a
different distro hits the same symptom.*
