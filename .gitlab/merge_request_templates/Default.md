## What and why

<!-- What this MR changes, and the architecture decision behind it if
     non-trivial. If the choice deserves an ADR (docs/adr/), link it here. -->

## Definition of done

- [ ] `pre-commit run --all-files` passes (Gitleaks + terraform fmt/validate)
- [ ] Security scan (tfsec/Checkov) passed locally or green in CI
- [ ] Tested locally (state how: `tofu plan`, playbook in check mode, etc.)
- [ ] No plaintext secrets — SOPS if applicable
- [ ] Docs up to date (README, ADR) if the change warrants it
- [ ] I can explain every choice in this MR without re-reading the code (interview goal)

## Rollback

<!-- How to revert if this change breaks something in the lab. -->
