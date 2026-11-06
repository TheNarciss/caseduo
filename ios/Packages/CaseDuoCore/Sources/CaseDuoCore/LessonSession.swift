import Foundation

/// One run of a lesson, as a value: the queue of items, the answers, the mistakes re-asked at
/// the end, the score, and what to send to the server. No clock, no UI: the app drives it.
public struct LessonSession: Sendable, Equatable {
    public struct Step: Sendable, Equatable, Identifiable {
        public var item: PathItem
        /// False when this is the item asked again after a mistake.
        public var firstTry: Bool
        public var id: String { item.id + (firstTry ? "" : "#again") }
    }

    public struct Answered: Sendable, Equatable {
        public var item: PathItem
        public var answer: PathAnswer
        public var verdict: PathVerdict
        public var firstTry: Bool
        public var ms: Int
    }

    public let start: LessonStart
    public private(set) var queue: [Step]
    public private(set) var index = 0
    public private(set) var answered: [Answered] = []
    public private(set) var requeued: Set<String> = []

    public init(start: LessonStart) {
        self.start = start
        self.queue = start.items.map { Step(item: $0, firstTry: true) }
    }

    public var current: Step? { queue[safe: index] }
    public var isFinished: Bool { index >= queue.count }
    /// Progress for the bar: answered steps over the whole queue (grows when a mistake is re-asked).
    public var progress: Double { queue.isEmpty ? 1 : Double(index) / Double(queue.count) }
    public var graded: [Answered] { answered.filter { $0.item.format.isGraded } }
    /// First-try correct over graded items, the way the server scores it.
    public var score: Int {
        let firsts = graded.filter(\.firstTry)
        guard !firsts.isEmpty else { return 100 }
        return Int((Double(firsts.filter(\.verdict.correct).count) / Double(firsts.count) * 100).rounded())
    }
    public var isPerfect: Bool { graded.allSatisfy { $0.verdict.correct && $0.firstTry } }
    public var streakOfCorrect: Int {
        var n = 0
        for a in graded.reversed() { if a.verdict.correct { n += 1 } else { break } }
        return n
    }

    /// Grades the current step, records it, re-queues it at the end when wrong (once).
    @discardableResult
    public mutating func submit(_ answer: PathAnswer, ms: Int = 0) -> PathVerdict? {
        guard let step = current else { return nil }
        let verdict = PathGrader.grade(step.item, answer)
        answered.append(Answered(item: step.item, answer: answer, verdict: verdict, firstTry: step.firstTry, ms: ms))
        if !verdict.correct, step.item.format.isGraded, !step.item.format.isOral, !requeued.contains(step.item.id) {
            requeued.insert(step.item.id)
            queue.append(Step(item: step.item, firstTry: false))
        }
        return verdict
    }

    public mutating func advance() {
        index = min(queue.count, index + 1)
    }

    /// The results for `POST /path/nodes/{code}/complete`: one per item, first try only, with
    /// the oral transcript.
    public var results: [PathItemResult] {
        var seen: Set<String> = []
        var out: [PathItemResult] = []
        for a in answered where !seen.contains(a.item.id) {
            seen.insert(a.item.id)
            var transcript: String?
            if case .transcript(let text) = a.answer { transcript = text }
            out.append(PathItemResult(itemId: a.item.id, correct: a.verdict.correct, firstTry: a.firstTry,
                                      ms: a.ms, response: nil, transcript: transcript))
        }
        return out
    }
}
