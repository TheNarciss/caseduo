"""A one-lesson course with one item of every format: what the contract fixtures and the
app's demo mode show, so every decoder and every format view gets exercised."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

UNIT = {
    "code": "d1",
    "order": 1,
    "title": "Démo du Parcours",
    "subtitle": "Un item de chaque format.",
    "symbol": "sparkles",
    "nodes": [
        {
            "code": "d1.showcase",
            "kind": "lesson",
            "title": "Tous les formats",
            "objective": "Voir chaque format d'exercice une fois.",
            "items": 20,
        },
        {"code": "d1.review", "kind": "review", "title": "Révision", "items": 6},
        {"code": "d1.applied", "kind": "applied", "title": "En situation", "applied_type": "case"},
        {"code": "d1.check", "kind": "checkpoint", "title": "Bilan", "items": 6},
        {"code": "d1.legendary", "kind": "legendary", "title": "Légendaire", "items": 6},
    ],
}


def items() -> list[dict[str, Any]]:
    s = "d1.showcase"
    out: list[dict[str, Any]] = [
        {
            "id": f"{s}.000",
            "format": "concept_card",
            "skill": s,
            "difficulty": 1,
            "payload": {
                "screens": [
                    {
                        "title": "Reformuler d'abord",
                        "body": "Avant toute structure, redis la question en une phrase : **la métrique, l'horizon, la contrainte**.",
                    },
                    {
                        "title": "Exemple",
                        "body": "« Notre client, une banque, perd de l'argent. » → *Vous voulez retrouver une marge positive sur l'activité de détail d'ici deux ans, sans fermer d'agence.*",
                    },
                    {
                        "title": "À retenir",
                        "body": "Une phrase, trois éléments. Si l'un manque, c'est ta première question.",
                    },
                ]
            },
        },
        {
            "id": f"{s}.001",
            "format": "choose_structure",
            "skill": s,
            "difficulty": 1,
            "sector": "banque",
            "stem": "Une banque de détail voit sa rentabilité reculer depuis trois ans. Quelle structure de départ ?",
            "explanation": "Rentabilité = revenus − coûts ; on segmente ensuite chaque branche.",
            "payload": {
                "options": [
                    {
                        "id": "a",
                        "text": "Revenus (marge d'intérêt, commissions) vs coûts (réseau, IT, risque)",
                    },
                    {
                        "id": "b",
                        "text": "Particuliers / professionnels / entreprises",
                        "why_wrong": "Segmentation utile au 2e niveau, mais n'isole pas la cause.",
                    },
                    {
                        "id": "c",
                        "text": "Forces / faiblesses / opportunités / menaces",
                        "why_wrong": "Grille descriptive, pas une décomposition du problème.",
                    },
                ],
                "correct": "a",
            },
        },
        {
            "id": f"{s}.002",
            "format": "pick_so_what",
            "skill": s,
            "difficulty": 2,
            "sector": "tech",
            "stem": "Adoption d'un assistant IA par direction, et budget de formation. Le so-what ?",
            "media": {
                "type": "bar",
                "title": "Adoption et budget",
                "categories": ["Finance", "RH", "Ventes", "Ops"],
                "series": [
                    {"name": "Adoption (%)", "values": [65, 20, 70, 25]},
                    {"name": "Budget (k€)", "values": [80, 75, 20, 25]},
                ],
            },
            "explanation": "Chercher ce qui contredit l'hypothèse évidente, c'est le so-what.",
            "payload": {
                "options": [
                    {
                        "id": "a",
                        "text": "Le budget n'explique pas l'adoption : Ventes atteint 70 % avec le plus petit",
                    },
                    {
                        "id": "b",
                        "text": "Finance a le plus gros budget, donc la meilleure adoption",
                        "why_wrong": "Ventes fait mieux avec quatre fois moins.",
                    },
                    {
                        "id": "c",
                        "text": "Il faut augmenter le budget RH",
                        "why_wrong": "Une recommandation sans cause identifiée.",
                    },
                ],
                "correct": "a",
            },
        },
        {
            "id": f"{s}.003",
            "format": "first_question",
            "skill": s,
            "difficulty": 1,
            "sector": "banque",
            "stem": "Une banque veut entrer sur le crédit à la consommation en ligne. Ta première question ?",
            "explanation": "Clarifier l'objectif avant toute structure.",
            "payload": {
                "options": [
                    {"id": "a", "text": "Quel objectif chiffré et quel horizon ?"},
                    {
                        "id": "b",
                        "text": "Quel fournisseur cloud utiliser ?",
                        "why_wrong": "Trop opérationnel pour une ouverture.",
                    },
                    {
                        "id": "c",
                        "text": "Quelle est la croissance du PIB ?",
                        "why_wrong": "Trop macro : ne cadre pas la décision.",
                    },
                ],
                "correct": "a",
            },
        },
        {
            "id": f"{s}.004",
            "format": "tree_complete",
            "skill": s,
            "difficulty": 2,
            "sector": "énergie",
            "stem": "Complète l'arbre.",
            "media": {
                "type": "tree",
                "root": "Réduire la facture énergétique",
                "children": ["Volume consommé → ?", "Prix unitaire → contrat, autoproduction"],
            },
            "explanation": "Sous « volume », on cherche ce qui réduit les kWh, pas le prix.",
            "payload": {
                "options": [
                    {"id": "a", "text": "Efficacité des équipements"},
                    {
                        "id": "b",
                        "text": "Taux de change",
                        "why_wrong": "Sans lien avec les kWh consommés.",
                    },
                    {
                        "id": "c",
                        "text": "Marge du fournisseur",
                        "why_wrong": "C'est le prix, pas le volume.",
                    },
                ],
                "correct": "a",
            },
        },
        {
            "id": f"{s}.005",
            "format": "swipe_valid",
            "skill": s,
            "difficulty": 2,
            "stem": "MECE ou pas ? Glisse à droite si le découpage tient.",
            "explanation": "Pas de chevauchement, pas de trou, une seule dimension par niveau.",
            "payload": {
                "cards": [
                    {
                        "id": "c1",
                        "text": "Coûts fixes / coûts variables",
                        "valid": True,
                        "reason": "Disjoints et complets.",
                    },
                    {
                        "id": "c2",
                        "text": "Coûts / coûts fournisseurs",
                        "valid": False,
                        "reason": "Les coûts fournisseurs sont déjà dans les coûts.",
                    },
                    {
                        "id": "c3",
                        "text": "Clients particuliers / clients en ligne",
                        "valid": False,
                        "reason": "Deux dimensions mélangées : type et canal.",
                    },
                    {
                        "id": "c4",
                        "text": "Prix × volume",
                        "valid": True,
                        "reason": "Le chiffre d'affaires, exactement.",
                    },
                ],
                "pass_ratio": 0.75,
            },
        },
        {
            "id": f"{s}.006",
            "format": "spot_error",
            "skill": s,
            "difficulty": 2,
            "sector": "énergie",
            "stem": "Touche la ligne fautive.",
            "explanation": "Toujours re-diviser le total par la bonne base.",
            "payload": {
                "lines": [
                    {"id": "l1", "text": "Parc de 50 MW × 8 760 h = 438 GWh à pleine puissance"},
                    {"id": "l2", "text": "Facteur de charge 25 % → 110 GWh produits"},
                    {"id": "l3", "text": "À 80 €/MWh, chiffre d'affaires ≈ 8,8 M€"},
                    {"id": "l4", "text": "Donc chaque MW rapporte ≈ 0,8 M€ par an"},
                ],
                "wrong_line": "l4",
                "fix": "8,8 M€ ÷ 50 MW ≈ 0,18 M€ par MW.",
            },
        },
        {
            "id": f"{s}.007",
            "format": "order_steps",
            "skill": s,
            "difficulty": 2,
            "stem": "Remets les étapes d'un market sizing dans l'ordre (une tuile est de trop).",
            "explanation": "Clarifier, structurer, estimer, vérifier, conclure.",
            "payload": {
                "tiles": [
                    {"id": "t1", "text": "Clarifier l'unité et le périmètre"},
                    {"id": "t2", "text": "Choisir top-down ou bottom-up"},
                    {"id": "t3", "text": "Poser les hypothèses et calculer"},
                    {"id": "t4", "text": "Vérifier l'ordre de grandeur"},
                    {"id": "t5", "text": "Conclure et nommer la sensibilité"},
                    {"id": "t6", "text": "Demander la réponse à l'interviewer"},
                ],
                "solution": ["t1", "t2", "t3", "t4", "t5"],
                "distractors": ["t6"],
            },
        },
        {
            "id": f"{s}.008",
            "format": "synth_order",
            "skill": s,
            "difficulty": 2,
            "sector": "retail",
            "stem": "Ordonne la synthèse de 30 secondes (une tuile n'a pas sa place).",
            "explanation": "Réponse d'abord, preuves, risque, prochaine étape ; le contexte n'a pas sa place.",
            "payload": {
                "tiles": [
                    {"id": "t1", "text": "Recommandation : lancer le programme dès T2"},
                    {"id": "t2", "text": "Raison 1 : +3 pts de fréquence d'achat en pilote"},
                    {"id": "t3", "text": "Raison 2 : coût d'acquisition −20 %"},
                    {"id": "t4", "text": "Risque : cannibalisation des promos papier"},
                    {"id": "t5", "text": "Prochaine étape : étendre à 50 magasins"},
                    {"id": "t6", "text": "Contexte : le retail est très concurrentiel"},
                ],
                "solution": ["t1", "t2", "t3", "t4", "t5"],
                "distractors": ["t6"],
            },
        },
        {
            "id": f"{s}.009",
            "format": "headline_tiles",
            "skill": s,
            "difficulty": 3,
            "sector": "secteur public",
            "stem": "Reconstruis le titre-message avec les tuiles (deux sont des intrus).",
            "explanation": "Un titre = constat chiffré + cause ; pas de « on observe ».",
            "payload": {
                "tiles": [
                    {"id": "w1", "text": "Le délai de traitement"},
                    {"id": "w2", "text": "a doublé"},
                    {"id": "w3", "text": "depuis 2022,"},
                    {"id": "w4", "text": "surtout"},
                    {"id": "w5", "text": "à cause des saisies manuelles"},
                    {"id": "w6", "text": "on observe que"},
                    {"id": "w7", "text": "ce qui est intéressant"},
                ],
                "solution": ["w1", "w2", "w3", "w4", "w5"],
                "distractors": ["w6", "w7"],
            },
        },
        {
            "id": f"{s}.010",
            "format": "mental_math",
            "skill": s,
            "difficulty": 2,
            "sector": "assurance",
            "explanation": "Arrondis d'abord, garde les zéros, corrige à la fin.",
            "payload": {
                "seconds": 60,
                "questions": [
                    {
                        "id": "q1",
                        "stem": "2,4 M de contrats, prime moyenne 480 €, ratio sinistres/primes 72 %. Sinistres annuels ?",
                        "computation": "2.4e6*480*0.72",
                        "answer": 829440000,
                        "unit": "€",
                        "tolerance_pct": 3,
                        "hint": "2,4 × 480 ≈ 1 150 M€ ; × 0,7 ≈ 805",
                    },
                    {
                        "id": "q2",
                        "stem": "Un magasin fait 36 000 € par jour, 6 jours sur 7, 50 semaines. CA annuel ?",
                        "computation": "36000*6*50",
                        "answer": 10800000,
                        "unit": "€",
                        "tolerance_pct": 3,
                        "hint": "36 k × 300 jours",
                    },
                ],
            },
        },
        {
            "id": f"{s}.011",
            "format": "estimate_range",
            "skill": s,
            "difficulty": 2,
            "sector": "santé",
            "stem": "Combien de passages aux urgences en France par an ?",
            "explanation": "Une référence : environ un passage pour trois habitants.",
            "payload": {
                "range": [18000000, 26000000],
                "slider": [1000000, 100000000],
                "unit": "passages/an",
                "scale": "log",
                "reference": "68 M d'habitants × ~0,3 passage par an ≈ 21 M.",
            },
        },
        {
            "id": f"{s}.012",
            "format": "two_step_calc",
            "skill": s,
            "difficulty": 3,
            "sector": "retail",
            "stem": "Coûts fixes 600 k€, prix 50 €, coût variable 30 €. Combien d'unités pour être à l'équilibre ?",
            "explanation": "Le seuil se calcule sur la marge unitaire, jamais sur le prix.",
            "payload": {
                "formulas": [
                    {"id": "a", "text": "Coûts fixes ÷ (prix − coût variable)"},
                    {
                        "id": "b",
                        "text": "Coûts fixes ÷ prix",
                        "why_wrong": "Le prix n'est pas la marge.",
                    },
                    {
                        "id": "c",
                        "text": "Coûts fixes × marge",
                        "why_wrong": "On cherche des unités : on divise.",
                    },
                ],
                "correct_formula": "a",
                "computation": "600000/(50-30)",
                "answer": 30000,
                "unit": "unités",
                "tolerance_pct": 3,
            },
        },
        {
            "id": f"{s}.013",
            "format": "fill_blank",
            "skill": s,
            "difficulty": 1,
            "stem": "Complète la règle.",
            "explanation": "Seuil = coûts fixes ÷ marge sur coût variable unitaire.",
            "payload": {
                "text": "Le seuil de rentabilité se calcule en divisant les coûts {{1}} par la marge {{2}}.",
                "slots": [
                    {"id": 1, "options": ["fixes", "variables", "totaux"], "correct": 0},
                    {"id": 2, "options": ["brute", "sur coût variable", "nette"], "correct": 1},
                ],
            },
        },
        {
            "id": f"{s}.014",
            "format": "mece_sort",
            "skill": s,
            "difficulty": 2,
            "sector": "retail",
            "stem": "Range chaque poste dans le bon panier.",
            "explanation": "Variable = proportionnel au volume vendu.",
            "payload": {
                "buckets": [
                    {"id": "fix", "label": "Coûts fixes"},
                    {"id": "var", "label": "Coûts variables"},
                ],
                "items": [
                    {"id": "i1", "text": "Loyers", "bucket": "fix"},
                    {"id": "i2", "text": "Assurance du magasin", "bucket": "fix"},
                    {"id": "i3", "text": "Marchandises vendues", "bucket": "var"},
                    {"id": "i4", "text": "Livraison par commande", "bucket": "var"},
                    {"id": "i5", "text": "Emballages", "bucket": "var"},
                    {"id": "i6", "text": "Abonnement logiciel de caisse", "bucket": "fix"},
                ],
            },
        },
        {
            "id": f"{s}.015",
            "format": "match_pairs",
            "skill": s,
            "difficulty": 1,
            "stem": "Associe chaque indicateur à sa définition.",
            "explanation": "Des définitions à connaître par cœur.",
            "payload": {
                "pairs": [
                    {"left": "Taux de conversion", "right": "clients / visiteurs"},
                    {"left": "Panier moyen", "right": "CA / nombre de transactions"},
                    {"left": "Churn", "right": "clients perdus / clients en début de période"},
                    {"left": "Pénétration", "right": "clients / population cible"},
                ]
            },
        },
        {
            "id": f"{s}.016",
            "format": "oral_prompt",
            "skill": s,
            "difficulty": 3,
            "sector": "santé",
            "stem": "Un groupe de cliniques veut réduire ses délais d'admission. Ouvre le case à voix haute : reformule, pose une question, annonce ton plan.",
            "explanation": "Reformuler, clarifier, annoncer : trois phrases.",
            "payload": {
                "seconds": 75,
                "rubric": [
                    {
                        "key": "reformulation",
                        "label": "Objectif reformulé en une phrase",
                        "weight": 2,
                    },
                    {
                        "key": "question",
                        "label": "Une question qui change la structure",
                        "weight": 1,
                    },
                    {"key": "plan", "label": "Démarche annoncée en trois branches", "weight": 2},
                ],
                "model_answer": "Je reformule : vous voulez réduire le délai moyen d'admission, aujourd'hui de 40 %, sans ouvrir de lits. Première question : le délai est-il le même sur tous les services ? Je vois trois axes : la demande, la capacité, le processus d'admission.",
            },
        },
    ]
    return out


def write(folder: Path) -> None:
    (folder / "units").mkdir(parents=True, exist_ok=True)
    (folder / "items").mkdir(parents=True, exist_ok=True)
    (folder / "units" / "01_d1.json").write_text(json.dumps(UNIT, ensure_ascii=False, indent=1))
    (folder / "items" / "d1.json").write_text(json.dumps(items(), ensure_ascii=False, indent=1))
