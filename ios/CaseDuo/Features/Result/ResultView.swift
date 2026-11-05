import CaseDuoCore
import SwiftUI

/// The correction: score (animated, with its haptic), the rubric, the three feedback sections as
/// they are written, the model answer, then the two ways to train what gets you caught in a real
/// interview: answering the follow-up (90 s) and redoing it orally in 2 minutes.
struct ResultView: View {
    let session: GradingSession
    @Environment(AppModel.self) private var model
    @State private var followUpMode: FollowUpMode?

    var body: some View {
        VStack(spacing: 0) {
            ScrollView {
                VStack(alignment: .leading, spacing: 18) {
                    ResultContent(
                        title: session.title,
                        typeLabel: session.type.label,
                        score: session.score,
                        rubric: session.state.rubricScores,
                        feedback: session.state.feedback,
                        followUp: session.followUp,
                        attempt: session.attempt,
                        xp: session.result?.xp,
                        progress: session.result?.progress,
                        grading: session.phase == .grading,
                        isRevenge: session.isRevenge
                    )
                    if case .failed(let message) = session.phase {
                        ErrorBanner(message: message)
                    }
                    if model.isAdmin, let attempt = session.attempt {
                        FlagButton(exerciseId: attempt.exerciseId, flagged: attempt.exercise?.flagged ?? false)
                    }
                }
                .padding(16)
            }
            if session.phase == .done {
                BottomActions {
                    if session.request.kind == .main, session.request.mockRunId == nil, let attempt = session.attempt {
                        if let question = session.followUp, !question.isEmpty {
                            Button("Répondre à la relance") {
                                followUpMode = .followUp(question: question, parentId: attempt.id)
                            }
                            .buttonStyle(.pill)
                        }
                        HStack(spacing: 10) {
                            Button("Refaire en 2 min à l'oral") {
                                followUpMode = .retry(parentId: attempt.id)
                            }
                            .buttonStyle(.pill(.secondary))
                            Button("Journée") { model.homePath = [] }
                                .buttonStyle(.pill(.secondary, compact: true))
                        }
                    } else {
                        Button("Retour à la journée") { model.homePath = [] }.buttonStyle(.pill)
                    }
                }
            }
        }
        .background(Brand.background)
        .navigationTitle("Correction")
        .navigationBarTitleDisplayMode(.inline)
        .navigationBarBackButtonHidden(session.phase == .grading)
        .sheet(item: $followUpMode) { mode in
            FollowUpView(mode: mode, exerciseId: session.request.exerciseId, title: session.title,
                         type: session.type, language: session.language)
                .environment(model)
                .environment(\.palette, model.palette)
                .interactiveDismissDisabled()
        }
    }
}

/// What a correction shows, whether it is streaming or read back from the history.
struct ResultContent: View {
    let title: String
    let typeLabel: String
    let score: Int?
    let rubric: [RubricScore]
    let feedback: String
    let followUp: String?
    let attempt: Attempt?
    let xp: XPInfo?
    let progress: GradeProgress?
    var grading = false
    var isRevenge = false
    var compact = false

    @Environment(\.palette) private var palette

