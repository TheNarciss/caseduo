import CaseDuoCore
import UIKit
import WidgetKit

/// Hands the widget a snapshot through the App Group, then asks WidgetKit to redraw.
enum WidgetBridge {
    private static var defaults: UserDefaults? { UserDefaults(suiteName: WidgetSnapshot.appGroup) }

    static var current: WidgetSnapshot? {
        guard let data = defaults?.data(forKey: WidgetSnapshot.defaultsKey) else { return nil }
        return WidgetSnapshot.decode(data)
    }

    static func save(_ snapshot: WidgetSnapshot) {
        guard let data = snapshot.encoded() else { return }
        defaults?.set(data, forKey: WidgetSnapshot.defaultsKey)
        WidgetCenter.shared.reloadAllTimelines()
    }

    static func update(from today: Today) {
        save(WidgetSnapshot(today: today))
    }

    /// After a graded exercise, before the next `/today`.
    static func update(from progress: GradeProgress) {
        guard var snapshot = current else { return }
        snapshot.apply(progress)
        snapshot.updatedAt = Date()
        save(snapshot)
    }

    static func clear() {
        defaults?.removeObject(forKey: WidgetSnapshot.defaultsKey)
        WidgetCenter.shared.reloadAllTimelines()
    }
}

/// Switches the app icon: 30-day streak, perfect week (which wins while it lasts), or default.
@MainActor
enum IconManager {
    static func apply(unlocks: Unlocks?, today: String) {
        guard UIApplication.shared.supportsAlternateIcons else { return }
        let wanted = AppIconChoice.choose(unlocks: unlocks, today: today)
        guard UIApplication.shared.alternateIconName != wanted else { return }
        UIApplication.shared.setAlternateIconName(wanted) { _ in }
    }
}
