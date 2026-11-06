import Foundation

/// Canned API answers, exactly as the backend writes them (docs/API.md). They feed the app's
/// `-uiDemo YES` mode (CI screenshots, previews, no network) and the tests, which check that
/// every shape of the contract decodes.
public enum DemoFixtures {
    public static let me = """
    {"id": "8d4d6a54-0000-4000-8000-000000000001", "email": "demo@riskybusinesses.uk",
     "display_name": "Clément", "is_admin": true, "timezone": "Asia/Singapore", "daily_goal_xp": 50,
     "sounds_enabled": true, "notifications_enabled": true, "streak_current": 12, "streak_longest": 17,
     "streak_freezes": 2, "xp_total": 1840, "league": "silver",
     "story_text": "ESILV, data engineer chez Thales à Rungis puis Singapour. Je vise la practice Data & IA d'un cabinet de transformation.",
     "story_updated_at": "2026-10-28T09:12:44.512331+00:00", "created_at": "2026-10-01T08:00:00+00:00",
     "commitment": {"id": "cmt-1", "daily_xp": 50, "days": 14, "start_date": "2026-11-04", "end_date": "2026-11-17",
                    "status": "active", "day_index": 5, "days_met": 4, "days_frozen": 0, "days_missed": 0,
                    "on_track": true, "kept": null, "badge_awarded": false,
                    "calendar": [{"date": "2026-11-04", "state": "met"}, {"date": "2026-11-05", "state": "met"},
                                 {"date": "2026-11-06", "state": "met"}, {"date": "2026-11-07", "state": "met"},
                                 {"date": "2026-11-08", "state": "today"}, {"date": "2026-11-09", "state": "future"},
                                 {"date": "2026-11-10", "state": "future"}, {"date": "2026-11-11", "state": "future"},
                                 {"date": "2026-11-12", "state": "future"}, {"date": "2026-11-13", "state": "future"},
                                 {"date": "2026-11-14", "state": "future"}, {"date": "2026-11-15", "state": "future"},
                                 {"date": "2026-11-16", "state": "future"}, {"date": "2026-11-17", "state": "future"}]}}
    """

    public static let today = """
    {"date": "2026-11-08", "weekday": 6, "timezone": "Asia/Singapore",
     "streak": {"current": 12, "longest": 17, "freezes": 2, "status": "at_risk",
                "freeze_used_on": ["2026-11-02"], "freeze_just_used": false},
     "goal": {"target_xp": 50, "xp_today": 20, "met": false},
     "remaining": 6, "day_complete": false, "easy_mode": false,
     "mock": {"kind": "full", "mbb": false, "language": "fr", "done": false, "run_id": null},
     "cards": [
       {"exercise_id": "ex-home", "type": "cadrage_home", "type_label": "Cadrage à domicile",
        "title": "Assureur mutualiste : feuille de route IA générative", "difficulty": 4, "language": "fr",
        "style": "wavestone", "sector": "assurance", "estimated_minutes": 90, "is_revenge": false,
        "revenge_step": null, "pinned": true, "done": false, "best_score": null, "xp_potential": 40,
        "due_label": "À rendre dimanche soir"},
       {"exercise_id": "ex-bt1", "type": "brainteaser", "type_label": "Brainteaser",
        "title": "Combien de fois les aiguilles se superposent-elles en 24 h ?", "difficulty": 2,
        "language": "fr", "style": "wavestone", "sector": null, "estimated_minutes": 4, "is_revenge": false,
        "revenge_step": null, "pinned": false, "done": true, "best_score": 85, "xp_potential": 10, "due_label": null},
       {"exercise_id": "ex-fit", "type": "fit", "type_label": "Fit",
        "title": "Pourquoi quitter un grand groupe pour le conseil ?", "difficulty": 2, "language": "fr",
        "style": "wavestone", "sector": null, "estimated_minutes": 3, "is_revenge": false, "revenge_step": null,
        "pinned": false, "done": false, "best_score": null, "xp_potential": 8, "due_label": null},
       {"exercise_id": "ex-ms", "type": "market_sizing", "type_label": "Market sizing",
        "title": "Combien de passagers transitent chaque jour par Changi ?", "difficulty": 2, "language": "fr",
        "style": "wavestone", "sector": "industrie/défense", "estimated_minutes": 6, "is_revenge": false,
        "revenge_step": null, "pinned": false, "done": false, "best_score": null, "xp_potential": 20, "due_label": null},
       {"exercise_id": "ex-cad", "type": "cadrage", "type_label": "Note de cadrage",
        "title": "Cadrer un projet de maintenance prédictive chez un motoriste", "difficulty": 3, "language": "en",
        "style": "mbb", "sector": "industrie/défense", "estimated_minutes": 10, "is_revenge": false,
        "revenge_step": null, "pinned": false, "done": false, "best_score": null, "xp_potential": 30, "due_label": null},
       {"exercise_id": "ex-bc", "type": "business_case", "type_label": "Business case",
        "title": "ROI d'un copilote IA pour 400 conseillers bancaires", "difficulty": 3, "language": "fr",
        "style": "wavestone", "sector": "banque", "estimated_minutes": 8, "is_revenge": false,
        "revenge_step": null, "pinned": false, "done": false, "best_score": null, "xp_potential": 30, "due_label": null},
       {"exercise_id": "ex-rev", "type": "diagnostic", "type_label": "Diagnostic",
        "title": "Maturité data d'un hôpital régional : par où commencer ?", "difficulty": 3, "language": "fr",
        "style": "wavestone", "sector": "santé", "estimated_minutes": 7, "is_revenge": true,
        "revenge_step": 1, "pinned": false, "done": false, "best_score": 48, "xp_potential": 36, "due_label": null}
     ],
     "unlocks": {"streak30_icon": false, "perfect_week_until": null},
     "league": {"tier": "silver", "tier_label": "Argent", "rank": 2, "size": 6, "xp_week": 240},
     "is_admin": true,
     "commitment": {"id": "cmt-1", "daily_xp": 50, "days": 14, "start_date": "2026-11-04", "end_date": "2026-11-17",
                    "status": "active", "day_index": 5, "days_met": 4, "days_frozen": 0, "days_missed": 0,
                    "on_track": true, "kept": null, "badge_awarded": false,
                    "calendar": [{"date": "2026-11-04", "state": "met"}, {"date": "2026-11-05", "state": "met"},
                                 {"date": "2026-11-06", "state": "met"}, {"date": "2026-11-07", "state": "met"},
                                 {"date": "2026-11-08", "state": "today"}, {"date": "2026-11-09", "state": "future"},
                                 {"date": "2026-11-10", "state": "future"}, {"date": "2026-11-11", "state": "future"},
                                 {"date": "2026-11-12", "state": "future"}, {"date": "2026-11-13", "state": "future"},
                                 {"date": "2026-11-14", "state": "future"}, {"date": "2026-11-15", "state": "future"},
                                 {"date": "2026-11-16", "state": "future"}, {"date": "2026-11-17", "state": "future"}]}}
    """

