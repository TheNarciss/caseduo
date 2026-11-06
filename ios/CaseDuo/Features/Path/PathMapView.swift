import CaseDuoCore
import SwiftUI

/// The Parcours on the Aujourd'hui tab (docs/PARCOURS.md): units one after the other, each a
/// header and its steps on a winding path. The active step pulses, done steps are gold, locked
/// ones grey. An « en situation » step opens one of the day's exercises.
struct PathMapView: View {
    let path: PathView
    @Environment(AppModel.self) private var model
    @Environment(\.pushRoute) private var pushRoute
    @Environment(\.palette) private var palette
    @State private var lockedHint: String?

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 8) {
                Image(systemName: "map.fill").font(.subheadline.weight(.bold)).foregroundStyle(palette.accent)
                Text("Parcours").font(.headline)
                Spacer()
                Text("\(path.done)/\(path.total)")
                    .font(.caption.monospacedDigit().weight(.bold))
                    .foregroundStyle(path.done == path.total ? Brand.success : Brand.textSecondary)
            }
            .padding(.top, 6)
            .accessibilityElement(children: .combine)

            ForEach(path.units) { unit in
                UnitHeader(unit: unit, isCurrent: unit.nodes.contains { $0.status == .active })
                NodeTrail(nodes: unit.nodes, tint: Brand.color(forTrack: unit.track)) { node in open(node) }
            }

            if let lockedHint {
                Text(lockedHint)
                    .font(.footnote)
                    .foregroundStyle(Brand.textSecondary)
                    .frame(maxWidth: .infinity)
                    .transition(.opacity)
            }
        }
        .animation(Brand.quick, value: lockedHint)
    }

    private func open(_ node: PathNode) {
        switch node.status {
        case .locked, .unknown:
            Haptics.shared.play(.tap)
            lockedHint = node.kind == .legendary
                ? "Termine le bilan de l'unité pour tenter la légendaire."
                : "Termine l'étape précédente pour débloquer « \(node.title) »."
            DispatchQueue.main.asyncAfter(deadline: .now() + 2.5) { lockedHint = nil }
        case .done, .active, .available:
            Haptics.shared.play(.tap)
            if node.kind == .applied {
                if let card = model.exerciseCard(forApplied: node.appliedType) {
                    pushRoute(.exercise(id: card.exerciseId, revenge: card.isRevenge))
                } else {
                    lockedHint = "Les exercices du jour ne sont pas encore là."
                    DispatchQueue.main.asyncAfter(deadline: .now() + 2.5) { lockedHint = nil }
                }
            } else {
                pushRoute(.lesson(code: node.code))
            }
        }
    }
}

extension Brand {
    /// A colour per track of the course: the common trunk is the flame, the specialisations each
    /// their own.
    static func color(forTrack track: String) -> Color {
        switch track {
        case "transfo": return techScreen
        case "strat": return businessCase
        case "finance": return diagnostic
        default: return flame
        }
    }
}

/// A unit: number, title, what it teaches, how far along.
struct UnitHeader: View {
    let unit: PathUnit
    let isCurrent: Bool
    @Environment(\.palette) private var palette

    var body: some View {
        HStack(spacing: 14) {
            IconCircle(symbol: unit.isComplete ? "checkmark" : unit.symbol,
                       tint: unit.isComplete ? Brand.success : Brand.color(forTrack: unit.track), size: 44)
            VStack(alignment: .leading, spacing: 3) {
                Text("Unité \(unit.order) · \(unit.title)")
                    .font(.headline)
                    .foregroundStyle(isCurrent || unit.isComplete ? .white : Brand.textSecondary)
                Text(unit.subtitle)
                    .font(.caption)
                    .foregroundStyle(Brand.textSecondary)
                    .lineLimit(2)
            }
            Spacer(minLength: 0)
            Text("\(unit.done)/\(unit.total)")
                .font(.caption.monospacedDigit().weight(.bold))
                .foregroundStyle(unit.isComplete ? Brand.success : Brand.textSecondary)
        }
        .padding(14)
        .card(radius: 16, fill: isCurrent ? Brand.cardRaised : Brand.card)
        .padding(.top, 8)
        .accessibilityElement(children: .combine)
    }
}

/// The steps of a unit on a winding line: each one a little left or right of the previous.
struct NodeTrail: View {
    let nodes: [PathNode]
    let tint: Color
    let open: (PathNode) -> Void

    private let step: CGFloat = 96
    private let amplitude: CGFloat = 64

