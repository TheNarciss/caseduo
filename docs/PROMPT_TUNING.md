# Ajuster les deux prompts

Deux fichiers pilotent toute la qualité de l'app :

| Fichier | Rôle | Lu par |
|---|---|---|
| `prompts/generate.md` | le senior manager qui écrit les exercices, corrigés et rubrics | la génération (batch de 03:00, secours de 05:30, seed) |
| `prompts/grade.md` | l'interviewer qui note, écrit le feedback et pose la relance | chaque `POST /api/grade` |

Les deux sont **relus à chaque appel**. Une modification s'applique dès la génération ou la notation suivante, sans rebuild ni redémarrage. Sur la VM, le dossier `prompts/` est monté en lecture seule dans le conteneur (DEVIATIONS D4).

## Ce qu'on peut changer sans risque, et ce qui casse le code

Chaque fichier a deux parties :

1. **Le haut, ton texte d'origine** (jusqu'à la ligne `---`). C'est le cœur : ton, exigences, structure des corrigés, sévérité. Modifie-le librement.
2. **Les sections « (ajouté par CaseDuo) »** : cibles réelles, variantes, format de sortie. Le **format de sortie** est un contrat avec le code :
   - `generate.md` : un seul objet JSON dans un bloc ```` ```json ````, avec les champs du schéma et les clés de rubric de `backend/app/catalog.py` (`CRITERIA`). Le validateur (`backend/app/generation/schema.py`) rejette le reste, et l'exercice est retenté deux fois.
   - `grade.md` : les trois blocs `<scores>`, `<feedback>`, `<follow_up>` dans cet ordre, `<scores>` en JSON sur une ligne. L'app affiche le score dès que `</scores>` se ferme.

   Pour ajouter un critère de rubric, il faut l'ajouter aussi dans `CRITERIA` et `RUBRIC_KEYS` (`catalog.py`), sinon les exercices qui l'utilisent seront rejetés.

## La boucle de travail

Toutes les commandes se lancent dans le conteneur, sur la VM ou en local :

```bash
DC="docker compose -f docker-compose.yml -f docker-compose.prod.yml exec backend"   # en local : docker compose exec backend
```

### 1. Repérer ce qui ne va pas

- Ouvre `https://caseduo.riskybusinesses.uk/admin/review/AAAA-MM-JJ` (connexion admin dans la page) : énoncé, données avec leurs sources (vérifiées par la recherche ou non), corrigé, rubric, coût du jour.
- **Marquer « mauvais »** un corrigé douteux, avec une note qui dit pourquoi. L'exercice sort des revanches, et la liste des exercices signalés devient ton jeu de cas à corriger :

  ```bash
  $DC python -c "
  import asyncio
  from sqlalchemy import select
  from app.db import async_session_factory
  from app.db.models import Exercise
  async def main():
      async with async_session_factory() as s:
          for e in (await s.execute(select(Exercise).where(Exercise.flagged))).scalars():
              print(e.date, e.slot, '|', e.title, '|', e.flag_note)
  asyncio.run(main())"
  ```

### 2. Modifier le prompt

Édite `prompts/generate.md` ou `prompts/grade.md` sur la VM (ou en local, puis push : la CD redéploie). Garde une copie de l'ancienne version (`git diff` suffit si tu passes par le dépôt).

### 3. Comparer sur une vraie journée, sans toucher au contenu de l'app

**Génération** : on régénère les exercices d'une date avec le prompt modifié, sans rien insérer, et on écrit côte à côte ce qui est en base et la nouvelle version.

```bash
$DC python -m app.prompt_lab generate --date 2026-11-06 --slots case_cadrage,case_market_sizing,fit --out /tmp/prompt_lab
docker cp caseduo-backend:/tmp/prompt_lab ./prompt_lab
diff -u prompt_lab/2026-11-06/case_cadrage.stored.md prompt_lab/2026-11-06/case_cadrage.new.md
```

Sans `--slots`, tous les exercices du jour sont régénérés. Les slots s'appellent `brainteaser_1..3`, `fit`, `case_market_sizing`, `case_cadrage`, `case_business_case`, `case_diagnostic`, `case_extra`, `cadrage_home` (le vendredi), `mock_*` (le week-end). Un exercice rejeté trois fois laisse un `<slot>.errors.json` qui dit pourquoi : c'est souvent le format de sortie qui a été abîmé.

