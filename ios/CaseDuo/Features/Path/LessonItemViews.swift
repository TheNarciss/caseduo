import CaseDuoCore
import SwiftUI

/// One item on screen, by format. Each view writes the learner's answer into `answer` (nil
/// while it is not complete enough to check) and freezes once `locked` (after the check).
struct LessonItemView: View {
    let item: PathItem
    let locked: Bool
    /// Once checked: the views colour the choice green or orange and reveal the key.
    var verdict: PathVerdict? = nil
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
            case .choice(let options, let correct, let shuffle):
                ChoiceView(options: options, correct: correct, shuffle: shuffle, seed: item.id, locked: locked,
                           verdict: verdict, tint: tint, answer: $answer)
            case .swipe(let cards, _):
                SwipeCardsView(cards: cards, locked: locked, verdict: verdict, tint: tint, answer: $answer)
            case .spotError(let lines, let wrongLine, _):
                SpotErrorView(lines: lines, wrongLine: wrongLine, locked: locked, verdict: verdict, tint: tint, answer: $answer)
            case .tiles(let tiles, _, _, _):
                TilesView(tiles: tiles, seed: item.id, locked: locked, verdict: verdict, tint: tint, answer: $answer)
            case .mentalMath(let questions, let seconds):
                MentalMathView(questions: questions, seconds: seconds, locked: locked, tint: tint, answer: $answer)
            case .estimate(_, let slider, let unit, let log, _):
                EstimateView(slider: slider, unit: unit, log: log, locked: locked, tint: tint, answer: $answer)
            case .twoStep(let formulas, let correctFormula, _, let unit, _):
                TwoStepView(formulas: formulas, correctFormula: correctFormula, unit: unit, locked: locked,
                            verdict: verdict, tint: tint, answer: $answer)
            case .fillBlank(let text, let slots):
                FillBlankView(text: text, slots: slots, locked: locked, verdict: verdict, tint: tint, answer: $answer)
            case .meceSort(let buckets, let items):
                MeceSortView(buckets: buckets, items: items, locked: locked, verdict: verdict, tint: tint, answer: $answer)
            case .matchPairs(let pairs):
                MatchPairsView(pairs: pairs, seed: item.id, locked: locked, verdict: verdict, tint: tint, answer: $answer)
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

/// How an answer row looks: untouched, chosen, and after the check: right, wrong, or the key
/// revealed next to a wrong choice.
enum OptionState: Equatable { case idle, selected, right, wrong, revealed }

extension OptionState {
    /// The state of one option once the answer is known.
    static func of(id: String, chosen: String?, correct: String, verdict: PathVerdict?) -> OptionState {
        guard verdict != nil else { return chosen == id ? .selected : .idle }
        if id == correct { return chosen == id ? .right : .revealed }
        return chosen == id ? .wrong : .idle
    }
}

/// A tappable answer row: one of several options, a line of a calculation. Green with a tick
/// when right, orange with a cross and a shake when wrong, green outline for the key.
struct OptionRow: View {
    let text: String
    var state: OptionState
    let locked: Bool
    var tint: Color
    var leading: String?
    let action: () -> Void
    @State private var shakes = 0

    private var accent: Color {
        switch state {
        case .idle: return Brand.stroke
        case .selected: return tint
        case .right, .revealed: return Brand.success
        case .wrong: return Brand.danger
        }
    }

    private var fillColor: Color {
        switch state {
        case .idle: return Brand.card
        case .selected: return tint.opacity(0.16)
        case .right: return Brand.success.opacity(0.18)
        case .revealed: return Brand.success.opacity(0.08)
        case .wrong: return Brand.danger.opacity(0.16)
        }
    }

