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

/// The streak flame: breathes gently, glows when the day's goal is met.
struct FlameView: View {
    let streak: Int
    var lit: Bool
    var size: CGFloat = 96
    @Environment(\.palette) private var palette
    @State private var breathe = false

    var body: some View {
        ZStack {
            Circle()
                .fill(palette.accent.opacity(lit ? 0.22 : 0.08))
                .frame(width: size * 1.25, height: size * 1.25)
                .blur(radius: 14)
                .scaleEffect(breathe ? 1.06 : 0.94)
            Image(systemName: lit ? "flame.fill" : "flame")
                .font(.system(size: size * 0.78, weight: .bold))
                .foregroundStyle(lit ? AnyShapeStyle(palette.linear) : AnyShapeStyle(Color.white.opacity(0.45)))
                .scaleEffect(breathe ? 1.04 : 1)
                .symbolEffect(.bounce, value: streak)
        }
        .frame(width: size * 1.3, height: size * 1.3)
        .onAppear {
            withAnimation(.easeInOut(duration: 1.6).repeatForever(autoreverses: true)) { breathe = true }
        }
        .accessibilityElement()
        .accessibilityLabel("Série de \(streak) jours")
    }
}
