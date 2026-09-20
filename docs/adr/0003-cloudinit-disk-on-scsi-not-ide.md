# ADR 0003: Attach the cloud-init disk on SCSI, not IDE

## Status
Accepted

## Context
When building the Ubuntu 24.04 cloud-init template on Proxmox, the VM
booted successfully but never obtained an IP address, the injected SSH
user never worked, and the QEMU guest agent never started — despite a
correct cloud-config (`#cloud-config`) file with `users`, `packages`, and
`runcmd` sections attached via `--cicustom`.

The symptom was misleading: it looked like a network/DHCP issue (`tcpdump`
on the Proxmox bridge showed zero DHCP traffic from the VM), which pointed
investigation toward the bridge, the cloud-init YAML syntax
(`user=` vs `vendor=`), and `--ipconfig0` — none of which were the actual
cause.

The real cause: the cloud-init drive was attached on an IDE bus
(`--ide2 local-lvm:cloudinit`), which is the configuration shown in most
Proxmox cloud-init tutorials. This is a known issue specific to Ubuntu
24.04 images: the guest boots and reads the IDE cloud-init ISO enough to
find the filesystem, but does not reliably apply the user-data/network
config from it — so nothing in the cloud-config (user, SSH key, network,
packages) actually gets applied, silently.

## Decision
Attach the cloud-init drive on a SCSI bus instead of IDE:
```
qm set 9000 --scsi1 local-lvm:cloudinit
```
instead of:
```
qm set 9000 --ide2 local-lvm:cloudinit
```
(with `--scsihw virtio-scsi-pci` already set, and the main OS disk on
`scsi0`).

## Consequences
- This applies to any future Ubuntu 24.04+ cloud-init template built on
  this Proxmox host — IDE for cloud-init should not be used again here.
- Debugging this cost significant time because the symptom (no IP) pointed
  toward network configuration, not disk bus assignment. Future cloud-init
  troubleshooting on this host should check the cloud-init drive's bus
  before investigating network/DHCP specifically.
- Not yet verified whether this is Ubuntu-24.04-specific or would also
  affect other cloud images (Debian 12, etc.) built later — revisit if a
  future template on a different distro shows the same symptom.