    var body: some View {
        Button(action: action) {
            HStack(alignment: .firstTextBaseline, spacing: 12) {
                if let leading {
                    Text(leading)
                        .font(.caption.weight(.bold))
                        .foregroundStyle(state == .idle ? tint : Color.black)
                        .frame(width: 26, height: 26)
                        .background(state == .idle ? tint.opacity(0.14) : accent, in: Circle())
                }
                Text(text)
                    .font(.body)
                    .multilineTextAlignment(.leading)
                    .foregroundStyle(.white)
                Spacer(minLength: 0)
                if state == .right || state == .wrong || state == .revealed {
                    Image(systemName: state == .wrong ? "xmark.circle.fill" : "checkmark.circle.fill")
                        .font(.title3)
                        .foregroundStyle(accent)
                        .transition(.scale.combined(with: .opacity))
                        .popIn()
                }
            }
            .padding(14)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(fillColor, in: RoundedRectangle(cornerRadius: 16, style: .continuous))
            .overlay(RoundedRectangle(cornerRadius: 16, style: .continuous).stroke(accent, lineWidth: state == .idle ? 1 : 2))
        }
        .buttonStyle(PressScaleStyle())
        .disabled(locked)
        .scaleEffect(state == .selected ? 1.015 : 1)
        .animation(Motion.snappy, value: state)
        .shake(trigger: shakes)
        .onChange(of: state) { _, new in if new == .wrong { shakes += 1 } }
        .accessibilityAddTraits(state == .selected ? .isSelected : [])
        .accessibilityValue(state == .right ? "juste" : state == .wrong ? "faux" : state == .revealed ? "la bonne réponse" : "")
    }
}

/// A button that gives a little under the finger.
struct PressScaleStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .scaleEffect(configuration.isPressed ? 0.97 : 1)
            .animation(Motion.snappy, value: configuration.isPressed)
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
    let correct: String
    let shuffle: Bool
    let seed: String
    let locked: Bool
    var verdict: PathVerdict?
    var tint: Color
    @Binding var answer: PathAnswer?
    @State private var chosen: String?

    private var ordered: [PathOption] { shuffle ? seededOrder(options, seed: seed) : options }

