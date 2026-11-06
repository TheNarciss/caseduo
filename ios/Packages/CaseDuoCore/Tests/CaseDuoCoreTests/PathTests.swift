import Foundation
import XCTest
@testable import CaseDuoCore

/// The Parcours on the phone: every format decodes from the backend's showcase lesson, grades
/// deterministically, and a lesson session re-asks mistakes, scores first tries, and builds what
/// the server expects.
final class PathTests: XCTestCase {
    private var lesson: LessonStart!
    private var byFormat: [PathFormat: PathItem] = [:]

    override func setUpWithError() throws {
        lesson = try CaseDuoJSON.decoder.decode(LessonStart.self, from: Data(DemoFixtures.pathLesson.utf8))
        byFormat = Dictionary(lesson.items.map { ($0.format, $0) }, uniquingKeysWith: { a, _ in a })
    }

    private func item(_ format: PathFormat) throws -> PathItem { try XCTUnwrap(byFormat[format], "no \(format) in showcase") }

    func testShowcaseCoversEveryFormat() throws {
        let missing = PathFormat.allCases.filter { $0 != .unknown && byFormat[$0] == nil }
        XCTAssertEqual(missing, [], "showcase lesson lacks formats")
        XCTAssertEqual(lesson.items.first?.format, .conceptCard)
        XCTAssertEqual(lesson.items.last?.format, .oralPrompt)
        XCTAssertEqual(lesson.xp, 10)
        for it in lesson.items where it.format != .conceptCard && it.format != .oralPrompt {
            XCTAssertFalse(it.explanation.isEmpty, "\(it.id) without explanation")
            if case .unknown = it.payload { XCTFail("\(it.id) payload not decoded") }
        }
    }

    func testPathDecodesWithStatuses() throws {
        let path = try CaseDuoJSON.decoder.decode(PathView.self, from: Data(DemoFixtures.path.utf8))
        XCTAssertEqual(path.active?.code, "d1.showcase")
        XCTAssertEqual(path.units.first?.nodes.map(\.status), [.active, .locked, .locked, .locked, .locked])
        XCTAssertEqual(path.units.first?.nodes.map(\.kind), [.lesson, .review, .applied, .checkpoint, .legendary])
        let done = try CaseDuoJSON.decoder.decode(LessonCompletion.self, from: Data(DemoFixtures.pathComplete.utf8))
        XCTAssertEqual(done.score, 81)
        XCTAssertEqual(done.oral?.first?.criteria.count, 3)
        XCTAssertEqual(done.nextNode, "d1.review")
    }

    func testUnknownFormatFallsBackInsteadOfFailing() throws {
        let json = #"{"id": "x.y.001", "format": "hologram", "skill": "x.y", "payload": {"anything": 1}}"#
        let it = try CaseDuoJSON.decoder.decode(PathItem.self, from: Data(json.utf8))
        XCTAssertEqual(it.format, .unknown)
        XCTAssertEqual(it.payload, .unknown)
        XCTAssertFalse(it.format.isGraded)
    }

    // MARK: Grading per format

    func testChoiceFormats() throws {
        for format in [PathFormat.chooseStructure, .pickSoWhat, .firstQuestion, .treeComplete] {
            let it = try item(format)
            XCTAssertTrue(PathGrader.grade(it, .option("a")).correct, "\(format)")
            let wrong = PathGrader.grade(it, .option("b"))
            XCTAssertFalse(wrong.correct)
            XCTAssertNotNil(wrong.whyWrong, "\(format) distractor without why_wrong")
            XCTAssertNotNil(wrong.expected)
        }
    }

    func testSwipeUsesPassRatio() throws {
        let it = try item(.swipeValid)
        guard case let .swipe(cards, passRatio) = it.payload else { return XCTFail() }
        let all = Dictionary(uniqueKeysWithValues: cards.map { ($0.id, $0.valid) })
        XCTAssertTrue(PathGrader.grade(it, .swipes(all)).correct)
        var oneOff = all
        oneOff[cards[0].id] = !cards[0].valid
        let v = PathGrader.grade(it, .swipes(oneOff))
        XCTAssertEqual(v.ratio, Double(cards.count - 1) / Double(cards.count), accuracy: 0.001)
        XCTAssertEqual(v.correct, v.ratio >= passRatio)
        XCTAssertNotNil(v.whyWrong)
        XCTAssertFalse(PathGrader.grade(it, .swipes([:])).correct)
    }

    func testSpotError() throws {
        let it = try item(.spotError)
        guard case let .spotError(lines, wrongLine, fix) = it.payload else { return XCTFail() }
        XCTAssertEqual(PathGrader.grade(it, .line(wrongLine)).expected, fix)
        let other = try XCTUnwrap(lines.first { $0.id != wrongLine })
        let v = PathGrader.grade(it, .line(other.id))
        XCTAssertFalse(v.correct)
        XCTAssertTrue(v.expected?.contains(fix) ?? false)
    }

