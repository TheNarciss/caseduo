import CaseDuoCore
import SwiftUI

/// One item on screen, by format. Each view writes the learner's answer into `answer` (nil
/// while it is not complete enough to check) and freezes once `locked` (after the check).
struct LessonItemView: View {
    let item: PathItem
    let locked: Bool
    @Binding var answer: PathAnswer?
    var tint: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text(item.format.label.uppercased())
                .font(.caption.weight(.bold))
                .foregroundStyle(tint)
            if !item.stem.isEmpty {
                MarkdownText(markdown: item.stem, font: .title3.weight(.semibold))
            }
            if let media = item.media {
                PathMediaView(media: media, tint: tint)
            }
            switch item.payload {
            case .concept(let screens):
                ConceptCardView(screens: screens, tint: tint, answer: $answer)
            case .choice(let options, _, let shuffle):
                ChoiceView(options: options, shuffle: shuffle, seed: item.id, locked: locked, tint: tint, answer: $answer)
            case .swipe(let cards, _):
                SwipeCardsView(cards: cards, locked: locked, tint: tint, answer: $answer)
            case .spotError(let lines, _, _):
                SpotErrorView(lines: lines, locked: locked, tint: tint, answer: $answer)
            case .tiles(let tiles, _, _, _):
                TilesView(tiles: tiles, seed: item.id, locked: locked, tint: tint, answer: $answer)
            case .mentalMath(let questions, let seconds):
                MentalMathView(questions: questions, seconds: seconds, locked: locked, tint: tint, answer: $answer)
            case .estimate(_, let slider, let unit, let log, _):
                EstimateView(slider: slider, unit: unit, log: log, locked: locked, tint: tint, answer: $answer)
            case .twoStep(let formulas, _, _, let unit, _):
                TwoStepView(formulas: formulas, unit: unit, locked: locked, tint: tint, answer: $answer)
            case .fillBlank(let text, let slots):
                FillBlankView(text: text, slots: slots, locked: locked, tint: tint, answer: $answer)
            case .meceSort(let buckets, let items):
                MeceSortView(buckets: buckets, items: items, locked: locked, tint: tint, answer: $answer)
            case .matchPairs(let pairs):
                MatchPairsView(pairs: pairs, seed: item.id, locked: locked, tint: tint, answer: $answer)
            case .oral(let seconds, let rubric, _):
                OralItemView(seconds: seconds, rubric: rubric, locked: locked, tint: tint, answer: $answer)
            case .unknown:
                UnknownFormatView(answer: $answer)
            }
        }
    }
}

// MARK: - Helpers

/// "A", "B", "C"… for the options.
private func letter(_ index: Int) -> String {
    String(Character(Unicode.Scalar(UInt8(65 + min(index, 25)))))
}

/// A stable shuffle per item, so the order does not change when the view redraws.
private func seededOrder<T>(_ items: [T], seed: String) -> [T] {
    var state = UInt64(5381)
    for byte in seed.utf8 { state = (state &* 33) &+ UInt64(byte) }
    var out = items
    for i in stride(from: out.count - 1, to: 0, by: -1) {
        state = state &* 6364136223846793005 &+ 1442695040888963407
        let j = Int((state >> 33) % UInt64(i + 1))
        out.swapAt(i, j)
    }
    return out
}

/// A tappable answer row: one of several options, a line of a calculation.
struct OptionRow: View {
    let text: String
    let selected: Bool
    let locked: Bool
    var tint: Color
    var leading: String?
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(alignment: .firstTextBaseline, spacing: 12) {
                if let leading {
                    Text(leading)
                        .font(.caption.weight(.bold))
                        .foregroundStyle(selected ? Color.black : tint)
                        .frame(width: 24, height: 24)
                        .background(selected ? tint : tint.opacity(0.14), in: Circle())
                }
                Text(text)
                    .font(.body)
                    .multilineTextAlignment(.leading)
                    .foregroundStyle(.white)
                Spacer(minLength: 0)
            }
            .padding(14)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(selected ? tint.opacity(0.16) : Brand.card, in: RoundedRectangle(cornerRadius: 14, style: .continuous))
            .overlay(RoundedRectangle(cornerRadius: 14, style: .continuous).stroke(selected ? tint : Brand.stroke, lineWidth: selected ? 2 : 1))
        }
        .buttonStyle(.plain)
        .disabled(locked)
        .accessibilityAddTraits(selected ? .isSelected : [])
    }
}

