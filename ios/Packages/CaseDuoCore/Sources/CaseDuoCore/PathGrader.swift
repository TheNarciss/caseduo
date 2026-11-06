import Foundation

// Grading an item on the phone, deterministically, from the key it carries. Pure, tested.

/// What a format view hands back when the learner confirms.
public enum PathAnswer: Sendable, Equatable {
    case read
    case option(String)
    case swipes([String: Bool])
    case line(String)
    case sequence([String])
    case numbers([String: Double])
    case estimate(Double)
    case twoStep(formula: String, value: Double?)
    case blanks([Int: Int])
    case buckets([String: String])
    case pairs([String: String])
    case transcript(String)
}

/// Right or wrong, with what to show: the explanation always, the reason for the chosen
/// wrong option when there is one, and the expected answer in words.
public struct PathVerdict: Sendable, Equatable {
    public var correct: Bool
    public var whyWrong: String?
    public var expected: String?
    /// 0…1 for formats graded in parts (swipes, math blocks, buckets, pairs).
    public var ratio: Double

    public init(correct: Bool, whyWrong: String? = nil, expected: String? = nil, ratio: Double? = nil) {
        self.correct = correct
        self.whyWrong = whyWrong
        self.expected = expected
        self.ratio = ratio ?? (correct ? 1 : 0)
    }
}

public enum PathGrader {
    public static func grade(_ item: PathItem, _ answer: PathAnswer) -> PathVerdict {
        switch (item.payload, answer) {
        case (.concept, _):
            return PathVerdict(correct: true)

        case let (.choice(options, correct, _), .option(chosen)):
            if chosen == correct { return PathVerdict(correct: true) }
            let picked = options.first { $0.id == chosen }
            let right = options.first { $0.id == correct }
            return PathVerdict(correct: false, whyWrong: picked?.whyWrong, expected: right?.text)

        case let (.swipe(cards, passRatio), .swipes(choices)):
            let right = cards.filter { choices[$0.id] == $0.valid }.count
            let ratio = Double(right) / Double(max(1, cards.count))
            let missed = cards.filter { choices[$0.id] != $0.valid }
            let detail = missed.prefix(2).map { "« \($0.text) » : \($0.reason)" }.joined(separator: "\n")
            return PathVerdict(correct: ratio >= passRatio, whyWrong: missed.isEmpty ? nil : detail,
                               expected: nil, ratio: ratio)

        case let (.spotError(lines, wrongLine, fix), .line(chosen)):
            if chosen == wrongLine { return PathVerdict(correct: true, expected: fix) }
            let right = lines.first { $0.id == wrongLine }
            return PathVerdict(correct: false, whyWrong: "Cette ligne est juste.",
                               expected: right.map { "La faute : « \($0.text) ». \(fix)" } ?? fix)

        case let (.tiles(tiles, solution, _, accepted), .sequence(chosen)):
            if chosen == solution || accepted.contains(chosen) { return PathVerdict(correct: true) }
            let matching = zip(chosen, solution).filter { $0 == $1 }.count
            let byId = Dictionary(uniqueKeysWithValues: tiles.map { ($0.id, $0.text) })
            let expected = solution.compactMap { byId[$0] }.joined(separator: " → ")
            return PathVerdict(correct: false, whyWrong: nil, expected: expected,
                               ratio: Double(matching) / Double(max(1, solution.count)))

        case let (.mentalMath(questions, _), .numbers(values)):
            let right = questions.filter { within($0.answer, values[$0.id], $0.tolerancePct) }
            let ratio = Double(right.count) / Double(max(1, questions.count))
            let missed = questions.filter { !within($0.answer, values[$0.id], $0.tolerancePct) }
            let expected = missed.prefix(2).map { "\($0.stem) → \(Format.number($0.answer)) \($0.unit)" }.joined(separator: "\n")
            return PathVerdict(correct: missed.isEmpty, whyWrong: nil, expected: missed.isEmpty ? nil : expected, ratio: ratio)

        case let (.estimate(range, _, unit, _, reference), .estimate(value)):
            let ok = range.contains(value)
            return PathVerdict(correct: ok, whyWrong: nil,
                               expected: ok ? reference : "Entre \(Format.number(range.lowerBound)) et \(Format.number(range.upperBound)) \(unit). \(reference)")

        case let (.twoStep(formulas, correctFormula, expectedValue, unit, tolerance), .twoStep(formula, value)):
            let formulaOk = formula == correctFormula
            let valueOk = within(expectedValue, value, tolerance)
            if formulaOk && valueOk { return PathVerdict(correct: true) }
            let picked = formulas.first { $0.id == formula }
            let right = formulas.first { $0.id == correctFormula }
            let expected = "\(right?.text ?? "") = \(Format.number(expectedValue)) \(unit)"
            return PathVerdict(correct: false, whyWrong: formulaOk ? nil : picked?.whyWrong, expected: expected,
                               ratio: formulaOk ? 0.5 : 0)

        case let (.fillBlank(_, slots), .blanks(chosen)):
            let right = slots.filter { chosen[$0.id] == $0.correct }
            let ratio = Double(right.count) / Double(max(1, slots.count))
            let expected = slots.map { $0.options[safe: $0.correct] ?? "" }.joined(separator: ", ")
            return PathVerdict(correct: right.count == slots.count, whyWrong: nil,
                               expected: right.count == slots.count ? nil : expected, ratio: ratio)

        case let (.meceSort(buckets, items), .buckets(placed)):
            let right = items.filter { placed[$0.id] == $0.bucket }
            let ratio = Double(right.count) / Double(max(1, items.count))
            let labels = Dictionary(uniqueKeysWithValues: buckets.map { ($0.id, $0.label) })
            let missed = items.filter { placed[$0.id] != $0.bucket }
            let expected = missed.prefix(3).map { "\($0.text) → \(labels[$0.bucket] ?? $0.bucket)" }.joined(separator: "\n")
            return PathVerdict(correct: missed.isEmpty, whyWrong: nil, expected: missed.isEmpty ? nil : expected, ratio: ratio)

        case let (.matchPairs(pairs), .pairs(matched)):
            let right = pairs.filter { matched[$0.left] == $0.right }
            let ratio = Double(right.count) / Double(max(1, pairs.count))
            let missed = pairs.filter { matched[$0.left] != $0.right }
            let expected = missed.prefix(2).map { "\($0.left) ↔ \($0.right)" }.joined(separator: "\n")
            return PathVerdict(correct: missed.isEmpty, whyWrong: nil, expected: missed.isEmpty ? nil : expected, ratio: ratio)

        case (.oral, .transcript(let text)):
            // Graded by the server at the end of the lesson; here only "said something".
            return PathVerdict(correct: text.trimmingCharacters(in: .whitespacesAndNewlines).count >= 10)

        default:
            return PathVerdict(correct: false, whyWrong: "Réponse incomplète.")
        }
    }

