import CaseDuoCore
import Combine
import SwiftUI

/// The mock interview, the closest thing to the real process: oral only, no going back, one
/// clock for the whole run, follow-ups asked on the spot, feedback only at the end. Counts
/// double in XP.
struct MockView: View {
    let kind: String
    let mbb: Bool

    @Environment(AppModel.self) private var model
    @Environment(\.dismiss) private var dismiss
    @Environment(\.palette) private var palette

    @State private var run: MockRun?
    @State private var stage: Stage = .intro
    @State private var stepIndex = 0
    @State private var partIndex = 0
    @State private var partAnswers: [String] = []
    @State private var answer = ""
    @State private var pendingFollowUp: (question: String, parentId: ID)?
    @State private var startedAt: Date?
    @State private var stepStartedAt = Date()
    @State private var now = Date()
    @State private var busy = false
    @State private var error: String?
    @State private var finish: MockFinish?
    @State private var dictation = Dictation()
    @State private var confirmQuit = false

    enum Stage: Equatable { case intro, answering, followUp, finishing, done }

    private let ticker = Timer.publish(every: 1, on: .main, in: .common).autoconnect()

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                switch stage {
                case .intro: intro
                case .answering, .followUp: answering
                case .finishing: LoadingView(message: "L'associé fait le bilan de l'entretien…")
                case .done: result
                }
            }
            .background(Brand.background)
            .navigationTitle(kind == "fit" ? "Mock fit" : "Mock entretien")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    if stage == .intro || stage == .done {
                        Button("Fermer") { dismiss() }
                    } else if stage != .finishing {
                        Button("Abandonner") { confirmQuit = true }
                    }
                }
                ToolbarItem(placement: .principal) {
                    if let run, let startedAt, stage == .answering || stage == .followUp {
                        ChronoLabel(seconds: run.timeLimitSeconds - Int(now.timeIntervalSince(startedAt)),
                                    budget: run.timeLimitSeconds, countdown: true)
                    }
                }
            }
            .confirmationDialog("Abandonner le mock ?", isPresented: $confirmQuit, titleVisibility: .visible) {
                Button("Abandonner", role: .destructive) { dictation.stop(); dismiss() }
                Button("Continuer", role: .cancel) {}
            } message: {
                Text("Les réponses déjà envoyées restent notées, mais le mock ne comptera pas.")
            }
        }
        .interactiveDismissDisabled(stage != .intro && stage != .done)
        .onReceive(ticker) { now = $0 }
        .onChange(of: dictation.transcript) { _, text in
            guard dictation.isRecording else { return }
            if currentStep?.parts?.isEmpty == false, stage == .answering, partAnswers.indices.contains(partIndex) {
                partAnswers[partIndex] = text
            } else {
                answer = text
            }
        }
    }

    private var currentStep: MockStep? { run?.steps[safe: stepIndex] }

    // MARK: Intro

    private var intro: some View {
        VStack(alignment: .leading, spacing: 18) {
            Spacer()
            Image(systemName: "person.2.wave.2.fill").font(.system(size: 48)).foregroundStyle(palette.linear)
            Text(kind == "fit" ? "Six questions de fit, quinze minutes." : "Trente minutes, comme en vrai.")
                .font(.title.weight(.heavy))
            VStack(alignment: .leading, spacing: 8) {
                Label("À l'oral uniquement : la dictée transcrit, tu ne tapes pas.", systemImage: "mic.fill")
                Label("Pas de retour en arrière.", systemImage: "arrow.uturn.backward.circle")
                Label("Les relances tombent comme en entretien.", systemImage: "bubble.left.and.exclamationmark.bubble.right")
                Label("Le retour arrive à la fin. XP ×2.", systemImage: "flag.checkered")
                if mbb { Label("Format MBB : PEI, case mené par l'interviewer, synthèse en 30 s.", systemImage: "briefcase") }
            }
            .font(.subheadline)
            .foregroundStyle(Brand.textSecondary)
            if let error { ErrorBanner(message: error) }
            Spacer()
            Button {
                Task { await start() }
            } label: {
                if busy { ProgressView().tint(.black) } else { Text("Commencer") }
            }
            .buttonStyle(.pill)
            .disabled(busy)
        }
        .padding(24)
    }

    private func start() async {
        busy = true
        defer { busy = false }
        do {
            let run = try await model.service.startMock(kind: kind)
            self.run = run
            startedAt = Date()
            beginStep(0)
        } catch {
            model.handle(error)
            self.error = error.localizedDescription
        }
    }

    private func beginStep(_ index: Int) {
        stepIndex = index
        partIndex = 0
        answer = ""
        partAnswers = Array(repeating: "", count: run?.steps[safe: index]?.parts?.count ?? 0)
        pendingFollowUp = nil
        dictation.reset()
        stepStartedAt = Date()
        stage = .answering
    }

    // MARK: Answering

    private var answering: some View {
        VStack(spacing: 0) {
            ScrollView {
                VStack(alignment: .leading, spacing: 14) {
                    if let run {
                        ProgressView(value: Double(stepIndex) + (stage == .followUp ? 0.5 : 0), total: Double(run.steps.count))
                            .tint(palette.accent)
                    }
                    if stage == .followUp, let followUp = pendingFollowUp {
                        Label("Relance", systemImage: "bubble.left.and.exclamationmark.bubble.right.fill")
                            .font(.caption.weight(.bold)).foregroundStyle(palette.accent)
                        Text(followUp.question).font(.title3.weight(.semibold))
                    } else if let step = currentStep {
                        Text("\(step.index + 1). \(step.type.label)".uppercased())
                            .font(.caption.weight(.bold)).foregroundStyle(Brand.textSecondary)
                        Text(step.title).font(.title3.weight(.bold))
                        MarkdownText(markdown: step.prompt)
                        if let parts = step.parts, !parts.isEmpty {
                            VStack(alignment: .leading, spacing: 6) {
                                Text("Question \(partIndex + 1) sur \(parts.count)").font(.caption.weight(.bold))
                                    .foregroundStyle(Brand.textSecondary)
                                Text(parts[partIndex].question).font(.headline)
                                if let data = parts[partIndex].data { Label(data, systemImage: "tablecells").foregroundStyle(Brand.mbb) }
                            }
                            .padding(14)
                            .card(radius: 14)
                        }
                        if let data = step.contextData, !data.isEmpty { ContextDataList(data: data) }
                    }
                    transcriptBox
                    if let error { ErrorBanner(message: error) { self.error = nil } }
                }
                .padding(16)
            }
            BottomActions {
                HStack(spacing: 12) {
                    MicButton(recording: dictation.isRecording) {
                        Task {
                            if dictation.isRecording { dictation.stop() } else {
                                await dictation.start(language: run?.language ?? "fr", existing: currentText)
                            }
                        }
                    }
                    Button {
                        Task { await next() }
                    } label: {
                        if busy { ProgressView().tint(.black) } else { Text(nextLabel) }
                    }
                    .buttonStyle(.pill)
                    .disabled(busy || currentText.trimmingCharacters(in: .whitespacesAndNewlines).count < 5)
                }
            }
        }
    }

    private var transcriptBox: some View {
        VStack(alignment: .leading, spacing: 6) {
            Label(dictation.isRecording ? "Je t'écoute…" : "Ta réponse (transcription)", systemImage: "waveform")
                .font(.caption.weight(.bold))
                .foregroundStyle(dictation.isRecording ? Brand.danger : Brand.textSecondary)
            Text(currentText.isEmpty ? "Appuie sur le micro et parle." : currentText)
                .foregroundStyle(currentText.isEmpty ? Brand.textTertiary : .white)
                .frame(maxWidth: .infinity, minHeight: 120, alignment: .topLeading)
        }
        .padding(14)
        .card(radius: 14)
    }

    private var currentText: String {
        if stage == .answering, let parts = currentStep?.parts, !parts.isEmpty { return partAnswers[safe: partIndex] ?? "" }
        return answer
    }

    private var nextLabel: String {
        if stage == .answering, let parts = currentStep?.parts, partIndex < parts.count - 1 { return "Question suivante" }
        if stage == .answering, currentStep?.followUpAfter == true { return "Valider" }
        if let run, stepIndex >= run.steps.count - 1 { return "Terminer l'entretien" }
        return "Question suivante"
    }

    private func next() async {
        dictation.stop()
        guard let run, let step = currentStep else { return }
        if stage == .answering, let parts = step.parts, partIndex < parts.count - 1 {
            partIndex += 1
            dictation.reset()
            return
        }
        busy = true
        defer { busy = false }
        let elapsed = Int(Date().timeIntervalSince(stepStartedAt))
        do {
            if stage == .followUp, let followUp = pendingFollowUp {
                _ = try await model.service.grade(GradeRequest(
                    exerciseId: step.exerciseId, kind: .followUp, answerText: answer, durationSeconds: elapsed,
                    inputMode: .voice, parentAttemptId: followUp.parentId, mockRunId: run.id))
                await advance()
                return
            }
            let request: GradeRequest
            if let parts = step.parts, !parts.isEmpty {
                request = GradeRequest(exerciseId: step.exerciseId, kind: .main,
                                       answerText: PartAnswers.answerText(parts: parts, answers: partAnswers),
                                       durationSeconds: elapsed, inputMode: .voice, mockRunId: run.id, partAnswers: partAnswers)
            } else {
                request = GradeRequest(exerciseId: step.exerciseId, kind: .main, answerText: answer,
                                       durationSeconds: elapsed, inputMode: .voice, mockRunId: run.id)
            }
            Haptics.shared.play(.answerSent)
            let result = try await model.service.grade(request)
            if step.followUpAfter, let question = result.attempt.followUp, !question.isEmpty {
                pendingFollowUp = (question, result.attempt.id)
                answer = ""
                dictation.reset()
                stepStartedAt = Date()
                withAnimation(Brand.quick) { stage = .followUp }
            } else {
                await advance()
            }
        } catch {
            model.handle(error)
            self.error = error.localizedDescription
        }
    }

    private func advance() async {
        guard let run else { return }
        if stepIndex + 1 < run.steps.count {
            withAnimation(Brand.quick) { beginStep(stepIndex + 1) }
        } else {
            await finishRun()
        }
    }

    private func finishRun() async {
        guard let run else { return }
        stage = .finishing
        do {
            finish = try await model.service.finishMock(id: run.id)
            stage = .done
            if let score = finish?.score { Haptics.shared.play(HapticPattern.forScore(score)) }
            await model.refreshToday()
        } catch {
            model.handle(error)
            self.error = error.localizedDescription
            stage = .answering
        }
    }

    // MARK: Result

    private var result: some View {
        VStack(spacing: 0) {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    if let finish {
                        HStack(spacing: 18) {
                            ScoreRing(score: finish.score)
                            VStack(alignment: .leading, spacing: 6) {
                                Text(Format.xp(finish.xpEarned, signed: true)).font(.title2.weight(.heavy)).foregroundStyle(palette.accent)
                                Text("XP ×2 : c'est l'exercice le plus proche du vrai process.").font(.caption)
                                    .foregroundStyle(Brand.textSecondary)
                            }
                        }
                        if let previous = finish.previous, !previous.isEmpty {
                            VStack(alignment: .leading, spacing: 8) {
                                Text("Tes mocks précédents").font(.headline)
                                ForEach(previous, id: \.self) { p in
                                    HStack {
                                        Text(Format.shortDay(p.date))
                                        Text(p.kind == "fit" ? "fit" : "complet").foregroundStyle(Brand.textSecondary)
                                        Spacer()
                                        Text(p.score.map(String.init) ?? "—").monospacedDigit().foregroundStyle(Brand.scoreColor(p.score))
                                        if let s = p.score, let now = finish.score {
                                            Image(systemName: now >= s ? "arrow.up.right" : "arrow.down.right")
                                                .foregroundStyle(now >= s ? Brand.success : Brand.danger)
                                        }
                                    }
                                    .font(.subheadline)
                                }
                            }
                            .padding(16)
                            .card()
                        }
                        if let feedback = finish.feedback {
                            ForEach(FeedbackSection.parse(feedback)) { FeedbackCard(section: $0) }
                        }
                        VStack(spacing: 0) {
                            ForEach(finish.attempts) { attempt in
                                AttemptRow(attempt: attempt)
                                if attempt.id != finish.attempts.last?.id { Divider().overlay(Brand.stroke) }
                            }
                        }
                        .padding(.horizontal, 16)
                        .card()
                    }
                }
                .padding(16)
            }
            BottomActions { Button("Fermer") { dismiss() }.buttonStyle(.pill) }
        }
    }
}