    public static let training = """
    {"date": "2026-11-08",
     "types": [{"type": "brainteaser", "label": "Brainteaser", "total": 3, "done": 1},
               {"type": "market_sizing", "label": "Market sizing", "total": 2, "done": 0},
               {"type": "cadrage", "label": "Note de cadrage", "total": 1, "done": 0},
               {"type": "business_case", "label": "Business case", "total": 1, "done": 1},
               {"type": "diagnostic", "label": "Diagnostic", "total": 1, "done": 0}],
     "exercises": [
       {"exercise_id": "tr-bt1", "type": "brainteaser", "type_label": "Brainteaser",
        "title": "Huit bagues et une balance à deux plateaux : trouver l'intruse en un minimum de pesées", "difficulty": 1,
        "language": "fr", "style": "wavestone", "sector": "général", "estimated_minutes": 4, "is_revenge": false,
        "revenge_step": null, "pinned": false, "done": true, "best_score": 92, "xp_potential": 5,
        "due_label": "Bonus · quand tu veux", "is_bonus": true, "date": "2026-11-06", "from_pack": true},
       {"exercise_id": "tr-bt2", "type": "brainteaser", "type_label": "Brainteaser",
        "title": "L'horloge de quai dont les aiguilles se superposent toutes les 65 minutes : avance ou retard ?", "difficulty": 5,
        "language": "fr", "style": "wavestone", "sector": "général", "estimated_minutes": 5, "is_revenge": false,
        "revenge_step": null, "pinned": false, "done": false, "best_score": null, "xp_potential": 25,
        "due_label": "Bonus · quand tu veux", "is_bonus": true, "date": "2026-11-06", "from_pack": true},
       {"exercise_id": "tr-bt3", "type": "brainteaser", "type_label": "Brainteaser",
        "title": "Combien de fois les aiguilles se superposent-elles en 24 h ?", "difficulty": 2,
        "language": "fr", "style": "wavestone", "sector": "général", "estimated_minutes": 4, "is_revenge": false,
        "revenge_step": null, "pinned": false, "done": false, "best_score": null, "xp_potential": 10,
        "due_label": "Jour passé", "is_bonus": true, "date": "2026-11-05", "from_pack": false},
       {"exercise_id": "tr-ms1", "type": "market_sizing", "type_label": "Market sizing",
        "title": "Marché des cafés en dosettes et capsules en France", "difficulty": 1,
        "language": "fr", "style": "wavestone", "sector": "retail", "estimated_minutes": 6, "is_revenge": false,
        "revenge_step": null, "pinned": false, "done": false, "best_score": null, "xp_potential": 10,
        "due_label": "Bonus · quand tu veux", "is_bonus": true, "date": "2026-11-06", "from_pack": true},
       {"exercise_id": "tr-ms2", "type": "market_sizing", "type_label": "Market sizing",
        "title": "Téléconsultation en France en 2030 : taille du marché et business plan d'une plateforme", "difficulty": 3,
        "language": "fr", "style": "mbb", "sector": "santé", "estimated_minutes": 9, "is_revenge": false,
        "revenge_step": null, "pinned": false, "done": false, "best_score": null, "xp_potential": 30,
        "due_label": "Bonus · quand tu veux", "is_bonus": true, "date": "2026-11-06", "from_pack": true},
       {"exercise_id": "tr-cad1", "type": "cadrage", "type_label": "Note de cadrage",
        "title": "Cadrer un assistant d'IA générative pour les 4 000 conseillers d'une banque régionale", "difficulty": 1,
        "language": "fr", "style": "wavestone", "sector": "banque", "estimated_minutes": 10, "is_revenge": false,
        "revenge_step": null, "pinned": false, "done": false, "best_score": null, "xp_potential": 10,
        "due_label": "Bonus · quand tu veux", "is_bonus": true, "date": "2026-11-06", "from_pack": true},
       {"exercise_id": "tr-bc1", "type": "business_case", "type_label": "Business case",
        "title": "Caisses automatiques dans 80 supermarchés : le business case tient-il face à la démarque ?", "difficulty": 2,
        "language": "fr", "style": "wavestone", "sector": "retail", "estimated_minutes": 8, "is_revenge": false,
        "revenge_step": null, "pinned": false, "done": true, "best_score": 68, "xp_potential": 20,
        "due_label": "Bonus · quand tu veux", "is_bonus": true, "date": "2026-11-06", "from_pack": true},
       {"exercise_id": "tr-dg1", "type": "diagnostic", "type_label": "Diagnostic",
        "title": "Diagnostic MBB : une chaîne régionale de supermarchés a perdu 1,4 point de marge en deux ans", "difficulty": 3,
        "language": "fr", "style": "mbb", "sector": "retail", "estimated_minutes": 10, "is_revenge": false,
        "revenge_step": null, "pinned": false, "done": false, "best_score": null, "xp_potential": 30,
        "due_label": "Bonus · quand tu veux", "is_bonus": true, "date": "2026-11-06", "from_pack": true}
     ]}
    """

