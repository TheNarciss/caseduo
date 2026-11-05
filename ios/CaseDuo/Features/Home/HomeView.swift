import CaseDuoCore
import SwiftUI

/// The day: the streak first and big, the XP goal, then the cards in the server's order
/// (Sunday's mock on top, Friday's cadrage à domicile pinned, warm-up brainteaser, fit, cases by
/// difficulty, revenges at the bottom).
struct HomeView: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        @Bindable var model = model
        NavigationStack(path: $model.homePath) {
            Group {
                if let today = model.today {
                    content(today)
                } else if let error = model.errorMessage {
                    VStack(spacing: 16) {
                        ErrorBanner(message: error)
                        Button("Réessayer") { Task { await model.refreshToday() } }.buttonStyle(.pill(.secondary, compact: true))
                    }
                    .padding(24)
                } else {
                    LoadingView(message: "Préparation de ta journée…")
                }
            }
            .background(Brand.background)
            .navigationDestination(for: HomeRoute.self) { route in
                switch route {
                case .exercise(let id, let revenge):
                    ExerciseView(exerciseId: id, isRevenge: revenge)
                case .result(let session):
                    ResultView(session: session)
                case .attempt(let id):
                    AttemptDetailView(attemptId: id)
                case .dayClose:
                    DayCloseView()
                }
            }
            .fullScreenCover(isPresented: $model.showMock) {
                if let mock = model.today?.mock {
                    MockView(kind: mock.kind, mbb: mock.mbb ?? false)
                        .environment(model)
                        .environment(\.palette, model.palette)
                }
            }
        }
    }

    private func content(_ today: Today) -> some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                StreakHeader(today: today)
                GoalBar(goal: today.goal)
                    .padding(16)
                    .card()

                if let error = model.errorMessage {
                    ErrorBanner(message: error) { model.errorMessage = nil }
                }

                if let mock = today.mock {
                    MockCard(mock: mock) { model.showMock = true }
                }

                if today.easyMode == true {
                    Label("Première semaine : difficulté plafonnée, un case et un brainteaser suffisent.",
                          systemImage: "leaf.fill")
                        .font(.footnote)
                        .foregroundStyle(Brand.success)
                }

                ForEach(today.cards) { card in
                    NavigationLink(value: HomeRoute.exercise(id: card.exerciseId, revenge: card.isRevenge)) {
                        ExerciseCardView(card: card)
                    }
                    .buttonStyle(.plain)
                }

                if today.cards.isEmpty {
                    Text("Les exercices du jour arrivent. Tire vers le bas pour actualiser.")
                        .foregroundStyle(Brand.textSecondary)
                        .padding(.vertical, 30)
                        .frame(maxWidth: .infinity)
                }
            }
            .padding(.horizontal, 16)
            .padding(.bottom, 24)
        }
        .refreshable { await model.refreshToday() }
        .safeAreaInset(edge: .bottom) {
            if today.goal.met || today.dayComplete {
                BottomActions {
                    NavigationLink(value: HomeRoute.dayClose) {
                        Text(today.dayComplete ? "Clôturer la journée" : "Voir le bilan du jour")
                    }
                    .buttonStyle(.pill(today.dayComplete ? .success : .secondary))
                }
            } else if let next = today.cards.first(where: { !$0.done && $0.type != .cadrageHome }) {
                BottomActions {
                    NavigationLink(value: HomeRoute.exercise(id: next.exerciseId, revenge: next.isRevenge)) {
                        Text("Continuer : \(next.displayType)")
                    }
                    .buttonStyle(.pill)
                }
            }
        }
        .navigationTitle("")
        .toolbar(.hidden, for: .navigationBar)
    }
}

/// The streak, the centre of the app.
struct StreakHeader: View {
    let today: Today
    @Environment(\.palette) private var palette

    var body: some View {
        HStack(alignment: .center, spacing: 14) {
            FlameView(streak: today.streak.current, lit: today.streak.status == .extendedToday, size: 76)
            VStack(alignment: .leading, spacing: 4) {
                Text("\(today.streak.current)")
                    .font(.system(size: 52, weight: .heavy, design: .rounded))
                    .monospacedDigit()
                    .contentTransition(.numericText())
                    .foregroundStyle(palette.linear)
                Text(today.streak.current == 1 ? "jour de série" : "jours de série")
                    .font(.headline)
                HStack(spacing: 8) {
                    statusChip
                    Chip(text: "\(today.streak.freezes)", symbol: "snowflake", tint: Brand.freeze)
                        .accessibilityLabel("\(today.streak.freezes) freezes en réserve")
                    if palette.isPerfectWeek {
                        Chip(text: "Semaine parfaite", symbol: "star.fill", tint: palette.accent)
                    }
                }
            }
            Spacer(minLength: 0)
        }
        .padding(.top, 12)
        .animation(Brand.spring, value: today.streak.current)
    }

