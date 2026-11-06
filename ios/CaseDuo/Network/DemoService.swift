import CaseDuoCore
import Foundation

/// Canned answers, no network (`-uiDemo YES`, previews, CI screenshots). The data is the same
/// JSON the tests check against the contract, so what the screenshots show is what the backend
/// would send.
final class DemoService: CaseDuoService, @unchecked Sendable {
    private let decoder = CaseDuoJSON.decoder

    private func load<T: Decodable>(_ json: String) throws -> T {
        try decoder.decode(T.self, from: Data(json.utf8))
    }

    private func pause(_ seconds: Double = 0.25) async {
        try? await Task.sleep(nanoseconds: UInt64(seconds * 1_000_000_000))
    }

    func providers() async throws -> Providers { try load(DemoFixtures.providers) }
    func login(email: String, password: String) async throws { await pause() }
    func loginWithApple(_ body: AppleLogin) async throws { await pause() }
    func logout() async throws {}
    func renewSession() async throws {}
    func me() async throws -> Me { try load(DemoFixtures.me) }

    func updateMe(_ patch: MePatch) async throws -> Me {
        var me: Me = try load(DemoFixtures.me)
        if let v = patch.displayName { me.displayName = v }
        if let v = patch.timezone { me.timezone = v }
        if let v = patch.dailyGoalXp { me.dailyGoalXp = v }
        if let v = patch.soundsEnabled { me.soundsEnabled = v }
        if let v = patch.notificationsEnabled { me.notificationsEnabled = v }
        return me
    }

    func updateStory(_ text: String) async throws -> Me {
        var me: Me = try load(DemoFixtures.me)
        me.storyText = text
        me.storyUpdatedAt = Date()
        return me
    }

    func registerPushToken(_ body: PushTokenRegistration) async throws {}
    func deleteAccount() async throws {}

    func today() async throws -> Today { try load(DemoFixtures.today) }
    func widget() async throws -> WidgetInfo { try load(DemoFixtures.widget) }
    func daySummary() async throws -> DaySummary { try load(DemoFixtures.daySummary) }

    func exercise(id: ID) async throws -> ExerciseDetail {
        await pause()
        if id == "ex-cad" { return try load(DemoFixtures.partsExercise) }
        var detail: ExerciseDetail = try load(DemoFixtures.exercise)
        let cards = ((try? load(DemoFixtures.today) as Today)?.cards ?? [])
            + ((try? load(DemoFixtures.training) as Training)?.exercises ?? [])
        if let card = cards.first(where: { $0.exerciseId == id }) {
            detail.id = card.exerciseId
            detail.type = card.type
            detail.typeLabel = card.typeLabel
            detail.title = card.title
            detail.language = card.language
            detail.difficulty = card.difficulty
            detail.style = card.style
            detail.isRevenge = card.isRevenge
        }
        return detail
    }

    func reveal(id: ID) async throws -> RevealResponse { try load(DemoFixtures.contextData) }

    func grade(_ request: GradeRequest) async throws -> GradeResult {
        await pause(1.0)
        var result: GradeResult = try load(DemoFixtures.gradeResult)
        result.attempt.kind = request.kind
        result.attempt.exerciseId = request.exerciseId
        result.attempt.mockRunId = request.mockRunId
        return result
    }

    func gradeStream(_ request: GradeRequest) -> AsyncThrowingStream<GradeStreamEvent, Error> {
        AsyncThrowingStream { continuation in
            let task = Task {
                var parser = SSELineParser()
                for line in DemoFixtures.gradeStreamLines {
                    try? await Task.sleep(nanoseconds: 180_000_000)
                    if let message = parser.consume(line), let event = try? GradeStreamEvent.decode(message) {
                        continuation.yield(event)
                    }
                }
                continuation.finish()
            }
            continuation.onTermination = { _ in task.cancel() }
        }
    }

    func attempts(limit: Int) async throws -> [AttemptSummary] { (try load(DemoFixtures.history) as History).recentAttempts ?? [] }
    func attempt(id: ID) async throws -> Attempt { try load(DemoFixtures.attempt) }
    func training() async throws -> Training { try load(DemoFixtures.training) }

    func commit(_ request: CommitmentRequest) async throws -> Me {
        await pause()
        var me: Me = try load(DemoFixtures.me)
        me.dailyGoalXp = request.dailyXp
        return me
    }
    func history(days: Int) async throws -> History { try load(DemoFixtures.history) }
    func league() async throws -> League { try load(DemoFixtures.league) }
    func badges() async throws -> [Badge] { try load(DemoFixtures.badges) }
    func startMock(kind: String) async throws -> MockRun { try load(DemoFixtures.mockRun) }
    func mock(id: ID) async throws -> MockRun { try load(DemoFixtures.mockRun) }
    func finishMock(id: ID) async throws -> MockFinish { await pause(1.0); return try load(DemoFixtures.mockFinish) }
    func flag(exerciseId: ID, flagged: Bool, note: String?) async throws {}

    // MARK: Parcours (the showcase lesson, every format once; progress is not kept)

    func path() async throws -> PathView { try load(DemoFixtures.path) }
    func startNode(code: String, seed: Int?) async throws -> LessonStart { await pause(); return try load(DemoFixtures.pathLesson) }
    func completeNode(code: String, _ body: LessonCompletionRequest) async throws -> LessonCompletion {
        await pause(0.6)
        var done: LessonCompletion = try load(DemoFixtures.pathComplete)
        let graded = body.results.filter { $0.transcript == nil }
        if !graded.isEmpty { done.score = Int((Double(graded.filter(\.correct).count) / Double(graded.count) * 100).rounded()) }
        done.xp = done.score == 100 ? 15 : 10
        if body.results.allSatisfy({ $0.transcript == nil }) { done.oral = nil }
        return done
    }
    func flagItem(id: String, note: String?) async throws -> FlagResult {
        try load(#"{"id": "\(id)", "flag_count": 1, "retired": false}"#)
    }
}
