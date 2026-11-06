import CaseDuoCore
import SwiftUI

/// « Je m'engage » on the day screen (D16). No commitment: the invitation. One running: the
/// promise day by day, with today's XP bar inside. Ended: the summary and a new start.
struct CommitmentCard: View {
    let commitment: Commitment?
    let goal: GoalInfo
    @Environment(AppModel.self) private var model
    @Environment(\.palette) private var palette
    @State private var showSheet = false

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            if let commitment, commitment.isActive {
                active(commitment)
            } else if let commitment, commitment.isEnded {
                ended(commitment)
            } else {
                invitation
            }
        }
        .padding(16)
        .card()
        .sheet(isPresented: $showSheet) {
            CommitmentSheet()
                .environment(model)
                .environment(\.palette, model.palette)
                .presentationDetents([.large])
        }
    }

    // MARK: Running

    @ViewBuilder private func active(_ c: Commitment) -> some View {
        HStack(alignment: .firstTextBaseline) {
            Label("Engagement", systemImage: "hand.raised.fill")
                .font(.subheadline.weight(.bold))
                .foregroundStyle(palette.accent)
            Spacer()
            Text("Jour \(c.dayIndex) sur \(c.days)")
                .font(.subheadline.monospacedDigit().weight(.semibold))
                .foregroundStyle(Brand.textSecondary)
        }
        Text("\(c.dailyXp) XP par jour, jusqu'au \(Format.shortDay(c.endDate))")
            .font(.headline)
        CommitmentDots(days: c.calendar)
        GoalBar(goal: goal)
        HStack(spacing: 8) {
            Chip(text: "\(c.daysHeld) tenu\(c.daysHeld > 1 ? "s" : "")", symbol: "checkmark", tint: Brand.success)
            if c.daysFrozen > 0 {
                Chip(text: "\(c.daysFrozen) freeze", symbol: "snowflake", tint: Brand.freeze)
            }
            if c.daysMissed > 0 {
                Chip(text: "\(c.daysMissed) manqué\(c.daysMissed > 1 ? "s" : "")", symbol: "xmark", tint: Brand.danger)
            } else {
                Chip(text: "Sans faute", symbol: "flame.fill", tint: palette.accent)
            }
        }
    }

    // MARK: Ended

    @ViewBuilder private func ended(_ c: Commitment) -> some View {
        HStack(alignment: .firstTextBaseline) {
            Label(c.kept == true ? "Parole tenue" : "Engagement terminé", systemImage: c.kept == true ? "rosette" : "hand.raised.fill")
                .font(.subheadline.weight(.bold))
                .foregroundStyle(c.kept == true ? Brand.success : Brand.textSecondary)
            Spacer()
            Text("\(c.daysHeld) / \(c.days) jours")
                .font(.subheadline.monospacedDigit().weight(.semibold))
        }
        Text(c.kept == true
             ? "\(c.days) jours à \(c.dailyXp) XP, sans un jour manqué. Badge « Parole tenue » gagné."
             : "\(c.daysHeld) jours tenus sur \(c.days). Le prochain se tient jusqu'au bout.")
            .font(.subheadline)
            .foregroundStyle(Brand.textSecondary)
        CommitmentDots(days: c.calendar)
        GoalBar(goal: goal)
        Button("Reprendre un engagement") { showSheet = true }
            .buttonStyle(.pill(.secondary, compact: true))
    }

    // MARK: None yet

    @ViewBuilder private var invitation: some View {
        GoalBar(goal: goal)
        HStack(alignment: .top, spacing: 12) {
            IconCircle(symbol: "hand.raised.fill", tint: palette.accent)
            VStack(alignment: .leading, spacing: 4) {
                Text("Prends un engagement").font(.headline)
                Text("Un objectif d'XP par jour, tenu 7, 14 ou 30 jours. Il ne bouge plus avant la fin.")
                    .font(.subheadline)
                    .foregroundStyle(Brand.textSecondary)
            }
        }
        Button("Je m'engage") { showSheet = true }
            .buttonStyle(.pill(.primary, compact: true))
    }
}

/// One dot per day of the promise: kept, frozen, missed, today, to come.
struct CommitmentDots: View {
    let days: [CommitmentDay]
    @Environment(\.palette) private var palette

    var body: some View {
        let columns = Array(repeating: GridItem(.flexible(), spacing: 6), count: min(15, max(7, days.count)))
        LazyVGrid(columns: columns, spacing: 6) {
            ForEach(days) { day in
                dot(day.state)
            }
        }
        .accessibilityElement()
        .accessibilityLabel("\(days.filter { $0.state == "met" || $0.state == "frozen" }.count) jours tenus sur \(days.count)")
    }

