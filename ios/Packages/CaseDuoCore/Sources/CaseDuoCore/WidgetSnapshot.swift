import Foundation

/// What the app hands the widget through the App Group after each refresh and each graded
/// exercise. The widget never needs the network to draw itself.
public struct WidgetSnapshot: Codable, Sendable, Equatable {
    public static let appGroup = "group.uk.riskybusinesses.caseduo"
    public static let defaultsKey = "widget.snapshot"

    public var date: String
    public var timezone: String
    public var streak: Int
    public var status: StreakStatus
    public var remaining: Int
    public var xpToday: Int
    public var goalXp: Int
    public var updatedAt: Date

    public init(date: String, timezone: String, streak: Int, status: StreakStatus, remaining: Int,
                xpToday: Int, goalXp: Int, updatedAt: Date) {
        self.date = date
        self.timezone = timezone
        self.streak = streak
        self.status = status
        self.remaining = remaining
        self.xpToday = xpToday
        self.goalXp = goalXp
        self.updatedAt = updatedAt
    }

    public init(today: Today, updatedAt: Date = Date()) {
        self.init(date: today.date, timezone: today.timezone ?? TimeZone.current.identifier,
                  streak: today.streak.current, status: today.streak.status,
                  remaining: today.remaining, xpToday: today.goal.xpToday,
                  goalXp: today.goal.targetXp, updatedAt: updatedAt)
    }

    public init(widget: WidgetInfo, timezone: String, updatedAt: Date = Date()) {
        self.init(date: widget.date, timezone: timezone, streak: widget.streak, status: widget.status,
                  remaining: widget.remaining, xpToday: widget.xpToday, goalXp: widget.goalXp,
                  updatedAt: updatedAt)
    }

    /// A graded exercise moves the numbers before the next `/today`.
    public mutating func apply(_ progress: GradeProgress) {
        streak = progress.streak.current
        status = progress.streak.status
        remaining = progress.remaining
        xpToday = progress.xpToday
        if let target = progress.goalTarget { goalXp = target }
    }

    /// What to draw at `now`: the snapshot's numbers on its own day, a fresh day otherwise.
    public func display(at now: Date) -> WidgetDisplay {
        let zone = userTimeZone(timezone)
        let today = LocalDay.string(for: now, in: zone)
        if today == date {
            return WidgetDisplay(isNewDay: false, streak: streak, status: status, remaining: remaining,
                                 xpToday: xpToday, goalXp: goalXp)
        }
        // A day has passed without the app opening: yesterday's goal decides what remains of the
        // streak, which only the server knows. Keep the number, mark it at risk.
        let atRisk: StreakStatus = streak > 0 ? .atRisk : .safe
        return WidgetDisplay(isNewDay: true, streak: streak, status: atRisk, remaining: nil,
                             xpToday: 0, goalXp: goalXp)
    }

    /// The widget's timeline: now, then the next local midnight.
    public func timelineDates(from now: Date) -> [Date] {
        [now, LocalDay.nextMidnight(after: now, in: userTimeZone(timezone))]
    }

    public func encoded() -> Data? { try? CaseDuoJSON.encoder.encode(self) }

    public static func decode(_ data: Data) -> WidgetSnapshot? {
        try? CaseDuoJSON.decoder.decode(WidgetSnapshot.self, from: data)
    }
}

public struct WidgetDisplay: Sendable, Equatable {
    public var isNewDay: Bool
    public var streak: Int
    public var status: StreakStatus
    /// nil on a new day: the server has not said yet.
    public var remaining: Int?
    public var xpToday: Int
    public var goalXp: Int

    public init(isNewDay: Bool, streak: Int, status: StreakStatus, remaining: Int? = nil, xpToday: Int, goalXp: Int) {
        self.isNewDay = isNewDay
        self.streak = streak
        self.status = status
        self.remaining = remaining
        self.xpToday = xpToday
        self.goalXp = goalXp
    }

    public var goalFraction: Double {
        guard goalXp > 0 else { return 0 }
        return min(1, Double(xpToday) / Double(goalXp))
    }

    public var headline: String {
        if isNewDay { return "Nouvelle journée" }
        guard let remaining else { return "" }
        switch remaining {
        case 0: return "Journée bouclée"
        case 1: return "1 exercice restant"
        default: return "\(remaining) exercices restants"
        }
    }
}
