import Foundation
import XCTest
@testable import CaseDuoCore

/// Every shape of docs/API.md decodes, as the backend writes it.
final class ContractTests: XCTestCase {
    private func decode<T: Decodable>(_ type: T.Type, _ json: String) throws -> T {
        try CaseDuoJSON.decoder.decode(T.self, from: Data(json.utf8))
    }

    func testMe() throws {
        let me = try decode(Me.self, DemoFixtures.me)
        XCTAssertEqual(me.dailyGoalXp, 50)
        XCTAssertEqual(me.timezone, "Asia/Singapore")
        XCTAssertNotNil(me.storyUpdatedAt, "six fractional digits must parse")
        XCTAssertEqual(me.isAdmin, true)
    }

    func testToday() throws {
        let today = try decode(Today.self, DemoFixtures.today)
        XCTAssertEqual(today.cards.count, 7)
        XCTAssertEqual(today.cards.first?.type, .cadrageHome)
        XCTAssertEqual(today.cards.first?.pinned, true)
        XCTAssertEqual(today.streak.status, .atRisk)
        XCTAssertEqual(today.goal.fraction, 0.4, accuracy: 0.001)
        XCTAssertEqual(today.mock?.kind, "full")
        XCTAssertEqual(today.unlocks?.streak30Icon, false)
        XCTAssertEqual(today.league?.tierLabel, "Argent")
        let revenge = try XCTUnwrap(today.cards.last)
        XCTAssertTrue(revenge.isRevenge)
        XCTAssertNotEqual(revenge.id, revenge.exerciseId, "a revenge card has its own identity")
        XCTAssertTrue(today.cards[4].isMBB)
    }

    func testUnknownTypesDoNotBreakDecoding() throws {
        let json = DemoFixtures.today.replacingOccurrences(of: "\"type\": \"fit\"", with: "\"type\": \"case_vocal\"")
        let today = try decode(Today.self, json)
        XCTAssertTrue(today.cards.contains { $0.type == .unknown })
    }

    func testExerciseAndParts() throws {
        let exercise = try decode(ExerciseDetail.self, DemoFixtures.exercise)
        XCTAssertFalse(exercise.hasParts)
        XCTAssertNil(exercise.contextData)
        let parts = try decode(ExerciseDetail.self, DemoFixtures.partsExercise)
        XCTAssertTrue(parts.hasParts)
        XCTAssertTrue(parts.isMBB)
        XCTAssertEqual(parts.parts?[1].data, "1,200 engines in service, 6% unscheduled visits a year.")
        XCTAssertEqual(parts.contextData?.facts?.first?.hypothesis, true)
    }

    func testReveal() throws {
        let reveal = try decode(RevealResponse.self, DemoFixtures.contextData)
        XCTAssertEqual(reveal.xpPenalty, 5)
        XCTAssertEqual(reveal.contextData.facts?.count, 2)
        XCTAssertEqual(reveal.contextData.facts?.first?.sourceUrl, "https://www.changiairport.com")
    }

    func testAttemptAndGradeResult() throws {
        let attempt = try decode(Attempt.self, DemoFixtures.attempt)
        XCTAssertEqual(attempt.score, 72)
        XCTAssertEqual(attempt.rubricScores?.count, 5)
        XCTAssertEqual(attempt.exercise?.rubric?.first?.levels?["2"], "Plan annoncé et suivi")
        XCTAssertEqual(attempt.kind, .main)
        let result = try decode(GradeResult.self, DemoFixtures.gradeResult)
        XCTAssertEqual(result.progress.remaining, 5)
        XCTAssertEqual(result.xp.breakdown?.first?.xp, 20)
    }

