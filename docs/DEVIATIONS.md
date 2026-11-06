# Écarts par rapport à la méthode Tangent / SingaSmoke

Chaque écart dit pourquoi, ce qui est fait en attendant, et comment revenir en arrière. Statuts :

- **À valider** : il faut ton accord. Le code suit ta demande ou la solution la plus proche de l'existant, et le changement tient en une ligne.
- **Appliqué** : nécessaire ou sans alternative dans l'existant (une brique qui n'existait pas, ajoutée dans le même style).

---

## D1 — Modèle Claude : `claude-sonnet-4-5` est retiré le 30 novembre 2026 · **À valider**

Le prompt demande `claude-sonnet-4-5` pour la génération et la notation. D'après la liste des modèles d'Anthropic, ce modèle est **déprécié et retiré le 2026-11-30**, soit 26 jours après l'écriture de ce code. Le 1er décembre, chaque génération et chaque notation échoueraient.

- **En attendant** : le code utilise `claude-sonnet-4-5`, comme demandé. Le modèle est une constante unique dans `backend/app/llm/anthropic_client.py`, surchargée par `CASEDUO_MODEL` dans `backend/.env`. C'est la même méthode que Tangent : une constante par usage.
- **Proposition** : `CASEDUO_MODEL=claude-sonnet-5-5`, le Sonnet actuel. Il coûte **2 $ / 10 $** par million de tokens au lieu de 3 $ / 15 $, soit un tiers de moins, et c'est la génération suivante. Tangent tourne déjà sur `claude-sonnet-5` et `claude-opus-5`.
- **Ce que le code gère déjà** : la variante de recherche web (`web_search_20250305` pour Sonnet 4.5, `web_search_20260209` pour Sonnet 4.6 et plus), la réflexion adaptative et l'effort (refusés par Sonnet 4.5, utilisés par Sonnet 5.x), et les prix. Changer la variable suffit.

## D2 — Cible de coût de génération · **Résolu par D13** (génération sur l'abonnement)

Le prompt fixe moins de 0,10 $ par jour pour la génération en batch. Avec la recherche web sur chaque case, ce n'est pas atteignable :