/// A word on a tile, in the bank or in the answer.
struct TileChip: View {
    let text: String
    var tint: Color
    var placed = false
    var ghost = false

    var body: some View {
        Text(text)
            .font(.subheadline.weight(.semibold))
            .foregroundStyle(ghost ? .clear : (placed ? Color.black : .white))
            .padding(.horizontal, 12)
            .padding(.vertical, 9)
            .background(ghost ? Brand.card : (placed ? tint : Brand.cardRaised), in: RoundedRectangle(cornerRadius: 10, style: .continuous))
            .overlay(RoundedRectangle(cornerRadius: 10, style: .continuous).stroke(ghost ? Brand.stroke : .clear, lineWidth: 1))
    }
}

// MARK: - Concept card

struct ConceptCardView: View {
    let screens: [ConceptScreen]
    var tint: Color
    @Binding var answer: PathAnswer?

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            ForEach(Array(screens.enumerated()), id: \.offset) { index, screen in
                VStack(alignment: .leading, spacing: 8) {
                    HStack(spacing: 8) {
                        Text("\(index + 1)")
                            .font(.caption.weight(.heavy))
                            .foregroundStyle(Color.black)
                            .frame(width: 22, height: 22)
                            .background(tint, in: Circle())
                        Text(screen.title).font(.headline)
                    }
                    MarkdownText(markdown: screen.body)
                }
                .padding(16)
                .frame(maxWidth: .infinity, alignment: .leading)
                .card(radius: 16)
            }
        }
        .onAppear { answer = .read }
    }
}

// MARK: - Choice (choose_structure, pick_so_what, first_question, tree_complete)

struct ChoiceView: View {
    let options: [PathOption]
    let shuffle: Bool
    let seed: String
    let locked: Bool
    var tint: Color
    @Binding var answer: PathAnswer?
    @State private var chosen: String?

    private var ordered: [PathOption] { shuffle ? seededOrder(options, seed: seed) : options }

    var body: some View {
        VStack(spacing: 10) {
            ForEach(Array(ordered.enumerated()), id: \.element.id) { index, option in
                OptionRow(text: option.text, selected: chosen == option.id, locked: locked, tint: tint,
                          leading: letter(index)) {
                    Haptics.shared.play(.tap)
                    chosen = option.id
                    answer = .option(option.id)
                }
                .accessibilityIdentifier("lesson.option.\(index)")
            }
        }
    }
}

// MARK: - Swipe

/// Cards one by one: drag right for « valide », left for « pas valide », or the two buttons.
struct SwipeCardsView: View {
    let cards: [PathCard]
    let locked: Bool
    var tint: Color
    @Binding var answer: PathAnswer?
    @State private var decisions: [String: Bool] = [:]
    @State private var drag: CGSize = .zero

    private var remaining: [PathCard] { cards.filter { decisions[$0.id] == nil } }

    var body: some View {
        VStack(spacing: 14) {
            ZStack {
                ForEach(Array(remaining.prefix(3).enumerated().reversed()), id: \.element.id) { index, card in
                    cardView(card, depth: index)
                }
                if remaining.isEmpty {
                    VStack(spacing: 8) {
                        ForEach(cards) { card in
                            HStack(spacing: 10) {
                                Image(systemName: decisions[card.id] == true ? "checkmark.circle.fill" : "xmark.circle.fill")
                                    .foregroundStyle(decisions[card.id] == true ? Brand.success : Brand.danger)
                                Text(card.text).font(.subheadline)
                                Spacer(minLength: 0)
                                if !locked {
                                    Button("Changer") {
                                        decisions[card.id] = nil
                                        answer = nil
                                    }
                                    .font(.caption.weight(.bold))
                                    .foregroundStyle(tint)
                                }
                            }
                            .padding(12)
                            .card(radius: 12)
                        }
                    }
                }
            }
            .frame(minHeight: 150)
            if !remaining.isEmpty {
                HStack(spacing: 16) {
                    decideButton(false, symbol: "xmark", label: "Pas valide", color: Brand.danger)
                    Text("\(cards.count - remaining.count + 1)/\(cards.count)")
                        .font(.caption.monospacedDigit().weight(.bold))
                        .foregroundStyle(Brand.textSecondary)
                    decideButton(true, symbol: "checkmark", label: "Valide", color: Brand.success)
                }
            }
        }
    }

