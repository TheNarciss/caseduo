# API CaseDuo (contrat app ↔ backend)

Base : `https://caseduo.riskybusinesses.uk/api` (prod), `http://localhost:8001/api` (dev).
Tout est en JSON UTF-8, dates `YYYY-MM-DD`, instants ISO 8601 avec fuseau. Auth par cookie `caseduo_auth` (HTTP-only, 7 jours, renouvelé par `GET /users/me`), exactement comme Tangent : l'app laisse `URLSession` garder et renvoyer le cookie.

Erreurs : `{"detail": "message lisible en français", "type": "NomDeLErreur"}` avec le code HTTP adapté (401 non connecté, 404, 409, 422, 429, 503 budget IA ou IA indisponible).

## Auth

| Méthode | Route | Corps | Réponse |
|---|---|---|---|
| POST | `/auth/login` | `application/x-www-form-urlencoded` : `username=<email>&password=…` | 204 + `Set-Cookie` ; 400 `LOGIN_BAD_CREDENTIALS` |
| POST | `/auth/logout` | — | 204 |
| POST | `/auth/apple/native` | `{"identity_token": "…", "nonce": "<nonce brut>", "display_name": "Clément" \| null}` | 204 + `Set-Cookie` |
| GET | `/auth/providers` | — | `{"apple": true}` |
| GET | `/users/me` | — | `{"id","email","is_active","is_superuser","is_verified","display_name"}` (renouvelle le cookie) |

## Profil

`GET /me` →
```json
{
  "id": "uuid", "email": "…", "display_name": "Clément", "is_admin": false,
  "timezone": "Asia/Singapore", "daily_goal_xp": 50,
  "sounds_enabled": true, "notifications_enabled": true,
  "streak_current": 4, "streak_longest": 9, "streak_freezes": 2,
  "xp_total": 820, "league": "bronze",
  "story_text": "…" , "story_updated_at": "…",
  "created_at": "2026-11-04T08:00:00+00:00"
}
```
- `commitment` (D16) : l'engagement en cours, ou le dernier pendant 7 jours après sa fin, sinon `null` :
```json
{"id": "uuid", "daily_xp": 50, "days": 14, "start_date": "2026-11-04", "end_date": "2026-11-17",
 "status": "active", "day_index": 5, "days_met": 4, "days_frozen": 0, "days_missed": 0,
 "on_track": true, "kept": null, "badge_awarded": false,
 "calendar": [{"date": "2026-11-04", "state": "met"}, {"date": "2026-11-08", "state": "today"}, {"date": "2026-11-09", "state": "future"}]}
```
  `status` ∈ `active, ended` ; `state` ∈ `met, frozen, missed, today, future` ; `kept` n'est renseigné qu'une fois terminé (aucun jour manqué, un freeze compte comme tenu). Le badge `commitment_kept` (« Parole tenue ») tombe au premier `/today` qui suit la fin d'un engagement tenu.
- `PATCH /me` : n'importe quel sous-ensemble de `{display_name, timezone, daily_goal_xp (30|50|80), sounds_enabled, notifications_enabled}` → `Me`. **409** sur `daily_goal_xp` tant qu'un engagement court.
- `POST /me/commitment` : `{"daily_xp": 30|50|80, "days": 7|14|30}` → `Me` (avec `commitment`). L'objectif prend cette valeur et ne bouge plus jusqu'à `end_date`. **409** si un engagement court déjà.
- `PUT /me/story` : `{"story_text": "…"}` → `Me`.
- `POST /me/push-token` : `{"token": "<hex APNs>", "environment": "sandbox" | "production"}` → 204.
- `DELETE /me` → 204 (suppression définitive du compte et de ses données).

## Aujourd'hui

