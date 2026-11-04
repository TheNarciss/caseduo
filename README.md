# CaseDuo

App iPhone de préparation aux entretiens de conseil, avec des mécaniques de jeu. Chaque jour, elle livre 5 cases, 2 ou 3 brainteasers et une question de fit. Tu réponds à l'écrit ou à l'oral, Claude te note contre une grille, puis te pose une relance comme un vrai interviewer. Ce qui te garde accroché vient de Duolingo : série, freezes, XP, rappel du soir, ligues, widget et haptique.

Construite pour un utilisateur (moi), préparant Wavestone (practice Data & IA), les cabinets IT et transfo, la pré-vente data/IA et, en ligne de mire, QuantumBlack, BCG X et le second cercle stratégie. L'architecture est prête pour plusieurs comptes. Coût : la VM existante et les appels à Claude.

## Ce qu'il y a dedans

**Le contenu, généré chaque nuit** (`prompts/generate.md`)

- 5 cases : market sizing, note de cadrage, business case, diagnostic, et un cran plus difficile. Le jeudi, ce dernier est un tech screen façon QuantumBlack ou BCG X.
- Un case sur cinq en style MBB du mercredi au vendredi : données dès le départ, une question à la fois, synthèse en 30 secondes exigée.
- Brainteasers (logique, estimation, calcul mental), une question de fit par jour, des questions PEI façon McKinsey trois jours par semaine.
- Le vendredi, un cadrage à la maison à rendre en 5 slides-texte avant dimanche soir.
- Secteurs tournants (le mardi, industrie, défense ou aéro), ~30 % des exercices en anglais.
- Difficulté : 2–3 en début de semaine, 4–5 le vendredi, 1–2 le week-end, et plafonnée à 2 la première semaine.
- 3 à 6 vrais chiffres par case, trouvés par recherche web et sourcés ; sinon marqués « hypothèse ».
- Au moins 2 cases par jour mettent sous pression tes 3 critères les plus faibles des 14 derniers jours.

**La notation** (`prompts/grade.md`)

- Chaque critère de la rubric est noté 0, 1 ou 2, avec une citation de ta réponse. Le score est recalculé côté serveur.
- Le feedback a trois sections : ce qui était bien, ce qu'il faut corriger (avec la phrase à dire), la version 30 secondes.
- En streaming : le score s'affiche d'abord, puis le feedback s'écrit au fur et à mesure.
- Une relance qui attaque ton point le plus faible (90 secondes, +5 XP), puis « Refaire en 2 min à l'oral » (+10 XP).
- Pour le fit, le correcteur reçoit ton récit de parcours et tes réponses de fit du mois, et relève les contradictions.

**Les mécaniques**

