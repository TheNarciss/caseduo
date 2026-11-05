# Conventions reprises de Tangent et SingaSmoke

Ce document dit d'où vient chaque choix de CaseDuo. Règle : **on refait comme dans les deux apps existantes**. Ce qui s'en écarte est dans [`DEVIATIONS.md`](DEVIATIONS.md), avec la raison.

Sources lues le 2026-11-04 :

- `TheNarciss/tangent` : backend FastAPI, front React dans une coque iOS Capacitor, en prod sur `riskybusinesses.uk`.
- `TheNarciss/SingaSmoke` : app iPhone SwiftUI native, sans backend, distribuée par TestFlight.
- `TheNarciss/thales-assessment-ios` : démo crypto SwiftUI sans réseau ; elle confirme XcodeGen + iOS 17, rien de plus.
- L'app de comparaison d'empreintes n'est pas sur GitHub : rien à en reprendre.

## 1. Backend (modèle : Tangent)

| Sujet | Tangent | CaseDuo |
|---|---|---|
| Langage, framework | Python 3.12, FastAPI, uvicorn, Pydantic v2 | idem |
| ORM, base | SQLAlchemy 2.0 async + asyncpg, PostgreSQL 16, JSONB pour le semi-structuré | idem (rubrics, context_data, rubric_scores en JSONB) |
| Migrations | Alembic, fichiers **écrits à la main** (`alembic/versions/<rev>_<slug>.py`), appliquées au démarrage par `init_db()` qui lance `alembic upgrade head` dans un sous-processus | idem, même `init_db.py` |
| Auth | fastapi-users : cookie HTTP-only `<app>_auth`, JWT HS256 7 jours, renouvelé sur `GET /api/users/me` (ADR-035), mots de passe argon2id, Sign in with Apple natif (`POST /api/auth/apple/native` avec l'`id_token`), admin = `is_superuser` | idem, cookie `caseduo_auth`. Pas de Google (pas de flux navigateur à gérer dans une app native). |
| Préfixe des routes | tout sous `/api/*` (ADR-020), `/api/health` pour Docker et la CD | idem ; une seule exception : la page HTML `/admin/review/{date}` |
| Secrets, config | `backend/.env` (gitignoré) + `backend/.env.example` commité ; lus par `os.getenv` dans le module qui en a besoin ; les secrets de CI dans GitHub Secrets | idem |
| Couches | `routers/` (HTTP), `repositories/` (accès DB filtré par `user_id`), `finance/` (calcul pur, sans I/O), `llm/` (pipeline Anthropic), `auth/` | `routers/`, `repositories/`, `game/` (XP, streak, ligues : pur, sans I/O), `llm/`, `push/`, `auth/` |
| LLM | `llm/anthropic_client.py` : singleton `AsyncAnthropic` paresseux, **une constante par modèle**, helper `web_search_tool()` ; `cost_tracker.py` : prix par modèle, coût par appel, **plafond journalier global** (table `llm_daily_cost`, UPSERT atomique) ; `_retry.py` : tenacity sur 529/503 pour `batches.create` | idem, plus le cache de prompt et le suivi par appel dans `cron_runs` / `attempts` |
| Batch | Message Batches : `batch_submitter.py` (03:00) + `batch_poller.py` (toutes les 15 min), `custom_id` routé par préfixe, idempotence par contrainte UNIQUE, résultats lus par `custom_id` | idem (soumission 03:00 SGT, polling 30 min, contrainte UNIQUE `(date, slot)`) |
| Streaming | SSE (`text/event-stream`, `event: error`, `event: done`), en-tête `X-Accel-Buffering: no`, vérifications (budget, doublon) **avant** d'ouvrir le flux | idem pour la notation |
| Jobs planifiés | APScheduler `AsyncIOScheduler` **dans le process FastAPI** (lifespan), `CronTrigger` avec fuseau, `max_instances=1, coalesce=True`, **rattrapage au démarrage** si un redémarrage a fait sauter le cron | idem, fuseau `Asia/Singapore` |
| Logs | `logging` standard, format `%(asctime)s [%(levelname)-7s] %(name)s — %(message)s` sur stdout, lus par `docker compose logs -f backend` ; pas d'e-mail ni de secret dans les logs | idem |
| Compte de démo | `python -m app.demo` avec `DEMO_EMAIL` / `DEMO_PASSWORD`, rejouable, données crédibles, non administrateur | idem |
| Tests | pytest + pytest-asyncio, `tests/unit` (pur) et `tests/integration` (vrai Postgres, migrations Alembic appliquées par la fixture), réseau externe coupé par une fixture autouse | idem |
| Qualité | ruff (lint + format, ligne 100), mypy non strict, couverture minimale en CI | idem |
| Docs | ADR en français dans `docs/adr/` (gabarit `TEMPLATE.md`), docs opératoires en français | docs en français dans `docs/` |

## 2. Infra et déploiement (modèle : Tangent)

- **Machine** : VM Oracle Cloud ARM64 (runner GitHub labellisé `self-hosted, Linux, oracle, prod`), projet Tangent cloné dans `/home/ubuntu/projet_finance`.
- **Exposition** : Cloudflare Tunnel (`cloudflared`) → `http://localhost:80` → conteneur **Caddy** → `backend:8000`. Aucun port entrant ouvert. Caddy force `X-Forwarded-Proto: https` (Cloudflare termine le TLS).
- **Conteneurs** : `docker-compose.yml` (dev : postgres + backend avec `--reload`, ports liés à `127.0.0.1`) et `docker-compose.prod.yml` (surcharge : `ENV=prod`, `COOKIE_SECURE=true`, plus de port public pour le backend et Postgres, Caddy ajouté). Image backend `python:3.12-slim`, utilisateur `app` (uid 1000), `HEALTHCHECK` sur `/api/health`.
- **Domaine** : `riskybusinesses.uk` (Cloudflare Registrar + DNS). Bundle IDs en `uk.riskybusinesses.<app>`.
- **CD** : `.github/workflows/cd.yml` sur push `main` : nettoyage Docker, `git fetch` avec le `GITHUB_TOKEN`, `git reset --hard origin/main`, `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build`, health check 60 s sur l'URL publique, **rollback** au commit précédent si échec.
- **CI** : `.github/workflows/ci.yml` : ruff, ruff format --check, mypy, pytest avec un service Postgres 16 ; actions épinglées par SHA.
- **Sauvegarde** : rien d'automatisé dans le repo Tangent (plan B mentionné dans l'ADR-005). CaseDuo ne fait pas mieux pour l'instant.
- **CI éventuelle** : release-please, semgrep, dependabot existent dans Tangent ; non repris au départ (un seul utilisateur, peu de dépendances).