    public static let exercise = """
    {"id": "ex-ms", "date": "2026-11-08", "type": "market_sizing", "type_label": "Market sizing",
     "style": "wavestone", "language": "fr", "difficulty": 2, "sector": "industrie/défense",
     "title": "Combien de passagers transitent chaque jour par Changi ?",
     "prompt": "Notre client, l'opérateur d'un grand aéroport d'Asie du Sud-Est, réfléchit à déployer une solution de vision par ordinateur pour fluidifier les contrôles. Avant de parler technologie, l'associé veut un ordre de grandeur. **Combien de passagers transitent en moyenne chaque jour par l'aéroport de Changi ?**",
     "estimated_minutes": 6, "parts": null, "context_data_available": true, "revealed": false,
     "context_data": null, "is_revenge": false, "flagged": false, "attempts": []}
    """

    public static let partsExercise = """
    {"id": "ex-cad", "date": "2026-11-08", "type": "cadrage", "type_label": "Note de cadrage",
     "style": "mbb", "language": "en", "difficulty": 3, "sector": "industrie/défense",
     "title": "Predictive maintenance for an engine maker",
     "prompt": "Our client builds aircraft engines and wants to cut unscheduled shop visits.",
     "estimated_minutes": 10,
     "parts": [{"question": "How would you structure the problem?", "data": null},
               {"question": "Shop visits cost $2.1M on average. What is the prize?", "data": "1,200 engines in service, 6% unscheduled visits a year."}],
     "context_data_available": true, "revealed": true,
     "context_data": {"facts": [{"label": "Engines in service", "value": "1,200", "source_url": null, "hypothesis": true}],
                      "constraints": ["Budget: $5M over 2 years"], "documents": []},
     "is_revenge": false, "flagged": false, "attempts": []}
    """

    public static let contextData = """
    {"context_data": {"facts": [
        {"label": "Passagers annuels à Changi (2024)", "value": "67,7 millions", "source_url": "https://www.changiairport.com", "hypothesis": false},
        {"label": "Part des passagers en transit", "value": "environ 30 %", "source_url": null, "hypothesis": true}],
      "constraints": ["Réponse attendue en ordre de grandeur, à ±20 %"], "documents": []},
     "xp_penalty": 5}
    """