    @ViewBuilder private func dot(_ state: String) -> some View {
        switch state {
        case "met":
            Image(systemName: "flame.fill").font(.caption2).foregroundStyle(palette.linear)
                .frame(maxWidth: .infinity).frame(height: 18)
        case "frozen":
            Image(systemName: "snowflake").font(.caption2).foregroundStyle(Brand.freeze)
                .frame(maxWidth: .infinity).frame(height: 18)
        case "missed":
            Circle().stroke(Brand.danger.opacity(0.7), lineWidth: 1.5).frame(width: 9, height: 9)
                .frame(maxWidth: .infinity).frame(height: 18)
        case "today":
            PulsingDot(tint: palette.accent)
                .frame(maxWidth: .infinity).frame(height: 18)
        default:
            Circle().fill(Color.white.opacity(0.14)).frame(width: 7, height: 7)
                .frame(maxWidth: .infinity).frame(height: 18)
        }
    }
}

/// Today's dot, pulsing from the clock (no animation transaction, nothing to leak).
private struct PulsingDot: View {
    let tint: Color
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var born = Date()

    var body: some View {
        TimelineView(.animation(minimumInterval: 1.0 / 30.0, paused: reduceMotion)) { context in
            let phase = reduceMotion ? 0 : sin(context.date.timeIntervalSince(born) * 2 * .pi / 1.8)
            Circle().fill(tint).frame(width: 10, height: 10)
                .scaleEffect(1.075 + 0.175 * CGFloat(phase))
        }
    }
}

/// Picking the promise: XP per day and how long, then « Je m'engage ».
struct CommitmentSheet: View {
    @Environment(AppModel.self) private var model
    @Environment(\.palette) private var palette
    @Environment(\.dismiss) private var dismiss
    @State private var xp = 50
    @State private var days = 14
    @State private var sending = false
    @State private var error: String?

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 22) {
                    FlameMascot(mood: .idle, size: 96)
                        .frame(maxWidth: .infinity)
                    Text("Combien d'XP par jour ?").font(.headline)
                    HStack(spacing: 10) {
                        ForEach(CommitmentRequest.xpChoices, id: \.self) { choice in
                            option(selected: xp == choice, title: "\(choice) XP", subtitle: xpHint(choice)) { xp = choice }
                        }
                    }
                    Text("Pendant combien de temps ?").font(.headline)
                    HStack(spacing: 10) {
                        ForEach(CommitmentRequest.dayChoices, id: \.self) { choice in
                            option(selected: days == choice, title: "\(choice) jours", subtitle: daysHint(choice)) { days = choice }
                        }
                    }
                    Label("Une fois pris, l'objectif ne bouge plus jusqu'au dernier jour. Un freeze couvre un jour manqué, comme pour la série.",
                          systemImage: "lock.fill")
                        .font(.footnote)
                        .foregroundStyle(Brand.textSecondary)
                    if let error { ErrorBanner(message: error) }
                }
                .padding(20)
            }
            .background(Brand.background)
            .navigationTitle("Je m'engage")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) { Button("Annuler") { dismiss() } }
            }
            .safeAreaInset(edge: .bottom) {
                BottomActions {
                    Button {
                        Task { await commit() }
                    } label: {
                        if sending { ProgressView().tint(.black) } else { Text("Je m'engage : \(xp) XP par jour, \(days) jours") }
                    }
                    .buttonStyle(.pill)
                    .disabled(sending)
                }
            }
        }
        .onAppear { xp = model.me?.dailyGoalXp ?? 50 }
    }

    private func option(selected: Bool, title: String, subtitle: String, action: @escaping () -> Void) -> some View {
        Button(action: { Haptics.shared.play(.tap); action() }) {
            VStack(spacing: 4) {
                Text(title).font(.headline).foregroundStyle(selected ? Color.black : .white)
                Text(subtitle).font(.caption2).foregroundStyle(selected ? Color.black.opacity(0.7) : Brand.textSecondary)
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, 12)
            .background(selected ? palette.accent : Brand.cardRaised, in: RoundedRectangle(cornerRadius: 14, style: .continuous))
        }
        .buttonStyle(.plain)
    }

    private func xpHint(_ xp: Int) -> String {
        switch xp {
        case 30: return "tranquille"
        case 80: return "intense"
        default: return "sérieux"
        }
    }

    private func daysHint(_ days: Int) -> String {
        switch days {
        case 7: return "une semaine"
        case 30: return "un mois"
        default: return "deux semaines"
        }
    }

    private func commit() async {
        sending = true
        defer { sending = false }
        do {
            try await model.commit(CommitmentRequest(dailyXp: xp, days: days))
            dismiss()
        } catch {
            self.error = error.localizedDescription
        }
    }
}