## 3. App iPhone (modèle : SingaSmoke, natif)

| Sujet | SingaSmoke | CaseDuo |
|---|---|---|
| Projet Xcode | **XcodeGen** : `project.yml` commité, `.xcodeproj` et `Info.plist` générés (gitignorés), personne n'a besoin d'ouvrir Xcode | idem, dans `ios/` |
| Cible | iOS 17, iPhone seul, portrait, `SWIFT_VERSION 5.0` | idem |
| Architecture | SwiftUI + `@MainActor @Observable final class AppModel` injecté par `.environment(model)`, une `RootView` qui aiguille selon une `phase` ; pas de MVVM par écran | idem |
| Dossiers | `App/`, `Model/`, `Features/<Écran>/`, `Shared/Theme.swift` (enum `Brand` : couleurs, `PillButtonStyle`, cartes), `Shared/Components.swift`, `Resources/` | idem, plus `Network/` et `Services/` (haptique, sons, dictée, notifications) |
| Logique testable | package Swift local `Packages/<App>Core` (Foundation seulement), testé par `swift test` sur macOS **et Linux** avant la compilation de l'app | `Packages/CaseDuoCore` : modèles d'API `Codable`, lecteur SSE, motifs haptiques, ordre des cartes, formats |
| Réseau | SingaSmoke n'en a pas ; Tangent passe par la pile HTTP native qui garde le cookie | `URLSession` + stockage de cookies : le cookie de session de fastapi-users suffit, exactement comme Tangent |
| Persistance locale | `@AppStorage` pour les préférences | idem (sons, dernier état connu) ; App Group partagé avec le widget |
| Signature | `Config/Signing.xcconfig` (`CODE_SIGN_STYLE = Automatic`), réécrit par la CI avec le certificat de distribution, la Team et l'UUID du profil | idem, un xcconfig par cible (app + widget) |
| Distribution | `.github/workflows/ios.yml` : runner `macos-15`, Xcode 26, `swift test`, `xcodegen generate`, build simulateur, captures d'écran sur PR ; push `main` → archive, export, `altool` vers TestFlight ; numéro de build = `github.run_number` ; secrets `IOS_CERTIFICATE_P12_B64`, `IOS_CERTIFICATE_PASSWORD`, `IOS_PROVISIONING_PROFILE_B64`, `APPLE_TEAM_ID`, `APPSTORE_API_KEY_ID`, `APPSTORE_API_ISSUER_ID`, `APPSTORE_API_KEY_P8_B64` (communs à toutes les apps du compte, sauf le profil) | idem, plus le profil du widget |
| App Store | `fastlane/metadata/…` (texte de la fiche, `review_information/notes.txt`), `PrivacyInfo.xcprivacy`, `ITSAppUsesNonExemptEncryption = NO`, doc pas à pas `docs/testflight.md` / `docs/ios-app-store.md` | idem |
| Push APNs | absent des deux apps | ajouté dans le style de l'existant (voir DEVIATIONS) |
| Debug / CI | arguments de lancement lus en `#if DEBUG` (`-uiAppearance dark`, `-uiSkipDisclaimer YES`) pour les captures | idem (`-uiDemo YES` pour des captures sans réseau) |

## 4. Ce que CaseDuo en tire concrètement

- `backend/` est un clone structurel de `tangent/backend/` réduit à ce dont CaseDuo a besoin.
- `ios/` est un clone structurel de `SingaSmoke/` (+ widget).
- Les noms : app `CaseDuo`, bundle `uk.riskybusinesses.caseduo`, widget `uk.riskybusinesses.caseduo.widget`, App Group `group.uk.riskybusinesses.caseduo`, cookie `caseduo_auth`, conteneurs `caseduo-*`, base `caseduo`.
- Le fuseau des jobs est `Asia/Singapore` (Tangent : `Europe/Paris`), puisque l'utilisateur vit à Singapour.