    @ViewBuilder private var statusChip: some View {
        switch today.streak.status {
        case .extendedToday:
            Chip(text: "Sauvée aujourd'hui", symbol: "checkmark", tint: Brand.success)
        case .atRisk:
            Chip(text: "En danger", symbol: "exclamationmark.triangle.fill", tint: Brand.danger)
        default:
            Chip(text: "Lance-toi", symbol: "sparkles", tint: palette.accent)
        }
    }
}

/// One exercise of the day.
struct ExerciseCardView: View {
    let card: ExerciseCard
    @Environment(\.palette) private var palette

    var body: some View {
        HStack(alignment: .top, spacing: 14) {
            IconCircle(symbol: card.done ? "checkmark" : card.type.symbol,
                       tint: card.done ? Brand.success : (card.isRevenge ? Brand.revenge : palette.accent))
            VStack(alignment: .leading, spacing: 6) {
                HStack(spacing: 6) {
                    Text(card.displayType.uppercased())
                        .font(.caption.weight(.bold))
                        .foregroundStyle(Brand.textSecondary)
                    if card.isRevenge { Chip(text: "Revanche ×1,2", symbol: "arrow.uturn.backward", tint: Brand.revenge) }
                    if card.pinned == true { Chip(text: "Épinglé", symbol: "pin.fill", tint: palette.accent) }
                }
                Text(card.title)
                    .font(.headline)
                    .multilineTextAlignment(.leading)
                    .foregroundStyle(card.done ? Brand.textSecondary : .white)
                HStack(spacing: 8) {
                    DifficultyDots(level: card.difficulty, tint: palette.accent)
                    ExerciseTags(language: card.language, style: card.style, minutes: card.estimatedMinutes)
                }
                if let due = card.dueLabel {
                    Label(due, systemImage: "calendar").font(.caption).foregroundStyle(Brand.danger)
                }
            }
            Spacer(minLength: 0)
            VStack(alignment: .trailing, spacing: 4) {
                if let score = card.bestScore, card.done || card.isRevenge {
                    Text("\(score)").font(.title3.weight(.heavy)).monospacedDigit().foregroundStyle(Brand.scoreColor(score))
                }
                if let xp = card.xpPotential, !card.done {
                    Text("+\(xp)").font(.caption.weight(.bold)).foregroundStyle(palette.accent)
                }
            }
        }
        .padding(16)
        .card(fill: card.pinned == true ? Brand.cardRaised : Brand.card)
        .opacity(card.done ? 0.75 : 1)
        .accessibilityElement(children: .combine)
    }
}

/// Sunday (and every other Saturday): the mock interview, first.
struct MockCard: View {
    let mock: MockInfo
    let open: () -> Void
    @Environment(\.palette) private var palette

    var body: some View {
        Button(action: open) {
            HStack(spacing: 14) {
                IconCircle(symbol: mock.done ? "checkmark" : "person.2.wave.2.fill", tint: mock.done ? Brand.success : palette.accent, size: 48)
                VStack(alignment: .leading, spacing: 4) {
                    Text(mock.kind == "fit" ? "Mock fit complet" : "Mock entretien")
                        .font(.title3.weight(.bold))
                    Text(subtitle).font(.subheadline).foregroundStyle(Brand.textSecondary)
                    HStack(spacing: 6) {
                        Chip(text: "XP ×2", tint: palette.accent)
                        if mock.mbb == true { Chip(text: "Format MBB", tint: Brand.mbb) }
                        if let lang = mock.language { Chip(text: Format.languageTag(lang)) }
                    }
                }
                Spacer(minLength: 0)
                Image(systemName: "chevron.right").foregroundStyle(Brand.textTertiary)
            }
            .padding(16)
            .card(fill: palette.accentSoft)
        }
        .buttonStyle(.plain)
        .disabled(mock.done)
    }

    private var subtitle: String {
        if mock.done { return "Fait. Le bilan est dans l'historique." }
        if mock.kind == "fit" { return "6 questions enchaînées, 15 min, à l'oral." }
        return mock.mbb == true ? "PEI, case mené par l'interviewer, synthèse : 30 min à l'oral." : "Fit, market sizing, cadrage et deux relances : 30 min à l'oral."
    }
}
