import Foundation

/// The local streak-saver notification, used only when push cannot do the job (no APNs token
/// registered with the server, or the phone was offline at the last call). The server sends the
/// real one at 20:00 local; this is the same message, scheduled by the phone itself.
public enum StreakSaverPlan {
    public static let hour = 20
    public static let identifier = "caseduo.streak-saver"

    /// When to fire, or nil when nothing should be scheduled.
    public static func fireDate(today: Today?, pushUsable: Bool, now: Date, timeZone: TimeZone) -> Date? {
        guard !pushUsable, let today else { return nil }
        guard !today.goal.met, today.streak.current > 0 else { return nil }
        guard today.date == LocalDay.string(for: now, in: timeZone) else { return nil }
        guard let fire = LocalDay.time(hour, 0, sameDayAs: now, in: timeZone), fire > now else { return nil }
        return fire
    }

    public static func title() -> String { "Ta série est en jeu" }

    public static func body(streak: Int) -> String {
        let days = streak == 1 ? "1 jour" : "\(streak) jours"
        return "Ta série de \(days) se termine dans 4 h"
    }
}

/// Which app icon to show. Nil is the default icon.
public enum AppIconChoice {
    public static let streak30 = "AppIconStreak30"
    public static let perfectWeek = "AppIconPerfectWeek"

    /// The perfect-week icon wins while the week's reward lasts, then the 30-day icon if earned.
    public static func choose(unlocks: Unlocks?, today: String) -> String? {
        guard let unlocks else { return nil }
        if let until = unlocks.perfectWeekUntil, until >= today { return perfectWeek }
        if unlocks.streak30Icon { return streak30 }
        return nil
    }

    public static func perfectWeekActive(unlocks: Unlocks?, today: String) -> Bool {
        guard let until = unlocks?.perfectWeekUntil else { return false }
        return until >= today
    }
}