`GET /today` →
```json
{
  "date": "2026-11-04",
  "weekday": 2,
  "timezone": "Asia/Singapore",
  "streak": {"current": 4, "longest": 9, "freezes": 2, "status": "at_risk",
             "freeze_used_on": ["2026-11-02"], "freeze_just_used": false},
  "goal": {"target_xp": 50, "xp_today": 20, "met": false},
  "remaining": 5,
  "day_complete": false,
  "easy_mode": false,
  "mock": {"kind": "full", "mbb": false, "language": "fr", "done": false, "run_id": null} ,
  "cards": [ExerciseCard, …],
  "unlocks": {"streak30_icon": false, "perfect_week_until": null},
  "league": {"tier": "bronze", "tier_label": "Bronze", "rank": 3, "size": 6, "xp_week": 120},
  "is_admin": false,
  "commitment": {…comme /me…}
}
```
- `streak.status` : `extended_today` (objectif atteint aujourd'hui), `at_risk` (série > 0, objectif pas encore atteint), `safe` (série à 0 et rien à perdre).
- `streak.freeze_just_used` : vrai une seule fois, au premier `/today` après qu'un freeze a sauvé la série (écran « Freeze utilisé »).
- `mock` : présent le dimanche (`kind: "full"`) et le samedi des semaines paires (`kind: "fit"`), sinon `null`.
- `cards` est **déjà dans l'ordre d'affichage** : mock (dimanche) n'est pas une carte ; cadrage_home épinglé (ven.→dim.), brainteaser d'échauffement, fit, cases par difficulté croissante, autres brainteasers, revanches.
- `remaining` : cartes non faites, hors cadrage_home. C'est le badge d'icône et le chiffre du widget.

`ExerciseCard` :
```json
{
  "exercise_id": "uuid", "type": "market_sizing", "type_label": "Market sizing",
  "title": "Combien de passagers par jour à Changi ?",
  "difficulty": 3, "language": "fr", "style": "wavestone", "sector": "industrie/défense",
  "estimated_minutes": 6, "is_revenge": false, "revenge_step": null,
  "pinned": false, "done": false, "best_score": null, "xp_potential": 30,
  "due_label": null, "is_bonus": false, "date": "2026-11-04", "from_pack": false
}
```
`type` ∈ `market_sizing, cadrage, business_case, diagnostic, brainteaser, fit, cadrage_home, tech_screen`. `style` ∈ `wavestone, mbb`. `language` ∈ `fr, en`. `due_label` : « À rendre dimanche soir » pour cadrage_home, « Bonus · quand tu veux » ou « Jour passé » dans l'onglet Entraîner. L'app groupe les cartes du jour par famille (brainteasers, fit, cases, revanches) et donne une couleur à chaque type (D16).

`GET /training` (onglet Entraîner, D16) → le pack bonus en entier, fait ou non, plus les exercices des 30 derniers jours restés sans réponse (hors cadrage_home et mocks) :
```json
{"date": "2026-11-06",
 "types": [{"type": "brainteaser", "label": "Brainteaser", "total": 15, "done": 2}],
 "exercises": [ExerciseCard, …]}
```
Triés par type puis difficulté. `is_bonus` vaut toujours `true` ici ; `from_pack` distingue le pack d'un jour passé. Ces exercices rapportent des XP mais ne comptent ni pour `remaining` ni pour « journée complète ».

`GET /widget` → `{"date": "…", "streak": 4, "status": "at_risk", "remaining": 3, "xp_today": 20, "goal_xp": 50}` (petit, pour le widget et le badge).

`GET /day/summary` →
```json
{"date": "…", "streak": {…comme /today…}, "xp_today": 75, "goal": {…},
 "exercises_done": 6, "league_tier": "bronze", "league_rank": 2,
 "weakest_criterion": {"key": "structure", "label": "Structure annoncée", "average": 0.7} ,
 "line": "Point faible du jour : la structure annoncée avant le déroulé."}
```

## Exercice

`GET /exercises/{id}` →
```json
{
  "id": "uuid", "date": "…", "type": "cadrage", "type_label": "Note de cadrage",
  "style": "wavestone", "language": "fr", "difficulty": 3, "sector": "banque",
  "title": "…", "prompt": "markdown", "estimated_minutes": 8,
  "parts": null,
  "context_data_available": true, "revealed": false, "context_data": null,
  "is_revenge": false, "flagged": false,
  "attempts": [AttemptSummary, …]
}
```
- `parts` : `null`, ou `[{"question": "…", "data": "…" | null}]` pour un case MBB mené par l'interviewer (questions successives) ou le mock fit (6 questions). L'app montre une partie à la fois et envoie `part_answers`.
- `context_data` est fourni d'emblée pour le style `mbb` (données données dès le départ, sans pénalité) ; sinon `null` jusqu'à `POST /exercises/{id}/reveal`.

`POST /exercises/{id}/reveal` → `{"context_data": ContextData, "xp_penalty": 5}` (pénalité appliquée seulement si la révélation précède la réponse principale ; 0 pour le style mbb).

`ContextData` :
```json
{"facts": [{"label": "Passagers annuels à Changi (2024)", "value": "67,7 millions",
            "source_url": "https://…", "hypothesis": false}],
 "constraints": ["Budget data annuel : 4 M€"],
 "documents": [{"title": "Organigramme DSI", "body": "markdown"}]}
```
`documents` sert surtout au cadrage_home.

## Notation

`POST /grade` (JSON, attend la note complète) et `POST /grade/stream` (SSE). Même corps :
```json
{
  "exercise_id": "uuid",
  "kind": "main",
  "answer_text": "…",
  "duration_seconds": 312,
  "input_mode": "voice",
  "parent_attempt_id": null,
  "mock_run_id": null,
  "part_answers": null,
  "slides": null
}
```
- `kind` : `main`, `retry_2min` (refaire en 2 min, `parent_attempt_id` = la tentative notée), `follow_up` (réponse à la relance, `parent_attempt_id` = la tentative qui a posé la relance).
- `slides` (cadrage_home) : `[{"title": "titre-message", "lines": ["…", "…"]}]` × 5 ; le serveur en fait le texte noté.
- `part_answers` : une réponse par élément de `parts`, dans l'ordre.

Réponse de `POST /grade` = `GradeResult` :
```json
{
  "attempt": Attempt,
  "xp": {"earned": 45, "breakdown": [{"label": "10 × difficulté 3", "xp": 30},
                                     {"label": "Score ≥ 80 : ×1,5", "xp": 15}]},
  "progress": {
    "xp_today": 65, "goal_target": 50, "goal_met": true, "goal_just_met": true,
    "streak": {…comme /today…}, "streak_extended": true, "freeze_earned": false,
    "day_complete": false, "day_complete_bonus": 0, "perfect_week": false,
    "remaining": 3, "new_badges": [Badge]
  }
}
```

### SSE (`/grade/stream`)

Chaque événement tient sur deux lignes `event:` puis `data:` (JSON sur une ligne), suivies d'une ligne vide :
```
event: scores
data: {"rubric_scores": [RubricScore, …], "score": 72}

event: feedback
data: {"delta": "### Ce qui était bien\n- …"}

event: follow_up
data: {"text": "Tu as dit 20 % d'adoption : d'où vient ce chiffre ?"}

event: done
data: GradeResult

event: error
data: {"reason": "budget" | "overloaded" | "invalid" | "internal", "detail": "…"}
```
`feedback` arrive en plusieurs morceaux à concaténer. Les erreurs connues avant le début (budget atteint, exercice inconnu) sont des réponses HTTP classiques, pas des événements.

`Attempt` :
```json
{
  "id": "uuid", "exercise_id": "uuid", "kind": "main", "parent_attempt_id": null,
  "answer_text": "…", "duration_seconds": 312, "input_mode": "voice",
  "score": 72,
  "rubric_scores": [{"key": "structure", "label": "Structure annoncée", "weight": 20,
                     "score": 1, "justification": "…", "quote": "« je vois trois axes »"}],
  "feedback": "markdown (trois sections)",
  "follow_up": "…", "xp_earned": 45, "is_revenge": false, "revealed_data": false,
  "mock_run_id": null, "created_at": "…",
  "exercise": {"id": "…", "title": "…", "type": "…", "type_label": "…", "language": "fr",
               "model_answer": "markdown", "sources": [{"url": "…", "title": "…", "verified": true}],
               "rubric": [RubricCriterion], "flagged": false}
}
```
`AttemptSummary` = `{"id","exercise_id","kind","score","xp_earned","created_at","title","type","type_label"}`.
`RubricCriterion` = `{"key","label","weight","levels": {"0": "…", "1": "…", "2": "…"}}`.

`GET /attempts?limit=30` → `[AttemptSummary]` ; `GET /attempts/{id}` → `Attempt`.

## Historique

`GET /history?days=90` →
```json
{
  "series": [{"type": "market_sizing", "label": "Market sizing",
              "points": [{"date": "…", "score": 64}]}],
  "weaknesses": [{"key": "structure", "label": "Structure annoncée", "average": 0.8, "count": 6}],
  "criteria": [{"key": "…", "label": "…", "average": 1.4, "count": 12}],
  "calendar": [{"date": "…", "goal_met": true, "freeze_used": false, "xp": 60}],
  "recent_attempts": [AttemptSummary],
  "mocks": [{"id": "…", "date": "…", "kind": "full", "score": 68}]
}
```
`average` est sur l'échelle 0–2 de la rubric. `weaknesses` = les 3 critères les plus faibles sur 14 jours. `calendar` couvre le mois en cours et le précédent.

## Ligue

`GET /league` →
```json
{"tier": "bronze", "tier_label": "Bronze", "week_start": "2026-11-02",
 "ends_at": "2026-11-08T23:00:00+08:00",
 "members": [{"name": "Camille", "xp": 140, "is_me": false, "rank": 1}],
 "promote_top": 2, "relegate_bottom": 2,
 "last_outcome": "promoted" | "relegated" | "stayed" | null}
```
Paliers : `bronze`, `silver` (Argent), `gold` (Or).

## Badges

`GET /badges` → `[{"code": "streak_10", "name": "10 jours", "description": "…", "symbol": "flame.fill", "earned_at": "…" | null}]`

## Mock entretien

- `POST /mocks` `{"kind": "full" | "fit"}` → `MockRun` (409 si pas de mock aujourd'hui ou déjà fait).
- `GET /mocks/{id}` → `MockRun`.
- `POST /mocks/{id}/finish` → `{"id", "score", "xp_earned", "attempts": [AttemptSummary], "previous": [{"date","kind","score"}], "feedback": "markdown"}`.

`MockRun` :
```json
{"id": "uuid", "kind": "full", "mbb": false, "language": "fr", "status": "in_progress",
 "time_limit_seconds": 1800, "started_at": "…",
 "steps": [{"index": 0, "exercise_id": "uuid", "type": "fit", "title": "…", "prompt": "…",
            "parts": null, "context_data": null, "time_limit_seconds": 300, "follow_up_after": false}]}
```
Déroulé dans l'app : pour chaque étape, réponse orale, `POST /grade` avec `mock_run_id` (le feedback n'est pas montré pendant le mock) ; si `follow_up_after`, la relance renvoyée est posée tout de suite, puis `POST /grade` en `kind: follow_up`. Pas de retour en arrière. À la fin, `POST /mocks/{id}/finish`.

## Admin (superuser)

- `GET /admin/review/{date}` (JSON) et la page HTML `GET /admin/review/{date}` hors `/api` (lisible dans un navigateur, se connecte avec le même cookie).
- `POST /admin/exercises/{id}/flag` `{"flagged": true, "note": "corrigé faux sur le chiffrage"}` → l'exercice sort des revanches.
- `POST /admin/generate` `{"date": "…", "mode": "sync" | "batch", "force": false}`.
- `GET /admin/cron-runs?limit=30`.

## Santé

`GET /health` → `{"status": "ok", "db": "up", "exercises_today": 9}`.
