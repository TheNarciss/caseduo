import CaseDuoCore
import SwiftUI

/// A step of the Parcours from start to finish: the items one by one, « Vérifier », the verdict
/// with the reason and the rule, the mistakes asked again at the end, then the score, the XP
/// and the oral feedback. The session itself is a value in CaseDuoCore (LessonSession).
struct LessonPlayerView: View {
    let nodeCode: String
    @Environment(AppModel.self) private var model
    @Environment(\.palette) private var palette
    @Environment(\.dismiss) private var dismiss

    private enum Phase: Equatable { case loading, playing, sending, done, failed(String) }

    @State private var phase: Phase = .loading
    @State private var session: LessonSession?
    @State private var answer: PathAnswer?
    @State private var verdict: PathVerdict?
    @State private var stepStart = Date()
    @State private var completion: LessonCompletion?
    @State private var burst = 0
    @State private var askQuit = false
    @State private var flagged: Set<String> = []
    @State private var flagNote = ""
    @State private var askFlag = false
    /// « Combo ×3 ! » floating over the item, at 3, 5 and 10 right in a row.
    @State private var combo: Int?
    @State private var comboBurst = 0

    private var tint: Color {
        guard let kind = session?.start.node.kind else { return palette.accent }
        switch kind {
        case .checkpoint: return Brand.marketSizing
        case .legendary: return palette.perfectWeekGold
        case .review: return Brand.cadrage
        default: return palette.accent
        }
    }

    var body: some View {
        ZStack {
            Brand.background.ignoresSafeArea()
            switch phase {
            case .loading:
                LoadingView(message: "Préparation de la leçon…")
            case .failed(let message):
                VStack(spacing: 16) {
                    ErrorBanner(message: message)
                    Button("Réessayer") { Task { await load() } }.buttonStyle(.pill(.secondary, compact: true))
                    Button("Retour") { dismiss() }.buttonStyle(.pill(.quiet, compact: true))
                }
                .padding(24)
            case .playing, .sending:
                if let session {
                    if session.isFinished {
                        LessonSendingView(session: session, tint: tint)
                    } else {
                        player(session)
                    }
                }
            case .done:
                if let session, let completion {
                    LessonDoneView(session: session, completion: completion, tint: tint, burst: burst) {
                        dismiss()
                    }
                }
            }
        }
        .navigationTitle("")
        .toolbar(.hidden, for: .navigationBar)
        .toolbar(.hidden, for: .tabBar)
        .task { await load() }
        .confirmationDialog("Quitter la leçon ?", isPresented: $askQuit, titleVisibility: .visible) {
            Button("Quitter", role: .destructive) { dismiss() }
            Button("Continuer", role: .cancel) {}
        } message: {
            Text("La progression de cette leçon ne sera pas enregistrée.")
        }
        .alert("Signaler cet exercice", isPresented: $askFlag) {
            TextField("Ce qui ne va pas (facultatif)", text: $flagNote)
            Button("Signaler") { Task { await flagCurrent() } }
            Button("Annuler", role: .cancel) {}
        } message: {
            Text("Ambigu, faux, mal écrit : après trois signalements il sort du Parcours.")
        }
    }

    // MARK: Playing

