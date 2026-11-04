import CaseDuoCore
import SwiftUI

/// A short fact in a capsule: "FR", "MBB", "6 min", "Revanche ×1,2".
struct Chip: View {
    let text: String
    var symbol: String?
    var tint: Color = Brand.textSecondary
    var filled = false

    var body: some View {
        HStack(spacing: 4) {
            if let symbol { Image(systemName: symbol).imageScale(.small) }
            Text(text).lineLimit(1)
        }
        .font(.caption.weight(.semibold))
        .padding(.horizontal, 9)
        .padding(.vertical, 5)
        .foregroundStyle(filled ? Color.black : tint)
        .background(filled ? tint : tint.opacity(0.14), in: Capsule())
    }
}

/// A coloured disc with a symbol.
struct IconCircle: View {
    let symbol: String
    let tint: Color
    var size: CGFloat = 40

    var body: some View {
        Image(systemName: symbol)
            .font(.system(size: size * 0.42, weight: .bold))
            .foregroundStyle(tint)
            .frame(width: size, height: size)
            .background(tint.opacity(0.16), in: Circle())
            .accessibilityHidden(true)
    }
}

/// Five dots for the difficulty.
struct DifficultyDots: View {
    let level: Int
    var tint: Color = Brand.flame

    var body: some View {
        HStack(spacing: 3) {
            ForEach(1...5, id: \.self) { i in
                Circle()
                    .fill(i <= level ? tint : Color.white.opacity(0.15))
                    .frame(width: 6, height: 6)
            }
        }
        .accessibilityElement()
        .accessibilityLabel("Difficulté \(level) sur 5")
    }
}

/// The XP goal bar.
struct GoalBar: View {
    let goal: GoalInfo
    @Environment(\.palette) private var palette

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text("Objectif du jour").font(.subheadline.weight(.semibold))
                Spacer()
                Text("\(goal.xpToday) / \(goal.targetXp) XP")
                    .font(.subheadline.monospacedDigit().weight(.bold))
                    .foregroundStyle(goal.met ? Brand.success : palette.accent)
            }
            GeometryReader { geo in
                ZStack(alignment: .leading) {
                    Capsule().fill(Color.white.opacity(0.08))
                    Capsule()
                        .fill(goal.met ? AnyShapeStyle(Brand.success) : AnyShapeStyle(palette.linear))
                        .frame(width: max(10, geo.size.width * goal.fraction))
                        .animation(Brand.spring, value: goal.fraction)
                }
            }
            .frame(height: 12)
        }
        .accessibilityElement(children: .combine)
    }
}

/// Main actions live at the bottom of the screen, within thumb reach.
struct BottomActions<Content: View>: View {
    @ViewBuilder var content: Content

    var body: some View {
        VStack(spacing: 10) { content }
            .padding(.horizontal, 20)
            .padding(.top, 12)
            .padding(.bottom, 8)
            .background(.ultraThinMaterial)
    }
}

/// A small error line that can be dismissed.
struct ErrorBanner: View {
    let message: String
    var onDismiss: (() -> Void)?

    var body: some View {
        HStack(alignment: .top, spacing: 10) {
            Image(systemName: "exclamationmark.circle.fill").foregroundStyle(Brand.danger)
            Text(message).font(.subheadline).frame(maxWidth: .infinity, alignment: .leading)
            if let onDismiss {
                Button(action: onDismiss) { Image(systemName: "xmark").font(.caption.weight(.bold)) }
                    .buttonStyle(.plain)
                    .accessibilityLabel("Fermer")
            }
        }
        .padding(14)
        .card(radius: 16, fill: Brand.danger.opacity(0.12))
    }
}

/// A chrono label that turns orange past its budget.
struct ChronoLabel: View {
    let seconds: Int
    var budget: Int?
    var countdown = false

    var body: some View {
        let over = budget.map { countdown ? seconds <= 10 : seconds > $0 } ?? false
        Label(Format.chrono(seconds), systemImage: countdown ? "timer" : "stopwatch")
            .font(.subheadline.monospacedDigit().weight(.semibold))
            .foregroundStyle(over ? Brand.danger : Brand.textSecondary)
            .contentTransition(.numericText())
            .accessibilityLabel(countdown ? "Temps restant \(Format.chrono(seconds))" : "Temps écoulé \(Format.chrono(seconds))")
    }
}