    var body: some View {
        VStack(spacing: 10) {
            ForEach(Array(ordered.enumerated()), id: \.element.id) { index, option in
                OptionRow(text: option.text, state: .of(id: option.id, chosen: chosen, correct: correct, verdict: verdict),
                          locked: locked, tint: tint, leading: letter(index)) {
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

/// Cards one by one, big, in the middle of the screen: drag right for « valide », left for
/// « pas valide », or the two large buttons. The card flies off in the chosen direction.
struct SwipeCardsView: View {
    let cards: [PathCard]
    let locked: Bool
    var verdict: PathVerdict?
    var tint: Color
    @Binding var answer: PathAnswer?
    @State private var decisions: [String: Bool] = [:]
    @State private var drag: CGSize = .zero
    /// The card leaving the screen and where it goes.
    @State private var flying: (id: String, valid: Bool)?
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    private var remaining: [PathCard] { cards.filter { decisions[$0.id] == nil || flying?.id == $0.id } }
    private var doneCount: Int { decisions.count - (flying == nil ? 0 : 1) }

    var body: some View {
        VStack(spacing: 18) {
            if remaining.isEmpty {
                recap
            } else {
                HStack {
                    Text("Carte \(min(cards.count, doneCount + 1)) sur \(cards.count)")
                        .font(.caption.weight(.bold)).foregroundStyle(Brand.textSecondary)
                    Spacer()
                    HStack(spacing: 4) {
                        ForEach(cards) { card in
                            Capsule().fill(decisions[card.id] == nil ? Color.white.opacity(0.15) : tint)
                                .frame(width: decisions[card.id] == nil ? 8 : 16, height: 6)
                        }
                    }
                    .animation(Motion.snappy, value: decisions.count)
                }
                ZStack {
                    ForEach(Array(remaining.prefix(3).enumerated().reversed()), id: \.element.id) { index, card in
                        cardView(card, depth: index)
                    }
                }
                .frame(maxWidth: .infinity, minHeight: 300)
                HStack(spacing: 14) {
                    decideButton(false, symbol: "xmark", label: "Pas valide", color: Brand.danger)
                    decideButton(true, symbol: "checkmark", label: "Valide", color: Brand.success)
                }
                Text("Glisse la carte, ou touche un bouton.")
                    .font(.caption2).foregroundStyle(Brand.textTertiary)
            }
        }
    }

    /// Every card with the choice made, and after the check, whether it was right.
    private var recap: some View {
        VStack(spacing: 8) {
            ForEach(cards) { card in
                let chosen = decisions[card.id] ?? false
                let judged = verdict != nil
                let right = chosen == card.valid
                HStack(spacing: 12) {
                    Image(systemName: judged ? (right ? "checkmark.circle.fill" : "xmark.circle.fill")
                                             : (chosen ? "hand.thumbsup.fill" : "hand.thumbsdown.fill"))
                        .font(.title3)
                        .foregroundStyle(judged ? (right ? Brand.success : Brand.danger) : (chosen ? Brand.success : Brand.danger))
                    VStack(alignment: .leading, spacing: 2) {
                        Text(card.text).font(.subheadline.weight(.medium))
                        if judged, !right {
                            Text(card.reason).font(.caption).foregroundStyle(Brand.textSecondary)
                        }
                    }
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
                .padding(14)
                .card(radius: 16, fill: judged ? (right ? Brand.success.opacity(0.10) : Brand.danger.opacity(0.12)) : Brand.card)
            }
        }
    }

    private func cardView(_ card: PathCard, depth: Int) -> some View {
        let isTop = depth == 0
        let isFlying = flying?.id == card.id
        let x: CGFloat = isFlying ? (flying?.valid == true ? 600 : -600) : (isTop ? drag.width : 0)
        return VStack(spacing: 14) {
            Image(systemName: "quote.opening")
                .font(.title3).foregroundStyle(tint.opacity(0.7))
            Text(card.text)
                .font(.title2.weight(.semibold))
                .multilineTextAlignment(.center)
                .minimumScaleFactor(0.8)
        }
        .padding(28)
        .frame(maxWidth: .infinity, minHeight: 300)
        .background(
            RoundedRectangle(cornerRadius: 28, style: .continuous)
                .fill(LinearGradient(colors: [Brand.cardRaised, Brand.card], startPoint: .top, endPoint: .bottom))
        )
        .overlay(RoundedRectangle(cornerRadius: 28, style: .continuous).stroke(borderColor(isTop: isTop), lineWidth: 2.5))
        .overlay(alignment: .topLeading) {
            if isTop, drag.width > 30 || (isFlying && flying?.valid == true) { stamp("VALIDE", color: Brand.success, angle: -12) }
        }
        .overlay(alignment: .topTrailing) {
            if isTop, drag.width < -30 || (isFlying && flying?.valid == false) { stamp("PAS VALIDE", color: Brand.danger, angle: 12) }
        }
        .shadow(color: Color.black.opacity(isTop ? 0.4 : 0.2), radius: 16, y: 8)
        .scaleEffect(1 - CGFloat(depth) * 0.05)
        .offset(x: x, y: CGFloat(depth) * 10)
        .rotationEffect(.degrees(Double(x) / 14))
        .opacity(isFlying ? 0 : 1)
        .gesture(dragGesture(card), including: isTop && !locked && !isFlying ? .all : .none)
        .animation(isFlying ? Motion.fling : Motion.settle, value: x)
        .animation(Motion.settle, value: depth)
    }

    private func stamp(_ text: String, color: Color, angle: Double) -> some View {
        Text(text)
            .font(.system(size: 18, weight: .black, design: .rounded))
            .foregroundStyle(color)
            .padding(.horizontal, 10).padding(.vertical, 5)
            .overlay(RoundedRectangle(cornerRadius: 8).stroke(color, lineWidth: 3))
            .rotationEffect(.degrees(angle))
            .padding(18)
            .transition(.scale(scale: 1.6).combined(with: .opacity))
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
            if let card = remaining.first(where: { flying?.id != $0.id }) { decide(card, valid) }
        } label: {
            Label(label, systemImage: symbol)
                .font(.headline)
                .foregroundStyle(color)
                .padding(.vertical, 16)
                .frame(maxWidth: .infinity)
                .background(color.opacity(0.16), in: Capsule())
                .overlay(Capsule().stroke(color.opacity(0.5), lineWidth: 1.5))
        }
        .buttonStyle(PressScaleStyle())
        .disabled(locked || flying != nil)
        .accessibilityIdentifier(valid ? "lesson.swipe.valid" : "lesson.swipe.invalid")
    }

    private func decide(_ card: PathCard, _ valid: Bool) {
        Haptics.shared.play(.tap)
        Sounds.shared.play(.pop)
        decisions[card.id] = valid
        if reduceMotion {
            answer = decisions.count == cards.count ? .swipes(decisions) : nil
            return
        }
        flying = (card.id, valid)
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.3) {
            flying = nil
            answer = decisions.count == cards.count ? .swipes(decisions) : nil
        }
    }
}

// MARK: - Spot the error

struct SpotErrorView: View {
    let lines: [PathLine]
    let wrongLine: String
    let locked: Bool
    var verdict: PathVerdict?
    var tint: Color
    @Binding var answer: PathAnswer?
    @State private var chosen: String?

    var body: some View {
        VStack(spacing: 8) {
            ForEach(Array(lines.enumerated()), id: \.element.id) { index, line in
                OptionRow(text: line.text, state: .of(id: line.id, chosen: chosen, correct: wrongLine, verdict: verdict),
                          locked: locked, tint: tint, leading: "\(index + 1)") {
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
    var verdict: PathVerdict?
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
                .background(verdictFill, in: RoundedRectangle(cornerRadius: 16, style: .continuous))
                .overlay(RoundedRectangle(cornerRadius: 16, style: .continuous).stroke(verdictStroke, lineWidth: verdict == nil ? 1 : 2))
                .shake(trigger: verdict?.correct == false ? 1 : 0)
            }
            FlowLayout(spacing: 8) {
                ForEach(bank) { tile in
                    let used = placed.contains(tile.id)
                    Button {
                        guard !locked, !used else { return }
                        Haptics.shared.play(.tap)
                        Sounds.shared.play(.pop)
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

    private var verdictFill: Color {
        guard let verdict else { return Brand.card }
        return verdict.correct ? Brand.success.opacity(0.12) : Brand.danger.opacity(0.12)
    }

    private var verdictStroke: Color {
        guard let verdict else { return Brand.stroke }
        return verdict.correct ? Brand.success : Brand.danger
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
    let correctFormula: String
    let unit: String
    let locked: Bool
    var verdict: PathVerdict?
    var tint: Color
    @Binding var answer: PathAnswer?
    @State private var formula: String?
    @State private var text = ""

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("1 · La formule").font(.caption.weight(.bold)).foregroundStyle(Brand.textSecondary)
            ForEach(Array(formulas.enumerated()), id: \.element.id) { index, option in
                OptionRow(text: option.text, state: .of(id: option.id, chosen: formula, correct: correctFormula, verdict: verdict),
                          locked: locked, tint: tint, leading: letter(index)) {
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
                    .overlay(RoundedRectangle(cornerRadius: 12, style: .continuous)
                        .stroke(verdict == nil ? Color.clear : (verdict?.correct == true ? Brand.success : Brand.danger), lineWidth: 2))
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
    var verdict: PathVerdict?
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

    private func chipTint(slot: FillSlot, index: Int) -> Color {
        guard verdict != nil else { return tint }
        if slot.correct == index { return Brand.success }
        return chosen[slot.id] == index ? Brand.danger : tint
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
                                TileChip(text: option, tint: chipTint(slot: slot, index: index), placed: chosen[slot.id] == index || (verdict != nil && slot.correct == index))
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
    var verdict: PathVerdict?
    var tint: Color
    @Binding var answer: PathAnswer?
    @State private var placed: [String: String] = [:]

    private func bucketTint(item: SortItem, bucket: SortBucket) -> Color {
        guard verdict != nil else { return tint }
        if item.bucket == bucket.id { return Brand.success }
        return placed[item.id] == bucket.id ? Brand.danger : tint
    }

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
                                let color = bucketTint(item: item, bucket: bucket)
                                let on = placed[item.id] == bucket.id || (verdict != nil && item.bucket == bucket.id)
                                Text(bucket.label)
                                    .font(.caption.weight(.bold))
                                    .lineLimit(1)
                                    .minimumScaleFactor(0.7)
                                    .foregroundStyle(on ? Color.black : color)
                                    .padding(.vertical, 10)
                                    .frame(maxWidth: .infinity)
                                    .background(on ? color : color.opacity(0.12), in: Capsule())
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
    var verdict: PathVerdict?
    var tint: Color
    @Binding var answer: PathAnswer?
    @State private var matched: [String: String] = [:]
    @State private var pendingLeft: String?

    private var rights: [String] { seededOrder(pairs.map(\.right), seed: seed + "#r") }
    private var pairColors: [Color] { [tint, Brand.marketSizing, Brand.cadrage, Brand.diagnostic, Brand.brainteaser, Brand.fit] }

    private func color(forLeft left: String) -> Color? {
        guard let right = matched[left], let index = pairs.firstIndex(where: { $0.left == left }) else { return nil }
        if verdict != nil { return pairs[index].right == right ? Brand.success : Brand.danger }
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
