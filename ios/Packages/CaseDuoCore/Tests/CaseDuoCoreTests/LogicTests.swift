import Foundation
import XCTest
@testable import CaseDuoCore

final class LogicTests: XCTestCase {
    let singapore = TimeZone(identifier: "Asia/Singapore")!

    private func date(_ iso: String) -> Date { ISODate.parse(iso)! }

    // MARK: Haptics

    func testScoreToHapticPattern() {
        XCTAssertEqual(HapticPattern.forScore(0), .scoreLow)
        XCTAssertEqual(HapticPattern.forScore(49), .scoreLow)
        XCTAssertEqual(HapticPattern.forScore(50), .scoreMid)
        XCTAssertEqual(HapticPattern.forScore(79), .scoreMid)
        XCTAssertEqual(HapticPattern.forScore(80), .scoreHigh)
        XCTAssertEqual(HapticPattern.forScore(100), .scoreHigh)
    }

    func testPatternShapes() {
        XCTAssertEqual(HapticPattern.answerSent.pulses.count, 1)
        XCTAssertLessThan(HapticPattern.answerSent.pulses[0].intensity, 0.5, "light")
        XCTAssertEqual(HapticPattern.scoreLow.pulses.count, 1)
        XCTAssertEqual(HapticPattern.scoreLow.pulses[0].intensity, 1.0, "one heavy hit")
        XCTAssertEqual(HapticPattern.scoreMid.pulses.count, 2)
        XCTAssertEqual(HapticPattern.scoreHigh.pulses.count, 3)
        XCTAssertTrue(HapticPattern.scoreHigh.endsWithSuccess)
        XCTAssertFalse(HapticPattern.scoreMid.endsWithSuccess)
        let rising = HapticPattern.streakUp.pulses.filter { !$0.isContinuous }.map(\.intensity)
        XCTAssertEqual(rising, rising.sorted(), "streak pattern rises")
        let longest = HapticPattern.allCases.map { p in p.pulses.map { $0.time + $0.duration }.max() ?? 0 }
        XCTAssertEqual(longest.max(), HapticPattern.perfectWeek.pulses.map { $0.time + $0.duration }.max(),
                       "perfect week is the long one")
        for pattern in HapticPattern.allCases {
            XCTAssertEqual(pattern.pulses.map(\.time), pattern.pulses.map(\.time).sorted())
        }
    }

    // MARK: Days

    func testLocalDayAcrossMidnight() {
        // 23:30 in Singapore is still 15:30 UTC the same day; 00:30 SGT is the previous day in UTC.
        let lateEvening = date("2026-11-04T15:30:00Z")
        XCTAssertEqual(LocalDay.string(for: lateEvening, in: singapore), "2026-11-04")
        let afterMidnight = date("2026-11-04T16:30:00Z")
        XCTAssertEqual(LocalDay.string(for: afterMidnight, in: singapore), "2026-11-05")
        XCTAssertEqual(LocalDay.string(for: afterMidnight, in: TimeZone(identifier: "Europe/Paris")!), "2026-11-04")
        let midnight = LocalDay.nextMidnight(after: lateEvening, in: singapore)
        XCTAssertEqual(midnight, date("2026-11-04T16:00:00Z"))
        XCTAssertEqual(LocalDay.date(from: "2026-11-05", in: singapore), midnight)
    }

    // MARK: Widget

    func testWidgetSnapshotSameDayAndNextDay() throws {
        let today = try CaseDuoJSON.decoder.decode(Today.self, from: Data(DemoFixtures.today.utf8))
        let snapshot = WidgetSnapshot(today: today, updatedAt: date("2026-11-08T02:00:00Z"))
        let sameDay = snapshot.display(at: date("2026-11-08T10:00:00Z")) // 18:00 SGT
        XCTAssertFalse(sameDay.isNewDay)
        XCTAssertEqual(sameDay.remaining, 6)
        XCTAssertEqual(sameDay.headline, "6 exercices restants")
        XCTAssertEqual(sameDay.goalFraction, 0.4, accuracy: 0.001)
        let nextDay = snapshot.display(at: date("2026-11-08T16:05:00Z")) // 00:05 SGT the 9th
        XCTAssertTrue(nextDay.isNewDay)
        XCTAssertNil(nextDay.remaining)
        XCTAssertEqual(nextDay.headline, "Nouvelle journée")
        XCTAssertEqual(nextDay.status, .atRisk)
        let dates = snapshot.timelineDates(from: date("2026-11-08T10:00:00Z"))
        XCTAssertEqual(dates.last, date("2026-11-08T16:00:00Z"))
        let roundTrip = WidgetSnapshot.decode(try XCTUnwrap(snapshot.encoded()))
        XCTAssertEqual(roundTrip, snapshot)
    }

    func testWidgetSnapshotFollowsGrading() throws {
        let today = try CaseDuoJSON.decoder.decode(Today.self, from: Data(DemoFixtures.today.utf8))
        var snapshot = WidgetSnapshot(today: today)
        let result = try CaseDuoJSON.decoder.decode(GradeResult.self, from: Data(DemoFixtures.gradeResult.utf8))
        snapshot.apply(result.progress)
        XCTAssertEqual(snapshot.remaining, 5)
        XCTAssertEqual(snapshot.xpToday, 40)
        XCTAssertEqual(WidgetDisplay(isNewDay: false, streak: 1, status: .safe, remaining: 1, xpToday: 0, goalXp: 30).headline,
                       "1 exercice restant")
        XCTAssertEqual(WidgetDisplay(isNewDay: false, streak: 1, status: .safe, remaining: 0, xpToday: 30, goalXp: 30).headline,
                       "Journée bouclée")
    }

