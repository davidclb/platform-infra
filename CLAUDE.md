# CLAUDE.md — platform-infra

Instructions pour Claude Code sur ce repo. Lire avant toute action.

## Objectif du projet

Homelab Proxmox : un vrai lab, reproductible, commissionable/décommissionable
à la volée. Ce n'est pas un projet de démo statique — c'est le terrain de
montée en compétence DevSecOps de l'utilisateur, et une pièce d'entretien
concrète dans sa gigaroadmap (voir `DevSecOps-IDP-Roadmap-6mois.md` dans le
2ndBrain — ce fichier CLAUDE.md ne remplace pas la roadmap, il la complète
pour ce repo précis). Deux choses comptent autant que le résultat :
- que le lab marche (up/down propre, reproductible)
- que l'utilisateur sache l'expliquer, le défendre, et le refaire seul,
  parce que c'est lui qui sera interrogé dessus en entretien, pas Claude.

## Règle #0 — Gouvernance de l'IA sur ce repo

Contrairement aux repos de code applicatif (Go — Ghamr, Morgoth,
vuln-server), où c'est zéro IA dans le code committé, ici l'IA PEUT
scaffolder et écrire de l'infra. Mais trois garde-fous s'appliquent
ensemble, jamais l'un sans l'autre :

**1. Garde-fou humain — les décisions d'architecture restent à l'utilisateur.**
- Claude ne tranche pas seul un choix structurant (provider, découpage des
  modules, pattern réseau, stratégie de secrets, etc.) : il présente les
  options, leurs compromis, et une recommandation — l'utilisateur décide.
- Avant d'écrire un fichier nouveau ou une décision non triviale, Claude
  confirme l'approche pas à pas plutôt que de livrer un bloc fini d'un coup.
- Objectif explicite : que l'utilisateur soit capable de justifier et de
  reproduire seul, en entretien, chaque choix du repo — pas seulement de
  savoir qu'il existe.

**2. Garde-fou pédagogique — signaler ce qui vaut la peine d'être fait à la main.**
- Dès qu'une action a de la valeur pédagogique pour l'utilisateur (un bloc
  de logique qu'il devrait taper lui-même pour vraiment le comprendre et
  pouvoir le refaire/défendre en entretien — pas du boilerplate répétitif,
  et pas non plus une action sur ses propres comptes/identifiants qui de
  toute façon ne peut être faite que par lui), Claude s'arrête et demande
  explicitement : le faire, ou laisser l'utilisateur le faire/le taper
  lui-même ? **Mode bloquant** : on attend la réponse avant d'avancer, on
  ne signale pas juste en continuant.
- Le scaffolding répétitif (structure de dossiers, YAML boilerplate) peut
  être produit directement ; la logique d'un module, un choix de resource
  block, une policy de sécurité relèvent de ce garde-fou.

**3. Garde-fou automatisé — aucune confiance non vérifiée par une machine.**
- Un CLAUDE.md peut halluciner ou être mal suivi. Une policy-as-code en
  pipeline ne ment jamais.
- Toute config produite avec l'aide de Claude (Terraform, Kustomize, Ansible)
  doit passer par un contrôle automatisé avant merge : lint + scan de
  sécurité (tfsec/Checkov côté Terraform, Kyverno/conftest côté K8s).
- Si ce garde-fou n'existe pas encore pour une couche donnée, le dire
  explicitement plutôt que de committer comme s'il existait — et proposer
  de le poser en même temps que le premier fichier concerné, pas après coup.

Ne jamais committer à l'aveugle : si du travail non lié se mélange à une
session, trier par sujet et proposer des commits atomiques.

## Conventions du repo

- **Conventional Commits** (`feat:`, `fix:`, `chore:`, `docs:`) sur tous les
  commits.
- **ADR** (`docs/adr/`) : un fichier par choix structurant (ex: pourquoi
  OpenTofu plutôt que Terraform, pourquoi Kustomize plutôt que Helm pour
  telle couche, pourquoi GitLab SaaS plutôt que self-hébergé). Sert
  directement l'objectif "justifier chaque choix en entretien".
- **MR template + definition of done** (`.gitlab/merge_request_templates/`)
  avec checklist avant merge sur `main` — même en solo, entraîne le réflexe
  de revue.
- **Secrets** : jamais en clair, dès le premier commit. SOPS + Age (voir
  roadmap Phase 6.6 pour la cible complète avec Vault).
- **CODEOWNERS** : présent dès Phase 0 même en solo (exercice de convention,
  utilisateur = seul owner pour l'instant).
- **Pre-commit hooks (Gitleaks)** : actifs avant même le premier fichier
  Terraform/OpenTofu — filet anti-secret dès le premier commit, pas ajouté
  après coup.
- **Branche `main` protégée** sur GitLab (pas de force-push direct) — à
  déprotéger temporairement seulement si nécessaire, et à toujours remettre
  ensuite.

## Contexte technique

- Homelab Proxmox, monorepo (`terraform/`, `ansible/`, `argocd/apps/<app>/base+overlays/`).
- Hébergé sur **GitLab SaaS** (`gitlab.com/davidclb/platform-infra`) avec
  **GitLab CI** — volontairement distinct de GitHub Actions utilisé sur les
  repos d'apps (Ghamr/Yoshu/Arbre), pour couvrir les deux écosystèmes
  CI/CD du marché. Ne pas basculer ce repo vers GitHub sans re-décision
  explicite.
  - Choix délibéré face à un self-hébergé sur le homelab lui-même : le
    homelab est le DEV/LAB "tout casser OK", donc la source de vérité Git
    + CI doit rester hors de l'infra qu'elle pilote (même logique que le
    state Terraform sur Oracle/S3 en Phase 3.1, jamais sur le cluster
    homelab). Idée à explorer séparément : héberger une forge (Gitea/GitLab
    CE) comme *application* du homelab plus tard, pas comme source de
    vérité pilotant le homelab.
- Trunk-based (main + branches courtes + MR), pas de Git Flow.
- Tooling piloté depuis le laptop uniquement (agentless), jamais depuis les
  VMs cibles.
- **OpenTofu** (pas Terraform officiel) : greenfield, licence OSI propre,
  skills 100% transférables vers Terraform. En entretien/CV : "Terraform/OpenTofu".
  (Terragrunt : pas encore décidé — à trancher quand le besoin d'orchestrer
  plusieurs environnements/modules sera réel, pas avant.)
- **mise** pour la gestion de versions d'outils (`.mise.toml` versionné).
- Contrainte de conception : tout doit pouvoir se monter et se démonter
  proprement (commission/décommission à la volée), pas seulement se
  déployer une fois.

## Référence

Voir `DevSecOps-IDP-Roadmap-6mois.md` (2ndBrain, `Active projects/IT/ROADMAP JUSTE SUIVRE/`)
pour le plan complet 6 mois (Phases 0-8, stack cible détaillée, défis de
réflexion par phase). Ce repo correspond principalement aux Phases 0, 1.2,
2.1, 3.1 et 6 de cette roadmap.
