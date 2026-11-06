import CaseDuoCore
import SwiftUI

/// The moments that make a finished exercise feel good (D16): a burst of particles when the
/// score lands, a verdict that pops under it, and the full-screen « Journée complète ».

/// A radial burst of particles, thrown once per change of `trigger`, from the centre.
struct BurstView: View {
    let trigger: Int
    var colors: [Color]
    var count = 26

    @State private var particles: [Particle] = []
    @State private var start: Date?
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    private let duration: TimeInterval = 0.9

    var body: some View {
        TimelineView(.animation(paused: start == nil)) { context in
            Canvas { canvas, size in
                guard let start else { return }
                let t = context.date.timeIntervalSince(start)
                guard t < duration else { return }
                let progress = t / duration
                let ease = 1 - pow(1 - progress, 3)
                let cx = Double(size.width) / 2
                let cy = Double(size.height) / 2
                let reach = Double(min(size.width, size.height)) / 2
                for p in particles {
                    let distance = reach * p.speed * ease
                    let x = cx + cos(p.angle) * distance
                    let y = cy + sin(p.angle) * distance + 40 * progress * progress
                    var piece = canvas
                    piece.opacity = max(0, 1 - progress * 1.1)
                    piece.translateBy(x: CGFloat(x), y: CGFloat(y))
                    let radius = p.size * (1 - 0.5 * progress)
                    piece.fill(Path(ellipseIn: CGRect(x: -radius, y: -radius, width: radius * 2, height: radius * 2)),
                               with: .color(p.color))
                }
            }
        }
        .allowsHitTesting(false)
        .accessibilityHidden(true)
        .onChange(of: trigger) { _, _ in burst() }
    }

    private func burst() {
        guard !reduceMotion else { return }
        particles = (0..<count).map { i in
            Particle(angle: Double(i) / Double(count) * 2 * .pi + .random(in: -0.12...0.12),
                     speed: .random(in: 0.55...1.0), size: .random(in: 3...6),
                     color: colors.randomElement() ?? .white)
        }
        start = Date()
        DispatchQueue.main.asyncAfter(deadline: .now() + duration + 0.1) { start = nil }
    }

    struct Particle {
        var angle, speed: Double
        var size: CGFloat
        var color: Color
    }
}

/// « Excellent ! », « Bien joué », « On s'accroche » : pops in with the score.
struct VerdictBadge: View {
    let score: Int
    var tint: Color
    @State private var shown = false
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    var body: some View {
        Label(text, systemImage: symbol)
            .font(.subheadline.weight(.heavy))
            .foregroundStyle(score >= 50 ? Color.black : Color.white)
            .padding(.horizontal, 12)
            .padding(.vertical, 7)
            .background(score >= 50 ? tint : Brand.cardRaised, in: Capsule())
            .scaleEffect(shown || reduceMotion ? 1 : 0.4)
            .opacity(shown || reduceMotion ? 1 : 0)
            .onAppear {
                withAnimation(.spring(duration: 0.4, bounce: 0.45).delay(0.15)) { shown = true }
            }
            .accessibilityLabel(text)
    }

    private var text: String {
        switch score {
        case 90...: return "Excellent !"
        case 80..<90: return "Très bien"
        case 65..<80: return "Bien joué"
        case 50..<65: return "Ça progresse"
        default: return "On s'accroche"
        }
    }

    private var symbol: String {
        switch score {
        case 80...: return "star.fill"
        case 50..<80: return "hand.thumbsup.fill"
        default: return "arrow.up.heart.fill"
        }
    }
}

/// The XP earned, counting up and rising a little when it lands.
struct XPPop: View {
    let earned: Int
    var tint: Color
    @State private var shown = 0
    @State private var landed = false
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    var body: some View {
        HStack(spacing: 6) {
            Image(systemName: "sparkles")
                .symbolEffect(.bounce, value: landed)
            Text(Format.xp(shown, signed: true))
                .monospacedDigit()
                .contentTransition(.numericText(value: Double(shown)))
        }
        .font(.title2.weight(.heavy))
        .foregroundStyle(tint)
        .offset(y: landed || reduceMotion ? 0 : 8)
        .onAppear {
            withAnimation(.easeOut(duration: 0.5).delay(0.1)) { shown = earned }
            withAnimation(.spring(duration: 0.35, bounce: 0.4).delay(0.1)) { landed = true }
        }
        .onChange(of: earned) { _, new in withAnimation(.easeOut(duration: 0.3)) { shown = new } }
        .accessibilityLabel(Format.xp(earned, signed: true))
    }
}

/// Every card of the day done: the mascot cheers, the bonus lands, confetti once.
struct DayCompleteOverlay: View {
    @Environment(AppModel.self) private var model
    @Environment(\.palette) private var palette
    @Environment(\.dismiss) private var dismiss
    @State private var burst = 0
    @State private var shown = false

    var body: some View {
        ZStack {
            Brand.background.ignoresSafeArea()
            BurstView(trigger: burst, colors: palette.gradient + [Brand.success, .white], count: 40)
                .frame(width: 320, height: 320)
            VStack(spacing: 18) {
                Spacer()
                FlameMascot(mood: .happy, size: 150)
                    .scaleEffect(shown ? 1 : 0.6)
                Text("Journée complète !")
                    .font(.system(size: 34, weight: .heavy, design: .rounded))
                    .foregroundStyle(palette.linear)
                Text("+20 XP de bonus. Tout le plan du jour est fait.")
                    .font(.headline)
                    .foregroundStyle(Brand.textSecondary)
                    .multilineTextAlignment(.center)
                if let today = model.today {
                    HStack(spacing: 12) {
                        stat(value: Format.xp(today.goal.xpToday), label: "aujourd'hui")
                        stat(value: "\(today.streak.current)", label: today.streak.current > 1 ? "jours de série" : "jour de série")
                    }
                    .padding(.top, 6)
                }
                Spacer()
                Button("Voir le bilan du jour") {
                    dismiss()
                    model.goHome()
                    model.homePath = [.dayClose]
                }
                .buttonStyle(.pill)
                Button("Continuer") { dismiss() }
                    .buttonStyle(.pill(.quiet))
            }
            .padding(24)
        }
        .onAppear {
            withAnimation(.spring(duration: 0.5, bounce: 0.4)) { shown = true }
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.25) { burst += 1 }
        }
    }

    private func stat(value: String, label: String) -> some View {
        VStack(spacing: 4) {
            Text(value).font(.title2.weight(.heavy)).monospacedDigit()
            Text(label).font(.caption).foregroundStyle(Brand.textSecondary)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 14)
        .card(radius: 16)
    }
}
