# CLAUDE.md — platform-infra

Instructions for Claude Code on this repo. Read before taking any action.

## Project goal

Proxmox homelab: a real lab, reproducible, that can be spun up and torn down
on demand. This is not a static demo project — it's the user's DevSecOps
skill-building ground, and a concrete talking point for their giga-roadmap
job search (see `DevSecOps-IDP-Roadmap-6mois.md` in the 2ndBrain — this
CLAUDE.md doesn't replace that roadmap, it complements it for this specific
repo). Two things matter as much as the end result:
- the lab actually works (clean up/down, reproducible)
- the user can explain it, defend it, and rebuild it alone, because they're
  the one who'll be interviewed on it, not Claude.

## Rule #0 — AI governance on this repo

Unlike application code repos (Go — Ghamr, Morgoth, vuln-server), where the
rule is zero AI in committed code, here AI CAN scaffold and write
infrastructure. But three guardrails apply together, never one without the
others:

**1. Human guardrail — architecture decisions stay with the user.**
- Claude does not decide alone on a structuring choice (provider, module
  breakdown, network pattern, secrets strategy, etc.): it presents options,
  their trade-offs, and a recommendation — the user decides.
- Before writing a new file or making a non-trivial decision, Claude
  confirms the approach step by step rather than delivering a finished
  block all at once.
- Explicit goal: the user should be able to justify and reproduce, alone,
  in an interview, every choice in this repo — not just know it exists.

**2. Learning guardrail — flag what's worth doing by hand.**
- Whenever an action has learning value for the user (a piece of logic they
  should type themselves to really understand it and be able to
  rebuild/defend it in an interview — not repetitive boilerplate, and not
  an action on their own accounts/credentials that only they can do
  anyway), Claude stops and explicitly asks: do it, or let the user do/type
  it themselves? **Blocking mode**: wait for the answer before proceeding,
  don't just flag it and continue.
- Repetitive scaffolding (folder structure, YAML boilerplate) can be
  produced directly; a module's logic, a resource block choice, a security
  policy fall under this guardrail.

**3. Automated guardrail — no trust unverified by a machine.**
- A CLAUDE.md can hallucinate or be poorly followed. A policy-as-code
  pipeline never lies.
- Any config produced with Claude's help (Terraform, Kustomize, Ansible)
  must pass an automated check before merge: lint + security scan
  (tfsec/Checkov for Terraform, Kyverno/conftest for K8s).
- If this guardrail doesn't exist yet for a given layer, say so explicitly
  rather than committing as if it did — and propose adding it alongside the
  first relevant file, not as an afterthought.

Never commit blindly: if unrelated work gets mixed into a session, sort by
topic and propose atomic commits.

## Repo conventions

- **Conventional Commits** (`feat:`, `fix:`, `chore:`, `docs:`) on every
  commit.
- **ADRs** (`docs/adr/`): one file per structuring choice (e.g. why
  OpenTofu over Terraform, why Kustomize over Helm for a given layer, why
  GitLab SaaS over self-hosted). Directly serves the "justify every choice
  in an interview" goal.
- **MR template + definition of done** (`.gitlab/merge_request_templates/`)
  with a checklist before merging into `main` — even solo, it builds the
  review habit.
- **Secrets**: never in plaintext, from the very first commit. SOPS + Age
  (see roadmap Phase 6.6 for the full target state with Vault).
- **CODEOWNERS**: present from Phase 0 even solo (convention exercise, user
  = sole owner for now).
- **Pre-commit hooks (Gitleaks)**: active before the first
  Terraform/OpenTofu file even exists — secret-leak safety net from the
  first commit, not bolted on afterward.
- **`main` branch protected** on GitLab (no direct force-push) — only
  unprotect temporarily if needed, and always re-protect afterward.

## Technical context

- Proxmox homelab, monorepo (`terraform/`, `ansible/`, `argocd/apps/<app>/base+overlays/`).
- Hosted on **GitLab SaaS** (`gitlab.com/davidclb/platform-infra`) with
  **GitLab CI** — deliberately distinct from GitHub Actions used on the app
  repos (Ghamr/Yoshu/Arbre), to cover both CI/CD ecosystems on the market.
  Don't move this repo to GitHub without an explicit re-decision.
  - Deliberate choice over self-hosting on the homelab itself: the homelab
    is the DEV/LAB where it's fine to break everything, so the Git source
    of truth + CI must stay outside the infrastructure it drives (same
    logic as the Terraform state living on Oracle/S3 in Phase 3.1, never on
    the homelab cluster). Idea to explore separately: hosting a forge
    (Gitea/GitLab CE) as an *application* of the homelab later, not as the
    source of truth driving the homelab.
- Trunk-based (main + short-lived branches + MR), no Git Flow.
- Tooling driven from the laptop only (agentless), never from the target
  VMs.
- **OpenTofu** (not official Terraform): greenfield, clean OSI license,
  skills 100% transferable to Terraform. For interviews/CV:
  "Terraform/OpenTofu".
  (Terragrunt: not decided yet — to be settled once there's a real need to
  orchestrate multiple environments/modules, not before.)
- **mise** for tool version management (`.mise.toml` tracked in git).
- Design constraint: everything must be able to come up and go down
  cleanly (spin up/tear down on demand), not just deploy once.

## Reference

See `DevSecOps-IDP-Roadmap-6mois.md` (2ndBrain,
`Active projects/IT/ROADMAP JUSTE SUIVRE/`) for the full 6-month plan
(Phases 0-8, target stack details, per-phase thinking challenges). This
repo mainly corresponds to Phases 0, 1.2, 2.1, 3.1 and 6 of that roadmap.