    // MARK: Local streak saver

    func testStreakSaverOnlyWithoutPushAndWhenAtRisk() throws {
        let today = try CaseDuoJSON.decoder.decode(Today.self, from: Data(DemoFixtures.today.utf8))
        let morning = date("2026-11-08T01:00:00Z") // 09:00 SGT
        let fire = StreakSaverPlan.fireDate(today: today, pushUsable: false, now: morning, timeZone: singapore)
        XCTAssertEqual(fire, date("2026-11-08T12:00:00Z"), "20:00 Singapore")
        XCTAssertNil(StreakSaverPlan.fireDate(today: today, pushUsable: true, now: morning, timeZone: singapore))
        let evening = date("2026-11-08T12:30:00Z") // 20:30 SGT
        XCTAssertNil(StreakSaverPlan.fireDate(today: today, pushUsable: false, now: evening, timeZone: singapore))
        var met = today
        met.goal.met = true
        XCTAssertNil(StreakSaverPlan.fireDate(today: met, pushUsable: false, now: morning, timeZone: singapore))
        var noStreak = today
        noStreak.streak.current = 0
        XCTAssertNil(StreakSaverPlan.fireDate(today: noStreak, pushUsable: false, now: morning, timeZone: singapore))
        let nextDay = date("2026-11-09T01:00:00Z")
        XCTAssertNil(StreakSaverPlan.fireDate(today: today, pushUsable: false, now: nextDay, timeZone: singapore),
                     "a stale /today must not schedule tomorrow's reminder")
        XCTAssertEqual(StreakSaverPlan.body(streak: 12), "Ta série de 12 jours se termine dans 4 h")
        XCTAssertEqual(StreakSaverPlan.body(streak: 1), "Ta série de 1 jour se termine dans 4 h")
    }

    // MARK: Icons

    func testIconChoice() {
        XCTAssertNil(AppIconChoice.choose(unlocks: nil, today: "2026-11-08"))
        XCTAssertNil(AppIconChoice.choose(unlocks: Unlocks(streak30Icon: false, perfectWeekUntil: nil), today: "2026-11-08"))
        XCTAssertEqual(AppIconChoice.choose(unlocks: Unlocks(streak30Icon: true, perfectWeekUntil: nil), today: "2026-11-08"),
                       AppIconChoice.streak30)
        XCTAssertEqual(AppIconChoice.choose(unlocks: Unlocks(streak30Icon: true, perfectWeekUntil: "2026-11-10"), today: "2026-11-08"),
                       AppIconChoice.perfectWeek)
        XCTAssertEqual(AppIconChoice.choose(unlocks: Unlocks(streak30Icon: true, perfectWeekUntil: "2026-11-07"), today: "2026-11-08"),
                       AppIconChoice.streak30, "an expired perfect week falls back")
        XCTAssertTrue(AppIconChoice.perfectWeekActive(unlocks: Unlocks(streak30Icon: false, perfectWeekUntil: "2026-11-08"), today: "2026-11-08"))
    }

    // MARK: Formats and drafts

    func testFormats() {
        XCTAssertEqual(Format.chrono(312), "05:12")
        XCTAssertEqual(Format.chrono(3723), "1:02:03")
        XCTAssertEqual(Format.chrono(-4), "00:00")
        XCTAssertEqual(Format.difficulty(3), "●●●○○")
        XCTAssertEqual(Format.xp(5, signed: true), "+5 XP")
        XCTAssertEqual(Format.streakDays(1), "1 jour")
        XCTAssertEqual(Format.leagueTier("silver"), "Argent")
        XCTAssertEqual(Format.shortDay("2026-11-04"), "4 nov.")
        let now = date("2026-11-06T10:00:00Z")
        XCTAssertEqual(Format.countdown(to: date("2026-11-08T14:00:00Z"), from: now), "2 j 4 h")
        XCTAssertEqual(Format.countdown(to: date("2026-11-06T13:05:00Z"), from: now), "3 h 05 min")
        XCTAssertEqual(Format.countdown(to: date("2026-11-06T10:08:00Z"), from: now), "8 min")
    }

    func testSlidesDraft() {
        var deck = SlideDraft.blankDeck()
        XCTAssertEqual(deck.count, 5)
        XCTAssertEqual(deck[0].issue, "titre-message manquant")
        deck[0].title = "Le sujet n'est pas l'IA, c'est la donnée sinistres"
        XCTAssertEqual(deck[0].issue, "3 lignes de plus")
        deck[0].lines = ["Constat A", "  ", "Constat B", "Constat C"]
        XCTAssertNil(deck[0].issue)
        XCTAssertTrue(deck[0].isComplete)
        deck[0].lines += ["D", "E", "F"]
        XCTAssertEqual(deck[0].issue, "5 lignes maximum")
        deck[0].lines = ["A", "B", "C"]
        let slides = SlideDraft.slides(from: deck)
        XCTAssertEqual(slides[0].lines, ["A", "B", "C"])
        XCTAssertTrue(SlideDraft.answerText(from: deck).hasPrefix("Slide 1 — Le sujet"))
    }

    func testPartAnswers() {
        let text = PartAnswers.answerText(parts: [ExercisePart(question: "Q1"), ExercisePart(question: "Q2")],
                                          answers: [" R1 ", "R2"])
        XCTAssertEqual(text, "Question 1 : Q1\nRéponse : R1\n\nQuestion 2 : Q2\nRéponse : R2")
    }
}