    var body: some View {
        VStack(alignment: .leading, spacing: 18) {
            VStack(alignment: .leading, spacing: 6) {
                Text(typeLabel.uppercased()).font(.caption.weight(.bold)).foregroundStyle(Brand.textSecondary)
                Text(title).font(.title3.weight(.bold))
            }

            HStack(alignment: .center, spacing: 18) {
                ScoreRing(score: score)
                VStack(alignment: .leading, spacing: 6) {
                    if let xp {
                        Text(Format.xp(xp.earned, signed: true))
                            .font(.title2.weight(.heavy))
                            .foregroundStyle(palette.accent)
                        ForEach(xp.breakdown ?? [], id: \.self) { line in
                            Text("\(line.label) : \(line.xp >= 0 ? "+" : "")\(line.xp)")
                                .font(.caption).foregroundStyle(Brand.textSecondary)
                        }
                    } else if grading {
                        Text(score == nil ? "L'interviewer relit ta réponse…" : "Il écrit son retour…")
                            .font(.subheadline).foregroundStyle(Brand.textSecondary)
                        ProgressView().tint(palette.accent)
                    }
                    if isRevenge { Chip(text: "Revanche ×1,2", symbol: "arrow.uturn.backward", tint: Brand.revenge) }
                }
                Spacer(minLength: 0)
            }

            if let progress { ProgressLine(progress: progress) }

            if !rubric.isEmpty {
                VStack(alignment: .leading, spacing: 12) {
                    ForEach(rubric) { RubricRow(score: $0) }
                }
                .padding(16)
                .card()
            }

            let sections = FeedbackSection.parse(feedback)
            ForEach(sections) { section in
                FeedbackCard(section: section)
            }

            if let followUp, !followUp.isEmpty, !compact {
                VStack(alignment: .leading, spacing: 6) {
                    Label("La relance de l'interviewer", systemImage: "bubble.left.and.exclamationmark.bubble.right.fill")
                        .font(.subheadline.weight(.bold))
                        .foregroundStyle(palette.accent)
                    Text(followUp).font(.body.italic())
                }
                .padding(16)
                .card(fill: palette.accentSoft)
            }

            if let exercise = attempt?.exercise, !compact {
                if let answer = exercise.modelAnswer, !answer.isEmpty {
                    DisclosureGroup {
                        MarkdownText(markdown: answer, font: .subheadline).padding(.top, 8)
                    } label: {
                        Label("Le corrigé", systemImage: "doc.text.magnifyingglass").font(.headline)
                    }
                    .padding(16)
                    .card()
                }
                if let sources = exercise.sources, !sources.isEmpty {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Sources").font(.headline)
                        ForEach(sources, id: \.self) { source in
                            if let url = URL(string: source.url) {
                                Link(destination: url) {
                                    HStack(spacing: 6) {
                                        Image(systemName: source.verified == false ? "questionmark.circle" : "link")
                                        Text(source.title ?? source.url).lineLimit(2).multilineTextAlignment(.leading)
                                    }
                                    .font(.subheadline)
                                }
                            }
                        }
                    }
                    .padding(16)
                    .card()
                }
            }
        }
    }
}

/// The score, counting up when it arrives.
struct ScoreRing: View {
    let score: Int?
    @State private var shown = 0
    @Environment(\.palette) private var palette

    var body: some View {
        ZStack {
            Circle().stroke(Color.white.opacity(0.08), lineWidth: 10)
            Circle()
                .trim(from: 0, to: CGFloat(shown) / 100)
                .stroke(Brand.scoreColor(score), style: StrokeStyle(lineWidth: 10, lineCap: .round))
                .rotationEffect(.degrees(-90))
            if score == nil {
                ProgressView().tint(palette.accent)
            } else {
                Text("\(shown)")
                    .font(.system(size: 34, weight: .heavy, design: .rounded))
                    .monospacedDigit()
                    .contentTransition(.numericText(value: Double(shown)))
                    .foregroundStyle(Brand.scoreColor(score))
            }
        }
        .frame(width: 104, height: 104)
        .onAppear { animate(to: score) }
        .onChange(of: score) { _, new in animate(to: new) }
        .accessibilityElement()
        .accessibilityLabel(score.map { "Score \($0) sur 100" } ?? "Correction en cours")
    }

    private func animate(to value: Int?) {
        guard let value else { return }
        withAnimation(.easeOut(duration: 0.28)) { shown = value }
    }
}

struct RubricRow: View {
    let score: RubricScore

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text(score.label).font(.subheadline.weight(.semibold))
                Spacer()
                Text("\(score.score)/2 · \(score.weight) %").font(.caption.monospacedDigit()).foregroundStyle(Brand.textSecondary)
            }
            GeometryReader { geo in
                ZStack(alignment: .leading) {
                    Capsule().fill(Color.white.opacity(0.08))
                    Capsule().fill(color).frame(width: max(8, geo.size.width * score.fraction))
                }
            }
            .frame(height: 8)
            if let justification = score.justification, !justification.isEmpty {
                Text(justification).font(.caption).foregroundStyle(Brand.textSecondary)
            }
            if let quote = score.quote, !quote.isEmpty {
                Text(quote).font(.caption.italic()).foregroundStyle(Brand.textTertiary)
            }
        }
    }

    private var color: Color {
        switch score.score {
        case 2: return Brand.success
        case 1: return Brand.flame
        default: return Brand.danger
        }
    }
}

