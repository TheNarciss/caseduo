import AppIntents
import CaseDuoCore
import SwiftUI
import WidgetKit

/// The home-screen widget, small and medium: the streak and what is left today. One of the
/// strongest retention levers: the flame is visible without opening the app.
@main
struct CaseDuoWidgetBundle: WidgetBundle {
    var body: some Widget {
        StreakWidget()
    }
}

struct StreakWidget: Widget {
    let kind = "CaseDuoStreak"

    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: StreakProvider()) { entry in
            StreakWidgetView(entry: entry)
                .containerBackground(for: .widget) { WidgetPalette.background }
                .widgetURL(URL(string: "caseduo://today"))
        }
        .configurationDisplayName("Série CaseDuo")
        .description("Ta série et les exercices qui restent aujourd'hui.")
        .supportedFamilies([.systemSmall, .systemMedium])
    }
}

// MARK: - Timeline

struct StreakEntry: TimelineEntry {
    let date: Date
    let display: WidgetDisplay?
}

struct StreakProvider: TimelineProvider {
    func placeholder(in context: Context) -> StreakEntry {
        StreakEntry(date: Date(), display: WidgetDisplay(isNewDay: false, streak: 12, status: .atRisk, remaining: 3,
                                                         xpToday: 20, goalXp: 50))
    }

    func getSnapshot(in context: Context, completion: @escaping (StreakEntry) -> Void) {
        if context.isPreview, SharedSnapshot.load() == nil {
            completion(placeholder(in: context))
            return
        }
        completion(StreakEntry(date: Date(), display: SharedSnapshot.load()?.display(at: Date())))
    }

    /// Now, then the next local midnight, when the day turns into "Nouvelle journée".
    func getTimeline(in context: Context, completion: @escaping (Timeline<StreakEntry>) -> Void) {
        let now = Date()
        guard let snapshot = SharedSnapshot.load() else {
            completion(Timeline(entries: [StreakEntry(date: now, display: nil)], policy: .after(now.addingTimeInterval(3600))))
            return
        }
        let entries = snapshot.timelineDates(from: now).map { StreakEntry(date: $0, display: snapshot.display(at: $0)) }
        completion(Timeline(entries: entries, policy: .atEnd))
    }
}

/// The snapshot the app leaves in the App Group.
enum SharedSnapshot {
    static func load() -> WidgetSnapshot? {
        guard let data = UserDefaults(suiteName: WidgetSnapshot.appGroup)?.data(forKey: WidgetSnapshot.defaultsKey) else { return nil }
        return WidgetSnapshot.decode(data)
    }

    static func save(_ snapshot: WidgetSnapshot) {
        guard let data = snapshot.encoded() else { return }
        UserDefaults(suiteName: WidgetSnapshot.appGroup)?.set(data, forKey: WidgetSnapshot.defaultsKey)
    }
}

// MARK: - Views

enum WidgetPalette {
    static let background = Color(red: 0.055, green: 0.059, blue: 0.071)
    static let flame = Color(red: 1.0, green: 0.62, blue: 0.10)
    static let flameGradient = LinearGradient(colors: [Color(red: 1.0, green: 0.82, blue: 0.35), flame,
                                                       Color(red: 1.0, green: 0.42, blue: 0.12)],
                                              startPoint: .top, endPoint: .bottom)
    static let success = Color(red: 0.17, green: 0.85, blue: 0.49)
    static let danger = Color(red: 1.0, green: 0.54, blue: 0.24)
    static let secondary = Color.white.opacity(0.62)
}

struct StreakWidgetView: View {
    let entry: StreakEntry
    @Environment(\.widgetFamily) private var family

    var body: some View {
        if let display = entry.display {
            switch family {
            case .systemMedium: medium(display)
            default: small(display)
            }
        } else {
            VStack(spacing: 6) {
                Image(systemName: "flame").font(.title).foregroundStyle(WidgetPalette.flame)
                Text("Ouvre CaseDuo pour lancer ta série").font(.caption).multilineTextAlignment(.center)
                    .foregroundStyle(WidgetPalette.secondary)
            }
        }
    }

    private func small(_ display: WidgetDisplay) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack(alignment: .firstTextBaseline, spacing: 4) {
                Image(systemName: display.status == .extendedToday ? "flame.fill" : "flame")
                    .font(.title2.weight(.bold))
                    .foregroundStyle(WidgetPalette.flameGradient)
                Text("\(display.streak)")
                    .font(.system(size: 40, weight: .heavy, design: .rounded))
                    .foregroundStyle(WidgetPalette.flameGradient)
                    .minimumScaleFactor(0.6)
            }
            Text(display.streak == 1 ? "jour de série" : "jours de série")
                .font(.caption.weight(.semibold))
                .foregroundStyle(.white)
            Spacer(minLength: 0)
            Text(display.headline)
                .font(.caption.weight(.bold))
                .foregroundStyle(color(display))
                .lineLimit(2)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .fontDesign(.rounded)
    }

    private func medium(_ display: WidgetDisplay) -> some View {
        HStack(spacing: 16) {
            small(display)
            VStack(alignment: .leading, spacing: 8) {
                Text("Objectif du jour").font(.caption.weight(.semibold)).foregroundStyle(WidgetPalette.secondary)
                Text("\(display.xpToday) / \(display.goalXp) XP").font(.headline.monospacedDigit()).foregroundStyle(.white)
                ProgressView(value: display.goalFraction)
                    .tint(display.goalFraction >= 1 ? WidgetPalette.success : WidgetPalette.flame)
                Spacer(minLength: 0)
                Button(intent: RefreshStreakIntent()) {
                    Label("Actualiser", systemImage: "arrow.clockwise")
                        .font(.caption2.weight(.semibold))
                }
                .tint(WidgetPalette.flame)
            }
        }
        .fontDesign(.rounded)
    }

    private func color(_ display: WidgetDisplay) -> Color {
        if display.isNewDay { return WidgetPalette.flame }
        switch display.status {
        case .extendedToday: return WidgetPalette.success
        case .atRisk: return WidgetPalette.danger
        default: return WidgetPalette.secondary
        }
    }
}

#if DEBUG
#Preview(as: .systemMedium) {
    StreakWidget()
} timeline: {
    StreakEntry(date: .now, display: WidgetDisplay(isNewDay: false, streak: 12, status: .atRisk, remaining: 3, xpToday: 20, goalXp: 50))
    StreakEntry(date: .now, display: WidgetDisplay(isNewDay: true, streak: 12, status: .atRisk, remaining: nil, xpToday: 0, goalXp: 50))
}
#endif