    private func player(_ session: LessonSession) -> some View {
        VStack(spacing: 0) {
            topBar(session)
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    if let step = session.current {
                        if !step.firstTry {
                            Label("On la refait", systemImage: "arrow.uturn.backward")
                                .font(.caption.weight(.bold)).foregroundStyle(Brand.cadrage)
                        }
                        LessonItemView(item: step.item, locked: verdict != nil, verdict: verdict, answer: $answer, tint: tint)
                            .id(step.id)
                            .transition(.asymmetric(insertion: .move(edge: .trailing).combined(with: .opacity),
                                                    removal: .move(edge: .leading).combined(with: .opacity)))
                    }
                }
                .padding(16)
                .padding(.bottom, 24)
                .containerRelativeFrame(.horizontal)
            }
            .scrollDismissesKeyboard(.interactively)
            .animation(Motion.settle, value: session.current?.id)
            .overlay(alignment: .top) {
                if let combo {
                    ComboToast(count: combo, tint: tint, burst: comboBurst)
                        .padding(.top, 60)
                        .transition(.scale(scale: 0.5).combined(with: .opacity))
                }
            }
            bottomPanel(session)
        }
    }

    private func topBar(_ session: LessonSession) -> some View {
        HStack(spacing: 12) {
            Button { askQuit = true } label: {
                Image(systemName: "xmark").font(.headline).foregroundStyle(Brand.textSecondary)
                    .frame(width: 36, height: 36)
            }
            .accessibilityLabel("Quitter la leçon")
            .accessibilityIdentifier("lesson.quit")
            GeometryReader { geo in
                ZStack(alignment: .leading) {
                    Capsule().fill(Brand.cardRaised)
                    Capsule()
                        .fill(LinearGradient(colors: [tint.opacity(0.85), tint], startPoint: .leading, endPoint: .trailing))
                        .overlay(alignment: .top) {
                            Capsule().fill(Color.white.opacity(0.35)).frame(height: 3).padding(.horizontal, 4).padding(.top, 2)
                        }
                        .frame(width: max(10, geo.size.width * session.progress))
                        .animation(Motion.settle, value: session.progress)
                }
            }
            .frame(height: 14)
            .accessibilityLabel("Progression \(Int(session.progress * 100)) %")
            if session.streakOfCorrect >= 2 {
                HStack(spacing: 3) {
                    Image(systemName: "flame.fill")
                    Text("\(session.streakOfCorrect)").monospacedDigit()
                }
                .font(.subheadline.weight(.heavy))
                .foregroundStyle(palette.linear)
                .bounce(trigger: session.streakOfCorrect)
                .transition(.scale.combined(with: .opacity))
            }
            Menu {
                Button(flagged.contains(session.current?.item.id ?? "") ? "Déjà signalé" : "Signaler cet exercice",
                       systemImage: "flag") { askFlag = true }
                    .disabled(flagged.contains(session.current?.item.id ?? ""))
            } label: {
                Image(systemName: "ellipsis").font(.headline).foregroundStyle(Brand.textSecondary)
                    .frame(width: 36, height: 36)
            }
            .accessibilityLabel("Options")
        }
        .padding(.horizontal, 12)
        .padding(.top, 8)
        .padding(.bottom, 4)
        .animation(Brand.spring, value: session.streakOfCorrect)
    }

    @ViewBuilder private func bottomPanel(_ session: LessonSession) -> some View {
        if let verdict {
            FeedbackPanel(verdict: verdict, item: session.current?.item, tint: tint,
                          isLast: session.index == session.queue.count - 1) { advance() }
                .transition(.move(edge: .bottom).combined(with: .opacity))
        } else {
            BottomActions {
                Button(session.current?.item.format.isGraded == false ? "Continuer"
                       : session.current?.item.format.isOral == true ? "Terminer" : "Vérifier") { check() }
                    .buttonStyle(.pill)
                    .disabled(answer == nil)
                    .accessibilityIdentifier("lesson.check")
            }
        }
    }

    // MARK: Actions

    private func load() async {
        phase = .loading
        do {
            let start = try await model.service.startNode(code: nodeCode, seed: nil)
            session = LessonSession(start: start)
            answer = nil
            verdict = nil
            stepStart = Date()
            phase = .playing
        } catch {
            if (error as? APIError) == .unauthorized { model.handle(error) }
            phase = .failed(error.localizedDescription)
        }
    }

    private func check() {
        guard var current = session, let answer else { return }
        let ms = Int(Date().timeIntervalSince(stepStart) * 1000)
        let result = current.submit(answer, ms: ms)
        session = current
        guard let step = current.current, let result else { return }
        if !step.item.format.isGraded || step.item.format.isOral {
            advance()
            return
        }
        withAnimation(Motion.settle) { verdict = result }
        if result.correct {
            Haptics.shared.play(.correct)
            Sounds.shared.play(.correct)
            let streak = current.streakOfCorrect
            if [3, 5, 10].contains(streak) || (streak > 10 && streak % 5 == 0) {
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.35) { showCombo(streak) }
            }
        } else {
            Haptics.shared.play(.wrong)
            Sounds.shared.play(.wrong)
        }
    }

    private func showCombo(_ count: Int) {
        Haptics.shared.play(.streakUp)
        Sounds.shared.play(.combo)
        withAnimation(Motion.bouncy) { combo = count }
        comboBurst += 1
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.4) {
            withAnimation(Motion.settle) { combo = nil }
        }
    }

    private func advance() {
        guard var current = session else { return }
        current.advance()
        withAnimation(Brand.quick) {
            verdict = nil
            answer = nil
            session = current
        }
        stepStart = Date()
        if current.isFinished { Task { await send(current) } }
    }

    private func send(_ finished: LessonSession) async {
        phase = .sending
        do {
            let done = try await model.service.completeNode(code: nodeCode, LessonCompletionRequest(results: finished.results))
            completion = done
            phase = .done
            Haptics.shared.play(done.passed ? .lessonDone : .scoreLow)
            if done.passed { Sounds.shared.play(.done) }
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.3) { burst += 1 }
            model.didCompleteLesson(done)
        } catch {
            if (error as? APIError) == .unauthorized { model.handle(error) }
            phase = .failed(error.localizedDescription)
        }
    }

    private func flagCurrent() async {
        guard let id = session?.current?.item.id else { return }
        flagged.insert(id)
        let note = flagNote.trimmingCharacters(in: .whitespacesAndNewlines)
        flagNote = ""
        _ = try? await model.service.flagItem(id: id, note: note.isEmpty ? nil : note)
        Haptics.shared.play(.tap)
    }
}

