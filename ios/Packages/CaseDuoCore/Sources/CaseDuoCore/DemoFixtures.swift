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
     "story_updated_at": "2026-10-28T09:12:44.512331+00:00", "created_at": "2026-10-01T08:00:00+00:00"}
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
     "is_admin": true}
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
}
