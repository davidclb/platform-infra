# ADR 0022: Guard every `apt:` task against fresh-VM lock contention

## Status
Accepted

## Context

Any Ansible playbook that runs `ansible.builtin.apt` against a freshly
created or recently rebooted VM in this homelab is exposed to a
race condition: `unattended-upgrades` (triggered by `apt-daily.timer`/
`apt-daily-upgrade.timer`) can grab the dpkg lock at the same moment
Ansible's own `apt-get install` runs. Unlike a clean "lock busy, retry
later" failure, the collision can leave dpkg itself in a broken state
— interrupted mid-package-configure, corrupting transaction files under
`/var/lib/dpkg/updates/` — which then blocks *every* subsequent `apt`
operation (including an unrelated one, in a different playbook) until
manually repaired:

```bash
for f in /var/lib/dpkg/updates/*; do sudo mv "$f" "${f}.bak"; done
sudo apt-get clean
sudo apt-get update
sudo dpkg --configure -a
```

This was first hit and fixed in `install_vault.yaml` (installing the
`vault` package), and resurfaced independently in `install_flux.yaml`
(installing `python3-kubernetes`, needed by the `kubernetes.core.*`
Ansible modules to talk to the K8s API from the target host) — same
root cause, different playbook, no shared fix between them at the
time. Never documented as an ADR despite being fixed once already,
which is why it had to be rediscovered from scratch.

A `retries`/`until` loop around the `apt:` task alone does **not**
fix this: once dpkg is left in a broken state (not just "lock busy"),
every retry hits the same broken state and fails identically — the
loop never recovers on its own, confirmed directly when it was tried.

## Decision

Every Ansible task that uses `ansible.builtin.apt` (or `apt-get`/`dpkg`
via `command`/`shell`) against one of this homelab's VMs must be
preceded, in the same play, by two guard tasks:

1. **Wait for cloud-init to finish**, so Ansible never races a VM's
   own first-boot package installs:
   ```yaml
   - name: Wait for cloud-init to finish
     ansible.builtin.wait_for:
       path: /var/lib/cloud/instance/boot-finished
       timeout: 300
   ```
2. **Mask the apt-daily timers**, so `unattended-upgrades` cannot
   start mid-playbook even after cloud-init itself is done (cloud-init
   finishing and `unattended-upgrades` triggering are not
   synchronized — the second can still fire independently):
   ```yaml
   - name: Disable apt-daily timers to prevent lock contention
     ansible.builtin.systemd_service:
       name: "{{ item }}"
       enabled: false
       masked: true
       state: stopped
     loop:
       - apt-daily.service
       - apt-daily.timer
       - apt-daily-upgrade.service
       - apt-daily-upgrade.timer
   ```

Applied so far in `install_vault.yaml`; to be added to
`install_flux.yaml` and any future playbook with an `apt:` task
against a homelab VM.

## Consequences

- If dpkg is already broken on a target VM (e.g. this guard is added
  *after* the race already happened once), the manual repair sequence
  above is still needed once, before the guarded playbook can run
  cleanly — the guard prevents recurrence, it doesn't un-break an
  already-corrupted dpkg state.
- Masking `apt-daily.timer` is a standing change on that VM, not
  reverted after the playbook finishes — acceptable on a solo homelab
  where `apt upgrade` is run deliberately via Ansible, not expected to
  happen silently in the background.
- Any new playbook touching `apt` on a homelab VM should copy both
  guard tasks rather than re-discover this failure mode independently
  — this ADR is the canonical reference going forward.