    private func cardView(_ card: PathCard, depth: Int) -> some View {
        let isTop = depth == 0
        return Text(card.text)
            .font(.title3.weight(.semibold))
            .multilineTextAlignment(.center)
            .padding(24)
            .frame(maxWidth: .infinity, minHeight: 150)
            .background(Brand.cardRaised, in: RoundedRectangle(cornerRadius: 20, style: .continuous))
            .overlay(RoundedRectangle(cornerRadius: 20, style: .continuous).stroke(borderColor(isTop: isTop), lineWidth: 2))
            .overlay(alignment: .topLeading) {
                if isTop, drag.width > 30 {
                    Label("Valide", systemImage: "checkmark").font(.headline).foregroundStyle(Brand.success).padding(14)
                }
            }
            .overlay(alignment: .topTrailing) {
                if isTop, drag.width < -30 {
                    Label("Pas valide", systemImage: "xmark").font(.headline).foregroundStyle(Brand.danger).padding(14)
                }
            }
            .scaleEffect(1 - CGFloat(depth) * 0.04)
            .offset(x: isTop ? drag.width : 0, y: CGFloat(depth) * 8)
            .rotationEffect(.degrees(isTop ? Double(drag.width) / 18 : 0))
            .gesture(dragGesture(card), including: isTop && !locked ? .all : .none)
            .animation(Brand.spring, value: drag)
    }

    private func borderColor(isTop: Bool) -> Color {
        guard isTop else { return Brand.stroke }
        if drag.width > 30 { return Brand.success }
        if drag.width < -30 { return Brand.danger }
        return tint.opacity(0.5)
    }

    private func dragGesture(_ card: PathCard) -> some Gesture {
        DragGesture(minimumDistance: 12)
            .onChanged { value in
                // Horizontal only: a vertical drag is the page scrolling.
                guard abs(value.translation.width) > abs(value.translation.height) else { return }
                drag = CGSize(width: value.translation.width, height: 0)
            }
            .onEnded { value in
                if value.translation.width > 80 { decide(card, true) }
                else if value.translation.width < -80 { decide(card, false) }
                drag = .zero
            }
    }

    private func decideButton(_ valid: Bool, symbol: String, label: String, color: Color) -> some View {
        Button {
            if let card = remaining.first { decide(card, valid) }
        } label: {
            Label(label, systemImage: symbol)
                .font(.subheadline.weight(.bold))
                .foregroundStyle(color)
                .padding(.vertical, 10)
                .frame(maxWidth: .infinity)
                .background(color.opacity(0.14), in: Capsule())
        }
        .buttonStyle(.plain)
        .disabled(locked)
        .accessibilityIdentifier(valid ? "lesson.swipe.valid" : "lesson.swipe.invalid")
    }

    private func decide(_ card: PathCard, _ valid: Bool) {
        Haptics.shared.play(.tap)
        decisions[card.id] = valid
        answer = decisions.count == cards.count ? .swipes(decisions) : nil
    }
}

// MARK: - Spot the error

struct SpotErrorView: View {
    let lines: [PathLine]
    let locked: Bool
    var tint: Color
    @Binding var answer: PathAnswer?
    @State private var chosen: String?

    var body: some View {
        VStack(spacing: 8) {
            ForEach(Array(lines.enumerated()), id: \.element.id) { index, line in
                OptionRow(text: line.text, selected: chosen == line.id, locked: locked, tint: tint, leading: "\(index + 1)") {
                    Haptics.shared.play(.tap)
                    chosen = line.id
                    answer = .line(line.id)
                }
            }
        }
    }
}

// MARK: - Tiles (order_steps, synth_order, headline_tiles)

struct TilesView: View {
    let tiles: [PathTile]
    let seed: String
    let locked: Bool
    var tint: Color
    @Binding var answer: PathAnswer?
    @State private var placed: [String] = []