    func testTilesAcceptSolutionAndAlternatives() throws {
        for format in [PathFormat.orderSteps, .synthOrder, .headlineTiles] {
            let it = try item(format)
            guard case let .tiles(_, solution, _, accepted) = it.payload else { return XCTFail() }
            XCTAssertTrue(PathGrader.grade(it, .sequence(solution)).correct, "\(format)")
            for alt in accepted { XCTAssertTrue(PathGrader.grade(it, .sequence(alt)).correct) }
            let v = PathGrader.grade(it, .sequence(solution.reversed()))
            XCTAssertFalse(v.correct)
            XCTAssertNotNil(v.expected)
        }
    }

    func testMentalMathTolerance() throws {
        let it = try item(.mentalMath)
        guard case let .mentalMath(questions, _) = it.payload else { return XCTFail() }
        let exact = Dictionary(uniqueKeysWithValues: questions.map { ($0.id, $0.answer) })
        XCTAssertTrue(PathGrader.grade(it, .numbers(exact)).correct)
        let rough = Dictionary(uniqueKeysWithValues: questions.map { ($0.id, $0.answer * (1 + $0.tolerancePct / 100 * 0.9)) })
        XCTAssertTrue(PathGrader.grade(it, .numbers(rough)).correct)
        let off = Dictionary(uniqueKeysWithValues: questions.map { ($0.id, $0.answer * 2) })
        let v = PathGrader.grade(it, .numbers(off))
        XCTAssertFalse(v.correct)
        XCTAssertEqual(v.ratio, 0)
        XCTAssertNotNil(v.expected)
    }

    func testEstimateRange() throws {
        let it = try item(.estimateRange)
        guard case let .estimate(range, slider, _, log, _) = it.payload else { return XCTFail() }
        XCTAssertTrue(log)
        XCTAssertTrue(slider.contains(range.lowerBound) && slider.contains(range.upperBound))
        XCTAssertTrue(PathGrader.grade(it, .estimate((range.lowerBound + range.upperBound) / 2)).correct)
        XCTAssertFalse(PathGrader.grade(it, .estimate(range.upperBound * 3)).correct)
    }

    func testTwoStepNeedsBoth() throws {
        let it = try item(.twoStepCalc)
        guard case let .twoStep(_, formula, answer, _, tol) = it.payload else { return XCTFail() }
        XCTAssertTrue(PathGrader.grade(it, .twoStep(formula: formula, value: answer * (1 + tol / 200))).correct)
        let halfRight = PathGrader.grade(it, .twoStep(formula: formula, value: answer * 3))
        XCTAssertFalse(halfRight.correct)
        XCTAssertEqual(halfRight.ratio, 0.5)
        XCTAssertNil(halfRight.whyWrong)
        let wrongFormula = PathGrader.grade(it, .twoStep(formula: "b", value: answer))
        XCTAssertNotNil(wrongFormula.whyWrong)
    }

    func testFillBlankSortAndPairs() throws {
        let fill = try item(.fillBlank)
        guard case let .fillBlank(text, slots) = fill.payload else { return XCTFail() }
        XCTAssertTrue(text.contains("{{1}}"))
        let right = Dictionary(uniqueKeysWithValues: slots.map { ($0.id, $0.correct) })
        XCTAssertTrue(PathGrader.grade(fill, .blanks(right)).correct)
        XCTAssertFalse(PathGrader.grade(fill, .blanks([:])).correct)

        let sort = try item(.meceSort)
        guard case let .meceSort(_, items) = sort.payload else { return XCTFail() }
        let placed = Dictionary(uniqueKeysWithValues: items.map { ($0.id, $0.bucket) })
        XCTAssertTrue(PathGrader.grade(sort, .buckets(placed)).correct)
        var one = placed
        one[items[0].id] = "nope"
        let v = PathGrader.grade(sort, .buckets(one))
        XCTAssertFalse(v.correct)
        XCTAssertTrue(v.expected?.contains(items[0].text) ?? false)

        let pairs = try item(.matchPairs)
        guard case let .matchPairs(list) = pairs.payload else { return XCTFail() }
        let matched = Dictionary(uniqueKeysWithValues: list.map { ($0.left, $0.right) })
        XCTAssertTrue(PathGrader.grade(pairs, .pairs(matched)).correct)
        XCTAssertEqual(PathGrader.grade(pairs, .pairs([:])).ratio, 0)
    }

    func testOralAndMismatchedAnswers() throws {
        let oral = try item(.oralPrompt)
        XCTAssertTrue(PathGrader.grade(oral, .transcript("Je reformule : le client veut doubler sa marge.")).correct)
        XCTAssertFalse(PathGrader.grade(oral, .transcript("   ")).correct)
        XCTAssertFalse(PathGrader.grade(try item(.chooseStructure), .estimate(3)).correct)
        XCTAssertTrue(PathGrader.grade(try item(.conceptCard), .read).correct)
    }

