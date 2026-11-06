# Écrire le contenu du Parcours

Le Parcours est un cours d'entretiens de conseil (IT / transformation, stratégie, finance), pour des étudiants d'écoles d'ingénieurs et de commerce de tout niveau. Chaque leçon a **une idée** (`objective` dans `units/*.json`), trois erreurs classiques, et une banque d'items dans `items/<unit>.json` d'où l'app tire 10 items par passage (donc écrire ~20 items par leçon, variés, pour que deux passages diffèrent).

## Règles de qualité (ce que le validateur ne voit pas)

- **Réaliste** : des situations qu'un interviewer pose vraiment, des chiffres plausibles, des secteurs variés (`banque, assurance, retail, énergie, santé, secteur public, industrie, télécoms, transport, luxe, tech, général`). Aucun cabinet nommé dans les items.
- **Un leurre a une raison** : chaque mauvaise option porte un `why_wrong` d'une ligne qui enseigne quelque chose ; pas de leurre absurde. Cible : 70-85 % de réussite au premier essai.
- **L'explication** (≤ 180 caractères) est montrée après chaque réponse, juste ou fausse : la règle à retenir, pas une paraphrase de la bonne réponse.
- **Court** : un item se lit en 10 secondes sur un téléphone. Énoncé ≤ 320 caractères, option ≤ 160.
- **Progressif** : `difficulty` 1-2 pour les premiers items d'une leçon (reconnaissance), 3-4 pour la production, 5 rare.
- **Français d'entretien** : tutoiement dans les consignes (« Choisis… », « Remets… »), vocabulaire du métier, pas de jargon inutile.
- La bonne réponse ne doit pas être la plus longue, ni toujours en position « a » (l'app mélange, mais varie quand même).
- Interdits : « toutes les réponses », « aucune des réponses ».

## Validation

```
cd backend && /home/user/.venv-caseduo/bin/python -m app.path check ../content/path/items/u1.json
```

## Enveloppe d'un item

```json
{"id": "u1.reformulate.003", "format": "choose_structure", "skill": "u1.reformulate",
 "difficulty": 2, "lang": "fr", "sector": "banque",
 "stem": "…", "media": null, "explanation": "…", "payload": {…}, "tags": []}
```

`id` = `<unité>.<leçon>.<numéro à 3 chiffres>` ; `skill` = `<unité>.<leçon>` (le code du nœud).

## Les formats et leur `payload`

**concept_card** (une par leçon, en premier ; 2-3 écrans, markdown léger, un exemple résolu)
```json
{"screens": [{"title": "L'idée", "body": "…"}, {"title": "Exemple", "body": "…"}, {"title": "À retenir", "body": "…"}]}
```

**choose_structure / first_question** (1 carte sur 2-4)
```json
{"options": [{"id": "a", "text": "Revenus vs coûts"},
             {"id": "b", "text": "Clients / produits / canaux", "why_wrong": "Utile au 2e niveau, n'isole pas la cause."},
             {"id": "c", "text": "Forces / faiblesses", "why_wrong": "Grille descriptive, pas une décomposition."}],
 "correct": "a"}
```

**pick_so_what** (même payload, avec un `media` graphique ou tableau)
```json
"media": {"type": "bar", "title": "Adoption de l'assistant IA", "unit": "%", "categories": ["Finance", "RH", "Ventes", "Ops"],
          "series": [{"name": "Adoption", "values": [65, 20, 70, 25]}, {"name": "Budget formation (k€)", "values": [80, 75, 20, 25]}]}
"media": {"type": "table", "header": ["Segment", "CA 2024", "CA 2025"], "rows": [["Pro", "120", "131"], ["Part.", "80", "72"]]}
```

**tree_complete** (un arbre à un niveau, un enfant contient « ? »)
```json
"media": {"type": "tree", "root": "Réduire la facture énergétique", "children": ["Volume consommé → ?", "Prix unitaire → contrat, autoproduction"]}
"payload": {"options": [{"id": "a", "text": "Efficacité des équipements"}, {"id": "b", "text": "Taux de change", "why_wrong": "Sans lien avec les kWh."}, {"id": "c", "text": "Marge du fournisseur", "why_wrong": "C'est le prix, pas le volume."}], "correct": "a"}
```

**swipe_valid** (4-8 cartes, valides et invalides mélangées, une `reason` chacune)
```json
{"cards": [{"id": "c1", "text": "Coûts fixes / coûts variables", "valid": true, "reason": "Deux ensembles disjoints qui couvrent tout."},
           {"id": "c2", "text": "Coûts / coûts fournisseurs", "valid": false, "reason": "Les coûts fournisseurs sont déjà dans les coûts."}],
 "pass_ratio": 0.8}
```

**spot_error** (3-6 lignes, une fautive, le `fix`)
```json
{"lines": [{"id": "l1", "text": "50 MW × 8 760 h = 438 GWh à pleine puissance"}, {"id": "l2", "text": "Facteur de charge 25 % → 110 GWh"},
           {"id": "l3", "text": "À 80 €/MWh → 8,8 M€"}, {"id": "l4", "text": "Donc 0,8 M€ par MW installé"}],
 "wrong_line": "l4", "fix": "8,8 M€ / 50 MW ≈ 0,18 M€ par MW."}
```

**order_steps / synth_order / headline_tiles** (tuiles, solution ordonnée, intruses à laisser de côté)
```json
{"tiles": [{"id": "t1", "text": "Recommandation : lancer le programme dès T2"}, {"id": "t2", "text": "Raison 1 : +3 pts de fréquence en pilote"},
           {"id": "t3", "text": "Risque : cannibalisation des promos papier"}, {"id": "t4", "text": "Prochaine étape : 50 magasins"},
           {"id": "t5", "text": "Contexte : le retail est concurrentiel"}],
 "solution": ["t1", "t2", "t3", "t4"], "distractors": ["t5"], "accepted": []}
```
`headline_tiles` : des mots ou groupes de mots (8-10 tuiles, 2-3 intruses comme « on observe que ») qui forment un titre-message.

**mental_math** (1-8 questions, `computation` recalculée par le serveur, tolérance 3 % par défaut)
```json
{"seconds": 60, "questions": [{"id": "q1", "stem": "2,4 M de contrats, prime 480 €, ratio S/P 72 %. Sinistres annuels ?",
                                "computation": "2.4e6*480*0.72", "answer": 829440000, "unit": "€", "tolerance_pct": 3, "hint": "2,4 × 480 ≈ 1 150 ; × 0,7"}]}
```
Le `stem` de l'item lui-même peut rester vide pour ce format.

**estimate_range** (curseur, souvent logarithmique ; plage acceptée ≤ facteur 4)
```json
{"range": [18000000, 26000000], "slider": [1000000, 100000000], "unit": "passages/an", "scale": "log",
 "reference": "68 M d'habitants × ~0,3 passage par an ≈ 21 M."}
```

**two_step_calc** (la formule d'abord, puis le nombre)
```json
{"formulas": [{"id": "a", "text": "Coûts fixes ÷ (prix − coût variable)"}, {"id": "b", "text": "Coûts fixes ÷ prix", "why_wrong": "Le prix n'est pas la marge."},
              {"id": "c", "text": "Coûts fixes × marge", "why_wrong": "On cherche un nombre d'unités : on divise."}],
 "correct_formula": "a", "computation": "600000/(50-30)", "answer": 30000, "unit": "unités", "tolerance_pct": 3}
```

**fill_blank** (1-4 trous `{{1}}`, 2-4 options chacun)
```json
{"text": "Le seuil de rentabilité se calcule en divisant les coûts {{1}} par la marge {{2}}.",
 "slots": [{"id": 1, "options": ["fixes", "variables", "totaux"], "correct": 0}, {"id": 2, "options": ["brute", "sur coût variable", "nette"], "correct": 1}]}
```

**mece_sort** (2-3 paniers, 4-8 items, ≥ 2 par panier)
```json
{"buckets": [{"id": "fix", "label": "Coûts fixes"}, {"id": "var", "label": "Coûts variables"}],
 "items": [{"id": "i1", "text": "Loyers", "bucket": "fix"}, {"id": "i2", "text": "Emballages", "bucket": "var"}, …]}
```

**match_pairs** (3-5 paires)
```json
{"pairs": [{"left": "Churn", "right": "clients perdus / clients en début de période"}, {"left": "Panier moyen", "right": "CA / nombre de transactions"}]}
```

**oral_prompt** (bilans seulement ; noté par Claude sur la transcription)
```json
{"seconds": 75, "rubric": [{"key": "reformulation", "label": "Objectif reformulé en une phrase", "weight": 2},
                           {"key": "plan", "label": "Démarche annoncée en 3 branches", "weight": 2},
                           {"key": "start", "label": "Dit par où commencer et pourquoi", "weight": 1}],
 "model_answer": "…"}
```