    private var bank: [PathTile] { seededOrder(tiles, seed: seed) }
    private var byId: [String: PathTile] { Dictionary(uniqueKeysWithValues: tiles.map { ($0.id, $0) }) }

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            VStack(alignment: .leading, spacing: 6) {
                Text("Ta réponse").font(.caption.weight(.bold)).foregroundStyle(Brand.textSecondary)
                FlowLayout(spacing: 8) {
                    ForEach(Array(placed.enumerated()), id: \.element) { index, id in
                        Button {
                            guard !locked else { return }
                            placed.remove(at: index)
                            update()
                        } label: {
                            HStack(spacing: 6) {
                                Text("\(index + 1)").font(.caption2.weight(.heavy)).foregroundStyle(Color.black.opacity(0.6))
                                Text(byId[id]?.text ?? id).font(.subheadline.weight(.semibold)).foregroundStyle(Color.black)
                            }
                            .padding(.horizontal, 12).padding(.vertical, 9)
                            .background(tint, in: RoundedRectangle(cornerRadius: 10, style: .continuous))
                        }
                        .buttonStyle(.plain)
                    }
                    if placed.isEmpty {
                        TileChip(text: "Touche les tuiles dans l'ordre", tint: tint, ghost: true)
                            .overlay(Text("Touche les tuiles dans l'ordre").font(.subheadline).foregroundStyle(Brand.textTertiary))
                    }
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(12)
                .background(Brand.card, in: RoundedRectangle(cornerRadius: 14, style: .continuous))
                .overlay(RoundedRectangle(cornerRadius: 14, style: .continuous).stroke(Brand.stroke, lineWidth: 1))
            }
            FlowLayout(spacing: 8) {
                ForEach(bank) { tile in
                    let used = placed.contains(tile.id)
                    Button {
                        guard !locked, !used else { return }
                        Haptics.shared.play(.tap)
                        placed.append(tile.id)
                        update()
                    } label: {
                        TileChip(text: tile.text, tint: tint, ghost: used)
                    }
                    .buttonStyle(.plain)
                    .disabled(used || locked)
                    .accessibilityIdentifier("lesson.tile.\(tile.id)")
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            if !placed.isEmpty, !locked {
                Button("Tout enlever") { placed = []; update() }
                    .font(.caption.weight(.bold)).foregroundStyle(Brand.textSecondary)
            }
        }
    }

    private func update() {
        answer = placed.isEmpty ? nil : .sequence(placed)
    }
}

// MARK: - Mental math

struct MentalMathView: View {
    let questions: [MathQuestion]
    let seconds: Int
    let locked: Bool
    var tint: Color
    @Binding var answer: PathAnswer?
    @State private var texts: [String: String] = [:]
    @State private var hints: Set<String> = []
    @State private var start = Date()
    @FocusState private var focused: String?

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            TimelineView(.periodic(from: start, by: 1)) { context in
                let left = max(0, seconds - Int(context.date.timeIntervalSince(start)))
                HStack(spacing: 6) {
                    Image(systemName: "timer")
                    Text(locked ? "Terminé" : Format.chrono(left)).monospacedDigit()
                }
                .font(.subheadline.weight(.bold))
                .foregroundStyle(left <= 10 && !locked ? Brand.danger : Brand.textSecondary)
            }
            ForEach(questions) { q in
                VStack(alignment: .leading, spacing: 8) {
                    Text(q.stem).font(.body)
                    HStack(spacing: 8) {
                        TextField("Réponse", text: Binding(get: { texts[q.id] ?? "" }, set: { texts[q.id] = $0; update() }))
                            .keyboardType(.numbersAndPunctuation)
                            .textFieldStyle(.plain)
                            .font(.title3.weight(.semibold).monospacedDigit())
                            .padding(12)
                            .background(Brand.cardRaised, in: RoundedRectangle(cornerRadius: 12, style: .continuous))
                            .focused($focused, equals: q.id)
                            .disabled(locked)
                            .accessibilityIdentifier("lesson.math.\(q.id)")
                        Text(q.unit).font(.subheadline).foregroundStyle(Brand.textSecondary)
                        if q.hint != nil, !hints.contains(q.id) {
                            Button {
                                hints.insert(q.id)
                            } label: {
                                Image(systemName: "lightbulb").foregroundStyle(tint)
                            }
                            .accessibilityLabel("Indice")
                        }
                    }
                    if hints.contains(q.id), let hint = q.hint {
                        Text(hint).font(.caption).foregroundStyle(Brand.textSecondary)
                    }
                }
                .padding(12)
                .card(radius: 14)
            }
            Text("Tu peux écrire 1,2 M, 830 k, 21 000…").font(.caption2).foregroundStyle(Brand.textTertiary)
        }
    }

    private func update() {
        var values: [String: Double] = [:]
        for q in questions {
            if let v = PathGrader.parseNumber(texts[q.id] ?? "") { values[q.id] = v }
        }
        answer = values.count == questions.count ? .numbers(values) : nil
    }
}