    public static let attempt = """
    {"id": "att-1", "exercise_id": "ex-ms", "kind": "main", "parent_attempt_id": null,
     "answer_text": "Je reformule : on cherche le nombre moyen de passagers par jour…",
     "duration_seconds": 312, "input_mode": "voice", "score": 72,
     "rubric_scores": [
       {"key": "reformulation", "label": "Reformulation et cadrage", "weight": 15, "score": 2, "justification": "Question reformulée et périmètre posé.", "quote": "« on parle des passagers, pas des employés »"},
       {"key": "structure", "label": "Structure annoncée", "weight": 25, "score": 1, "justification": "Plan annoncé mais à moitié suivi.", "quote": "« je vois deux approches »"},
       {"key": "hypotheses", "label": "Hypothèses et chiffrage", "weight": 25, "score": 2, "justification": "Décomposition claire.", "quote": "« 365 jours, pics à +15 % »"},
       {"key": "business_sense", "label": "Sens business", "weight": 20, "score": 1, "justification": "Lien au besoin client léger.", "quote": null},
       {"key": "recommendation", "label": "Recommandation", "weight": 15, "score": 1, "justification": "Conclusion sans risque principal.", "quote": "« donc environ 185 000 »"}],
     "feedback": "### Ce qui était bien\\n- Reformulation nette.\\n### À corriger\\n- Annonce un seul angle : « Je pars du trafic annuel publié. »\\n### En 30 secondes tu aurais dû dire\\nJe pars des 68 M de passagers annuels, soit environ 185 000 par jour, avec des pics à 210 000.",
     "follow_up": "Tu as retenu 30 % de passagers en transit : comment le vérifierais-tu en deux minutes ?",
     "xp_earned": 20, "is_revenge": false, "revealed_data": false, "mock_run_id": null,
     "created_at": "2026-11-08T10:42:12.120394+08:00",
     "exercise": {"id": "ex-ms", "title": "Combien de passagers transitent chaque jour par Changi ?",
                  "type": "market_sizing", "type_label": "Market sizing", "language": "fr",
                  "model_answer": "**Reformulation.** On cherche un ordre de grandeur du nombre de passagers par jour.\\n\\n**Structure.** Je pars du trafic annuel publié…",
                  "sources": [{"url": "https://www.changiairport.com", "title": "Changi Airport Group — trafic 2024", "verified": true}],
                  "rubric": [{"key": "structure", "label": "Structure annoncée", "weight": 25, "levels": {"0": "Aucun plan", "1": "Plan partiel", "2": "Plan annoncé et suivi"}}],
                  "flagged": false}}
    """

    public static var gradeResult: String {
        """
        {"attempt": \(attempt),
         "xp": {"earned": 20, "breakdown": [{"label": "10 × difficulté 2", "xp": 20}]},
         "progress": {"xp_today": 40, "goal_target": 50, "goal_met": false, "goal_just_met": false,
                      "streak": {"current": 12, "longest": 17, "freezes": 2, "status": "at_risk", "freeze_used_on": [], "freeze_just_used": false},
                      "streak_extended": false, "freeze_earned": false, "day_complete": false,
                      "day_complete_bonus": 0, "perfect_week": false, "remaining": 5, "new_badges": []}}
        """
    }

    /// The stream as the backend writes it, line by line.
    public static var gradeStreamLines: [String] {
        let oneLineResult = gradeResult.replacingOccurrences(of: "\n", with: " ")
        return [
            "event: scores",
            #"data: {"rubric_scores": [{"key": "structure", "label": "Structure annoncée", "weight": 25, "score": 1, "justification": "Plan annoncé mais à moitié suivi.", "quote": "« je vois deux approches »"}], "score": 72}"#,
            "",
            "event: feedback",
            "data: {\"delta\": \"### Ce qui était bien\\n- Reformulation nette.\\n\"}",
            "",
            "event: feedback",
            "data: {\"delta\": \"### À corriger\\n- Annonce un seul angle.\\n\"}",
            "",
            ": keep-alive",
            "event: follow_up",
            #"data: {"text": "Comment vérifierais-tu les 30 % de transit ?"}"#,
            "",
            "event: done",
            "data: \(oneLineResult)",
            "",
        ]
    }

    public static let widget = """
    {"date": "2026-11-08", "streak": 12, "status": "at_risk", "remaining": 3, "xp_today": 20, "goal_xp": 50}
    """

    public static let daySummary = """
    {"date": "2026-11-08", "streak": {"current": 13, "longest": 17, "freezes": 2, "status": "extended_today", "freeze_used_on": [], "freeze_just_used": false},
     "xp_today": 95, "goal": {"target_xp": 50, "xp_today": 95, "met": true}, "exercises_done": 7,
     "league_tier": "silver", "league_rank": 1,
     "weakest_criterion": {"key": "structure", "label": "Structure annoncée", "average": 0.7, "count": 4},
     "line": "Point faible du jour : la structure annoncée avant le déroulé."}
    """

    public static let history = """
    {"series": [
        {"type": "market_sizing", "label": "Market sizing", "points": [{"date": "2026-11-01", "score": 55}, {"date": "2026-11-04", "score": 63}, {"date": "2026-11-07", "score": 72}]},
        {"type": "cadrage", "label": "Note de cadrage", "points": [{"date": "2026-11-02", "score": 48}, {"date": "2026-11-05", "score": 61}, {"date": "2026-11-08", "score": 66}]},
        {"type": "fit", "label": "Fit", "points": [{"date": "2026-11-03", "score": 70}, {"date": "2026-11-06", "score": 78}]}],
     "weaknesses": [{"key": "structure", "label": "Structure annoncée", "average": 0.8, "count": 6},
                    {"key": "recommendation", "label": "Recommandation", "average": 1.0, "count": 6},
                    {"key": "concision", "label": "Concision", "average": 1.1, "count": 3}],
     "criteria": [{"key": "reformulation", "label": "Reformulation et cadrage", "average": 1.6, "count": 6}],
     "calendar": [{"date": "2026-11-01", "goal_met": true, "freeze_used": false, "xp": 60},
                  {"date": "2026-11-02", "goal_met": false, "freeze_used": true, "xp": 0},
                  {"date": "2026-11-03", "goal_met": true, "freeze_used": false, "xp": 75}],
     "recent_attempts": [{"id": "att-1", "exercise_id": "ex-ms", "kind": "main", "score": 72, "xp_earned": 20,
                          "created_at": "2026-11-08T10:42:12+08:00", "title": "Combien de passagers transitent chaque jour par Changi ?",
                          "type": "market_sizing", "type_label": "Market sizing"}],
     "mocks": [{"id": "mock-1", "date": "2026-11-01", "kind": "full", "score": 61}]}
    """