    /// Whether `value` is within `tolerancePct` percent of `expected`.
    public static func within(_ expected: Double, _ value: Double?, _ tolerancePct: Double) -> Bool {
        guard let value else { return false }
        if expected == 0 { return abs(value) < 1e-9 }
        return abs(value - expected) / abs(expected) <= tolerancePct / 100
    }

    /// "1,2 M", "830 M", "21 k", "30 000" : numbers as a candidate says them.
    public static func parseNumber(_ text: String) -> Double? {
        var s = text.lowercased().replacingOccurrences(of: " ", with: "").replacingOccurrences(of: "\u{202F}", with: "")
            .replacingOccurrences(of: ",", with: ".").replacingOccurrences(of: "€", with: "").replacingOccurrences(of: "%", with: "")
        var factor = 1.0
        if s.hasSuffix("md") || s.hasSuffix("mds") || s.hasSuffix("b") { factor = 1e9; s = s.replacingOccurrences(of: "mds", with: "").replacingOccurrences(of: "md", with: "").replacingOccurrences(of: "b", with: "") }
        else if s.hasSuffix("m") { factor = 1e6; s.removeLast() }
        else if s.hasSuffix("k") { factor = 1e3; s.removeLast() }
        guard let base = Double(s) else { return nil }
        return base * factor
    }
}

extension Array {
    subscript(safe index: Int) -> Element? { indices.contains(index) ? self[index] : nil }
}

public extension Format {
    /// "829 M", "30 000", "21 M", "0,18 M" : readable magnitudes for the feedback lines.
    static func number(_ value: Double) -> String {
        let abs = Swift.abs(value)
        func trim(_ x: Double) -> String {
            let rounded = (x * 10).rounded() / 10
            if rounded == rounded.rounded() { return String(Int(rounded)) }
            return String(format: "%.1f", rounded).replacingOccurrences(of: ".", with: ",")
        }
        if abs >= 1e9 { return trim(value / 1e9) + " Md" }
        if abs >= 1e6 { return trim(value / 1e6) + " M" }
        if abs >= 1e4 {
            let formatter = NumberFormatter()
            formatter.numberStyle = .decimal
            formatter.groupingSeparator = "\u{202F}"
            formatter.maximumFractionDigits = 0
            return formatter.string(from: NSNumber(value: value.rounded())) ?? String(Int(value))
        }
        return trim(value)
    }
}
