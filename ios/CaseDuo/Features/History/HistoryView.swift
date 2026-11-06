import CaseDuoCore
import Charts
import SwiftUI

/// Progress over time: the score curve per exercise type, the recurring weak points (from the
/// rubric scores), the month's streak calendar, recent corrections and mock interviews.
struct HistoryView: View {
    @Environment(AppModel.self) private var model
    @Environment(\.palette) private var palette
    @State private var history: History?
    @State private var error: String?
    @State private var selectedTypes: Set<String> = []

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    if let history {
                        content(history)
                    } else if let error {
                        ErrorBanner(message: error)
                    } else {
                        LoadingView().frame(height: 400)
                    }
                }
                .padding(16)
            }
            .background(Brand.background)
            .navigationTitle("Historique")
            .refreshable { await load() }
            .task { if history == nil { await load() } }
            .navigationDestination(for: ID.self) { AttemptDetailView(attemptId: $0) }
        }
    }

    private func load() async {
        do {
            history = try await model.service.history(days: 90)
            error = nil
        } catch {
            model.handle(error)
            self.error = error.localizedDescription
        }
    }

    @ViewBuilder
    private func content(_ history: History) -> some View {
        SectionTitle(text: "Score par type")
        ScoreChart(series: visibleSeries(history))
            .frame(height: 220)
            .padding(16)
            .card()
        TypeFilter(series: history.series, selected: $selectedTypes)

        SectionTitle(text: "Points faibles récurrents", trailing: "14 jours")
        if history.weaknesses.isEmpty {
            Text("Pas encore assez de corrections pour en tirer quelque chose.").foregroundStyle(Brand.textSecondary)
        } else {
            VStack(spacing: 12) {
                ForEach(history.weaknesses) { CriterionBar(criterion: $0, highlight: true) }
                if let criteria = history.criteria, !criteria.isEmpty {
                    Divider().overlay(Brand.stroke)
                    ForEach(criteria.filter { c in !history.weaknesses.contains { $0.key == c.key } }) {
                        CriterionBar(criterion: $0, highlight: false)
                    }
                }
            }
            .padding(16)
            .card()
        }

        SectionTitle(text: "Série")
        StreakCalendar(days: history.calendar, today: model.today?.date)
            .padding(16)
            .card()

        if let mocks = history.mocks, !mocks.isEmpty {
            SectionTitle(text: "Mocks entretien")
            VStack(spacing: 8) {
                ForEach(mocks) { mock in
                    HStack {
                        Image(systemName: "person.2.wave.2.fill").foregroundStyle(palette.accent)
                        Text(mock.kind == "fit" ? "Mock fit" : "Mock complet")
                        Text(Format.shortDay(mock.date)).foregroundStyle(Brand.textSecondary)
                        Spacer()
                        Text(mock.score.map(String.init) ?? "—").font(.headline.monospacedDigit())
                            .foregroundStyle(Brand.scoreColor(mock.score))
                    }
                    .font(.subheadline)
                }
            }
            .padding(16)
            .card()
        }

        if let recent = history.recentAttempts, !recent.isEmpty {
            SectionTitle(text: "Dernières corrections")
            VStack(spacing: 0) {
                ForEach(recent) { attempt in
                    NavigationLink(value: attempt.id) {
                        AttemptRow(attempt: attempt)
                    }
                    .buttonStyle(.plain)
                    if attempt.id != recent.last?.id { Divider().overlay(Brand.stroke) }
                }
            }
            .padding(.horizontal, 16)
            .card()
        }
    }

    private func visibleSeries(_ history: History) -> [ScoreSeries] {
        selectedTypes.isEmpty ? history.series : history.series.filter { selectedTypes.contains($0.label) }
    }
}

struct ScoreChart: View {
    let series: [ScoreSeries]

    var body: some View {
        if series.allSatisfy({ $0.points.isEmpty }) {
            Text("Ta courbe apparaîtra après quelques corrections.")
                .foregroundStyle(Brand.textSecondary)
                .frame(maxWidth: .infinity, maxHeight: .infinity)
        } else {
            Chart {
                ForEach(series) { s in
                    ForEach(s.points, id: \.self) { point in
                        LineMark(x: .value("Jour", LocalDay.date(from: point.date, in: .current) ?? Date()),
                                 y: .value("Score", point.score))
                            .foregroundStyle(by: .value("Type", s.label))
                            .interpolationMethod(.monotone)
                        PointMark(x: .value("Jour", LocalDay.date(from: point.date, in: .current) ?? Date()),
                                  y: .value("Score", point.score))
                            .foregroundStyle(by: .value("Type", s.label))
                            .symbolSize(24)
                    }
                }
                RuleMark(y: .value("Seuil revanche", 60))
                    .lineStyle(StrokeStyle(lineWidth: 1, dash: [4, 4]))
                    .foregroundStyle(Brand.textTertiary)
            }
            .chartYScale(domain: 0...100)
            .chartForegroundStyleScale(domain: series.map(\.label), range: series.map { Brand.color(for: $0.type) })
            .chartLegend(position: .bottom, alignment: .leading)
        }
    }
}

private struct TypeFilter: View {
    let series: [ScoreSeries]
    @Binding var selected: Set<String>