| Poste (une journée, ~10 exercices) | Sonnet 4.5 batch | Sonnet 5.5 batch |
|---|---|---|
| Sortie (~25 k tokens : corrigés, rubrics, données) | 0,19 $ | 0,13 $ |
| Entrée (prompt système en cache + résultats de recherche réinjectés, ~80 k tokens) | 0,12 $ | 0,08 $ |
| Recherches web (0,01 $ l'une, **sans remise batch**, ~12 par jour) | 0,12 $ | 0,12 $ |
| **Total estimé** | **~0,40 $** | **~0,30 $** |

- **Fait** : au plus 3 recherches par case, aucune pour les brainteasers et le fit (rien à sourcer), prompt système mis en cache, et le même **plafond global journalier** que Tangent (`LLM_DAILY_CAP_USD`, 1 $ par défaut, notations comprises). Le coût réel de chaque appel est écrit dans `cron_runs` et `attempts` : on saura vite si l'estimation tient.
- **Pour descendre vers 0,10 $** : passer `GENERATION_WEB_SEARCH_MAX_USES` à 1. C'est un réglage, pas un changement de code.
- **Notation** : moins de 0,03 $ par note est tenable avec Sonnet 5.5 (~5 k tokens en entrée dont la moitié en cache, ~1,2 k en sortie ≈ 0,02 $). Avec Sonnet 4.5, c'est juste (~0,03 $).

## D3 — Hébergement : sous-domaine et stack Compose séparée · **À valider**

Sur la VM, le Caddy de Tangent occupe déjà `127.0.0.1:80`, l'unique cible du tunnel Cloudflare. Ses routes servent le site de Tangent.

- **Choix** : CaseDuo a sa propre stack Compose (`caseduo-postgres`, `caseduo-backend`, `caseduo-caddy`) avec le même Caddyfile, mais son Caddy écoute sur `127.0.0.1:8081`. Le tunnel reçoit un nom d'hôte public de plus, `caseduo.riskybusinesses.uk`, vers `http://localhost:8081`. Les deux apps restent indépendantes : déploiement, rollback et base séparés, comme deux projets Tangent.
- **Écarté** : passer par le Caddy de Tangent (`/caseduo/*`) lierait deux dépôts, deux déploiements et deux rollbacks.
- **Étapes manuelles** (README, section Déploiement) : ajouter le nom d'hôte dans Cloudflare Zero Trust → Tunnels, enregistrer un **deuxième runner** GitHub sur la VM pour ce dépôt (un runner personnel est lié à un dépôt), cloner dans `/home/ubuntu/caseduo`.

## D4 — Prompts hors de l'image Docker · **Appliqué**

Tu demandes `/prompts/generate.*` et `/prompts/grade.*` à la racine du dépôt. Le contexte de build Docker est `backend/`, comme dans Tangent : `prompts/` est donc monté en lecture seule dans le conteneur (`./prompts:/app/prompts:ro`), comme Tangent monte `config/` en dev. Conséquence : modifier un prompt sur la VM ne demande qu'un `docker compose restart backend`, sans rebuild (voir `PROMPT_TUNING.md`).

## D5 — Push APNs : nouvelle brique · **Appliqué**

Aucune des deux apps n'envoie de notifications push. Elle est ajoutée sans nouvelle pile :

- Côté serveur : `httpx` (déjà présent dans Tangent), avec HTTP/2 (`httpx[http2]`), et un JWT ES256 signé par `pyjwt` avec la clé `.p8`. C'est exactement ce que fait `tangent/backend/app/auth/apple.py` pour Sign in with Apple. Variables `APNS_*` dans `.env`, au même format base64 que `APPLE_PRIVATE_KEY_B64`.
- Les jobs (rappel de série à 20:00 locale, désengagement après 7 jours) sont des jobs APScheduler, comme ceux de Tangent.
- Côté app : `UNUserNotificationCenter` et l'entitlement `aps-environment`. La clé APNs se crée une fois dans le compte Apple Developer et vaut pour toutes les apps.

## D6 — Widget : App Group et deuxième profil de provisionnement · **Appliqué**

SingaSmoke n'a qu'une cible, donc un seul profil. Le widget (WidgetKit) est une extension : il lui faut son App ID (`uk.riskybusinesses.caseduo.widget`), son profil App Store et un **App Group** (`group.uk.riskybusinesses.caseduo`) partagé avec l'app. Le workflow iOS installe donc deux profils, avec un secret de plus : `IOS_WIDGET_PROVISIONING_PROFILE_B64`. Tout le reste reprend le workflow de SingaSmoke à l'identique.

## D7 — L'app iOS vit dans `ios/` · **Appliqué**

SingaSmoke a `project.yml` à la racine parce qu'il n'y a rien d'autre dans son dépôt. Ici, le dépôt contient aussi le backend, donc le projet est rangé dans `ios/`, comme Tangent range le sien dans `frontend/ios` et Thales dans `app/`.

## D8 — Connexion : e-mail + mot de passe et Apple, sans Google ni inscription dans l'app · **Appliqué**

On garde la même pile que Tangent : fastapi-users, cookie et Sign in with Apple natif. Google est retiré : dans Tangent, il demande un aller-retour par le navigateur système avec un code d'échange PKCE, du code qui ne servirait pas pour un seul utilisateur. Sans Google, Apple n'impose pas Sign in with Apple (règle 4.8), mais il est gardé pour se connecter en un geste.

Il n'y a pas de formulaire d'inscription dans l'app : ton compte se crée avec `python -m app.cli create-user` ou par Apple. La suppression du compte est dans Profil, comme le demande la règle 5.1.1.

## D9 — Les exercices du jour sont communs à tous les comptes · **Appliqué**

La table `exercises` n'a pas de `user_id` (le schéma demandé n'en a pas) : une seule génération par jour, servie à tous. L'adaptation aux faiblesses et le plafond de difficulté de la première semaine sont calculés sur le **compte propriétaire** : le premier superuser, ou `OWNER_EMAIL` dans `.env`. Les revanches, elles, sont par utilisateur. Le passage à plusieurs comptes demandera une génération par utilisateur, ou des « emplacements » personnels en plus du tronc commun.

## D10 — Une requête par exercice, pas une par jour · **Appliqué**

Le batch envoie une requête par exercice (`custom_id = gen:<date>:<slot>`). Une sortie plus courte se valide et se relance seule : un exercice raté ne fait pas jeter la journée. Le prompt système reste celui que tu as écrit (« Tu reçois… la liste des types à produire ») ; chaque requête en reçoit une liste d'un seul, plus le contexte de la journée. Le prompt système étant identique d'une requête à l'autre, le cache de prompt joue pleinement.

## D11 — Pack de démarrage écrit à la main · **Appliqué**

