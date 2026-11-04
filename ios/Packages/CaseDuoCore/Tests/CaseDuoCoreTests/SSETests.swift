import Foundation
import XCTest
@testable import CaseDuoCore

final class SSETests: XCTestCase {
    func testParsesTheBackendStream() throws {
        var parser = SSELineParser()
        var state = GradeStreamState()
        var events: [GradeStreamEvent] = []
        for line in DemoFixtures.gradeStreamLines {
            if let message = parser.consume(line) {
                let event = try GradeStreamEvent.decode(message)
                events.append(event)
                state.apply(event)
            }
        }
        XCTAssertEqual(events.count, 5)
        guard case .scores(let scores) = events[0] else { return XCTFail("scores first") }
        XCTAssertEqual(scores.score, 72)
        XCTAssertTrue(state.isFinished)
        XCTAssertEqual(state.score, 72)
        XCTAssertEqual(state.result?.progress.remaining, 5)
        XCTAssertEqual(state.rubricScores.count, 5, "the final attempt replaces the early scores")
        XCTAssertTrue(state.feedback.contains("En 30 secondes"))
    }

    func testWithoutBlankLines() throws {
        // AsyncLineSequence drops empty lines: the parser must not need them.
        var parser = SSELineParser()
        let lines = DemoFixtures.gradeStreamLines.filter { !$0.isEmpty }
        let messages = lines.compactMap { parser.consume($0) }
        XCTAssertEqual(messages.map(\.event), ["scores", "feedback", "feedback", "follow_up", "done"])
    }

    func testFeedbackDeltasConcatenate() throws {
        var state = GradeStreamState()
        state.apply(.feedback("### Ce qui"))
        state.apply(.feedback(" était bien\n- A"))
        XCTAssertEqual(state.feedback, "### Ce qui était bien\n- A")
        XCTAssertFalse(state.isFinished)
        XCTAssertFalse(state.hasScores)
    }

    func testErrorEventAndUnknownEvents() throws {
        var parser = SSELineParser()
        XCTAssertNil(parser.consume("event: error"))
        let message = try XCTUnwrap(parser.consume(#"data: {"reason": "overloaded", "detail": "Réessaie"}"#))
        let event = try GradeStreamEvent.decode(message)
        XCTAssertEqual(event, .error(StreamError(reason: "overloaded", detail: "Réessaie")))
        XCTAssertNil(parser.consume("event: ping"))
        let ping = try XCTUnwrap(parser.consume("data: {}"))
        XCTAssertEqual(try GradeStreamEvent.decode(ping), .ignored("ping"))
    }

    func testDataWithoutEventIsAMessageAndCRLFIsTrimmed() {
        var parser = SSELineParser()
        let message = parser.consume("data: {\"x\": 1}\r")
        XCTAssertEqual(message, SSEMessage(event: "message", data: "{\"x\": 1}"))
        XCTAssertNil(parser.consume("id: 3"))
        XCTAssertNil(parser.consume("retry: 1000"))
    }

    func testFeedbackSections() {
        let markdown = "### Ce qui était bien\n- Clair\n### À corriger\n- Dis plutôt X\n### En 30 secondes tu aurais dû dire\nJe recommande Y."
        let sections = FeedbackSection.parse(markdown)
        XCTAssertEqual(sections.map(\.kind), [.strengths, .fixes, .thirtySeconds])
        XCTAssertEqual(sections[2].body, "Je recommande Y.")
        let partial = FeedbackSection.parse("### Ce qui était bien\n- Cl")
        XCTAssertEqual(partial.count, 1)
        XCTAssertEqual(partial[0].body, "- Cl")
        XCTAssertEqual(FeedbackSection.parse("Sans titre").first?.kind, .other)
    }
}