extension Palette {
    /// Gold for the legendary step, whatever the week.
    var perfectWeekGold: Color { Color(red: 1.0, green: 0.80, blue: 0.30) }
}

/// Under the item once checked: green and the rule, or orange, why the choice was wrong, what
/// was expected, and the rule.
struct FeedbackPanel: View {
    let verdict: PathVerdict
    let item: PathItem?
    var tint: Color
    var isLast: Bool
    let next: () -> Void

    private var color: Color { verdict.correct ? Brand.success : Brand.danger }

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 10) {
                Image(systemName: verdict.correct ? "checkmark.circle.fill" : "xmark.circle.fill")
                    .font(.title)
                    .popIn()
                    .background {
                        if verdict.correct {
                            BurstView(trigger: 1, colors: [Brand.success, .white, Brand.flameLight], count: 18)
                                .frame(width: 140, height: 140)
                        }
                    }
                Text(verdict.correct ? headline : "Pas tout à fait")
                    .font(.title3.weight(.heavy))
                    .popIn(delay: 0.05)
                Spacer()
                if !verdict.correct, verdict.ratio > 0 {
                    Text("\(Int((verdict.ratio * 100).rounded())) %")
                        .font(.caption.weight(.bold).monospacedDigit())
                }
            }
            .foregroundStyle(color)
            ScrollView {
                VStack(alignment: .leading, spacing: 8) {
                    if let whyWrong = verdict.whyWrong, !verdict.correct {
                        Text(whyWrong).font(.subheadline.weight(.semibold))
                    }
                    if let expected = verdict.expected {
                        VStack(alignment: .leading, spacing: 2) {
                            Text(verdict.correct ? "Pour aller plus loin" : "La bonne réponse")
                                .font(.caption.weight(.bold)).foregroundStyle(Brand.textSecondary)
                            Text(expected).font(.subheadline)
                        }
                    }
                    if let explanation = item?.explanation, !explanation.isEmpty {
                        MarkdownText(markdown: explanation, font: .subheadline)
                            .foregroundStyle(Brand.textSecondary)
                    }
                }
                .frame(maxWidth: .infinity, alignment: .leading)
            }
            .frame(maxHeight: 180)
            Button(isLast ? "Terminer" : "Continuer", action: next)
                .buttonStyle(.pill(verdict.correct ? .success : .primary))
                .accessibilityIdentifier("lesson.next")
        }
        .padding(20)
        .background(color.opacity(0.12))
        .background(.ultraThinMaterial)
        .accessibilityElement(children: .contain)
    }

    private var headline: String {
        let seed = (item?.id ?? "").utf8.reduce(0) { ($0 + Int($1)) % 5 }
        return ["Exact !", "Bien vu", "Oui !", "C'est ça", "Parfait"][seed]
    }
}

