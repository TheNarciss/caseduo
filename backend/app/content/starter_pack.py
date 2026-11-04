"""A day of hand-written exercises: the safety net (DEVIATIONS D11).

Inserted only when a date has nothing and Claude cannot generate (no API
key, daily cap reached, outage), and for the App Review demo account. The
figures are marked as hypotheses: no source is claimed that was not checked.
"""

from __future__ import annotations

from typing import Any

from ..catalog import criterion_label

LEVELS: dict[str, tuple[str, str, str]] = {
    "reformulation": (
        "Se lance sans reformuler ni vérifier l'objectif.",
        "Reformule, mais sans préciser le périmètre ou l'objectif chiffré.",
        "Reformule en une phrase avec l'objectif, le périmètre et une question de clarification utile.",
    ),
    "structure": (
        "Déroule sans plan annoncé.",
        "Annonce un plan, mais flou, non MECE ou abandonné en route.",
        "Annonce 3 ou 4 branches claires avant de dérouler, et s'y tient.",
    ),
    "hypotheses": (
        "Chiffres sortis de nulle part.",
        "Hypothèses posées mais calcul peu décomposé ou sans vérification.",
        "Chiffre décomposé étape par étape, hypothèses dites à voix haute, ordre de grandeur vérifié.",
    ),
    "business_sense": (
        "Raisonnement générique ou purement technique.",
        "Quelques remarques sectorielles pertinentes, sans lien avec la décision.",
        "Lit la situation comme un dirigeant du secteur : enjeux, contraintes, ce qui fait bouger la décision.",
    ),
    "recommendation": (
        "Pas de recommandation.",
        "Recommandation molle ou sans risque identifié.",
        "Recommandation en une phrase, assumée, avec le risque principal et sa parade.",
    ),
    "concrete": (
        "Récit abstrait, aucun fait.",
        "Un exemple concret mais sans résultat mesurable.",
        "Situation précise, actions personnelles, résultat chiffré.",
    ),
    "coherence": (
        "Contredit le parcours ou une réponse précédente.",
        "Cohérent mais sans fil conducteur.",
        "Chaque étape du parcours mène logiquement à la suivante et au conseil.",
    ),
    "motivation": (
        "Motivation vague ou opportuniste.",
        "Motivation plausible mais interchangeable entre cabinets.",
        "Motivation spécifique, appuyée sur des faits du parcours et sur le cabinet.",
    ),
    "concision": (
        "Plus de 3 minutes ou digressions.",
        "Un peu long, quelques détails inutiles.",
        "Moins de 2 minutes, chaque phrase sert.",
    ),
    "no_self_deprecation": (
        "Se dévalorise plusieurs fois.",
        "Une formule qui minimise son rôle.",
        "Assume ses choix et ses résultats sans se rabaisser.",
    ),
    "accuracy": (
        "Mauvaise réponse et mauvais ordre de grandeur.",
        "Bon ordre de grandeur, réponse exacte manquée.",
        "Réponse exacte ou estimation juste à ±20 %.",
    ),
    "sanity_check": (
        "Aucune vérification.",
        "Vérification mentionnée mais pas faite.",
        "Vérifie le résultat par une autre voie ou un cas limite.",
    ),
    "rigor": (
        "Erreurs techniques ou affirmations fausses.",
        "Techniquement juste mais superficiel.",
        "Précis sur les métriques, les données et les limites.",
    ),
    "tradeoffs": (
        "Une seule option, sans alternative.",
        "Alternatives citées sans critère de choix.",
        "Compare 2 ou 3 options avec des critères explicites (coût, risque, délai, qualité).",
    ),
    "vulgarisation": (
        "Jargon incompréhensible pour un partner.",
        "Compréhensible mais long.",
        "Un partner non technique comprend l'enjeu et la décision en une minute.",
    ),
}


def rubric(*items: tuple[str, int]) -> list[dict[str, Any]]:
    return [
        {
            "key": key,
            "label": criterion_label(key),
            "weight": weight,
            "levels": dict(zip(("0", "1", "2"), LEVELS[key], strict=True)),
        }
        for key, weight in items
    ]


CASE_RUBRIC = (
    ("reformulation", 15),
    ("structure", 25),
    ("hypotheses", 25),
    ("business_sense", 20),
    ("recommendation", 15),
)


def hyp(label: str, value: str) -> dict[str, Any]:
    return {"label": label, "value": value, "source_url": None, "hypothesis": True}


