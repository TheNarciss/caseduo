import CaseDuoCore
import Combine
import SwiftUI

/// An exercise: the statement, a chrono, the answer (typed full screen or dictated), the data on
/// request (−5 XP, like asking the interviewer), questions one at a time when the case is
/// interviewer-led, five slides for a cadrage à domicile.
struct ExerciseView: View {
    let exerciseId: ID
    let isRevenge: Bool

    @Environment(AppModel.self) private var model
    @Environment(\.pushRoute) private var pushRoute
    @State private var exercise: ExerciseDetail?
    @State private var loadError: String?
    @State private var pane: Pane = .statement
    @State private var answer = ""
    @State private var partAnswers: [String] = []
    @State private var partIndex = 0
    @State private var slides = SlideDraft.blankDeck()
    @State private var usedVoice = false
    @State private var startedAt = Date()
    @State private var now = Date()
    @State private var contextData: ContextData?
    @State private var showData = false
    @State private var confirmReveal = false
    @State private var revealing = false
    @State private var dictation = Dictation()

    enum Pane: String, CaseIterable { case statement = "Énoncé", answer = "Ma réponse" }

    private let ticker = Timer.publish(every: 1, on: .main, in: .common).autoconnect()

    var body: some View {
        Group {
            if let exercise {
                content(exercise)
            } else if let loadError {
                VStack(spacing: 16) {
                    ErrorBanner(message: loadError)
                    Button("Réessayer") { Task { await load() } }.buttonStyle(.pill(.secondary, compact: true))
                }
                .padding(24)
            } else {
                LoadingView()
            }
        }
        .background(Brand.background)
        .navigationBarTitleDisplayMode(.inline)
        .task { await load() }
        .onReceive(ticker) { now = $0 }
        .onChange(of: dictation.transcript) { _, text in
            guard dictation.isRecording else { return }
            usedVoice = true
            setCurrentAnswer(text)
        }
        .onDisappear { dictation.stop() }
    }

    private var elapsed: Int { Int(now.timeIntervalSince(startedAt)) }

    // MARK: Loading

    private func load() async {
        guard exercise == nil else { return }
        do {
            let detail = try await model.service.exercise(id: exerciseId)
            exercise = detail
            partAnswers = Array(repeating: "", count: detail.parts?.count ?? 0)
            if detail.isMBB || detail.revealed == true { contextData = detail.contextData }
            startedAt = Date()
            if detail.type == .cadrageHome { pane = .statement }
        } catch {
            model.handle(error)
            loadError = error.localizedDescription
        }
    }

    // MARK: Layout

    @ViewBuilder
    private func content(_ exercise: ExerciseDetail) -> some View {
        VStack(spacing: 0) {
            Picker("Vue", selection: $pane) {
                ForEach(Pane.allCases, id: \.self) { Text($0.rawValue).tag($0) }
            }
            .pickerStyle(.segmented)
            .padding(.horizontal, 16)
            .padding(.vertical, 8)

            switch pane {
            case .statement:
                StatementView(exercise: exercise, contextData: contextData, isRevenge: isRevenge) {
                    showData = true
                }
            case .answer:
                answerPane(exercise)
            }

            bottomBar(exercise)
        }
        .toolbar {
            ToolbarItem(placement: .principal) {
                VStack(spacing: 0) {
                    Text(exercise.displayType).font(.subheadline.weight(.semibold))
                    ChronoLabel(seconds: elapsed, budget: exercise.estimatedMinutes.map { $0 * 60 })
                }
            }
            ToolbarItem(placement: .topBarTrailing) {
                if exercise.contextDataAvailable == true {
                    Button {
                        if contextData != nil { showData = true } else { confirmReveal = true }
                    } label: {
                        Image(systemName: contextData != nil ? "tablecells.fill" : "tablecells")
                    }
                    .accessibilityLabel("Demander les données")
                }
            }
        }
        .confirmationDialog("Demander les données ?", isPresented: $confirmReveal, titleVisibility: .visible) {
            Button("Demander les données (−5 XP)") { Task { await reveal() } }
            Button("Annuler", role: .cancel) {}
        } message: {
            Text("En entretien, on pose la question à l'interviewer. Ici, ça coûte 5 XP si tu n'as pas encore répondu.")
        }
        .sheet(isPresented: $showData) {
            if let contextData { ContextDataSheet(data: contextData) }
        }
    }

    @ViewBuilder
    private func answerPane(_ exercise: ExerciseDetail) -> some View {
        if exercise.type == .cadrageHome {
            SlidesEditor(slides: $slides)
        } else if let parts = exercise.parts, !parts.isEmpty {
            PartAnswerView(parts: parts, index: $partIndex, answers: $partAnswers, recording: dictation.isRecording)
        } else {
            AnswerEditor(text: $answer, placeholder: placeholder(exercise), recording: dictation.isRecording)
        }
    }