struct LoadingView: View {
    var message = "Chargement…"

    var body: some View {
        VStack(spacing: 14) {
            ProgressView().tint(Brand.flame)
            Text(message).font(.subheadline).foregroundStyle(Brand.textSecondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}

/// A section title in the scroll views.
struct SectionTitle: View {
    let text: String
    var trailing: String?

    var body: some View {
        HStack {
            Text(text).font(.title3.weight(.bold))
            Spacer()
            if let trailing { Text(trailing).font(.subheadline).foregroundStyle(Brand.textSecondary) }
        }
        .padding(.top, 8)
    }
}

/// Block-level Markdown, enough for the statements, corrections and feedback: headings, lists,
/// paragraphs, with inline emphasis and links.
struct MarkdownText: View {
    let markdown: String
    var font: Font = .body

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            ForEach(Array(blocks.enumerated()), id: \.offset) { _, block in
                switch block {
                case .heading(let level, let text):
                    inline(text).font(level <= 2 ? Font.title3.weight(.bold) : Font.headline)
                        .padding(.top, 4)
                case .bullet(let text):
                    HStack(alignment: .firstTextBaseline, spacing: 8) {
                        Text("•").foregroundStyle(Brand.flame)
                        inline(text)
                    }
                case .numbered(let number, let text):
                    HStack(alignment: .firstTextBaseline, spacing: 8) {
                        Text("\(number).").monospacedDigit().foregroundStyle(Brand.textSecondary)
                        inline(text)
                    }
                case .quote(let text):
                    inline(text).italic().padding(.leading, 10)
                        .overlay(alignment: .leading) { Rectangle().fill(Brand.flame).frame(width: 2) }
                case .paragraph(let text):
                    inline(text)
                }
            }
        }
        .font(font)
        .textSelection(.enabled)
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private func inline(_ text: String) -> Text {
        let options = AttributedString.MarkdownParsingOptions(interpretedSyntax: .inlineOnlyPreservingWhitespace)
        if let attributed = try? AttributedString(markdown: text, options: options) {
            return Text(attributed)
        }
        return Text(text)
    }

    enum Block {
        case heading(Int, String)
        case bullet(String)
        case numbered(String, String)
        case quote(String)
        case paragraph(String)
    }

    private var blocks: [Block] {
        var result: [Block] = []
        var paragraph: [String] = []
        func flush() {
            if !paragraph.isEmpty {
                result.append(.paragraph(paragraph.joined(separator: "\n")))
                paragraph = []
            }
        }
        for raw in markdown.components(separatedBy: "\n") {
            let line = raw.trimmingCharacters(in: .whitespaces)
            if line.isEmpty { flush(); continue }
            if line.hasPrefix("#") {
                flush()
                let level = line.prefix(while: { $0 == "#" }).count
                result.append(.heading(level, line.drop(while: { $0 == "#" }).trimmingCharacters(in: .whitespaces)))
            } else if line.hasPrefix("- ") || line.hasPrefix("* ") || line.hasPrefix("• ") {
                flush()
                result.append(.bullet(String(line.dropFirst(2))))
            } else if let dot = line.firstIndex(of: "."), line[..<dot].allSatisfy(\.isNumber), !line[..<dot].isEmpty,
                      line.index(after: dot) < line.endIndex, line[line.index(after: dot)] == " " {
                flush()
                result.append(.numbered(String(line[..<dot]), String(line[line.index(dot, offsetBy: 2)...])))
            } else if line.hasPrefix(">") {
                flush()
                result.append(.quote(line.dropFirst().trimmingCharacters(in: .whitespaces)))
            } else {
                paragraph.append(line)
            }
        }
        flush()
        return result
    }
}

/// Tags of an exercise: language, style, duration.
struct ExerciseTags: View {
    let language: String
    let style: String?
    let minutes: Int?
    var sector: String?

    var body: some View {
        HStack(spacing: 6) {
            Chip(text: Format.languageTag(language), tint: language == "en" ? Brand.mbb : Brand.textSecondary)
            if style == "mbb" { Chip(text: "MBB", tint: Brand.mbb) }
            if let m = Format.minutes(minutes) { Chip(text: m, symbol: "clock") }
            if let sector, !sector.isEmpty { Chip(text: sector) }
        }
    }
}