    private func offset(_ index: Int) -> CGFloat {
        amplitude * CGFloat(sin(Double(index) * 1.1))
    }

    var body: some View {
        ZStack(alignment: .top) {
            Canvas { context, size in
                var line = Path()
                let cx = size.width / 2
                for (i, _) in nodes.enumerated() {
                    let point = CGPoint(x: cx + offset(i), y: step * CGFloat(i) + step / 2)
                    if i == 0 { line.move(to: point) } else { line.addLine(to: point) }
                }
                context.stroke(line, with: .color(Color.white.opacity(0.10)),
                               style: StrokeStyle(lineWidth: 6, lineCap: .round, lineJoin: .round, dash: [0.1, 12]))
            }
            .frame(height: step * CGFloat(nodes.count))
            .accessibilityHidden(true)
            VStack(spacing: 0) {
                ForEach(Array(nodes.enumerated()), id: \.element.id) { index, node in
                    NodeButton(node: node, tint: tint) { open(node) }
                        .frame(height: step)
                        .offset(x: offset(index))
                }
            }
        }
        .frame(maxWidth: .infinity)
    }
}

/// One step: a disc with the kind's symbol, the title under it, the state in its colour.
struct NodeButton: View {
    let node: PathNode
    let tint: Color
    let action: () -> Void
    @Environment(\.palette) private var palette
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var born = Date()

    private var size: CGFloat { node.kind == .checkpoint || node.kind == .legendary ? 72 : 64 }

    private var fill: Color {
        switch node.status {
        case .done: return node.kind == .legendary ? palette.accent : Brand.success
        case .active: return tint
        case .available: return Brand.cardRaised
        case .locked, .unknown: return Brand.card
        }
    }

    private var symbol: String {
        if node.status == .done { return node.kind == .legendary ? "crown.fill" : "checkmark" }
        if node.status == .locked || node.status == .unknown { return "lock.fill" }
        switch node.kind {
        case .lesson: return "star.fill"
        case .review: return "arrow.triangle.2.circlepath"
        case .applied: return "briefcase.fill"
        case .checkpoint: return "flag.checkered"
        case .legendary: return "crown.fill"
        case .unknown: return "questionmark"
        }
    }

    private var foreground: Color {
        switch node.status {
        case .done, .active: return .black
        case .available: return tint
        case .locked, .unknown: return Brand.textTertiary
        }
    }

    var body: some View {
        Button(action: action) {
            VStack(spacing: 6) {
                ZStack {
                    if node.status == .active {
                        TimelineView(.animation(minimumInterval: 1.0 / 30.0, paused: reduceMotion)) { context in
                            let t = context.date.timeIntervalSince(born)
                            let phase = (t.truncatingRemainder(dividingBy: 1.6)) / 1.6
                            Circle()
                                .stroke(tint.opacity(0.7 * (1 - phase)), lineWidth: 3)
                                .frame(width: size + 10 + 26 * phase, height: size + 10 + 26 * phase)
                        }
                        .accessibilityHidden(true)
                    }
                    Circle()
                        .fill(fill)
                        .frame(width: size, height: size)
                        .overlay(Circle().stroke(node.status == .available ? tint.opacity(0.6) : Brand.stroke, lineWidth: 2))
                        .shadow(color: node.status == .active ? tint.opacity(0.45) : .clear, radius: 12, y: 4)
                    Image(systemName: symbol)
                        .font(.system(size: size * 0.36, weight: .bold))
                        .foregroundStyle(foreground)
                }
                Text(node.title)
                    .font(.caption.weight(node.status == .active ? .bold : .semibold))
                    .foregroundStyle(node.status == .locked ? Brand.textTertiary : .white)
                    .lineLimit(1)
                    .frame(width: 130)
                if node.status == .done, let score = node.bestScore, node.kind != .applied {
                    Text("\(score) %")
                        .font(.caption2.monospacedDigit())
                        .foregroundStyle(Brand.scoreColor(score))
                } else if node.status == .active {
                    Text(node.kind == .applied ? "Le case du jour" : "+\(node.xp) XP")
                        .font(.caption2.weight(.bold))
                        .foregroundStyle(tint)
                }
            }
        }
        .buttonStyle(.plain)
        .accessibilityLabel("\(node.title), \(label)")
        .accessibilityIdentifier("path.node.\(node.code)")
    }

    private var label: String {
        switch node.status {
        case .done: return "terminé" + (node.bestScore.map { " à \($0) %" } ?? "")
        case .active: return "étape en cours"
        case .available: return "disponible"
        case .locked, .unknown: return "verrouillé"
        }
    }
}
