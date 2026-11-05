import CaseDuoCore
import Combine
import SwiftUI

enum FollowUpMode: Identifiable, Hashable {
    /// Answer the interviewer's follow-up: 90 s, spoken or typed. +5 XP from 60.
    case followUp(question: String, parentId: ID)
    /// Redo the whole answer orally in 2 minutes. +10 XP from 70.
    case retry(parentId: ID)

    var id: String {
        switch self {
        case .followUp(_, let parentId): return "follow-\(parentId)"
        case .retry(let parentId): return "retry-\(parentId)"
        }
    }

    var seconds: Int {
        switch self {
        case .followUp: return 90
        case .retry: return 120
        }
    }

    var kind: AttemptKind {
        switch self {
        case .followUp: return .followUp
        case .retry: return .retry2min
        }
    }

    var parentId: ID {
        switch self {
        case .followUp(_, let id), .retry(let id): return id
        }
    }
}

/// The moment you get caught in a real interview: the follow-up, under a 90-second clock; or
/// the same case again, out loud, in two minutes.
struct FollowUpView: View {
    let mode: FollowUpMode
    let exerciseId: ID
    let title: String
    let type: ExerciseType
    let language: String

    @Environment(AppModel.self) private var model
    @Environment(\.dismiss) private var dismiss
    @Environment(\.palette) private var palette
    @State private var answer = ""
    @State private var dictation = Dictation()
    @State private var started = false
    @State private var remaining = 0
    @State private var usedVoice = false
    @State private var session: GradingSession?

    private let ticker = Timer.publish(every: 1, on: .main, in: .common).autoconnect()

    var body: some View {
        NavigationStack {
            Group {
                if let session {
                    ScrollView {
                        ResultContent(title: title, typeLabel: modeTitle, score: session.score,
                                      rubric: session.state.rubricScores, feedback: session.state.feedback,
                                      followUp: nil, attempt: nil, xp: session.result?.xp, progress: session.result?.progress,
                                      grading: session.phase == .grading, compact: true)
                            .padding(16)
                        if case .failed(let message) = session.phase { ErrorBanner(message: message).padding(16) }
                    }
                } else {
                    answering
                }
            }
            .background(Brand.background)
            .navigationTitle(modeTitle)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    if session == nil || session?.isFinished == true {
                        Button(session == nil ? "Annuler" : "Fermer") {
                            dictation.stop()
                            dismiss()
                        }
                    }
                }
            }
            .safeAreaInset(edge: .bottom) { bottomBar }
        }
        .onAppear { remaining = mode.seconds }
        .onReceive(ticker) { _ in tick() }
        .onChange(of: dictation.transcript) { _, text in
            if dictation.isRecording {
                usedVoice = true
                answer = text
            }
        }
    }

    private var modeTitle: String {
        switch mode {
        case .followUp: return "Relance"
        case .retry: return "Refaire en 2 min"
        }
    }

    private var answering: some View {
        VStack(alignment: .leading, spacing: 0) {
            VStack(alignment: .leading, spacing: 10) {
                HStack {
                    ChronoLabel(seconds: remaining, budget: mode.seconds, countdown: true)
                        .font(.title2.monospacedDigit().weight(.bold))
                    Spacer()
                    Chip(text: mode.kind == .followUp ? "+5 XP dès 60" : "+10 XP dès 70", tint: palette.accent)
                }
                switch mode {
                case .followUp(let question, _):
                    Text(question).font(.title3.weight(.semibold))
                case .retry:
                    Text("Même exercice, à l'oral, deux minutes. Reformulation, structure, chiffre, recommandation.")
                        .font(.headline)
                    Text(title).font(.subheadline).foregroundStyle(Brand.textSecondary)
                }
                if !started {
                    Text(mode.kind == .followUp ? "Le chrono démarre quand tu appuies sur le micro ou commences à écrire."
                                                : "Le chrono démarre avec le micro.")
                        .font(.footnote).foregroundStyle(Brand.textSecondary)
                }
            }
            .padding(16)
            AnswerEditor(text: $answer, placeholder: "Ta réponse…", recording: dictation.isRecording)
                .onChange(of: answer) { _, text in if !text.isEmpty { started = true } }
        }
    }

    @ViewBuilder private var bottomBar: some View {
        if session == nil {
            BottomActions {
                HStack(spacing: 12) {
                    MicButton(recording: dictation.isRecording) {
                        Task {
                            if dictation.isRecording { dictation.stop() } else {
                                started = true
                                await dictation.start(language: language, existing: answer)
                            }
                        }
                    }
                    Button("Envoyer") { submit() }
                        .buttonStyle(.pill)
                        .disabled(answer.trimmingCharacters(in: .whitespacesAndNewlines).count < 5)
                }
            }
        } else if session?.isFinished == true {
            BottomActions {
                Button("Terminer") { dismiss() }.buttonStyle(.pill)
            }
        }
    }

    private func tick() {
        guard started, session == nil, remaining > 0 else { return }
        remaining -= 1
        if remaining == 0 {
            dictation.stop()
            if answer.trimmingCharacters(in: .whitespacesAndNewlines).count >= 5 { submit() }
        }
    }

    private func submit() {
        guard session == nil else { return }
        dictation.stop()
        let request = GradeRequest(exerciseId: exerciseId, kind: mode.kind, answerText: answer,
                                   durationSeconds: mode.seconds - remaining, inputMode: usedVoice ? .voice : .text,
                                   parentAttemptId: mode.parentId)
        let session = GradingSession(request: request, title: title, type: type, language: language,
                                     isRevenge: false, model: model)
        self.session = session
        session.start()
    }
}

/// Admin only: marks a doubtful correction as bad, which takes it out of the revenges.
struct FlagButton: View {
    let exerciseId: ID
    @State var flagged: Bool
    @Environment(AppModel.self) private var model
    @State private var askNote = false
    @State private var note = ""

    var body: some View {
        Button {
            if flagged { Task { await send(false) } } else { askNote = true }
        } label: {
            Label(flagged ? "Corrigé marqué douteux (annuler)" : "Corrigé douteux", systemImage: flagged ? "flag.fill" : "flag")
                .font(.subheadline.weight(.semibold))
        }
        .buttonStyle(.pill(.secondary, compact: true))
        .alert("Qu'est-ce qui cloche ?", isPresented: $askNote) {
            TextField("Chiffrage faux, source morte…", text: $note)
            Button("Marquer douteux") { Task { await send(true) } }
            Button("Annuler", role: .cancel) {}
        } message: {
            Text("L'exercice sortira des revanches et servira à affiner le prompt de génération.")
        }
    }

    private func send(_ value: Bool) async {
        do {
            try await model.service.flag(exerciseId: exerciseId, flagged: value, note: value ? note : nil)
            flagged = value
        } catch {
            model.handle(error)
        }
    }
}