`backend/app/content/starter_pack.py` contient une journée d'exercices rédigés à la main. Ils ne servent que si une date n'a rien et que la génération est impossible (pas de clé API, plafond atteint, panne Anthropic), et pour le compte de démo. C'est le filet de sécurité contre un refus d'App Review dû à un écran vide.

## D12 — Format de sortie de la notation · **Appliqué**

Tu demandes une réponse en streaming. Un JSON qui arrive token par token n'est pas affichable. Le correcteur écrit donc trois sections balisées dans l'ordre : `<scores>{…json…}</scores>`, puis `<feedback>…markdown…</feedback>`, puis `<follow_up>…</follow_up>`. Le serveur les découpe à la volée : l'app reçoit les notes en premier (animation du score et haptique tout de suite), puis le feedback qui s'écrit, puis la relance. Le score final est **recalculé par le serveur** à partir des notes 0/1/2 et des poids, sans se fier à l'arithmétique du modèle. `POST /api/grade` (sans streaming) renvoie la même chose en un seul JSON.

## D13 — Les exercices sont écrits par une tâche planifiée Claude Code, livrés par GitHub Actions · **Remplacé par D15**

> La tâche planifiée n'avait pas le droit d'écrire dans le dépôt (une tâche planifiée créée ainsi n'a aucun dépôt attaché) : la nuit du 5 au 6 novembre, elle s'est arrêtée sans rien produire. Elle est désactivée et les deux workflows sont en sommeil (lançables à la main). Ce qui suit décrit l'ancien circuit.

Deux méthodes que tu utilises déjà, mises bout à bout : la tâche planifiée Claude Code de ton projet Thales, et le circuit de Tangent et SingaSmoke, où **seul GitHub Actions touche la VM** par le runner installé dessus. Il n'y a ni port ni route d'import à ouvrir sur la VM, et aucun secret de la VM dans l'environnement cloud. La branche `nightly` du dépôt sert de boîte aux lettres : elle ne contient que des données, aucun code.

| Heure (Singapour) | Où | Quoi |
|---|---|---|
| 00:40 | VM, `nightly-plan.yml` | `python -m app.nightly plan` lit la base et pousse `plans/<demain>.json` sur `nightly` : le system prompt `prompts/generate.md` et, pour chaque exercice manquant, la consigne exacte qu'une génération API enverrait (faiblesses, titres déjà vus, style, langue) |
| 01:32 | claude.ai, tâche planifiée « CaseDuo — exercices du lendemain » | une session neuve lit ce plan, écrit chaque exercice (recherche web comprise) et les vérifie avec `python -m app.nightly check`, la même validation que l'import, sans base. Elle pousse ensuite `generated/<demain>/<slot>.json` sur `nightly` |
| 01:00 → 05:50, toutes les 10 min | VM, `nightly-import.yml` | `ops/nightly_import.py` → `python -m app.nightly import` : validé à nouveau, inséré (UNIQUE date + slot, idempotent), réponse dans `results/<demain>.json`, ligne `cron_runs` (job `claude_code`) |
| 05:30 | VM, backend | le secours habituel complète ce qui manque (API si une clé est configurée, sinon le pack écrit à la main) |

- **Coût** : la génération passe sur ton abonnement, sans facture API. Seule la notation reste payante (~0,02 $ par réponse).
- **Prompt de la tâche** : versionné dans `ops/nightly-generation-prompt.md`. Le modifier là, puis mettre à jour la tâche planifiée avec le même texte.
- **Visibilité** : le dépôt est public. Les plans (avec tes 3 critères les plus faibles) et les exercices générés y sont donc lisibles. Pour les cacher, passe le dépôt en privé : rien d'autre ne change.
- **Retour au batch API** : `GENERATION_PROVIDER=api` dans `backend/.env`, puis désactiver la tâche planifiée.

## D14 — La notation passe par Claude Code sur ton abonnement · **Appliqué (à ta demande)**

Tu veux une note immédiate sans payer l'API. Le backend lance donc la ligne de commande Claude Code (`claude -p`) dans son conteneur, avec le jeton longue durée de ton abonnement (`claude setup-token`). Chaque réponse est un appel isolé : sans outils, sans MCP, sans réglages ni session gardée, avec `prompts/grade.md` pour prompt système et la même consigne que par l'API (exercice, corrigé, rubric, réponse).

- **Rien ne change pour l'app** : la sortie est le même texte balisé (D12), découpé à la volée. Les notes arrivent toujours en premier, puis le feedback, puis la relance, et le serveur recalcule toujours le score. Mesuré avec Sonnet 5.5 en effort `low` : notes à ~5 s, correction complète à ~15 s.
- **Plusieurs réponses à la fois** : chacune a son processus, au plus `CLAUDE_CODE_MAX_PARALLEL` (3) en même temps, les suivantes attendent leur tour.
- **Coût** : 0 $ côté API. La notation compte dans l'usage de ton abonnement (fenêtres de 5 heures). Les tokens sont enregistrés dans `attempts` comme avant, avec `cost_usd = 0`. Le plafond `LLM_DAILY_CAP_USD` ne s'applique plus qu'à l'API.
- **Limite atteinte ou jeton refusé** : l'app affiche « La limite d'usage de l'abonnement Claude est atteinte… » ou « Le jeton Claude Code du serveur est refusé… ». Rien n'est enregistré, et la réponse peut être renvoyée.
- **Modèle** : `CLAUDE_CODE_MODEL=sonnet`, un alias qui suit le Sonnet courant, sans date de retrait à surveiller (D1 ne concerne plus que l'API).
- **Image Docker** : le binaire officiel du canal stable (~290 Mo), vérifié par sa somme SHA-256, sans mise à jour automatique. Un rebuild prend la version stable du moment.
- **Jeton** : secret GitHub `CLAUDE_CODE_OAUTH_TOKEN`, écrit dans `backend/.env` par la CD comme les autres. Il se crée avec `claude setup-token`, sur un ordinateur où Claude Code est connecté à ton compte, et dure un an.
- **Écarté : une tâche planifiée déclenchée à chaque réponse.** Une session dans le cloud met 1 à 3 minutes à démarrer et à renvoyer le résultat par GitHub Actions. C'est trop lent pour une note qu'on attend devant l'écran.
- **Retour à l'API** : `GRADING_PROVIDER=api` dans `backend/.env` (avec `ANTHROPIC_API_KEY`). En mode `auto`, l'API ne sert que si le jeton Claude Code est vide.

## D15 — Le serveur écrit lui-même les exercices avec Claude Code · **Appliqué (à ta demande)**

D13 dépendait d'une tâche planifiée dans le cloud qui n'a pas pu pousser dans le dépôt. Depuis D14, Claude Code tourne déjà dans le conteneur du backend avec le jeton de ton abonnement : la génération y passe aussi. Il n'y a plus ni tâche planifiée, ni branche `nightly`, ni import.

- **Quand** : à 03:00 (heure de Singapour) pour le lendemain. Au démarrage du serveur, s'il manque des exercices aujourd'hui, ils sont écrits tout de suite. Le secours de 05:30 complète ce qui manque encore.
- **Comment** : chaque exercice est un appel `claude -p` isolé, avec `prompts/generate.md` et la même consigne que par l'API (faiblesses, titres déjà vus, style, langue). Les cases ont l'outil WebSearch, au plus 3 recherches comme avant. Les URL renvoyées par la recherche servent à vérifier les sources, et un exercice passe par le même validateur et les mêmes deux relances qu'avec l'API. Effort `high` (personne n'attend la nuit), au plus 2 exercices écrits en même temps. La notation garde ses propres places, pour qu'elle reste immédiate.
- **Le pack écrit à la main** : quand de vrais exercices arrivent pour un jour qui n'avait que lui, ses exercices non entamés sont retirés. Ceux auxquels tu as répondu ou dont tu as vu les données restent.
- **Pack bonus** : `backend/app/content/packs/*.json` contient des exercices écrits à l'avance (le premier : 15 brainteasers et 15 cases, difficultés 1 à 5, cases sourcés par recherche web). Ils passent par le même validateur au démarrage, sont importés une seule fois et ne dépendent d'aucun jour : l'écran du jour les montre après les cartes du jour, marqués « Bonus · quand tu veux », tant que tu ne les as pas faits. Ils ne comptent ni pour « journée complète » ni pour le badge des exercices restants, mais rapportent des XP comme les autres.
- **Coût** : 0 $ côté API. La génération compte dans l'usage de ton abonnement, la nuit.
- **Sans jeton** : `GENERATION_PROVIDER=auto` passe à l'API si `ANTHROPIC_API_KEY` est rempli, sinon le pack écrit à la main garde chaque jour non vide.

## D16 — Cinq onglets, familles colorées, engagement verrouillé, mascotte · **Appliqué (à ta demande)**

Tes retours sur l'app : accueil pas assez clair, pas de couleur par type, rien ne se passe quand on finit un exercice, l'objectif « engage » sans engager, pas d'identité visuelle, plus de retour haptique.

- **Navigation** : un cinquième onglet, **Entraîner**, prend le pack bonus et les exercices des jours passés restés sans réponse, filtrés par famille (`GET /training`). L'accueil ne garde que le plan du jour, découpé en sections avec compteur (Brainteasers, Fit, Cases, Revanches, À rendre). Les deux onglets partagent les mêmes écrans d'exercice et de correction, chacun avec sa pile de navigation.
- **Couleur par famille** : rose brainteaser, indigo fit, cyan market sizing, violet cadrage, turquoise business case, citron diagnostic (`Brand.color(for:)`). Sur l'icône et la bande gauche de chaque carte, les titres de section, les filtres d'Entraîner et les courbes de l'historique. Le vert reste le succès, l'orange le danger, la flamme l'accent.
- **Fin d'exercice** : quand les notes arrivent, l'anneau de score rebondit dans une gerbe de particules de la couleur du type, un verdict surgit (« Excellent ! », « Bien joué », « On s'accroche »), les XP montent. Quand le plan du jour est fini, un écran plein « Journée complète ! » avec la mascotte et des confettis. La règle « confettis trois fois seulement » du cahier des charges s'élargit donc à la journée complète ; les scores n'en ont pas, seulement la gerbe.
- **Engagement** (le changement de règle) : le cahier des charges disait « choisir 30/50/80 XP, bouton Je m'engage ». Tu as constaté qu'un objectif modifiable à tout moment n'engage à rien. Désormais `POST /me/commitment` fixe l'objectif **et une durée** (7, 14 ou 30 jours) ; `PATCH /me daily_goal_xp` répond 409 tant que l'engagement court. La carte de l'accueil devient le suivi de la promesse (un point par jour : tenu, freeze, manqué, aujourd'hui), avec la barre d'XP du jour à l'intérieur. À la fin : bilan, et le badge « Parole tenue » si aucun jour n'a été manqué (un freeze compte comme tenu, comme pour la série). Table `goal_commitments`, migration 0002. Le plafond de la première semaine (30 XP) s'applique toujours à l'objectif effectif.
- **Mascotte** : pas d'outil pour générer des images ici, donc une flamme-personnage **dessinée en vectoriel SwiftUI** (`Shared/Mascot.swift`), prototypée en SVG et vérifiée à l'œil en PNG avant d'être portée. Six humeurs : idle, contente (objectif tenu), fière (journée complète, semaine parfaite), endormie (série en danger), pensive (exercices en route), triste (score < 50). Elle respire, cligne des yeux, rebondit quand elle est contente, et reste immobile si « Réduire les animations » est activé. Elle remplace le symbole flamme sur l'accueil, le bilan du jour et l'écran de fin de journée.
- **Haptique** : quatre motifs de plus dans `CaseDuoCore` (`tap`, `goalMet`, `dayComplete`, `commit`), joués à la pression d'une carte, d'un filtre ou d'un onglet, à l'objectif atteint, à la journée complète et au moment de s'engager. Le motif de la semaine parfaite reste le plus long.

## D17 — Aujourd'hui devient un Parcours, un cours d'entretiens en chemin · **Appliqué (à ta demande)**

Le cahier des charges faisait de l'accueil un plan du jour : des exercices complets notés par Claude. Tu as demandé un vrai cours, gradué, qui enseigne toutes les méthodes par des exercices courts à la Duolingo, pour un public large (écoles d'ingénieurs et de commerce, tous niveaux, conseil IT et transformation vers la stratégie et la finance), sans se limiter à un cabinet. Le plan complet est dans [PARCOURS.md](PARCOURS.md).

- **Ce qui change** : l'onglet Aujourd'hui montre d'abord le Parcours (unités, étapes sur un chemin serpentin, étape active qui pulse), puis le plan du jour, conservé tel quel. Les exercices complets restent le cœur de l'entraînement, le Parcours apprend les méthodes qu'ils demandent.
- **Le contenu vit dans le dépôt**, pas dans un prompt : `content/path/units/*.json` (les unités et leurs étapes) et `content/path/items/*.json` (les items), relus et validés par `python -m app.path check`. Le serveur les charge au démarrage (`CONTENT_DIR`, monté en lecture seule) et les met à jour par empreinte ; un item inconnu du dossier n'est pas supprimé, il n'est plus servi. La règle d'écriture est dans `content/path/GUIDE.md` : une seule bonne réponse, un `why_wrong` par distracteur, une explication qui énonce la règle, aucun calcul recopié sans être recalculé, aucun cabinet dans les mauvaises réponses.
- **La correction se fait sur le téléphone** : les items partent avec leur clé, `PathGrader` (CaseDuoCore, testé) corrige les 16 formats fermés, `LessonSession` repose les erreurs en fin de leçon et ne compte que le premier essai. Le serveur reçoit les résultats, calcule le score, les XP, et note le seul item ouvert, l'oral, avec Claude Code (D14). Tricher est possible et sans intérêt : il n'y a ni ligue ni classement sur le Parcours.
- **Les règles de jeu** : déblocage linéaire, étapes « en situation » et « légendaire » facultatives, 30 % de révision dans chaque leçon, +5 XP sans faute, 5 XP pour refaire, bilan d'unité à 60 %, légendaire à 75 %. Les XP comptent pour l'objectif, l'engagement et la série comme ceux d'un exercice. Un item signalé trois fois (« Signaler cet exercice » dans le menu de la leçon) sort du Parcours.
- **Phase 1 livrée** : le moteur, les unités 0 à 3 (anatomie de l'entretien, ouvrir un case, le calcul en entretien, structurer), le chemin et le lecteur de leçon. **Phase 2** (PARCOURS.md § 7) : test de placement, génération nocturne d'items par Claude Code dans le style des banques existantes, révision espacée, spécialisations transfo / strat / finance, mock hebdomadaire, niveaux de compétence, quêtes.
- **Écarté : des images ou des vidéos dans les leçons.** Les graphiques des items sont des données (`media` : barres, courbe, tableau, arbre) dessinées par l'app ; rien à télécharger, rien à héberger.

## D18 — Motion design, sons et haptique dans les leçons · **Appliqué (à ta demande)**

Ton retour sur le build 26 : « pas assez hype », les cartes à glisser trop petites, les blocs gris datés, les libellés du chemin qui se chevauchent.

- **Un vocabulaire de mouvement** (`Motion` dans `Shared/Theme.swift`) : trois ressorts nommés, `snappy` (une pression reconnue, moins de 150 ms pour démarrer), `bouncy` (une récompense qui rebondit), `settle` (un panneau qui se pose, sans rebond), et `fling` pour une carte qui part. Trois modificateurs : `popIn` (apparaît en rebondissant), `bounce(trigger:)` (sursaute à chaque changement), `shake(trigger:)` (secoue, pour une erreur). Tout respecte « Réduire les animations ».
- **Dans la leçon** : l'option choisie se colore en vert avec une coche qui surgit dans une gerbe, ou en orange avec une croix et une secousse, pendant que la bonne réponse se révèle en vert ; même langage pour les trous, le tri, les paires, les tuiles. La barre de progression a un reflet et se pose en ressort. Le compteur de bonnes réponses sursaute, et à 3, 5, 10 d'affilée un « Combo ×N » surgit avec une gerbe, un motif haptique et un arpège. Les cartes « valide ou pas » occupent l'écran, se glissent avec un tampon VALIDE / PAS VALIDE, s'envolent du côté choisi, et les deux boutons font toute la largeur.
- **Sons** : cinq de plus, synthétisés par `ios/scripts/make-sounds.py` (aucune licence à suivre, régénérables) : juste, faux, pop (une tuile ou une carte qui se pose), combo, leçon terminée. Les anciens sont régénérés dans la même gamme.
- **Haptique** : trois motifs de plus (`correct`, `wrong`, `lessonDone`), joués à chaque vérification et en fin de leçon ; `streakUp` sur un combo.
- **Surfaces** : les cartes ne sont plus des rectangles gris plats : un fond légèrement dégradé, une lumière en haut, un filet qui s'éclaircit vers le haut, une ombre portée. Les chiffres du bilan du jour, de la journée complète et des fins d'exercice sont des tuiles teintées (`StatTile`) avec leur icône et un halo de leur couleur, et le nombre monte en comptant.
- **Le chemin** : le score ou les XP d'une étape sont une pastille sur le bord du disque, plus sous le titre ; les pas sont plus hauts. Plus de chevauchement avec l'étape suivante.
- **Écarté : des animations Lottie ou des vidéos.** Tout est dessiné et animé en SwiftUI : rien à télécharger, un seul style, et « Réduire les animations » suffit à tout calmer.