    private func placeholder(_ exercise: ExerciseDetail) -> String {
        switch exercise.type {
        case .fit: return "Situation, tâche, action, résultat chiffré…"
        case .brainteaser: return "Ta méthode en trois étapes, puis le chiffre."
        default: return exercise.language == "en"
            ? "Restate, announce your structure, then go branch by branch…"
            : "Reformule, annonce ta structure, puis déroule branche par branche…"
        }
    }

    @ViewBuilder
    private func bottomBar(_ exercise: ExerciseDetail) -> some View {
        BottomActions {
            if case .denied(let message) = dictation.state {
                Text(message).font(.footnote).foregroundStyle(Brand.danger)
            } else if case .unavailable(let message) = dictation.state {
                Text(message).font(.footnote).foregroundStyle(Brand.danger)
            }
            HStack(spacing: 12) {
                if exercise.type != .cadrageHome {
                    MicButton(recording: dictation.isRecording) {
                        Task { await toggleDictation(exercise) }
                    }
                }
                if pane == .statement {
                    Button("Répondre") { withAnimation(Brand.quick) { pane = .answer } }
                        .buttonStyle(.pill)
                } else if let parts = exercise.parts, !parts.isEmpty, partIndex < parts.count - 1 {
                    Button("Question suivante") {
                        dictation.stop()
                        withAnimation(Brand.quick) { partIndex += 1 }
                    }
                    .buttonStyle(.pill)
                    .disabled((partAnswers[safe: partIndex] ?? "").trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                } else {
                    Button("Envoyer") { submit(exercise) }
                        .buttonStyle(.pill)
                        .disabled(!canSubmit(exercise))
                }
            }
        }
    }

    // MARK: Actions

    private func toggleDictation(_ exercise: ExerciseDetail) async {
        Haptics.shared.play(.tap)
        if dictation.isRecording {
            dictation.stop()
            return
        }
        if pane == .statement { pane = .answer }
        await dictation.start(language: exercise.language, existing: currentAnswer)
    }

    private var currentAnswer: String {
        if let count = exercise?.parts?.count, count > 0 { return partAnswers[safe: partIndex] ?? "" }
        return answer
    }

    private func setCurrentAnswer(_ text: String) {
        if let count = exercise?.parts?.count, count > 0, partAnswers.indices.contains(partIndex) {
            partAnswers[partIndex] = text
        } else {
            answer = text
        }
    }

    private func canSubmit(_ exercise: ExerciseDetail) -> Bool {
        if exercise.type == .cadrageHome { return slides.allSatisfy(\.isComplete) }
        if exercise.hasParts { return partAnswers.allSatisfy { !$0.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty } }
        return answer.trimmingCharacters(in: .whitespacesAndNewlines).count >= 20
    }

    private func reveal() async {
        guard !revealing else { return }
        revealing = true
        defer { revealing = false }
        do {
            let response = try await model.service.reveal(id: exerciseId)
            contextData = response.contextData
            showData = true
        } catch {
            model.handle(error)
        }
    }

    private func submit(_ exercise: ExerciseDetail) {
        dictation.stop()
        let request: GradeRequest
        if exercise.type == .cadrageHome {
            request = GradeRequest(exerciseId: exercise.id, kind: .main, answerText: SlideDraft.answerText(from: slides),
                                   durationSeconds: elapsed, inputMode: .text, slides: SlideDraft.slides(from: slides))
        } else if let parts = exercise.parts, !parts.isEmpty {
            request = GradeRequest(exerciseId: exercise.id, kind: .main,
                                   answerText: PartAnswers.answerText(parts: parts, answers: partAnswers),
                                   durationSeconds: elapsed, inputMode: usedVoice ? .voice : .text, partAnswers: partAnswers)
        } else {
            request = GradeRequest(exerciseId: exercise.id, kind: .main, answerText: answer, durationSeconds: elapsed,
                                   inputMode: usedVoice ? .voice : .text)
        }
        let session = GradingSession(request: request, title: exercise.title, type: exercise.type,
                                     language: exercise.language, isRevenge: isRevenge || exercise.isRevenge == true,
                                     model: model)
        session.start()
        pushRoute(.result(session))
    }
}

extension Array {
    subscript(safe index: Int) -> Element? { indices.contains(index) ? self[index] : nil }
}

// MARK: - Pieces

/// The statement, as an interviewer would say it.
struct StatementView: View {
    let exercise: ExerciseDetail
    let contextData: ContextData?
    let isRevenge: Bool
    let showData: () -> Void
    @Environment(\.palette) private var palette

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 14) {
                HStack(spacing: 6) {
                    DifficultyDots(level: exercise.difficulty, tint: palette.accent)
                    ExerciseTags(language: exercise.language, style: exercise.style, minutes: exercise.estimatedMinutes,
                                 sector: exercise.sector)
                }
                if isRevenge || exercise.isRevenge == true {
                    Label("Revanche : tu l'avais raté, XP ×1,2", systemImage: "arrow.uturn.backward")
                        .font(.subheadline.weight(.semibold))
                        .foregroundStyle(Brand.revenge)
                }
                Text(exercise.title).font(.title2.weight(.bold))
                MarkdownText(markdown: exercise.prompt)
                if let parts = exercise.parts, !parts.isEmpty {
                    Label("L'interviewer posera \(parts.count) questions, une à la fois.", systemImage: "person.wave.2")
                        .font(.subheadline)
                        .foregroundStyle(Brand.textSecondary)
                }
                if let contextData, exercise.isMBB {
                    ContextDataList(data: contextData).padding(.top, 4)
                } else if contextData != nil {
                    Button(action: showData) { Label("Voir les données obtenues", systemImage: "tablecells.fill") }
                        .buttonStyle(.pill(.secondary, compact: true))
                }
            }
            .padding(20)
        }
    }
}