// MARK: - Estimate

struct EstimateView: View {
    let slider: ClosedRange<Double>
    let unit: String
    let log: Bool
    let locked: Bool
    var tint: Color
    @Binding var answer: PathAnswer?
    @State private var position: Double = 0.5

    private var value: Double {
        if log, slider.lowerBound > 0 {
            let lo = log10(slider.lowerBound), hi = log10(slider.upperBound)
            return pow(10, lo + (hi - lo) * position)
        }
        return slider.lowerBound + (slider.upperBound - slider.lowerBound) * position
    }

    var body: some View {
        VStack(spacing: 10) {
            Text(Format.number(value) + (unit.isEmpty ? "" : " \(unit)"))
                .font(.system(size: 34, weight: .heavy, design: .rounded).monospacedDigit())
                .foregroundStyle(tint)
                .contentTransition(.numericText())
            Slider(value: $position, in: 0...1, onEditingChanged: { _ in Haptics.shared.play(.tap) })
            .tint(tint)
            .disabled(locked)
            .accessibilityLabel("Estimation")
            .accessibilityValue(Format.number(value) + " " + unit)
            HStack {
                Text(Format.number(slider.lowerBound)).font(.caption2)
                Spacer()
                if log { Text("échelle log").font(.caption2) }
                Spacer()
                Text(Format.number(slider.upperBound)).font(.caption2)
            }
            .foregroundStyle(Brand.textTertiary)
        }
        .padding(16)
        .card(radius: 16)
        .onAppear { answer = .estimate(value) }
        .onChange(of: position) { _, _ in answer = .estimate(value) }
    }
}

// MARK: - Two-step calculation

struct TwoStepView: View {
    let formulas: [PathOption]
    let unit: String
    let locked: Bool
    var tint: Color
    @Binding var answer: PathAnswer?
    @State private var formula: String?
    @State private var text = ""

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("1 · La formule").font(.caption.weight(.bold)).foregroundStyle(Brand.textSecondary)
            ForEach(Array(formulas.enumerated()), id: \.element.id) { index, option in
                OptionRow(text: option.text, selected: formula == option.id, locked: locked, tint: tint,
                          leading: letter(index)) {
                    Haptics.shared.play(.tap)
                    formula = option.id
                    update()
                }
            }
            Text("2 · Le résultat").font(.caption.weight(.bold)).foregroundStyle(Brand.textSecondary).padding(.top, 4)
            HStack(spacing: 8) {
                TextField("Résultat", text: $text)
                    .keyboardType(.numbersAndPunctuation)
                    .textFieldStyle(.plain)
                    .font(.title3.weight(.semibold).monospacedDigit())
                    .padding(12)
                    .background(Brand.cardRaised, in: RoundedRectangle(cornerRadius: 12, style: .continuous))
                    .disabled(locked)
                    .onChange(of: text) { _, _ in update() }
                    .accessibilityIdentifier("lesson.twostep.value")
                Text(unit).font(.subheadline).foregroundStyle(Brand.textSecondary)
            }
        }
    }

    private func update() {
        guard let formula else { answer = nil; return }
        answer = .twoStep(formula: formula, value: PathGrader.parseNumber(text))
    }
}

// MARK: - Fill in the blank

struct FillBlankView: View {
    let text: String
    let slots: [FillSlot]
    let locked: Bool
    var tint: Color
    @Binding var answer: PathAnswer?
    @State private var chosen: [Int: Int] = [:]

    /// The sentence with each blank shown as the chosen word or a gap.
    private var sentence: String {
        var out = text
        for slot in slots {
            let word = chosen[slot.id].flatMap { slot.options[safe: $0] }
            out = out.replacingOccurrences(of: "{{\(slot.id)}}", with: word.map { "**\($0)**" } ?? "＿＿＿")
        }
        return out
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            MarkdownText(markdown: sentence, font: .title3)
                .padding(14)
                .frame(maxWidth: .infinity, alignment: .leading)
                .card(radius: 14)
            ForEach(slots) { slot in
                VStack(alignment: .leading, spacing: 6) {
                    if slots.count > 1 {
                        Text("Trou \(slot.id)").font(.caption.weight(.bold)).foregroundStyle(Brand.textSecondary)
                    }
                    FlowLayout(spacing: 8) {
                        ForEach(Array(slot.options.enumerated()), id: \.offset) { index, option in
                            Button {
                                guard !locked else { return }
                                Haptics.shared.play(.tap)
                                chosen[slot.id] = index
                                answer = chosen.count == slots.count ? .blanks(chosen) : nil
                            } label: {
                                TileChip(text: option, tint: tint, placed: chosen[slot.id] == index)
                            }
                            .buttonStyle(.plain)
                            .disabled(locked)
                            .accessibilityIdentifier("lesson.blank.\(slot.id).\(index)")
                        }
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                }
            }
        }
    }
}