    public static let league = """
    {"tier": "silver", "tier_label": "Argent", "week_start": "2026-11-02", "ends_at": "2026-11-08T23:00:00+08:00",
     "members": [{"name": "Camille", "xp": 310, "is_me": false, "rank": 1},
                 {"name": "Clément", "xp": 240, "is_me": true, "rank": 2},
                 {"name": "Wei Ling", "xp": 205, "is_me": false, "rank": 3},
                 {"name": "Hugo", "xp": 150, "is_me": false, "rank": 4},
                 {"name": "Priya", "xp": 95, "is_me": false, "rank": 5},
                 {"name": "Antoine", "xp": 40, "is_me": false, "rank": 6}],
     "promote_top": 2, "relegate_bottom": 2, "last_outcome": "promoted"}
    """

    public static let badges = """
    [{"code": "first_case", "name": "Premier case", "description": "Premier exercice noté.", "symbol": "checkmark.seal.fill", "earned_at": "2026-10-01T09:00:00+00:00"},
     {"code": "streak_10", "name": "10 jours", "description": "Dix jours d'objectif d'affilée.", "symbol": "flame.fill", "earned_at": "2026-10-30T12:00:00+00:00"},
     {"code": "perfect_week", "name": "Semaine parfaite", "description": "Sept jours sur sept, sans freeze.", "symbol": "star.circle.fill", "earned_at": null}]
    """

    public static let mockRun = """
    {"id": "mock-2", "kind": "full", "mbb": false, "language": "fr", "status": "in_progress",
     "time_limit_seconds": 1800, "started_at": "2026-11-08T09:00:00+08:00",
     "steps": [
       {"index": 0, "exercise_id": "mk-fit", "type": "fit", "title": "Parle-moi d'un échec", "prompt": "Racontez-moi un échec professionnel et ce que vous en avez tiré.", "parts": null, "context_data": null, "time_limit_seconds": 300, "follow_up_after": false},
       {"index": 1, "exercise_id": "mk-ms", "type": "market_sizing", "title": "Bornes de recharge à Paris", "prompt": "Combien de bornes de recharge publiques faudra-t-il à Paris en 2030 ?", "parts": null, "context_data": null, "time_limit_seconds": 600, "follow_up_after": true},
       {"index": 2, "exercise_id": "mk-cad", "type": "cadrage", "title": "IA générative dans une mutuelle", "prompt": "Le DG d'une mutuelle veut « faire de l'IA générative ». Cadrez la mission.", "parts": null, "context_data": null, "time_limit_seconds": 720, "follow_up_after": true}]}
    """

    public static let mockFinish = """
    {"id": "mock-2", "score": 67, "xp_earned": 140,
     "attempts": [{"id": "a1", "exercise_id": "mk-fit", "kind": "main", "score": 74, "xp_earned": 32, "created_at": "2026-11-08T09:06:00+08:00", "title": "Parle-moi d'un échec", "type": "fit", "type_label": "Fit"}],
     "previous": [{"date": "2026-11-01", "kind": "full", "score": 61}, {"date": "2026-10-25", "kind": "full", "score": 55}],
     "feedback": "### Ce qui était bien\\n- Fit concret et chiffré.\\n### À corriger\\n- Le cadrage manquait de livrable à 3 mois."}
    """

    public static let providers = #"{"apple": true}"#

    // MARK: Parcours (written by tests/showcase_path.py: one item of every format)