/// « Combo ×3 ! » : a burst and a label that pops over the item.
struct ComboToast: View {
    let count: Int
    var tint: Color
    var burst: Int
    @Environment(\.palette) private var palette

    var body: some View {
        ZStack {
            BurstView(trigger: burst, colors: palette.gradient + [.white], count: 30)
                .frame(width: 220, height: 220)
            VStack(spacing: 2) {
                Text("Combo ×\(count)")
                    .font(.system(size: 30, weight: .black, design: .rounded))
                    .foregroundStyle(palette.linear)
                Text(count >= 10 ? "Imparable" : count >= 5 ? "En feu" : "Ça s'enchaîne")
                    .font(.subheadline.weight(.bold))
                    .foregroundStyle(Brand.textSecondary)
            }
            .padding(.horizontal, 22).padding(.vertical, 12)
            .background(.ultraThinMaterial, in: Capsule())
            .overlay(Capsule().stroke(tint.opacity(0.6), lineWidth: 1.5))
            .shadow(color: tint.opacity(0.4), radius: 16)
        }
        .allowsHitTesting(false)
        .accessibilityLabel("Combo de \(count) bonnes réponses")
    }
}

/// The results are leaving: the mascot thinks, the oral item is being graded.
struct LessonSendingView: View {
    let session: LessonSession
    var tint: Color

    var body: some View {
        VStack(spacing: 16) {
            FlameMascot(mood: .thinking, size: 120)
            Text(session.graded.contains { $0.item.format.isOral } ? "L'interviewer relit ta réponse orale…" : "Enregistrement…")
                .font(.headline)
                .foregroundStyle(Brand.textSecondary)
                .multilineTextAlignment(.center)
            ProgressView().tint(tint)
        }
        .padding(24)
    }
}

/// The end of a step: the score pops, the XP counts up, the streak line, the oral feedback.
struct LessonDoneView: View {
    let session: LessonSession
    let completion: LessonCompletion
    var tint: Color
    var burst: Int
    let close: () -> Void
    @Environment(\.palette) private var palette
    @State private var shown = false
    @State private var shownScore = 0

    private var mood: MascotMood {
        if !completion.passed { return .sad }
        return completion.score >= 80 ? .proud : .happy
    }