struct FeedbackCard: View {
    let section: FeedbackSection
    @Environment(\.palette) private var palette

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            if !section.title.isEmpty {
                Label(section.title, systemImage: symbol).font(.headline).foregroundStyle(tint)
            }
            MarkdownText(markdown: section.body, font: section.kind == .thirtySeconds ? Font.body.italic() : Font.subheadline)
        }
        .padding(16)
        .frame(maxWidth: .infinity, alignment: .leading)
        .card(fill: section.kind == .thirtySeconds ? palette.accentSoft : Brand.card)
    }

    private var symbol: String {
        switch section.kind {
        case .strengths: return "hand.thumbsup.fill"
        case .fixes: return "wrench.and.screwdriver.fill"
        case .thirtySeconds: return "timer"
        case .other: return "text.bubble"
        }
    }

    private var tint: Color {
        switch section.kind {
        case .strengths: return Brand.success
        case .fixes: return Brand.danger
        case .thirtySeconds: return palette.accent
        case .other: return .white
        }
    }
}

/// The streak and goal line under the score.
struct ProgressLine: View {
    let progress: GradeProgress
    @Environment(\.palette) private var palette

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 10) {
                Image(systemName: progress.streakExtended ? "flame.fill" : "flame")
                    .foregroundStyle(progress.streakExtended ? AnyShapeStyle(palette.linear) : AnyShapeStyle(Brand.textSecondary))
                Text(progress.streakExtended
                     ? "Série prolongée : \(Format.streakDays(progress.streak.current)) !"
                     : "Série : \(Format.streakDays(progress.streak.current))")
                    .font(.subheadline.weight(.semibold))
                Spacer()
                Text("\(progress.xpToday)/\(progress.goalTarget ?? 0) XP").font(.subheadline.monospacedDigit())
                    .foregroundStyle(progress.goalMet ? Brand.success : Brand.textSecondary)
            }
            if progress.freezeEarned == true {
                Label("Un freeze de plus en réserve", systemImage: "snowflake").font(.footnote).foregroundStyle(Brand.freeze)
            }
            if let bonus = progress.dayCompleteBonus, bonus > 0 {
                Label("Journée complète : +\(bonus) XP", systemImage: "checkmark.seal.fill").font(.footnote).foregroundStyle(Brand.success)
            }
            if progress.perfectWeek == true {
                Label("Semaine parfaite !", systemImage: "star.fill").font(.footnote.weight(.bold)).foregroundStyle(palette.accent)
            }
            ForEach(progress.newBadges ?? []) { badge in
                Label("Badge : \(badge.name)", systemImage: badge.symbol ?? "rosette").font(.footnote.weight(.semibold))
                    .foregroundStyle(palette.accent)
            }
        }
        .padding(14)
        .card(radius: 16)
    }
}

/// A correction read back from the history.
struct AttemptDetailView: View {
    let attemptId: ID
    @Environment(AppModel.self) private var model
    @State private var attempt: Attempt?
    @State private var error: String?

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                if let attempt {
                    ResultContent(title: attempt.exercise?.title ?? "Exercice",
                                  typeLabel: attempt.exercise?.typeLabel ?? attempt.exercise?.type.label ?? "",
                                  score: attempt.score, rubric: attempt.rubricScores ?? [], feedback: attempt.feedback ?? "",
                                  followUp: attempt.followUp, attempt: attempt,
                                  xp: XPInfo(earned: attempt.xpEarned, breakdown: nil), progress: nil,
                                  isRevenge: attempt.isRevenge ?? false)
                    if let answer = attempt.answerText, !answer.isEmpty {
                        DisclosureGroup {
                            Text(answer).font(.subheadline).textSelection(.enabled).padding(.top, 8)
                        } label: {
                            Label("Ma réponse", systemImage: "text.quote").font(.headline)
                        }
                        .padding(16)
                        .card()
                    }
                    if model.isAdmin {
                        FlagButton(exerciseId: attempt.exerciseId, flagged: attempt.exercise?.flagged ?? false)
                    }
                } else if let error {
                    ErrorBanner(message: error)
                } else {
                    LoadingView().frame(height: 300)
                }
            }
            .padding(16)
        }
        .background(Brand.background)
        .navigationTitle("Correction")
        .navigationBarTitleDisplayMode(.inline)
        .task {
            do { attempt = try await model.service.attempt(id: attemptId) } catch {
                model.handle(error)
                self.error = error.localizedDescription
            }
        }
    }
}
