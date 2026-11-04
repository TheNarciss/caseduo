import Foundation

/// French formats used across the screens.
public enum Format {
    /// "05:12", "1:02:03".
    public static func chrono(_ seconds: Int) -> String {
        let s = max(0, seconds)
        let h = s / 3600, m = (s % 3600) / 60, r = s % 60
        if h > 0 { return String(format: "%d:%02d:%02d", h, m, r) }
        return String(format: "%02d:%02d", m, r)
    }

    public static func xp(_ value: Int, signed: Bool = false) -> String {
        if signed && value > 0 { return "+\(value) XP" }
        return "\(value) XP"
    }

    /// "●●●○○" for difficulty 3 out of 5.
    public static func difficulty(_ level: Int) -> String {
        let n = min(5, max(0, level))
        return String(repeating: "●", count: n) + String(repeating: "○", count: 5 - n)
    }

    public static func languageTag(_ code: String) -> String { code.uppercased() }

    public static func minutes(_ value: Int?) -> String? {
        guard let value, value > 0 else { return nil }
        return "\(value) min"
    }

    public static func streakDays(_ n: Int) -> String { n <= 1 ? "\(n) jour" : "\(n) jours" }

    /// "2 j 4 h", "3 h 12 min", "8 min" until `end`.
    public static func countdown(to end: Date, from now: Date) -> String {
        let total = max(0, Int(end.timeIntervalSince(now)))
        let d = total / 86_400, h = (total % 86_400) / 3600, m = (total % 3600) / 60
        if d > 0 { return "\(d) j \(h) h" }
        if h > 0 { return "\(h) h \(String(format: "%02d", m)) min" }
        return "\(m) min"
    }

    public static func leagueTier(_ tier: String) -> String {
        switch tier {
        case "bronze": return "Bronze"
        case "silver": return "Argent"
        case "gold": return "Or"
        default: return tier.capitalized
        }
    }

    /// "4 nov." for a "2026-11-04" day string.
    public static func shortDay(_ day: String) -> String {
        let parts = day.split(separator: "-").compactMap { Int($0) }
        guard parts.count == 3 else { return day }
        let months = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]
        let month = (1...12).contains(parts[1]) ? months[parts[1] - 1] : ""
        return "\(parts[2]) \(month)"
    }
}

/// The three sections of the grader's feedback, split for display.
public struct FeedbackSection: Sendable, Equatable, Identifiable {
    public var title: String
    public var body: String
    public var id: String { title }

    public enum Kind: Sendable { case strengths, fixes, thirtySeconds, other }

    public var kind: Kind {
        let t = title.lowercased()
        if t.contains("bien") || t.contains("well") { return .strengths }
        if t.contains("corriger") || t.contains("fix") || t.contains("improve") { return .fixes }
        if t.contains("30") { return .thirtySeconds }
        return .other
    }

    /// Splits markdown on its `##`/`###` headings. Text before the first heading becomes an
    /// untitled section. Works on a partial stream too: the last section simply grows.
    public static func parse(_ markdown: String) -> [FeedbackSection] {
        var sections: [FeedbackSection] = []
        var currentTitle = ""
        var currentBody: [String] = []
        func flush() {
            let body = currentBody.joined(separator: "\n").trimmingCharacters(in: .whitespacesAndNewlines)
            if !currentTitle.isEmpty || !body.isEmpty {
                sections.append(FeedbackSection(title: currentTitle, body: body))
            }
        }
        for line in markdown.components(separatedBy: "\n") {
            let trimmed = line.trimmingCharacters(in: .whitespaces)
            if trimmed.hasPrefix("#") {
                let title = trimmed.drop(while: { $0 == "#" }).trimmingCharacters(in: .whitespaces)
                if !title.isEmpty {
                    flush()
                    currentTitle = title
                    currentBody = []
                    continue
                }
            }
            currentBody.append(line)
        }
        flush()
        return sections
    }
}

/// The five slides of a cadrage à domicile, as typed.
public struct SlideDraft: Sendable, Equatable, Identifiable {
    public var id: Int
    public var title: String
    public var lines: [String]

    public init(id: Int, title: String = "", lines: [String] = ["", "", ""]) {
        self.id = id
        self.title = title
        self.lines = lines
    }

    public static func blankDeck() -> [SlideDraft] { (0..<5).map { SlideDraft(id: $0) } }

    var filledLines: [String] {
        lines.map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }.filter { !$0.isEmpty }
    }

    public var isComplete: Bool {
        !title.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty && (3...5).contains(filledLines.count)
    }

    /// What is missing on this slide, in French, or nil when it is ready.
    public var issue: String? {
        if title.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty { return "titre-message manquant" }
        let n = filledLines.count
        if n < 3 { return "\(3 - n) ligne\(3 - n > 1 ? "s" : "") de plus" }
        if n > 5 { return "5 lignes maximum" }
        return nil
    }

    public static func slides(from deck: [SlideDraft]) -> [Slide] {
        deck.map { Slide(title: $0.title.trimmingCharacters(in: .whitespacesAndNewlines), lines: $0.filledLines) }
    }

    /// The same deck as plain text, for `answer_text`.
    public static func answerText(from deck: [SlideDraft]) -> String {
        slides(from: deck).enumerated().map { index, slide in
            (["Slide \(index + 1) — \(slide.title)"] + slide.lines.map { "- \($0)" }).joined(separator: "\n")
        }.joined(separator: "\n\n")
    }
}

/// Answers to an exercise in several parts (interviewer-led MBB case, mock fit).
public enum PartAnswers {
    public static func answerText(parts: [ExercisePart], answers: [String]) -> String {
        zip(parts, answers).enumerated().map { index, pair in
            "Question \(index + 1) : \(pair.0.question)\nRéponse : \(pair.1.trimmingCharacters(in: .whitespacesAndNewlines))"
        }.joined(separator: "\n\n")
    }
}