    var body: some View {
        VStack(spacing: 0) {
            ScrollView {
                VStack(spacing: 18) {
                    ZStack {
                        BurstView(trigger: burst, colors: [tint, Brand.success, .white] + palette.gradient, count: 32)
                            .frame(width: 260, height: 260)
                        FlameMascot(mood: mood, size: 130)
                            .scaleEffect(shown ? 1 : 0.6)
                    }
                    .frame(height: 200)
                    .padding(.top, 20)

                    Text(title)
                        .font(.system(size: 30, weight: .heavy, design: .rounded))
                        .foregroundStyle(completion.passed ? AnyShapeStyle(palette.linear) : AnyShapeStyle(Brand.textSecondary))
                        .multilineTextAlignment(.center)
                        .popIn(delay: 0.15)
                    Text(session.start.node.title).font(.headline).foregroundStyle(Brand.textSecondary)

                    HStack(spacing: 12) {
                        stat(value: "\(shownScore) %", label: "au premier essai", color: Brand.scoreColor(completion.score))
                        VStack(spacing: 4) {
                            XPPop(earned: completion.xp, tint: tint)
                            Text(completion.replay == true ? "déjà réussie" : session.isPerfect ? "sans faute !" : "gagnés")
                                .font(.caption).foregroundStyle(Brand.textSecondary)
                        }
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 14)
                        .card(radius: 16)
                    }
                    .accessibilityIdentifier("lesson.done")

                    if let progress = completion.progress {
                        ProgressLine(progress: progress)
                    }

                    if let orals = completion.oral, !orals.isEmpty {
                        ForEach(orals, id: \.itemId) { oral in OralFeedbackCard(verdict: oral, tint: tint) }
                    }

                    let missed = session.graded.filter { $0.firstTry && !$0.verdict.correct }
                    if !missed.isEmpty {
                        VStack(alignment: .leading, spacing: 8) {
                            Text("À retenir").font(.headline)
                            ForEach(missed, id: \.item.id) { a in
                                HStack(alignment: .top, spacing: 8) {
                                    Image(systemName: "arrow.turn.down.right").font(.caption).foregroundStyle(Brand.danger).padding(.top, 3)
                                    Text(a.item.explanation.isEmpty ? a.item.stem : a.item.explanation).font(.subheadline)
                                }
                            }
                        }
                        .padding(14)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .card(radius: 16)
                    }

                    if completion.unitDone == true, completion.passed {
                        Label("Unité terminée !", systemImage: "checkmark.seal.fill")
                            .font(.headline).foregroundStyle(Brand.success)
                    } else if !completion.passed, let pass = session.start.passScore {
                        Text("Il faut \(pass) % pour valider. Reprends les leçons de l'unité et retente.")
                            .font(.footnote).foregroundStyle(Brand.textSecondary).multilineTextAlignment(.center)
                    }
                }
                .padding(16)
                .padding(.bottom, 24)
                .containerRelativeFrame(.horizontal)
            }
            BottomActions {
                Button(completion.passed ? "Continuer le Parcours" : "Retour au Parcours", action: close)
                    .buttonStyle(.pill(completion.passed ? .success : .secondary))
                    .accessibilityIdentifier("lesson.close")
            }
        }
        .onAppear {
            withAnimation(.spring(duration: 0.5, bounce: 0.4)) { shown = true }
            withAnimation(.easeOut(duration: 0.7).delay(0.2)) { shownScore = completion.score }
        }
    }

    private var title: String {
        if completion.replay == true { return "Refait !" }
        if !completion.passed { return "Pas encore" }
        switch completion.score {
        case 100: return "Sans faute !"
        case 80...: return "Très bien"
        case 60...: return "Bien joué"
        default: return "Leçon terminée"
        }
    }

    private func stat(value: String, label: String, color: Color) -> some View {
        StatTile(value: value, label: label, color: color)
    }
}

/// What the interviewer said about the oral item: the score, the criteria, the feedback.
struct OralFeedbackCard: View {
    let verdict: OralVerdict
    var tint: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Label("À l'oral", systemImage: "waveform").font(.headline)
                Spacer()
                if let score = verdict.score {
                    Text("\(score)").font(.title3.weight(.heavy)).monospacedDigit().foregroundStyle(Brand.scoreColor(score))
                } else {
                    Text("non noté").font(.caption).foregroundStyle(Brand.textSecondary)
                }
            }
            ForEach(verdict.criteria, id: \.key) { c in
                HStack(spacing: 8) {
                    Text(c.label).font(.subheadline)
                    Spacer()
                    HStack(spacing: 3) {
                        ForEach(0..<3, id: \.self) { i in
                            Circle().fill(i < c.score ? tint : Color.white.opacity(0.15)).frame(width: 8, height: 8)
                        }
                    }
                }
            }
            if !verdict.feedback.isEmpty {
                MarkdownText(markdown: verdict.feedback, font: .subheadline)
            }
        }
        .padding(14)
        .frame(maxWidth: .infinity, alignment: .leading)
        .card(radius: 16)
    }
}