/// The answer, full screen.
struct AnswerEditor: View {
    @Binding var text: String
    let placeholder: String
    let recording: Bool
    @FocusState private var focused: Bool

    var body: some View {
        ZStack(alignment: .topLeading) {
            if text.isEmpty {
                Text(recording ? "Je t'écoute…" : placeholder)
                    .foregroundStyle(Brand.textTertiary)
                    .padding(.horizontal, 21)
                    .padding(.vertical, 18)
            }
            TextEditor(text: $text)
                .focused($focused)
                .scrollContentBackground(.hidden)
                .padding(.horizontal, 16)
                .padding(.vertical, 10)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Brand.card)
        .overlay(alignment: .topTrailing) {
            if recording {
                Label("Dictée", systemImage: "waveform").font(.caption.weight(.bold)).foregroundStyle(Brand.danger)
                    .padding(10)
                    .symbolEffect(.variableColor.iterative, isActive: recording)
            }
        }
    }
}

/// One question at a time, for interviewer-led cases and the fit mock.
struct PartAnswerView: View {
    let parts: [ExercisePart]
    @Binding var index: Int
    @Binding var answers: [String]
    let recording: Bool

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            VStack(alignment: .leading, spacing: 8) {
                Text("Question \(index + 1) sur \(parts.count)").font(.caption.weight(.bold)).foregroundStyle(Brand.textSecondary)
                Text(parts[index].question).font(.headline)
                if let data = parts[index].data, !data.isEmpty {
                    Label(data, systemImage: "tablecells").font(.subheadline).foregroundStyle(Brand.mbb)
                }
                if index > 0 {
                    Button("Question précédente") { index -= 1 }.font(.footnote)
                }
            }
            .padding(16)
            AnswerEditor(text: Binding(get: { answers[safe: index] ?? "" },
                                       set: { if answers.indices.contains(index) { answers[index] = $0 } }),
                         placeholder: "Ta réponse à cette question…", recording: recording)
        }
    }
}

/// The microphone: tap to dictate, tap again to stop.
struct MicButton: View {
    let recording: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Image(systemName: recording ? "stop.fill" : "mic.fill")
                .font(.title2.weight(.bold))
                .foregroundStyle(recording ? Color.black : Color.white)
                .frame(width: 56, height: 56)
                .background(recording ? Brand.danger : Brand.cardRaised, in: Circle())
                .symbolEffect(.pulse, isActive: recording)
        }
        .accessibilityLabel(recording ? "Arrêter la dictée" : "Répondre à l'oral")
    }
}

/// The data, as the interviewer would give it.
struct ContextDataSheet: View {
    let data: ContextData
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            ScrollView { ContextDataList(data: data).padding(20) }
                .background(Brand.background)
                .navigationTitle("Données")
                .navigationBarTitleDisplayMode(.inline)
                .toolbar { ToolbarItem(placement: .confirmationAction) { Button("OK") { dismiss() } } }
        }
        .presentationDetents([.medium, .large])
    }
}

struct ContextDataList: View {
    let data: ContextData

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            ForEach(Array((data.facts ?? []).enumerated()), id: \.offset) { _, fact in
                VStack(alignment: .leading, spacing: 4) {
                    HStack(alignment: .firstTextBaseline) {
                        Text(fact.label).font(.subheadline).foregroundStyle(Brand.textSecondary)
                        Spacer()
                        if fact.hypothesis == true { Chip(text: "hypothèse", tint: Brand.danger) }
                    }
                    Text(fact.value).font(.headline)
                    if let source = fact.sourceUrl, let url = URL(string: source) {
                        Link(destination: url) {
                            Label(url.host() ?? source, systemImage: "link").font(.caption)
                        }
                    }
                }
                .padding(14)
                .card(radius: 14)
            }
            if let constraints = data.constraints, !constraints.isEmpty {
                Text("Contraintes").font(.headline)
                ForEach(constraints, id: \.self) { Label($0, systemImage: "exclamationmark.circle").font(.subheadline) }
            }
            ForEach(Array((data.documents ?? []).enumerated()), id: \.offset) { _, document in
                VStack(alignment: .leading, spacing: 8) {
                    Text(document.title).font(.headline)
                    MarkdownText(markdown: document.body, font: .subheadline)
                }
                .padding(14)
                .card(radius: 14)
            }
            if data.isEmpty {
                Text("Pas de données chiffrées pour cet exercice : pose tes hypothèses.").foregroundStyle(Brand.textSecondary)
            }
        }
    }
}