def exercises() -> list[tuple[str, dict[str, Any]]]:
    """(slot, fields) pairs, fields ready for an `Exercise` row."""
    return [
        (
            "starter_brainteaser",
            {
                "type": "brainteaser",
                "style": "wavestone",
                "language": "fr",
                "difficulty": 2,
                "sector": "général",
                "title": "Combien de fois les aiguilles d'une horloge se superposent-elles en 24 heures ?",
                "prompt": (
                    "On commence par un petit échauffement. Une horloge classique, deux aiguilles, "
                    "les heures et les minutes. Sur une journée complète de 24 heures, combien de fois "
                    "les deux aiguilles sont-elles exactement l'une sur l'autre ? Donne-moi le chiffre "
                    "et la façon dont tu y arrives."
                ),
                "parts": None,
                "context_data": {"facts": [], "constraints": [], "documents": []},
                "model_answer": (
                    "**Réponse : 22 fois.**\n\n"
                    "1. **Vitesses** : l'aiguille des minutes fait 360° par heure, celle des heures 30° "
                    "par heure. La grande rattrape la petite à 330° par heure.\n"
                    "2. **Intervalle** : elle doit reprendre un tour complet (360°) pour la rattraper : "
                    "360 / 330 = 12/11 h, soit environ 1 h 05 min 27 s.\n"
                    "3. **Comptage** : 24 / (12/11) = 22.\n\n"
                    "**Vérification** : sur 12 h on obtient 11, et non 12, car la superposition de "
                    "11 h 59 tombe en réalité à midi, déjà comptée."
                ),
                "rubric": rubric(
                    ("structure", 20),
                    ("hypotheses", 20),
                    ("accuracy", 30),
                    ("sanity_check", 15),
                    ("concision", 15),
                ),
                "sources": [],
                "targets_weakness": [],
                "estimated_minutes": 4,
            },
        ),
        (
            "starter_fit",
            {
                "type": "fit",
                "style": "wavestone",
                "language": "fr",
                "difficulty": 2,
                "sector": "général",
                "title": "Pourquoi le conseil, et pourquoi maintenant ?",
                "prompt": (
                    "Tu as un poste d'ingénieur data dans un grand groupe industriel, avec des projets "
                    "concrets. Qu'est-ce qui te pousse vers le conseil, et pourquoi maintenant plutôt "
                    "que dans deux ans ?"
                ),
                "parts": None,
                "context_data": {"facts": [], "constraints": [], "documents": []},
                "model_answer": (
                    "**Structure attendue (2 minutes)**\n\n"
                    "1. **Le déclic, en un fait** : un projet où tu as vu que la valeur se jouait dans le "
                    "cadrage et l'adoption, plus que dans le modèle (avec un chiffre : délai, gain, adoption).\n"
                    "2. **Ce que le conseil t'apporte** : la variété des secteurs, des problèmes posés par "
                    "des dirigeants, l'apprentissage accéléré.\n"
                    "3. **Ce que tu apportes** : ta double compétence technique et terrain (industrie, "
                    "défense, Singapour), utile dès la première mission.\n"
                    "4. **Pourquoi maintenant** : 2 à 3 ans d'expérience, assez pour être crédible face au "
                    "client, encore tôt pour changer de trajectoire.\n\n"
                    "**3 pièges à éviter**\n"
                    "- Critiquer ton employeur actuel.\n"
                    "- Parler de salaire ou de « voir du pays » en premier.\n"
                    "- Une motivation qui marcherait aussi bien pour n'importe quel métier."
                ),
                "rubric": rubric(
                    ("concrete", 25),
                    ("coherence", 20),
                    ("motivation", 25),
                    ("concision", 15),
                    ("no_self_deprecation", 15),
                ),
                "sources": [],
                "targets_weakness": [],
                "estimated_minutes": 3,
            },
        ),
        (
            "starter_market_sizing",
            {
                "type": "market_sizing",
                "style": "wavestone",
                "language": "fr",
                "difficulty": 2,
                "sector": "industrie/défense",
                "title": "Combien de passagers transitent chaque jour par l'aéroport de Changi ?",
                "prompt": (
                    "Un de nos clients, un opérateur de services au sol, veut dimensionner une offre "
                    "de traitement des bagages à Singapour. Avant toute chose, il nous demande un ordre "
                    "de grandeur : combien de passagers passent chaque jour par l'aéroport de Changi ? "
                    "Je te laisse construire l'estimation."
                ),
                "parts": None,
                "context_data": {
                    "facts": [
                        hyp(
                            "Mouvements de passagers annuels à Changi (ordre de grandeur)",
                            "≈ 65 à 70 millions",
                        ),
                        hyp("Part de passagers en correspondance", "≈ 30 %"),
                        hyp(
                            "Vols de passagers par jour",
                            "≈ 1 000 à 1 100 décollages et atterrissages",
                        ),
                        hyp("Taux de remplissage moyen", "≈ 80 %"),
                    ],
                    "constraints": ["Un mouvement = un passager qui arrive ou qui part."],
                    "documents": [],
                },
                "model_answer": (
                    "**Reformulation** : on cherche le nombre de passagers qui passent par Changi un jour "
                    "moyen, arrivées et départs, correspondances comprises.\n\n"
                    "**Approche bottom-up par les vols** :\n"
                    "1. ~1 000 mouvements d'avions passagers par jour (500 départs, 500 arrivées).\n"
                    "2. Capacité moyenne ~230 sièges (mix moyen et long-courrier) × 80 % de remplissage "
                    "≈ 185 passagers par vol.\n"
                    "3. 1 000 × 185 ≈ **185 000 mouvements de passagers par jour**.\n\n"
                    "**Vérification** : 185 000 × 365 ≈ 67 millions par an, cohérent avec l'ordre de "
                    "grandeur publié de 65 à 70 millions.\n\n"
                    "**Sensibilité** : ±10 points de remplissage déplacent le résultat de ±23 000 par jour.\n\n"
                    "**Recommandation** : dimensionner l'offre bagages sur ~180 000 passagers par jour, "
                    "avec des pointes de +20 % en période de vacances ; le risque principal est la part "
                    "de correspondances, dont les bagages ne passent pas par les mêmes circuits : à "
                    "vérifier avec l'aéroport."
                ),
                "rubric": rubric(*CASE_RUBRIC),
                "sources": [],
                "targets_weakness": [],
                "estimated_minutes": 6,
            },
        ),
        (
            "starter_cadrage",
            {
                "type": "cadrage",
                "style": "wavestone",
                "language": "fr",
                "difficulty": 3,
                "sector": "assurance",
                "title": "Cadrer l'IA générative pour la gestion des sinistres auto d'un assureur",
                "prompt": (
                    "Le directeur des opérations d'un assureur IARD de 2 000 salariés nous appelle. Ses "
                    "gestionnaires de sinistres auto passent un temps fou à lire des déclarations, des "
                    "photos et des devis de garage, et les délais de règlement se dégradent. Le comité de "
                    "direction a vu des démos d'IA générative et veut lancer un projet. Il te demande de "
                    "lui présenter, à l'oral, la note de cadrage que tu ferais. Par quoi commences-tu ?"
                ),
                "parts": None,
                "context_data": {
                    "facts": [
                        hyp("Sinistres auto traités par an", "≈ 120 000"),
                        hyp("Temps moyen de gestion d'un dossier simple", "≈ 45 minutes"),
                        hyp("Gestionnaires sinistres auto", "≈ 150 ETP"),
                        hyp("Délai moyen de règlement", "≈ 21 jours"),
                    ],
                    "constraints": [
                        "Données clients soumises au RGPD, hébergement en Europe exigé.",
                        "Budget de la première phase : 600 k€.",
                    ],
                    "documents": [],
                },
                "model_answer": (
                    "**Reformulation** : réduire le délai et le coût de gestion des sinistres auto grâce à "
                    "l'IA générative, sans dégrader la qualité ni la conformité.\n\n"
                    "**Plan en 4 temps** : objectifs et périmètre ; use cases priorisés ; prérequis et "
                    "choix de solution ; gouvernance, planning et premier livrable.\n\n"
                    "1. **Objectifs et périmètre** : les dossiers simples (bris de glace, accrochages sans "
                    "corporel), soit environ 60 % du volume ; cible : délai de 21 à 10 jours, −30 % de temps "
                    "de gestion.\n"
                    "2. **Use cases** : (a) lecture et pré-remplissage des déclarations ; (b) synthèse du "
                    "dossier pour le gestionnaire ; (c) contrôle des devis de garage. On commence par (a) "
                    "et (b), à fort volume et faible risque.\n"
                    "3. **Prérequis et build vs buy** : accès aux documents, qualité des données, "
                    "hébergement européen ; un modèle du marché via une plateforme cloud européenne plutôt "
                    "qu'un développement maison.\n"
                    "4. **Chiffrage** : 120 000 dossiers × 60 % × 45 min × 30 % ≈ 16 000 heures par an, "
                    "soit ~10 ETP ; à ~60 k€ chargés, ≈ 600 k€ par an, le budget de la phase 1 est remboursé "
                    "en un an.\n"
                    "5. **Gouvernance et risques** : comité mensuel avec métier, DSI, DPO ; le gestionnaire "
                    "valide toujours (humain dans la boucle).\n"
                    "6. **Planning** : 6 semaines de cadrage, 3 mois de pilote sur une plateforme régionale.\n\n"
                    "**Sensibilité** : à 15 % de gain au lieu de 30 %, le retour sur investissement passe à "
                    "deux ans.\n\n"
                    "**Recommandation** : lancer un pilote de 3 mois sur la lecture des déclarations ; "
                    "premier livrable à 3 mois : mesure du temps gagné sur 2 000 dossiers réels. Risque "
                    "principal : l'adoption par les gestionnaires, couverte en les associant dès le cadrage."
                ),
                "rubric": rubric(*CASE_RUBRIC),
                "sources": [],
                "targets_weakness": [],
                "estimated_minutes": 8,
            },
        ),
        (
            "starter_business_case",
            {
                "type": "business_case",
                "style": "wavestone",
                "language": "fr",
                "difficulty": 3,
                "sector": "industrie/défense",
                "title": "ROI de la maintenance prédictive sur une flotte de radars",
                "prompt": (
                    "Un industriel de défense maintient une flotte de 40 radars déployés chez un client "
                    "étatique. Chaque panne imprévue mobilise une équipe et coûte cher en pénalités "
                    "contractuelles. Le directeur du support envisage un projet de maintenance prédictive "
                    "à partir des données de télémétrie. Est-ce que ça vaut le coup ?"
                ),
                "parts": None,
                "context_data": {
                    "facts": [
                        hyp("Pannes imprévues par radar et par an", "≈ 3"),
                        hyp(
                            "Coût moyen d'une panne imprévue (intervention + pénalités)", "≈ 80 k€"
                        ),
                        hyp("Coût du projet (build)", "≈ 1,2 M€ sur 12 mois"),
                        hyp("Coût annuel de fonctionnement (run)", "≈ 250 k€"),
                    ],
                    "constraints": [
                        "Données de télémétrie classifiées : traitement sur site obligatoire."
                    ],
                    "documents": [],
                },
                "model_answer": (
                    "**Reformulation** : décider si un projet de maintenance prédictive est rentable, et "
                    "à quelles conditions.\n\n"
                    "**Plan** : coûts ; gains ; ROI et point mort ; sensibilité et recommandation.\n\n"
                    "1. **Coûts** : build 1,2 M€ ; run 250 k€ par an ; conduite du changement ~100 k€ "
                    "(formation des équipes support).\n"
                    "2. **Gains** : 40 radars × 3 pannes × 80 k€ = 9,6 M€ de coût annuel des pannes. Si le "
                    "modèle en anticipe 30 %, et qu'une panne anticipée coûte moitié moins, le gain est de "
                    "9,6 × 30 % × 50 % ≈ 1,4 M€ par an.\n"
                    "3. **ROI** : gain net ≈ 1,4 − 0,25 = 1,15 M€ par an ; point mort ≈ 1,3 M€ / 1,15 ≈ "
                    "13 à 14 mois après la mise en service.\n"
                    "4. **Sensibilité** : avec 15 % de pannes anticipées, le gain net tombe à ~0,45 M€ et "
                    "le point mort à 3 ans.\n\n"
                    "**Recommandation** : oui, mais en commençant par un pilote sur 10 radars pour mesurer "
                    "le taux d'anticipation réel avant d'engager le build complet. Risque principal : la "
                    "qualité et l'historique de la télémétrie, à auditer dans les 6 premières semaines."
                ),
                "rubric": rubric(*CASE_RUBRIC),
                "sources": [],
                "targets_weakness": [],
                "estimated_minutes": 8,
            },
        ),
        (
            "starter_diagnostic",
            {
                "type": "diagnostic",
                "style": "wavestone",
                "language": "fr",
                "difficulty": 2,
                "sector": "banque",
                "title": "Diagnostic de maturité data d'une banque régionale",
                "prompt": (
                    "Une banque régionale de 3 000 collaborateurs a recruté un Chief Data Officer il y a "
                    "six mois. Il a hérité de dizaines d'entrepôts de données, de tableaux de bord Excel "
                    "par agence et d'un comité de direction qui veut « faire de l'IA ». Il nous demande un "
                    "diagnostic rapide : où en est la banque, et par où doit-il commencer ?"
                ),
                "parts": None,
                "context_data": {
                    "facts": [
                        hyp("Sources de données recensées", "≈ 60"),
                        hyp("Tableaux de bord Excel maintenus à la main", "≈ 400"),
                        hyp("Équipe data centrale", "≈ 12 personnes"),
                    ],
                    "constraints": [
                        "Un audit réglementaire sur la qualité des données arrive dans 9 mois."
                    ],
                    "documents": [],
                },
                "model_answer": (
                    "**Reformulation** : évaluer la maturité data et IA de la banque, et proposer les "
                    "premiers chantiers.\n\n"
                    "**Plan** : maturité ; 3 constats ; par où commencer ; ce qu'on ne fait pas.\n\n"
                    "1. **Maturité** : niveau 2 sur 5 : des données abondantes mais éclatées, peu de "
                    "gouvernance, des usages surtout descriptifs.\n"
                    "2. **3 constats** : (a) pas de référentiel client unique ; (b) ~400 Excel manuels, "
                    "soit des milliers d'heures par an et un risque d'erreur ; (c) une équipe centrale de "
                    "12 personnes absorbée par le run.\n"
                    "3. **Par où commencer** : la gouvernance et la qualité des données critiques pour "
                    "l'audit réglementaire (échéance à 9 mois, risque de sanction), puis un socle de "
                    "reporting commun qui remplace les Excel les plus utilisés. Chiffrage : si chaque "
                    "Excel coûte 2 h par mois, 400 × 2 × 12 ≈ 9 600 h par an, soit ~6 ETP récupérables.\n"
                    "4. **Ce qu'on ne fait pas** : pas de projet d'IA générative vitrine avant d'avoir des "
                    "données fiables.\n\n"
                    "**Recommandation** : un programme de 9 mois centré sur la qualité des données "
                    "réglementaires, financé par la suppression progressive des Excel ; risque principal : "
                    "la résistance des agences, couverte par des sponsors régionaux."
                ),
                "rubric": rubric(*CASE_RUBRIC),
                "sources": [],
                "targets_weakness": [],
                "estimated_minutes": 7,
            },
        ),
        (
            "starter_tech_screen",
            {
                "type": "tech_screen",
                "style": "wavestone",
                "language": "en",
                "difficulty": 3,
                "sector": "général",
                "title": "How would you evaluate a RAG assistant before a firm-wide rollout?",
                "prompt": (
                    "We built a retrieval-augmented assistant that answers consultants' questions from "
                    "our internal knowledge base. Leadership wants to roll it out to 5,000 people next "
                    "quarter. How would you evaluate it before saying yes, and what would you tell the "
                    "partner sponsoring it?"
                ),
                "parts": None,
                "context_data": {"facts": [], "constraints": [], "documents": []},
                "model_answer": (
                    "**For the partner, first**: we measure whether it answers correctly, cites the "
                    "right sources and never leaks a client document to the wrong person; rollout "
                    "follows a go/no-go on those three numbers.\n\n"
                    "**Structure**: retrieval quality; answer quality; safety; operations.\n\n"
                    "1. **Retrieval**: a golden set of ~300 real questions with the expected documents; "
                    "recall@5 and MRR. Without good retrieval, nothing else matters.\n"
                    "2. **Answers**: faithfulness to the retrieved passages, correctness and citation "
                    "accuracy, scored by expert reviewers on a sample and by an LLM judge calibrated on "
                    "it for scale.\n"
                    "3. **Safety**: access control (no document outside the user's rights), refusal when "
                    "the base has no answer, prompt-injection tests.\n"
                    "4. **Operations**: latency, cost per question, monitoring and feedback loop.\n\n"
                    "**Trade-offs**: an LLM judge is cheap and fast but drifts; human review is accurate "
                    "but slow — use both. A bigger model improves answers but triples cost; fix retrieval "
                    "first.\n\n"
                    "**Recommendation**: pilot with 200 consultants for 6 weeks, go/no-go on faithfulness "
                    "above 90 % and zero access-control breach."
                ),
                "rubric": rubric(
                    ("structure", 20),
                    ("rigor", 25),
                    ("tradeoffs", 20),
                    ("vulgarisation", 20),
                    ("recommendation", 15),
                ),
                "sources": [],
                "targets_weakness": [],
                "estimated_minutes": 6,
            },
        ),
    ]