    func testOtherScreens() throws {
        let widget = try decode(WidgetInfo.self, DemoFixtures.widget)
        XCTAssertEqual(widget.goalXp, 50)
        let summary = try decode(DaySummary.self, DemoFixtures.daySummary)
        XCTAssertEqual(summary.weakestCriterion?.key, "structure")
        let history = try decode(History.self, DemoFixtures.history)
        XCTAssertEqual(history.series.count, 3)
        XCTAssertEqual(history.calendar[1].freezeUsed, true)
        let league = try decode(League.self, DemoFixtures.league)
        XCTAssertEqual(league.members.count, 6)
        XCTAssertNotNil(league.endsAt)
        let badges = try decode([Badge].self, DemoFixtures.badges)
        XCTAssertNil(badges.last?.earnedAt)
        let run = try decode(MockRun.self, DemoFixtures.mockRun)
        XCTAssertEqual(run.steps.filter(\.followUpAfter).count, 2)
        let finish = try decode(MockFinish.self, DemoFixtures.mockFinish)
        XCTAssertEqual(finish.previous?.count, 2)
        let providers = try decode(Providers.self, DemoFixtures.providers)
        XCTAssertTrue(providers.apple)
    }

    func testLeagueZones() throws {
        var league = try decode(League.self, DemoFixtures.league)
        XCTAssertEqual(league.zone(of: 1), .promotion)
        XCTAssertEqual(league.zone(of: 3), .safe)
        XCTAssertEqual(league.zone(of: 6), .relegation)
        league.tier = "bronze"
        XCTAssertEqual(league.zone(of: 6), .safe, "nobody falls below bronze")
        league.tier = "gold"
        XCTAssertEqual(league.zone(of: 1), .safe, "nothing above gold")
    }

    func testGradeRequestEncodesSnakeCaseAndSkipsNils() throws {
        let request = GradeRequest(exerciseId: "ex-ms", kind: .retry2min, answerText: "…", durationSeconds: 118,
                                   inputMode: .voice, parentAttemptId: "att-1")
        let json = String(decoding: try CaseDuoJSON.encoder.encode(request), as: UTF8.self)
        XCTAssertTrue(json.contains("\"exercise_id\":\"ex-ms\""))
        XCTAssertTrue(json.contains("\"kind\":\"retry_2min\""))
        XCTAssertTrue(json.contains("\"parent_attempt_id\":\"att-1\""))
        XCTAssertTrue(json.contains("\"duration_seconds\":118"))
        XCTAssertFalse(json.contains("mock_run_id"))
        XCTAssertFalse(json.contains("slides"))
    }

    func testPatchEncodesOnlySetFields() throws {
        let json = String(decoding: try CaseDuoJSON.encoder.encode(MePatch(dailyGoalXp: 80)), as: UTF8.self)
        XCTAssertEqual(json, "{\"daily_goal_xp\":80}")
    }

    func testAPIErrorBodyAcceptsValidationLists() throws {
        let plain = try decode(APIErrorBody.self, #"{"detail": "Exercice inconnu", "type": "NotFound"}"#)
        XCTAssertEqual(plain.detail, "Exercice inconnu")
        let validation = try decode(APIErrorBody.self, #"{"detail": [{"loc": ["body"], "msg": "x"}]}"#)
        XCTAssertNil(validation.detail)
    }

    func testISODates() {
        XCTAssertNotNil(ISODate.parse("2026-11-04T08:00:00+00:00"))
        XCTAssertNotNil(ISODate.parse("2026-11-04T08:00:00.123456+08:00"))
        XCTAssertNotNil(ISODate.parse("2026-11-04T08:00:00Z"))
        XCTAssertNotNil(ISODate.parse("2026-11-04T08:00:00.5Z"))
        XCTAssertEqual(ISODate.normalizeFraction("2026-11-04T08:00:00.123456+08:00"), "2026-11-04T08:00:00.123+08:00")
        let a = ISODate.parse("2026-11-04T08:00:00.999999+00:00")!
        let b = ISODate.parse("2026-11-04T08:00:00+00:00")!
        XCTAssertEqual(a.timeIntervalSince(b), 0.999, accuracy: 0.002)
    }
}