// MARK: - MECE sort

struct MeceSortView: View {
    let buckets: [SortBucket]
    let items: [SortItem]
    let locked: Bool
    var tint: Color
    @Binding var answer: PathAnswer?
    @State private var placed: [String: String] = [:]

    var body: some View {
        VStack(spacing: 10) {
            ForEach(items) { item in
                VStack(alignment: .leading, spacing: 8) {
                    Text(item.text).font(.body.weight(.medium))
                    HStack(spacing: 6) {
                        ForEach(buckets) { bucket in
                            Button {
                                guard !locked else { return }
                                Haptics.shared.play(.tap)
                                placed[item.id] = bucket.id
                                answer = placed.count == items.count ? .buckets(placed) : nil
                            } label: {
                                Text(bucket.label)
                                    .font(.caption.weight(.bold))
                                    .lineLimit(1)
                                    .minimumScaleFactor(0.7)
                                    .foregroundStyle(placed[item.id] == bucket.id ? Color.black : tint)
                                    .padding(.vertical, 8)
                                    .frame(maxWidth: .infinity)
                                    .background(placed[item.id] == bucket.id ? tint : tint.opacity(0.12), in: Capsule())
                            }
                            .buttonStyle(.plain)
                            .disabled(locked)
                            .accessibilityLabel("\(item.text) : \(bucket.label)")
                        }
                    }
                }
                .padding(12)
                .card(radius: 14)
            }
        }
    }
}

// MARK: - Match pairs

struct MatchPairsView: View {
    let pairs: [MatchPair]
    let seed: String
    let locked: Bool
    var tint: Color
    @Binding var answer: PathAnswer?
    @State private var matched: [String: String] = [:]
    @State private var pendingLeft: String?

    private var rights: [String] { seededOrder(pairs.map(\.right), seed: seed + "#r") }
    private var pairColors: [Color] { [tint, Brand.marketSizing, Brand.cadrage, Brand.diagnostic, Brand.brainteaser, Brand.fit] }

    private func color(forLeft left: String) -> Color? {
        guard matched[left] != nil, let index = pairs.firstIndex(where: { $0.left == left }) else { return nil }
        return pairColors[index % pairColors.count]
    }

    private func color(forRight right: String) -> Color? {
        guard let left = matched.first(where: { $0.value == right })?.key else { return nil }
        return color(forLeft: left)
    }

    var body: some View {
        HStack(alignment: .top, spacing: 10) {
            VStack(spacing: 8) {
                ForEach(pairs, id: \.left) { pair in
                    cell(pair.left, color: color(forLeft: pair.left), highlighted: pendingLeft == pair.left) {
                        tapLeft(pair.left)
                    }
                }
            }
            VStack(spacing: 8) {
                ForEach(rights, id: \.self) { right in
                    cell(right, color: color(forRight: right), highlighted: false) { tapRight(right) }
                }
            }
        }
    }

    private func cell(_ text: String, color: Color?, highlighted: Bool, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Text(text)
                .font(.subheadline.weight(.semibold))
                .multilineTextAlignment(.center)
                .minimumScaleFactor(0.8)
                .foregroundStyle(color == nil ? .white : Color.black)
                .padding(.horizontal, 8)
                .padding(.vertical, 12)
                .frame(maxWidth: .infinity, minHeight: 56)
                .background(color ?? (highlighted ? tint.opacity(0.2) : Brand.card), in: RoundedRectangle(cornerRadius: 12, style: .continuous))
                .overlay(RoundedRectangle(cornerRadius: 12, style: .continuous).stroke(highlighted ? tint : Brand.stroke, lineWidth: highlighted ? 2 : 1))
        }
        .buttonStyle(.plain)
        .disabled(locked)
        .accessibilityAddTraits(highlighted ? .isSelected : [])
    }

    private func tapLeft(_ left: String) {
        Haptics.shared.play(.tap)
        if matched[left] != nil {
            matched[left] = nil
            answer = nil
        }
        pendingLeft = pendingLeft == left ? nil : left
    }

    private func tapRight(_ right: String) {
        Haptics.shared.play(.tap)
        if let left = matched.first(where: { $0.value == right })?.key {
            matched[left] = nil
            answer = nil
            return
        }
        guard let left = pendingLeft else { return }
        matched[left] = right
        pendingLeft = nil
        answer = matched.count == pairs.count ? .pairs(matched) : nil
    }
}

