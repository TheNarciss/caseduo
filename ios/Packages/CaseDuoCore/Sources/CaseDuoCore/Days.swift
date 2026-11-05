import Foundation

/// Calendar days as the backend writes them ("2026-11-04"), in a given time zone.
public enum LocalDay {
    public static func string(for date: Date, in timeZone: TimeZone) -> String {
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = timeZone
        let parts = calendar.dateComponents([.year, .month, .day], from: date)
        return String(format: "%04d-%02d-%02d", parts.year ?? 0, parts.month ?? 0, parts.day ?? 0)
    }

    /// The start of the day after `date`, in that time zone.
    public static func nextMidnight(after date: Date, in timeZone: TimeZone) -> Date {
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = timeZone
        let start = calendar.startOfDay(for: date)
        return calendar.date(byAdding: .day, value: 1, to: start) ?? date.addingTimeInterval(86_400)
    }

    /// `hour:minute` on the same local day as `date`.
    public static func time(_ hour: Int, _ minute: Int, sameDayAs date: Date, in timeZone: TimeZone) -> Date? {
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = timeZone
        return calendar.date(bySettingHour: hour, minute: minute, second: 0, of: date)
    }

    /// Parses "2026-11-04" as that day's local midnight.
    public static func date(from day: String, in timeZone: TimeZone) -> Date? {
        let parts = day.split(separator: "-").compactMap { Int($0) }
        guard parts.count == 3 else { return nil }
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = timeZone
        return calendar.date(from: DateComponents(year: parts[0], month: parts[1], day: parts[2]))
    }

    /// Day strings compare correctly as text: "2026-11-04" < "2026-11-10".
    public static func isOnOrAfter(_ day: String, _ other: String) -> Bool { day >= other }
}

/// The time zone the backend uses for this user, falling back to the device's.
public func userTimeZone(_ identifier: String?) -> TimeZone {
    if let identifier, let zone = TimeZone(identifier: identifier) { return zone }
    return .current
}