    func testNumberParsingAndFormatting() {
        XCTAssertEqual(PathGrader.parseNumber("1,2 M"), 1_200_000)
        XCTAssertEqual(PathGrader.parseNumber("830M€"), 830_000_000)
        XCTAssertEqual(PathGrader.parseNumber("21 k"), 21_000)
        XCTAssertEqual(PathGrader.parseNumber("30 000"), 30_000)
        XCTAssertEqual(PathGrader.parseNumber("2 Md"), 2_000_000_000)
        XCTAssertEqual(PathGrader.parseNumber("18 %"), 18)
        XCTAssertNil(PathGrader.parseNumber("beaucoup"))
        XCTAssertEqual(Format.number(829_440_000), "829,4 M")
        XCTAssertEqual(Format.number(30_000), "30\u{202F}000")
        XCTAssertEqual(Format.number(2_000_000_000), "2 Md")
        XCTAssertEqual(Format.number(0.18), "0,2")
        XCTAssertEqual(Format.number(72), "72")
    }

    // MARK: The session

    func testSessionReasksMistakesAndScoresFirstTries() throws {
        var s = LessonSession(start: lesson)
        let n = lesson.items.count
        XCTAssertEqual(s.queue.count, n)
        XCTAssertEqual(s.current?.item.format, .conceptCard)
        s.submit(.read)
        s.advance()
        // Answer everything right except the first two graded items.
        var wrongs = 0
        while let step = s.current, step.firstTry {
            let it = step.item
            let answer: PathAnswer
            switch it.payload {
            case .choice: answer = wrongs < 2 ? .option("b") : .option("a")
            case let .swipe(cards, _): answer = .swipes(Dictionary(uniqueKeysWithValues: cards.map { ($0.id, $0.valid) }))
            case let .spotError(_, w, _): answer = .line(w)
            case let .tiles(_, sol, _, _): answer = .sequence(sol)
            case let .mentalMath(q, _): answer = .numbers(Dictionary(uniqueKeysWithValues: q.map { ($0.id, $0.answer) }))
            case let .estimate(r, _, _, _, _): answer = .estimate(r.lowerBound)
            case let .twoStep(_, f, a, _, _): answer = .twoStep(formula: f, value: a)
            case let .fillBlank(_, slots): answer = .blanks(Dictionary(uniqueKeysWithValues: slots.map { ($0.id, $0.correct) }))
            case let .meceSort(_, items): answer = .buckets(Dictionary(uniqueKeysWithValues: items.map { ($0.id, $0.bucket) }))
            case let .matchPairs(p): answer = .pairs(Dictionary(uniqueKeysWithValues: p.map { ($0.left, $0.right) }))
            case .oral: answer = .transcript("Je reformule l'objectif, je pose une question, j'annonce trois axes.")
            case .concept, .unknown: answer = .read
            }
            let v = s.submit(answer, ms: 3000)
            if case .choice = it.payload, wrongs < 2 { XCTAssertEqual(v?.correct, false); wrongs += 1 }
            s.advance()
        }
        XCTAssertEqual(wrongs, 2)
        XCTAssertEqual(s.queue.count, n + 2, "the two mistakes come back at the end")
        XCTAssertFalse(s.isFinished)
        XCTAssertEqual(s.current?.firstTry, false)
        // Second try right: no third ask.
        s.submit(.option("a")); s.advance()
        s.submit(.option("b")); s.advance()
        XCTAssertTrue(s.isFinished)
        XCTAssertEqual(s.queue.count, n + 2)
        XCTAssertEqual(s.score, Int((Double(16 - 2) / 16 * 100).rounded()))
        XCTAssertFalse(s.isPerfect)

        let results = s.results
        XCTAssertEqual(results.count, n, "one result per item, first try only")
        XCTAssertEqual(results.filter { !$0.firstTry }.count, 0)
        XCTAssertEqual(results.filter { !$0.correct }.count, 2)
        XCTAssertEqual(results.last?.transcript?.isEmpty, false)
        let body = try CaseDuoJSON.encoder.encode(LessonCompletionRequest(results: results))
        let json = try XCTUnwrap(try JSONSerialization.jsonObject(with: body) as? [String: Any])
        let first = try XCTUnwrap((json["results"] as? [[String: Any]])?.first)
        XCTAssertEqual(first["item_id"] as? String, lesson.items.first?.id)
        XCTAssertEqual(first["first_try"] as? Bool, true)
    }

    func testPerfectRun() throws {
        let small = LessonStart(node: lesson.node, items: [try item(.conceptCard), try item(.chooseStructure)],
                                xp: 10, perfectBonus: 5, passScore: nil)
        var s = LessonSession(start: small)
        s.submit(.read); s.advance()
        s.submit(.option("a")); s.advance()
        XCTAssertTrue(s.isFinished && s.isPerfect)
        XCTAssertEqual(s.score, 100)
        XCTAssertEqual(s.progress, 1)
        XCTAssertEqual(s.streakOfCorrect, 1)
    }
}