- Série au fuseau de l'utilisateur. Freezes : 2 au départ, +1 tous les 7 jours, 3 au plus, appliqués automatiquement.
- Objectif journalier de 30, 50 ou 80 XP ; atteignable la première semaine avec 1 case + 1 brainteaser.
- Rappel de série à 20:00 si l'objectif n'est pas atteint, jamais plus d'un push par jour. Silence après 7 jours d'absence.
- Revanches : un exercice raté (< 60) revient à J+3 puis J+10, XP ×1,2.
- Mock entretien le dimanche (30 min, oral, sans retour en arrière, XP ×2) ; un dimanche sur quatre en format MBB. Mock fit de 6 questions un samedi sur deux.
- Ligues bronze → argent → or contre 5 bots (pour l'instant), badges, perfect week.
- Icônes alternatives, widget, badge d'icône.

**Le pilotage**

- `/admin/review/{date}` pour relire les corrigés et leurs sources, et marquer « mauvais » ceux qui sont douteux.
- Coût de chaque génération et de chaque notation, en base.

## Stack

Exactement celle de Tangent pour le backend, celle de SingaSmoke pour l'iPhone (détails : [`docs/CONVENTIONS.md`](docs/CONVENTIONS.md), écarts : [`docs/DEVIATIONS.md`](docs/DEVIATIONS.md)).

- **Backend** : Python 3.12, FastAPI, SQLAlchemy 2.0 async, PostgreSQL 16, Alembic, fastapi-users (cookie JWT), APScheduler dans le process, SDK Anthropic avec Message Batches, cache de prompt et recherche web.
- **iPhone** : SwiftUI, iOS 17, XcodeGen, `@Observable`, package `CaseDuoCore` testé sous Linux, WidgetKit, CoreHaptics, Speech, UserNotifications, Swift Charts.
- **Infra** : Docker Compose, Caddy, Cloudflare Tunnel, VM Oracle ARM (la même que Tangent), GitHub Actions (CI, déploiement par runner auto-hébergé, TestFlight sur Mac GitHub).

## Démarrer en local

Docker, Docker Compose et une clé Anthropic suffisent.

```bash
git clone https://github.com/TheNarciss/caseduo.git
cd caseduo
cp backend/.env.example backend/.env
# Ouvre backend/.env : JWT_SECRET, ANTHROPIC_API_KEY au minimum
docker compose up -d
docker compose exec backend python -m app.cli create-user moi@example.com --admin --name "Clément"
docker compose exec backend python -m app.seed      # aujourd'hui + 2 jours, en synchrone
curl http://localhost:8001/api/health
```

Le backend écoute sur `127.0.0.1:8001` et Postgres sur `127.0.0.1:5433`. Ces ports sont décalés de ceux de Tangent pour que les deux stacks cohabitent. L'app Debug se pointe dessus avec l'argument de lancement `-apiBaseURL http://localhost:8001/api`.

## Les variables d'environnement (`backend/.env`)

| Variable | Rôle |
|---|---|
| `JWT_SECRET` | signe le cookie de session. `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `POSTGRES_PASSWORD` | mot de passe de la base (Compose construit `DATABASE_URL` avec) |
| `ANTHROPIC_API_KEY` | génération et notation. Sans elle, l'app tourne sur le pack d'exercices écrit à la main et la notation répond 503 |
| `GENERATION_PROVIDER` | `claude_code` (défaut conseillé) : les exercices sont écrits chaque nuit par une tâche planifiée Claude Code, sur ton abonnement ([D13](docs/DEVIATIONS.md)) ; `api` : batch Message Batches à 03:00 |
| `GENERATION_IMPORT_TOKEN` | jeton partagé avec cette tâche planifiée (même valeur que `CASEDUO_IMPORT_TOKEN` dans l'environnement cloud) |
| `CASEDUO_MODEL` | `claude-sonnet-4-5` par défaut, comme demandé. **Ce modèle est retiré le 30/11/2026** : voir [DEVIATIONS D1](docs/DEVIATIONS.md) (proposition : `claude-sonnet-5-5`) |
| `LLM_DAILY_CAP_USD` | plafond global par jour, génération et notations confondues (1 $ par défaut) |
| `GENERATION_WEB_SEARCH_MAX_USES` | recherches web par case (3 par défaut, 0 pour les couper) |
| `OWNER_EMAIL` | le compte dont les faiblesses orientent la génération (défaut : le premier admin) |
| `JOBS_TIMEZONE` | fuseau des jobs (`Asia/Singapore`) |
| `APPLE_BUNDLE_ID` | audience vérifiée pour Sign in with Apple (`uk.riskybusinesses.caseduo`) |
| `APNS_TEAM_ID`, `APNS_KEY_ID`, `APNS_PRIVATE_KEY_B64`, `APNS_BUNDLE_ID` | push. Clé `.p8` « Apple Push Notifications service » du compte développeur, en base64 sur une ligne : `base64 -w0 AuthKey_XXXX.p8` |
| `COOKIE_SECURE` | `true` en prod (forcé par `docker-compose.prod.yml`) |

## Déploiement sur la VM (riskybusinesses.uk)

Même schéma que Tangent, à côté de lui : une stack Compose séparée derrière le même tunnel Cloudflare, sur le sous-domaine `caseduo.riskybusinesses.uk` (DEVIATIONS D3).

**Une seule fois**

```bash
# 1. Le code
cd /home/ubuntu && git clone https://github.com/TheNarciss/caseduo.git && cd caseduo
cp backend/.env.example backend/.env && nano backend/.env    # secrets, clé Anthropic, APNs

# 2. La stack (Caddy CaseDuo écoute sur 127.0.0.1:8081, le :80 reste à Tangent)
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# 3. Le tunnel : Cloudflare Zero Trust → Networks → Tunnels → le tunnel de Tangent
#    → Public Hostname → Add : caseduo.riskybusinesses.uk → HTTP → localhost:8081
curl https://caseduo.riskybusinesses.uk/api/health

# 4. Ton compte, puis le contenu des premiers jours
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec backend \
  python -m app.cli create-user moi@example.com --admin --name "Clément"
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec backend python -m app.seed

# 5. La génération de nuit par Claude Code (D13)
#    - dans backend/.env : GENERATION_PROVIDER=claude_code et GENERATION_IMPORT_TOKEN=<un jeton>
#    - dans l'environnement cloud de Claude Code (menu de l'environnement → Edit) :
#      variable CASEDUO_IMPORT_TOKEN = le même jeton
#    - la tâche planifiée « CaseDuo — exercices du lendemain » tourne chaque nuit à 01:32 (Singapour)

# 6. Le déploiement continu : un 2e runner GitHub sur la VM, pour ce dépôt
#    (GitHub → TheNarciss/caseduo → Settings → Actions → Runners → New self-hosted runner,
#    Linux ARM64), installé dans ~/actions-runner-caseduo avec les labels « oracle,prod »,
#    puis ./svc.sh install && ./svc.sh start
```

**Ensuite** : chaque push sur `main` déclenche `.github/workflows/cd.yml`, comme dans Tangent : `git reset --hard origin/main`, `up -d --build`, health check sur l'URL publique, rollback au commit précédent si ça échoue. Les migrations Alembic s'appliquent au démarrage du backend. Les logs se lisent avec `docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f backend`.

## Les jobs planifiés (et comment les lancer à la main)

Ils tournent dans le process du backend (APScheduler, comme Tangent), à l'heure de Singapour :

| Quand | Quoi |
|---|---|
| 01:32 | **tâche planifiée Claude Code** (sur claude.ai, comme le projet Thales) : écrit les exercices du lendemain et les envoie au backend (`GENERATION_PROVIDER=claude_code`) |
| 03:00 | ou, avec `GENERATION_PROVIDER=api` : batch Message Batches (−50 %) des exercices du lendemain |
| toutes les 30 min | lecture des batchs terminés, insertion dès réception, exercices ratés refaits en synchrone |
| 05:30 | secours : ce qui manque au lendemain est généré en synchrone (le batch est annulé) ; aujourd'hui est vérifié aussi |
| au démarrage | rattrapage si un redémarrage nocturne a fait sauter un de ces jobs ; aujourd'hui jamais vide |
| toutes les heures | série : jours ratés réglés, freezes appliqués |
| toutes les 15 min | push : rappel de série à 20:00 locale, désengagement après 7 jours |
| toutes les 30 min | ligues : promotion et relégation après dimanche 23:00 locale |

Tout est idempotent : un exercice déjà là n'est jamais refait (contrainte UNIQUE date + slot). À la main, depuis la VM :

```bash
DC="docker compose -f docker-compose.yml -f docker-compose.prod.yml exec backend"
$DC python -m app.seed --days 0                          # aujourd'hui, en synchrone
$DC python -m app.seed --date 2026-11-07                 # une date précise
$DC python -c "import asyncio; from app.generation import jobs; asyncio.run(jobs.job_submit_batch())"
$DC python -c "import asyncio; from app.generation import jobs; asyncio.run(jobs.job_poll_batches())"
$DC python -c "import asyncio; from app.generation import jobs; asyncio.run(jobs.job_fallback())"
$DC python -m app.seed --starter --days 0                # pack écrit à la main, sans API
```

Chaque génération écrit une ligne dans `cron_runs` : id du batch, statut, tokens in/out, cache, recherches, coût, erreurs. Les notations ont leur coût dans `attempts`. On les lit sur `/admin/review/{date}` ou avec `GET /api/admin/cron-runs`.

## Coûts

Avec la génération par Claude Code (D13), les exercices ne coûtent rien de plus que ton abonnement. En mode `api`, une journée en batch revient à ~0,40 $ avec Sonnet 4.5, ~0,30 $ avec Sonnet 5.5. La recherche web pèse lourd (0,01 $ par recherche, sans remise batch). Une notation coûte ~0,02 à 0,03 $. La cible de 0,10 $ par jour n'est pas tenable avec une recherche web sur chaque case : le détail est dans [DEVIATIONS D2](docs/DEVIATIONS.md). Le plafond journalier coupe tout au-delà de `LLM_DAILY_CAP_USD`.

## L'app iPhone

Tout est dans `ios/` et suit SingaSmoke : `project.yml` (XcodeGen), un Mac de GitHub compile et envoie sur TestFlight. La mise en place, une seule fois, est dans **[docs/ios-testflight.md](docs/ios-testflight.md)** : App IDs, App Group, clé APNs, profils de l'app et du widget, secrets, compte de démo.

```bash
gh workflow run ios.yml -R TheNarciss/caseduo -f testflight=true
gh run watch -R TheNarciss/caseduo
```

### App Review

Tangent s'est fait refuser pour un compte de démo cassé. Ici :

- `python -m app.demo` (avec `DEMO_EMAIL` et `DEMO_PASSWORD`) crée ou rafraîchit `demo@riskybusinesses.uk`. Le compte reçoit une série de 5 jours, des corrections, une revanche due aujourd'hui, un récit de parcours, des badges et une ligue. Il n'est pas administrateur et se relance avant chaque soumission.
- Les exercices du jour existent toujours : génération, secours de 05:30, sinon le pack écrit à la main.
- Aucun login externe à tester. L'e-mail et le mot de passe suffisent, Sign in with Apple est en plus.
- Le texte des notes de revue est dans `ios/fastlane/metadata/review_information/notes.txt`. Les pages légales sont `https://caseduo.riskybusinesses.uk/legal/privacy.html` et `/legal/about.html`. La suppression du compte est dans Profil.

## Faire évoluer les prompts

C'est ce qui bouge le plus : [**docs/PROMPT_TUNING.md**](docs/PROMPT_TUNING.md).

## Le code

```
backend/
  app/
    routers/        HTTP (/api/*), une route par écran (today, exercises, grade, history, league…)
    generation/     planning du jour, requêtes, validation, synchrone, batch, jobs
    grading/        prompt du correcteur, lecture du flux, score, hooks (revanches, fit, badges)
    game/           règles pures : XP, série, faiblesses, revanches, ligues, badges
    services/       cas d'usage partagés : cartes du jour, progression, série, mocks, ligues
    llm/            client Anthropic, coûts et plafond, prompts, retries
    push/           APNs et règles d'envoi
    auth/           fastapi-users, Sign in with Apple natif
    content/        pack d'exercices écrit à la main, pages légales
    seed.py demo.py prompt_lab.py cli.py
  alembic/          migrations écrites à la main
  tests/            unit (pur) + integration (vrai Postgres, Claude simulé)
prompts/            generate.md, grade.md (montés en lecture seule dans le conteneur)
ios/                l'app SwiftUI, le widget, CaseDuoCore, fastlane
docs/               conventions, écarts, contrat d'API, TestFlight, prompts
```

Tests : `cd backend && pip install -e ".[dev]" && pytest`. Il faut un Postgres sur `localhost:5433` avec une base `caseduo_test` : `docker compose up -d postgres && docker compose exec postgres createdb -U caseduo caseduo_test`. Côté iPhone : `cd ios/Packages/CaseDuoCore && swift test`. Les vraies réponses du backend, une par écran, sont décodées avec les types de l'app (`BackendContractTests`) ; après un changement d'API, régénère-les avec `UPDATE_CONTRACT_FIXTURES=1 pytest tests/integration/test_contract.py`.

## Licence

MIT.
