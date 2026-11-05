import CaseDuoCore
import Foundation
import Observation

/// One answer being graded: the stream of `POST /grade/stream` turned into screen state.
/// The score arrives first (animation, haptic), then the feedback as it is written, then the
/// interviewer's follow-up question.
@MainActor
@Observable
final class GradingSession: Identifiable, Hashable {
    enum Phase: Equatable { case grading, done, failed(String) }

    let id = UUID()
    let request: GradeRequest
    let title: String
    let type: ExerciseType
    let language: String
    let isRevenge: Bool

    private(set) var state = GradeStreamState()
    private(set) var phase: Phase = .grading
    /// The score as shown: counts up from 0 when the real one arrives.
    var displayedScore = 0

    @ObservationIgnored private weak var model: AppModel?
    @ObservationIgnored private var task: Task<Void, Never>?
    @ObservationIgnored private var playedScoreHaptic = false

    init(request: GradeRequest, title: String, type: ExerciseType, language: String, isRevenge: Bool, model: AppModel) {
        self.request = request
        self.title = title
        self.type = type
        self.language = language
        self.isRevenge = isRevenge
        self.model = model
    }

    nonisolated static func == (lhs: GradingSession, rhs: GradingSession) -> Bool { lhs.id == rhs.id }
    nonisolated func hash(into hasher: inout Hasher) { hasher.combine(id) }

    var result: GradeResult? { state.result }
    var attempt: Attempt? { state.result?.attempt }
    var score: Int? { state.score }
    var followUp: String? { state.followUp }
    var isFinished: Bool { phase != .grading }

    func start(streaming: Bool = true) {
        guard task == nil, let model else { return }
        Haptics.shared.play(.answerSent)
        Sounds.shared.play(.send)
        let service = model.service
        let request = request
        task = Task { [weak self] in
            guard let self else { return }
            if streaming {
                do {
                    for try await event in service.gradeStream(request) {
                        self.receive(event)
                    }
                    if self.state.result == nil, self.state.error == nil {
                        // The stream ended without its last event: ask for the stored result.
                        if !self.state.hasScores { await self.gradeWithoutStream(service) } else {
                            self.fail("La correction s'est interrompue. Retrouve-la dans l'historique.")
                        }
                    }
                } catch {
                    if self.state.hasScores {
                        // The attempt may already be saved: do not grade (and pay) twice.
                        self.fail(error.localizedDescription + " La note est enregistrée dans l'historique.")
                    } else if (error as? APIError) == .unauthorized {
                        self.model?.handle(error)
                        self.fail(error.localizedDescription)
                    } else if case .aiUnavailable? = error as? APIError {
                        self.fail(error.localizedDescription)
                    } else {
                        await self.gradeWithoutStream(service)
                    }
                }
            } else {
                await self.gradeWithoutStream(service)
            }
        }
    }

    private func gradeWithoutStream(_ service: CaseDuoService) async {
        do {
            let result = try await service.grade(request)
            receive(.scores(ScoresPayload(rubricScores: result.attempt.rubricScores ?? [], score: result.attempt.score ?? 0)))
            receive(.done(result))
        } catch {
            model?.handle(error)
            fail(error.localizedDescription)
        }
    }

    private func receive(_ event: GradeStreamEvent) {
        state.apply(event)
        switch event {
        case .scores(let payload):
            playScore(payload.score)
        case .done(let result):
            if let score = result.attempt.score { playScore(score) }
            phase = .done
            model?.didGrade(result)
        case .error(let error):
            fail(APIError.stream(error).localizedDescription)
        default:
            break
        }
    }

    private func playScore(_ score: Int) {
        guard !playedScoreHaptic else { return }
        playedScoreHaptic = true
        Haptics.shared.play(HapticPattern.forScore(score))
        if score >= 80 { Sounds.shared.play(.success) }
    }

    private func fail(_ message: String) {
        phase = .failed(message)
    }

    func cancel() {
        task?.cancel()
    }
}