La génération se fait en **synchrone** : plein tarif, environ 0,04 à 0,08 $ par case avec la recherche web. Le coût de chaque slot s'affiche et compte dans le plafond du jour.

**Notation** : on renote une réponse déjà donnée avec le prompt modifié, et on compare critère par critère.

```bash
$DC python -m app.prompt_lab grade --attempt <uuid-de-la-tentative>
```

La sortie ressemble à ceci, avec le feedback avant/après dans un fichier :

```
critère                                       avant  après
Reformulation et cadrage                          2      2
Structure annoncée avant le déroulé               1      0
...
score                                            64     52   ($0.0213)
```

Les identifiants de tentatives sont dans `GET /api/attempts` ou dans la table `attempts`. Pour juger un changement de sévérité, renote 5 à 10 réponses variées (bonnes et mauvaises, texte et oral) plutôt qu'une seule.

### 4. Appliquer pour de vrai

- **Les prochains jours** : rien à faire, le batch de 03:00 utilise déjà le nouveau prompt.
- **Refaire un jour déjà généré** (par exemple aujourd'hui) : les exercices sans réponse sont supprimés puis régénérés, ceux auxquels tu as répondu sont gardés.

  ```bash
  $DC python -m app.prompt_lab replace --date 2026-11-06
  # ou, depuis n'importe où : POST /api/admin/generate {"date": "2026-11-06", "force": true}
  ```

- **Tester le batch** plutôt que le synchrone, pour une date future :

  ```bash
  $DC python -c "import asyncio; from datetime import date; from app.db import async_session_factory; from app.generation import batch
  async def m():
      async with async_session_factory() as s: print(await batch.submit_batch(s, date(2026, 11, 20)))
  asyncio.run(m())"
  ```

  Le polling insère le résultat dans les 30 minutes qui suivent la fin du batch.

## Le cache de prompt

Le system prompt est mis en cache (5 minutes) : dans un batch de 10 exercices, les 9 derniers le lisent à 10 % du prix. Modifier le prompt invalide le cache une fois, rien de plus. Pour la notation, l'énoncé, le corrigé et la rubric de l'exercice forment un second bloc en cache, si bien que la relance et le « refaire en 2 min » coûtent moins cher que la première note.

Le cache ne s'active qu'au-delà d'une taille minimale de prompt (1 024 tokens pour Sonnet 4.5). Les deux prompts la dépassent. Si tu les raccourcis beaucoup, regarde `cache_read_tokens` dans `cron_runs` ou `attempts` : s'il reste à 0, le cache ne joue plus.

## Changer de modèle

Une ligne dans `backend/.env`, puis `docker compose … up -d backend` :

```
CASEDUO_MODEL=claude-sonnet-5-5
```

Le code adapte la requête au modèle : variante de recherche web, réflexion adaptative et effort, prix (voir `backend/app/llm/anthropic_client.py` et `cost_tracker.py`). `claude-sonnet-4-5`, la valeur par défaut, est retiré le 30/11/2026 (DEVIATIONS D1). Après un changement de modèle, rejoue l'étape 3 sur 2 ou 3 journées : le ton et la sévérité bougent d'un modèle à l'autre.

## Où regarder quand ça dérape

| Symptôme | Où |
|---|---|
| Des exercices manquent un matin | `cron_runs` (job `batch`, `fallback`, `sync`) et sa colonne `errors` ; `/admin/review/<date>` affiche les deux |
| Un exercice rejeté en boucle | `errors` contient la raison : « poids = 95 », « critères non autorisés », « aucune source ne vient de la recherche web »… |
| Des sources « non vérifiées » | le modèle a cité une URL que la recherche ne lui a pas renvoyée : renforce la règle dans `generate.md` ou marque l'exercice « mauvais » |
| Notes trop sévères ou trop gentilles | `prompt_lab grade` sur un échantillon, puis ajuste le paragraphe de sévérité de `grade.md` |
| Coût qui grimpe | `cron_runs.cost_usd` par jour, `attempts.cost_usd` par note ; `GENERATION_WEB_SEARCH_MAX_USES` est le premier levier |
