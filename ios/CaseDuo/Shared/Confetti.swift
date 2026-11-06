import SwiftUI

/// Confetti, kept for three moments only (spec): streak +1, perfect week, league promotion.
/// Each change of `trigger` throws one burst; the view never takes touches.
struct ConfettiView: View {
    let trigger: Int
    var colors: [Color] = [Brand.flame, Brand.flameLight, Brand.success, Brand.freeze, Brand.revenge, .white]

    @State private var particles: [Particle] = []
    @State private var start: Date?

    private let duration: TimeInterval = 1.8

    var body: some View {
        TimelineView(.animation(paused: start == nil)) { context in
            Canvas { canvas, size in
                guard let start else { return }
                let t = context.date.timeIntervalSince(start)
                guard t < duration else { return }
                let width = Double(size.width)
                let height = Double(size.height)
                for p in particles {
                    let x: Double = p.x * width + p.vx * t * width
                    let fall: Double = 0.5 * 900 * t * t * p.gravity
                    let y: Double = -20 + p.vy * t * height + fall
                    let fade = max(0, 1 - t / duration)
                    var piece = canvas
                    piece.opacity = fade
                    piece.translateBy(x: CGFloat(x), y: CGFloat(y))
                    piece.rotate(by: .degrees(p.spin * t * 360))
                    piece.fill(Path(CGRect(x: -p.size / 2, y: -p.size / 4, width: p.size, height: p.size / 2)),
                               with: .color(p.color))
                }
            }
        }
        .allowsHitTesting(false)
        .accessibilityHidden(true)
        .onChange(of: trigger) { _, _ in burst() }
    }

    private func burst() {
        particles = (0..<90).map { _ in
            Particle(x: .random(in: 0.05...0.95), vx: .random(in: -0.15...0.15), vy: .random(in: 0.1...0.45),
                     gravity: .random(in: 0.6...1.2), spin: .random(in: -1.5...1.5), size: .random(in: 7...12),
                     color: colors.randomElement() ?? .white)
        }
        start = Date()
        DispatchQueue.main.asyncAfter(deadline: .now() + duration + 0.1) {
            start = nil
        }
    }

    struct Particle {
        var x, vx, vy, gravity, spin: Double
        var size: CGFloat
        var color: Color
    }
}

/// The streak flame (login, launch): breathes gently, glows when lit. The breath is computed
/// from the clock, so no animation transaction can leak into the screen around it.
struct FlameView: View {
    let streak: Int
    var lit: Bool
    var size: CGFloat = 96
    @Environment(\.palette) private var palette
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var born = Date()

    var body: some View {
        TimelineView(.animation(minimumInterval: 1.0 / 30.0, paused: reduceMotion)) { context in
            let phase = reduceMotion ? 0 : sin(context.date.timeIntervalSince(born) * 2 * .pi / 3.2)
            ZStack {
                Circle()
                    .fill(palette.accent.opacity(lit ? 0.22 : 0.08))
                    .frame(width: size * 1.25, height: size * 1.25)
                    .blur(radius: 14)
                    .scaleEffect(1 + 0.06 * CGFloat(phase))
                Image(systemName: lit ? "flame.fill" : "flame")
                    .font(.system(size: size * 0.78, weight: .bold))
                    .foregroundStyle(lit ? AnyShapeStyle(palette.linear) : AnyShapeStyle(Color.white.opacity(0.45)))
                    .scaleEffect(1.02 + 0.02 * CGFloat(phase))
                    .symbolEffect(.bounce, value: streak)
            }
        }
        .frame(width: size * 1.3, height: size * 1.3)
        .accessibilityElement()
        .accessibilityLabel("Série de \(streak) jours")
    }
}