// MARK: - Oral

/// Said out loud, dictated, graded by the server at the end of the lesson.
struct OralItemView: View {
    let seconds: Int
    let rubric: [RubricLine]
    let locked: Bool
    var tint: Color
    @Binding var answer: PathAnswer?
    @State private var dictation = Dictation()
    @State private var typed = ""
    @State private var startedAt: Date?

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            VStack(alignment: .leading, spacing: 6) {
                Text("Ce qu'on attend").font(.caption.weight(.bold)).foregroundStyle(Brand.textSecondary)
                ForEach(rubric, id: \.key) { line in
                    Label(line.label, systemImage: "circle").font(.subheadline).foregroundStyle(.white)
                }
            }
            .padding(12)
            .frame(maxWidth: .infinity, alignment: .leading)
            .card(radius: 14)

            HStack(spacing: 14) {
                MicButton(recording: dictation.isRecording) { toggle() }
                    .disabled(locked)
                VStack(alignment: .leading, spacing: 2) {
                    if let startedAt {
                        TimelineView(.periodic(from: startedAt, by: 1)) { context in
                            let left = max(0, seconds - Int(context.date.timeIntervalSince(startedAt)))
                            Text(dictation.isRecording ? "Reste \(Format.chrono(left))" : "Dicté")
                                .font(.subheadline.weight(.bold)).monospacedDigit()
                                .foregroundStyle(left <= 10 && dictation.isRecording ? Brand.danger : .white)
                        }
                    } else {
                        Text("\(seconds) secondes").font(.subheadline.weight(.bold))
                    }
                    Text(dictation.isRecording ? "Parle comme en entretien." : "Touche le micro, puis parle.")
                        .font(.caption).foregroundStyle(Brand.textSecondary)
                }
                Spacer(minLength: 0)
            }

            if case .denied(let message) = dictation.state {
                Text(message).font(.footnote).foregroundStyle(Brand.danger)
            } else if case .unavailable(let message) = dictation.state {
                Text(message).font(.footnote).foregroundStyle(Brand.danger)
            }

            TextField("Ou écris ta réponse…", text: $typed, axis: .vertical)
                .lineLimit(3...8)
                .textFieldStyle(.plain)
                .padding(12)
                .background(Brand.cardRaised, in: RoundedRectangle(cornerRadius: 12, style: .continuous))
                .disabled(locked || dictation.isRecording)
                .onChange(of: typed) { _, text in
                    guard !dictation.isRecording else { return }
                    answer = .transcript(text)
                }
                .accessibilityIdentifier("lesson.oral.text")
        }
        .onChange(of: dictation.transcript) { _, text in
            guard dictation.isRecording else { return }
            typed = text
            answer = .transcript(text)
        }
        .onChange(of: locked) { _, isLocked in if isLocked { dictation.stop() } }
        .onDisappear { dictation.stop() }
    }

    private func toggle() {
        if dictation.isRecording {
            dictation.stop()
            Haptics.shared.play(.tap)
            answer = .transcript(typed)
            return
        }
        Haptics.shared.play(.tap)
        startedAt = Date()
        Task { await dictation.start(language: "fr", existing: typed) }
    }
}

// MARK: - Unknown

struct UnknownFormatView: View {
    @Binding var answer: PathAnswer?

    var body: some View {
        VStack(spacing: 8) {
            Image(systemName: "arrow.down.app").font(.title).foregroundStyle(Brand.textSecondary)
            Text("Ce format d'exercice demande une version plus récente de l'app.")
                .font(.subheadline).foregroundStyle(Brand.textSecondary).multilineTextAlignment(.center)
        }
        .frame(maxWidth: .infinity)
        .padding(20)
        .card(radius: 14)
        .onAppear { answer = .read }
    }
}