    public static let path = ####"""
    {"units": [{"code": "d1", "order": 1, "track": "common", "title": "Démo du Parcours", "subtitle": "Un item de chaque format.", "symbol": "sparkles", "done": 0, "total": 3, "nodes": [{"code": "d1.showcase", "kind": "lesson", "title": "Tous les formats", "objective": "Voir chaque format d'exercice une fois.", "status": "active", "best_score": null, "times": 0, "items": 20, "applied_type": null, "xp": 10}, {"code": "d1.review", "kind": "review", "title": "Révision", "objective": null, "status": "locked", "best_score": null, "times": 0, "items": 6, "applied_type": null, "xp": 10}, {"code": "d1.applied", "kind": "applied", "title": "En situation", "objective": null, "status": "locked", "best_score": null, "times": 0, "items": 10, "applied_type": "case", "xp": 0}, {"code": "d1.check", "kind": "checkpoint", "title": "Bilan", "objective": null, "status": "locked", "best_score": null, "times": 0, "items": 6, "applied_type": null, "xp": 20}, {"code": "d1.legendary", "kind": "legendary", "title": "Légendaire", "objective": null, "status": "locked", "best_score": null, "times": 0, "items": 6, "applied_type": null, "xp": 40}]}], "active_node": "d1.showcase", "done": 0, "total": 3}
    """####

    public static let pathLesson = ####"""
    {"node": {"code": "d1.showcase", "kind": "lesson", "title": "Tous les formats", "objective": "Voir chaque format d'exercice une fois."}, "items": [{"id": "d1.showcase.000", "format": "concept_card", "skill": "d1.showcase", "difficulty": 1, "lang": "fr", "sector": null, "stem": "", "media": null, "explanation": "", "payload": {"screens": [{"body": "Avant toute structure, redis la question en une phrase : **la métrique, l'horizon, la contrainte**.", "title": "Reformuler d'abord"}, {"body": "« Notre client, une banque, perd de l'argent. » → *Vous voulez retrouver une marge positive sur l'activité de détail d'ici deux ans, sans fermer d'agence.*", "title": "Exemple"}, {"body": "Une phrase, trois éléments. Si l'un manque, c'est ta première question.", "title": "À retenir"}]}}, {"id": "d1.showcase.015", "format": "match_pairs", "skill": "d1.showcase", "difficulty": 1, "lang": "fr", "sector": null, "stem": "Associe chaque indicateur à sa définition.", "media": null, "explanation": "Des définitions à connaître par cœur.", "payload": {"pairs": [{"left": "Taux de conversion", "right": "clients / visiteurs"}, {"left": "Panier moyen", "right": "CA / nombre de transactions"}, {"left": "Churn", "right": "clients perdus / clients en début de période"}, {"left": "Pénétration", "right": "clients / population cible"}]}}, {"id": "d1.showcase.003", "format": "first_question", "skill": "d1.showcase", "difficulty": 1, "lang": "fr", "sector": "banque", "stem": "Une banque veut entrer sur le crédit à la consommation en ligne. Ta première question ?", "media": null, "explanation": "Clarifier l'objectif avant toute structure.", "payload": {"correct": "a", "options": [{"id": "a", "text": "Quel objectif chiffré et quel horizon ?"}, {"id": "b", "text": "Quel fournisseur cloud utiliser ?", "why_wrong": "Trop opérationnel pour une ouverture."}, {"id": "c", "text": "Quelle est la croissance du PIB ?", "why_wrong": "Trop macro : ne cadre pas la décision."}]}}, {"id": "d1.showcase.001", "format": "choose_structure", "skill": "d1.showcase", "difficulty": 1, "lang": "fr", "sector": "banque", "stem": "Une banque de détail voit sa rentabilité reculer depuis trois ans. Quelle structure de départ ?", "media": null, "explanation": "Rentabilité = revenus − coûts ; on segmente ensuite chaque branche.", "payload": {"correct": "a", "options": [{"id": "a", "text": "Revenus (marge d'intérêt, commissions) vs coûts (réseau, IT, risque)"}, {"id": "b", "text": "Particuliers / professionnels / entreprises", "why_wrong": "Segmentation utile au 2e niveau, mais n'isole pas la cause."}, {"id": "c", "text": "Forces / faiblesses / opportunités / menaces", "why_wrong": "Grille descriptive, pas une décomposition du problème."}]}}, {"id": "d1.showcase.007", "format": "order_steps", "skill": "d1.showcase", "difficulty": 2, "lang": "fr", "sector": null, "stem": "Remets les étapes d'un market sizing dans l'ordre (une tuile est de trop).", "media": null, "explanation": "Clarifier, structurer, estimer, vérifier, conclure.", "payload": {"tiles": [{"id": "t1", "text": "Clarifier l'unité et le périmètre"}, {"id": "t2", "text": "Choisir top-down ou bottom-up"}, {"id": "t3", "text": "Poser les hypothèses et calculer"}, {"id": "t4", "text": "Vérifier l'ordre de grandeur"}, {"id": "t5", "text": "Conclure et nommer la sensibilité"}, {"id": "t6", "text": "Demander la réponse à l'interviewer"}], "solution": ["t1", "t2", "t3", "t4", "t5"], "distractors": ["t6"]}}, {"id": "d1.showcase.011", "format": "estimate_range", "skill": "d1.showcase", "difficulty": 2, "lang": "fr", "sector": "santé", "stem": "Combien de passages aux urgences en France par an ?", "media": null, "explanation": "Une référence : environ un passage pour trois habitants.", "payload": {"unit": "passages/an", "range": [18000000, 26000000], "scale": "log", "slider": [1000000, 100000000], "reference": "68 M d'habitants × ~0,3 passage par an ≈ 21 M."}}, {"id": "d1.showcase.004", "format": "tree_complete", "skill": "d1.showcase", "difficulty": 2, "lang": "fr", "sector": "énergie", "stem": "Complète l'arbre.", "media": {"root": "Réduire la facture énergétique", "rows": null, "type": "tree", "unit": null, "title": null, "header": null, "series": null, "children": ["Volume consommé → ?", "Prix unitaire → contrat, autoproduction"], "categories": null}, "explanation": "Sous « volume », on cherche ce qui réduit les kWh, pas le prix.", "payload": {"correct": "a", "options": [{"id": "a", "text": "Efficacité des équipements"}, {"id": "b", "text": "Taux de change", "why_wrong": "Sans lien avec les kWh consommés."}, {"id": "c", "text": "Marge du fournisseur", "why_wrong": "C'est le prix, pas le volume."}]}}, {"id": "d1.showcase.002", "format": "pick_so_what", "skill": "d1.showcase", "difficulty": 2, "lang": "fr", "sector": "tech", "stem": "Adoption d'un assistant IA par direction, et budget de formation. Le so-what ?", "media": {"root": null, "rows": null, "type": "bar", "unit": null, "title": "Adoption et budget", "header": null, "series": [{"name": "Adoption (%)", "values": [65, 20, 70, 25]}, {"name": "Budget (k€)", "values": [80, 75, 20, 25]}], "children": null, "categories": ["Finance", "RH", "Ventes", "Ops"]}, "explanation": "Chercher ce qui contredit l'hypothèse évidente, c'est le so-what.", "payload": {"correct": "a", "options": [{"id": "a", "text": "Le budget n'explique pas l'adoption : Ventes atteint 70 % avec le plus petit"}, {"id": "b", "text": "Finance a le plus gros budget, donc la meilleure adoption", "why_wrong": "Ventes fait mieux avec quatre fois moins."}, {"id": "c", "text": "Il faut augmenter le budget RH", "why_wrong": "Une recommandation sans cause identifiée."}]}}, {"id": "d1.showcase.006", "format": "spot_error", "skill": "d1.showcase", "difficulty": 2, "lang": "fr", "sector": "énergie", "stem": "Touche la ligne fautive.", "media": null, "explanation": "Toujours re-diviser le total par la bonne base.", "payload": {"fix": "8,8 M€ ÷ 50 MW ≈ 0,18 M€ par MW.", "lines": [{"id": "l1", "text": "Parc de 50 MW × 8 760 h = 438 GWh à pleine puissance"}, {"id": "l2", "text": "Facteur de charge 25 % → 110 GWh produits"}, {"id": "l3", "text": "À 80 €/MWh, chiffre d'affaires ≈ 8,8 M€"}, {"id": "l4", "text": "Donc chaque MW rapporte ≈ 0,8 M€ par an"}], "wrong_line": "l4"}}, {"id": "d1.showcase.010", "format": "mental_math", "skill": "d1.showcase", "difficulty": 2, "lang": "fr", "sector": "assurance", "stem": "", "media": null, "explanation": "Arrondis d'abord, garde les zéros, corrige à la fin.", "payload": {"seconds": 60, "questions": [{"id": "q1", "hint": "2,4 × 480 ≈ 1 150 M€ ; × 0,7 ≈ 805", "stem": "2,4 M de contrats, prime moyenne 480 €, ratio sinistres/primes 72 %. Sinistres annuels ?", "unit": "€", "answer": 829440000, "computation": "2.4e6*480*0.72", "tolerance_pct": 3}, {"id": "q2", "hint": "36 k × 300 jours", "stem": "Un magasin fait 36 000 € par jour, 6 jours sur 7, 50 semaines. CA annuel ?", "unit": "€", "answer": 10800000, "computation": "36000*6*50", "tolerance_pct": 3}]}}, {"id": "d1.showcase.008", "format": "synth_order", "skill": "d1.showcase", "difficulty": 2, "lang": "fr", "sector": "retail", "stem": "Ordonne la synthèse de 30 secondes (une tuile n'a pas sa place).", "media": null, "explanation": "Réponse d'abord, preuves, risque, prochaine étape ; le contexte n'a pas sa place.", "payload": {"tiles": [{"id": "t1", "text": "Recommandation : lancer le programme dès T2"}, {"id": "t2", "text": "Raison 1 : +3 pts de fréquence d'achat en pilote"}, {"id": "t3", "text": "Raison 2 : coût d'acquisition −20 %"}, {"id": "t4", "text": "Risque : cannibalisation des promos papier"}, {"id": "t5", "text": "Prochaine étape : étendre à 50 magasins"}, {"id": "t6", "text": "Contexte : le retail est très concurrentiel"}], "solution": ["t1", "t2", "t3", "t4", "t5"], "distractors": ["t6"]}}, {"id": "d1.showcase.005", "format": "swipe_valid", "skill": "d1.showcase", "difficulty": 2, "lang": "fr", "sector": null, "stem": "MECE ou pas ? Glisse à droite si le découpage tient.", "media": null, "explanation": "Pas de chevauchement, pas de trou, une seule dimension par niveau.", "payload": {"cards": [{"id": "c1", "text": "Coûts fixes / coûts variables", "valid": true, "reason": "Disjoints et complets."}, {"id": "c2", "text": "Coûts / coûts fournisseurs", "valid": false, "reason": "Les coûts fournisseurs sont déjà dans les coûts."}, {"id": "c3", "text": "Clients particuliers / clients en ligne", "valid": false, "reason": "Deux dimensions mélangées : type et canal."}, {"id": "c4", "text": "Prix × volume", "valid": true, "reason": "Le chiffre d'affaires, exactement."}], "pass_ratio": 0.75}}, {"id": "d1.showcase.014", "format": "mece_sort", "skill": "d1.showcase", "difficulty": 2, "lang": "fr", "sector": "retail", "stem": "Range chaque poste dans le bon panier.", "media": null, "explanation": "Variable = proportionnel au volume vendu.", "payload": {"items": [{"id": "i1", "text": "Loyers", "bucket": "fix"}, {"id": "i2", "text": "Assurance du magasin", "bucket": "fix"}, {"id": "i3", "text": "Marchandises vendues", "bucket": "var"}, {"id": "i4", "text": "Livraison par commande", "bucket": "var"}, {"id": "i5", "text": "Emballages", "bucket": "var"}, {"id": "i6", "text": "Abonnement logiciel de caisse", "bucket": "fix"}], "buckets": [{"id": "fix", "label": "Coûts fixes"}, {"id": "var", "label": "Coûts variables"}]}}, {"id": "d1.showcase.009", "format": "headline_tiles", "skill": "d1.showcase", "difficulty": 3, "lang": "fr", "sector": "secteur public", "stem": "Reconstruis le titre-message avec les tuiles (deux sont des intrus).", "media": null, "explanation": "Un titre = constat chiffré + cause ; pas de « on observe ».", "payload": {"tiles": [{"id": "w1", "text": "Le délai de traitement"}, {"id": "w2", "text": "a doublé"}, {"id": "w3", "text": "depuis 2022,"}, {"id": "w4", "text": "surtout"}, {"id": "w5", "text": "à cause des saisies manuelles"}, {"id": "w6", "text": "on observe que"}, {"id": "w7", "text": "ce qui est intéressant"}], "solution": ["w1", "w2", "w3", "w4", "w5"], "distractors": ["w6", "w7"]}}, {"id": "d1.showcase.012", "format": "two_step_calc", "skill": "d1.showcase", "difficulty": 3, "lang": "fr", "sector": "retail", "stem": "Coûts fixes 600 k€, prix 50 €, coût variable 30 €. Combien d'unités pour être à l'équilibre ?", "media": null, "explanation": "Le seuil se calcule sur la marge unitaire, jamais sur le prix.", "payload": {"unit": "unités", "answer": 30000, "formulas": [{"id": "a", "text": "Coûts fixes ÷ (prix − coût variable)"}, {"id": "b", "text": "Coûts fixes ÷ prix", "why_wrong": "Le prix n'est pas la marge."}, {"id": "c", "text": "Coûts fixes × marge", "why_wrong": "On cherche des unités : on divise."}], "computation": "600000/(50-30)", "tolerance_pct": 3, "correct_formula": "a"}}, {"id": "d1.showcase.013", "format": "fill_blank", "skill": "d1.showcase", "difficulty": 1, "lang": "fr", "sector": null, "stem": "Complète la règle.", "media": null, "explanation": "Seuil = coûts fixes ÷ marge sur coût variable unitaire.", "payload": {"text": "Le seuil de rentabilité se calcule en divisant les coûts {{1}} par la marge {{2}}.", "slots": [{"id": 1, "correct": 0, "options": ["fixes", "variables", "totaux"]}, {"id": 2, "correct": 1, "options": ["brute", "sur coût variable", "nette"]}]}}, {"id": "d1.showcase.016", "format": "oral_prompt", "skill": "d1.showcase", "difficulty": 3, "lang": "fr", "sector": "santé", "stem": "Un groupe de cliniques veut réduire ses délais d'admission. Ouvre le case à voix haute : reformule, pose une question, annonce ton plan.", "media": null, "explanation": "Reformuler, clarifier, annoncer : trois phrases.", "payload": {"rubric": [{"key": "reformulation", "label": "Objectif reformulé en une phrase", "weight": 2}, {"key": "question", "label": "Une question qui change la structure", "weight": 1}, {"key": "plan", "label": "Démarche annoncée en trois branches", "weight": 2}], "seconds": 75, "model_answer": "Je reformule : vous voulez réduire le délai moyen d'admission, aujourd'hui de 40 %, sans ouvrir de lits. Première question : le délai est-il le même sur tous les services ? Je vois trois axes : la demande, la capacité, le processus d'admission."}}], "xp": 10, "perfect_bonus": 5, "pass_score": null}
    """####

    public static let pathComplete = ####"""
    {"node": "d1.showcase", "passed": true, "score": 81, "xp": 10, "replay": false, "oral": [{"item_id": "d1.showcase.016", "score": 100, "feedback": "### Ce qui était bien\n- Plan clair.\n### À corriger\n- Chiffre → « je pose 30 % »\n### En 30 secondes tu aurais dû dire\n« Je recommande… »", "criteria": [{"key": "reformulation", "label": "Objectif reformulé en une phrase", "weight": 2, "score": 2, "justification": "Une phrase."}, {"key": "question", "label": "Une question qui change la structure", "weight": 1, "score": 2, "justification": "Une phrase."}, {"key": "plan", "label": "Démarche annoncée en trois branches", "weight": 2, "score": 2, "justification": "Une phrase."}]}], "progress": {"xp_today": 55, "goal_target": 30, "goal_met": true, "goal_just_met": false, "streak": {"current": 1, "longest": 1, "freezes": 2, "status": "extended_today", "freeze_used_on": [], "freeze_just_used": false}, "streak_extended": false, "freeze_earned": false, "day_complete": false, "day_complete_bonus": 0, "perfect_week": false, "remaining": 5, "new_badges": []}, "next_node": "d1.review", "unit_done": false}
    """####
}
