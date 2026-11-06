import Foundation
import XCTest
@testable import CaseDuoCore

/// Every response the backend really sends, decoded with the app's types.
///
/// The JSON files in Fixtures/backend are written by the backend's own test suite
/// (`UPDATE_CONTRACT_FIXTURES=1 pytest tests/integration/test_contract.py`), from a full
/// scenario: login, today, an exercise, a reveal, a grading and its follow-up, the SSE events,
/// history, league, badges, widget, end of day, a Sunday mock. If the backend changes a shape
/// the app relies on, this fails here rather than on the phone.
final class BackendContractTests: XCTestCase {
    private func load(_ name: String) throws -> Data {
        let url = try XCTUnwrap(
            Bundle.module.url(forResource: name, withExtension: "json", subdirectory: "Fixtures/backend"),
            "missing fixture \(name).json"
        )
        return try Data(contentsOf: url)
    }

    private func decode<T: Decodable>(_ type: T.Type, _ name: String) throws -> T {
        do {
            return try CaseDuoJSON.decoder.decode(T.self, from: try load(name))
        } catch let DecodingError.keyNotFound(key, context) {
            XCTFail("\(name).json: key \(key.stringValue) missing at \(context.codingPath.map(\.stringValue))")
            throw DecodingError.keyNotFound(key, context)
        } catch let DecodingError.typeMismatch(type, context) {
            XCTFail("\(name).json: \(type) expected at \(context.codingPath.map(\.stringValue))")
            throw DecodingError.typeMismatch(type, context)
        }
    }

    func testAuthAndProfile() throws {
        XCTAssertTrue(try decode(Providers.self, "providers").apple)
        let me = try decode(Me.self, "me")
        XCTAssertNotNil(me.storyText)
        XCTAssertEqual(me.commitment?.isActive, true)
    }

    func testTraining() throws {
        let training = try decode(Training.self, "training")
        XCTAssertEqual(training.exercises.count, 30)
        XCTAssertTrue(training.exercises.allSatisfy { $0.isBonus == true && $0.fromPack == true })
        XCTAssertEqual(training.types.map(\.total).reduce(0, +), 30)
    }

    func testToday() throws {
        let today = try decode(Today.self, "today")
        XCTAssertFalse(today.cards.isEmpty)
        XCTAssertEqual(today.cards.first?.type, .brainteaser)
        _ = try decode(WidgetInfo.self, "widget")
        _ = try decode(DaySummary.self, "day_summary")
    }

    func testExerciseRevealAndGrading() throws {
        _ = try decode(ExerciseDetail.self, "exercise")
        let reveal = try decode(RevealResponse.self, "reveal")
        XCTAssertFalse(reveal.contextData.facts?.isEmpty ?? true)
        let result = try decode(GradeResult.self, "grade_result")
        XCTAssertFalse(result.attempt.rubricScores?.isEmpty ?? true)
        let followUp = try decode(GradeResult.self, "grade_result_follow_up")
        XCTAssertEqual(followUp.attempt.kind, .followUp)
        _ = try decode(ScoresPayload.self, "sse_scores")
        _ = try decode([AttemptSummary].self, "attempts")
        _ = try decode(Attempt.self, "attempt")
    }

    func testOtherScreens() throws {
        let history = try decode(History.self, "history")
        XCTAssertFalse(history.series.isEmpty)
        let league = try decode(League.self, "league")
        XCTAssertEqual(league.members.count, 6)
        let badges = try decode([Badge].self, "badges")
        XCTAssertFalse(badges.isEmpty)
    }

    func testMock() throws {
        let run = try decode(MockRun.self, "mock_run")
        XCTAssertEqual(run.steps.count, 3)
        _ = try decode(MockFinish.self, "mock_finish")
    }

    func testPath() throws {
        let path = try decode(PathView.self, "path")
        XCTAssertEqual(path.activeNode, "d1.showcase")
        XCTAssertEqual(path.units.first?.nodes.count, 5)
        let lesson = try decode(LessonStart.self, "path_lesson")
        XCTAssertEqual(Set(lesson.items.map(\.format)).count, PathFormat.allCases.count - 1, "one item per format")
        XCTAssertFalse(lesson.items.contains { $0.payload == .unknown })
        let done = try decode(LessonCompletion.self, "path_complete")
        XCTAssertEqual(done.oral?.first?.score, 100)
        XCTAssertEqual(done.progress?.xpToday, 55)
    }

    func testErrors() throws {
        XCTAssertNotNil(try decode(APIErrorBody.self, "error_404").detail)
        XCTAssertNotNil(try decode(APIErrorBody.self, "error_422").detail)
    }
}
