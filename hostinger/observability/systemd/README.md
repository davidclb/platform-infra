# VPS-side reload: user timer

The CI deploy key is rsync-write-only (`restrict,command="rrsync -wo …"`),
so the pipeline cannot run `docker compose up -d` itself. Instead the VPS
reconciles its own stack: a **user** systemd timer runs
`docker compose up -d` every 2 minutes, which is idempotent — it does
nothing until an rsync changes a file, then recreates the affected
containers.

These unit files travel with the stack (they are rsynced into
`~/infra/observability/systemd/`), but systemd does not read them from
there. They are installed **once, by hand**, into the user unit directory.

## One-time install (as `dev` on the VPS)

```sh
# 1. Let the user manager run without an active login session, so the timer
#    keeps firing after you disconnect. (Needs sudo once.)
sudo loginctl enable-linger dev

# 2. Link the units into the user unit directory.
mkdir -p ~/.config/systemd/user
ln -sf ~/infra/observability/systemd/observability-reload.service ~/.config/systemd/user/
ln -sf ~/infra/observability/systemd/observability-reload.timer   ~/.config/systemd/user/

# 3. Enable and start the timer.
systemctl --user daemon-reload
systemctl --user enable --now observability-reload.timer
```

## Check it

```sh
systemctl --user list-timers observability-reload.timer   # next/last run
systemctl --user status observability-reload.service      # last reconcile
journalctl --user -u observability-reload.service -n 50    # its output
```

## Notes

- The units are symlinked, so a later rsync that updates them + a
  `systemctl --user daemon-reload` is enough to pick up changes; no copy.
- If `docker compose` needs a newer compose plugin than the host has, fix
  that on the host — the service just calls `docker compose`.
- To stop auto-reload: `systemctl --user disable --now observability-reload.timer`.
