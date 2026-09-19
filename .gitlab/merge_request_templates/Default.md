## Quoi et pourquoi

<!-- Ce que ce MR change, et le choix d'architecture derrière si non trivial.
     Si le choix mérite un ADR (docs/adr/), le lier ici. -->

## Definition of done

- [ ] `pre-commit run --all-files` passe (Gitleaks + terraform fmt/validate)
- [ ] Scan de sécurité (tfsec/Checkov) passé en local ou vert en CI
- [ ] Testé localement (préciser comment : `tofu plan`, playbook en check mode, etc.)
- [ ] Pas de secret en clair — SOPS si applicable
- [ ] Documentation à jour (README, ADR) si le changement le justifie
- [ ] Je peux expliquer chaque choix de ce MR sans relire le code (objectif entretien)

## Rollback

<!-- Comment revenir en arrière si ce changement casse quelque chose en lab. -->