    var body: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                ForEach(series) { s in
                    let on = selected.isEmpty || selected.contains(s.label)
                    Button {
                        if selected.contains(s.label) { selected.remove(s.label) } else { selected.insert(s.label) }
                    } label: {
                        Chip(text: s.label, tint: on ? Brand.color(for: s.type) : Brand.textTertiary, filled: selected.contains(s.label))
                    }
                    .buttonStyle(.plain)
                }
            }
        }
    }
}

struct CriterionBar: View {
    let criterion: CriterionAverage
    let highlight: Bool

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text(criterion.label).font(highlight ? .subheadline.weight(.semibold) : .subheadline)
                Spacer()
                Text(String(format: "%.1f / 2", criterion.average)).font(.caption.monospacedDigit())
                    .foregroundStyle(Brand.textSecondary)
            }
            GeometryReader { geo in
                ZStack(alignment: .leading) {
                    Capsule().fill(Color.white.opacity(0.08))
                    Capsule().fill(color).frame(width: max(8, geo.size.width * min(1, criterion.average / 2)))
                }
            }
            .frame(height: 8)
        }
    }

    private var color: Color {
        switch criterion.average {
        case 1.5...: return Brand.success
        case 1.0..<1.5: return Brand.flame
        default: return Brand.danger
        }
    }
}

struct AttemptRow: View {
    let attempt: AttemptSummary

    var body: some View {
        HStack(spacing: 12) {
            IconCircle(symbol: attempt.type?.symbol ?? "doc.text", tint: attempt.type.map { Brand.color(for: $0) } ?? Brand.textSecondary, size: 34)
            VStack(alignment: .leading, spacing: 2) {
                Text(attempt.title ?? "Exercice").font(.subheadline.weight(.semibold)).lineLimit(2)
                Text(kindLabel).font(.caption).foregroundStyle(Brand.textSecondary)
            }
            Spacer()
            Text(attempt.score.map(String.init) ?? "—").font(.headline.monospacedDigit())
                .foregroundStyle(Brand.scoreColor(attempt.score))
        }
        .padding(.vertical, 12)
        .contentShape(Rectangle())
    }

    private var kindLabel: String {
        let type = attempt.typeLabel ?? attempt.type?.label ?? ""
        switch attempt.kind {
        case .main: return type
        case .followUp: return "\(type) · relance"
        case .retry2min: return "\(type) · refait en 2 min"
        }
    }
}

/// This month and the previous one: a flame for each day the goal was met, a snowflake when a
/// freeze covered it.
struct StreakCalendar: View {
    let days: [CalendarDay]
    let today: String?
    @State private var monthOffset = 0
    @Environment(\.palette) private var palette

    private var calendar: Calendar {
        var c = Calendar(identifier: .gregorian)
        c.firstWeekday = 2 // lundi
        c.locale = Locale(identifier: "fr_FR")
        return c
    }

    var body: some View {
        let byDay = Dictionary(days.map { ($0.date, $0) }, uniquingKeysWith: { a, _ in a })
        let month = calendar.date(byAdding: .month, value: monthOffset, to: Date()) ?? Date()
        VStack(spacing: 10) {
            HStack {
                Button { monthOffset -= 1 } label: { Image(systemName: "chevron.left") }
                    .disabled(monthOffset <= -1)
                Spacer()
                Text(month.formatted(.dateTime.month(.wide).year().locale(Locale(identifier: "fr_FR"))).capitalized)
                    .font(.headline)
                Spacer()
                Button { monthOffset += 1 } label: { Image(systemName: "chevron.right") }
                    .disabled(monthOffset >= 0)
            }
            let symbols = ["L", "M", "M", "J", "V", "S", "D"]
            HStack {
                ForEach(Array(symbols.enumerated()), id: \.offset) { _, s in
                    Text(s).font(.caption2.weight(.bold)).foregroundStyle(Brand.textTertiary).frame(maxWidth: .infinity)
                }
            }
            LazyVGrid(columns: Array(repeating: GridItem(.flexible(), spacing: 4), count: 7), spacing: 6) {
                ForEach(Array(cells(for: month).enumerated()), id: \.offset) { _, day in
                    if let day {
                        let key = LocalDay.string(for: day, in: .current)
                        let info = byDay[key]
                        ZStack {
                            if info?.goalMet == true {
                                Image(systemName: "flame.fill").foregroundStyle(palette.linear)
                            } else if info?.freezeUsed == true {
                                Image(systemName: "snowflake").foregroundStyle(Brand.freeze)
                            } else {
                                Text("\(calendar.component(.day, from: day))").font(.caption)
                                    .foregroundStyle(key == today ? palette.accent : Brand.textTertiary)
                            }
                        }
                        .frame(height: 30)
                        .frame(maxWidth: .infinity)
                        .background(key == today ? palette.accentSoft : .clear, in: RoundedRectangle(cornerRadius: 8))
                    } else {
                        Color.clear.frame(height: 30)
                    }
                }
            }
        }
    }

    /// The month's days, padded so the 1st falls under its weekday.
    private func cells(for month: Date) -> [Date?] {
        guard let interval = calendar.dateInterval(of: .month, for: month) else { return [] }
        let first = interval.start
        let weekday = calendar.component(.weekday, from: first)
        let leading = (weekday - calendar.firstWeekday + 7) % 7
        let count = calendar.range(of: .day, in: .month, for: month)?.count ?? 30
        let days = (0..<count).compactMap { calendar.date(byAdding: .day, value: $0, to: first) }
        return Array(repeating: nil, count: leading) + days
    }
}
