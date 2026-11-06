import SwiftUI

// The CaseDuo mascot (D16): the streak flame with a face, drawn in SwiftUI, no image. All geometry
// lives in a 100 × 120 design box, prototyped as SVG and checked by eye before being ported, and
// is scaled by `size`. Six moods, same body: only the face changes.

public enum MascotMood: String, CaseIterable, Sendable {
    case idle, happy, proud, sleepy, thinking, sad

    /// Read by VoiceOver as the accessibility value.
    var frenchDescription: String {
        switch self {
        case .idle: return "calme"
        case .happy: return "joyeuse"
        case .proud: return "fière"
        case .sleepy: return "somnolente"
        case .thinking: return "en pleine réflexion"
        case .sad: return "un peu triste"
        }
    }

    /// Closed or half-closed eyes do not blink.
    var blinks: Bool { self != .happy && self != .sleepy }
}

// MARK: - Palette (mirrors Brand in Theme.swift; local so the file is self-contained)

private enum MascotColor {
    static let flameLight = Color(red: 1.0, green: 0.82, blue: 0.35)   // #FFD159
    static let flame      = Color(red: 1.0, green: 0.62, blue: 0.10)   // #FF9E1A
    static let flameDeep  = Color(red: 1.0, green: 0.42, blue: 0.12)   // #FF6B1F
    static let pupil      = Color(red: 0.08, green: 0.08, blue: 0.10)
}

// MARK: - Shapes (design box 100 × 120)

/// Maps a design-box point into `rect`.
private func designPoint(_ x: CGFloat, _ y: CGFloat, in rect: CGRect) -> CGPoint {
    CGPoint(x: rect.minX + x / 100 * rect.width, y: rect.minY + y / 120 * rect.height)
}

/// Outer flame: pointed tip leaning right, concave "lick" on the left, round bottom.
struct FlameBody: Shape {
    /// How far the tip sags, in design units (0 normally, 8 when sleepy).
    var droop: CGFloat = 0
    var animatableData: CGFloat { get { droop } set { droop = newValue } }

    func path(in rect: CGRect) -> Path {
        func p(_ x: CGFloat, _ y: CGFloat) -> CGPoint { designPoint(x, y, in: rect) }
        let d = droop
        let tip = p(64 + d * 0.5, 6 + d)
        var path = Path()
        path.move(to: tip)
        path.addCurve(to: p(93, 78), control1: p(68 + d * 0.5, 22 + d * 0.7), control2: p(93, 50)) // right side
        path.addCurve(to: p(50, 116), control1: p(93, 100), control2: p(75, 116))                   // round bottom
        path.addCurve(to: p(7, 78), control1: p(25, 116), control2: p(7, 100))
        path.addCurve(to: p(24, 40), control1: p(7, 62), control2: p(14, 50))                       // left shoulder
        path.addCurve(to: tip, control1: p(34 + d * 0.2, 30 + d * 0.4), control2: p(54 + d * 0.3, 22 + d * 0.6))
        path.closeSubpath()
        return path
    }
}

/// Lighter core in the lower half; the face sits on it.
struct InnerFlame: Shape {
    func path(in rect: CGRect) -> Path {
        func p(_ x: CGFloat, _ y: CGFloat) -> CGPoint { designPoint(x, y, in: rect) }
        var path = Path()
        path.move(to: p(59, 54))
        path.addCurve(to: p(78, 92), control1: p(63, 66), control2: p(78, 76))
        path.addCurve(to: p(50, 111), control1: p(78, 105), control2: p(64, 111))
        path.addCurve(to: p(22, 92), control1: p(36, 111), control2: p(22, 105))
        path.addCurve(to: p(59, 54), control1: p(22, 78), control2: p(48, 68))
        path.closeSubpath()
        return path
    }
}

/// Four-point star, the pupil when proud.
private struct Sparkle: Shape {
    func path(in rect: CGRect) -> Path {
        let c = CGPoint(x: rect.midX, y: rect.midY)
        let r = min(rect.width, rect.height) / 2
        let k = r * 0.22                                           // how pinched the waist is
        let tips = [CGPoint(x: c.x, y: c.y - r), CGPoint(x: c.x + r, y: c.y),
                    CGPoint(x: c.x, y: c.y + r), CGPoint(x: c.x - r, y: c.y)]
        let waists = [CGPoint(x: c.x + k, y: c.y - k), CGPoint(x: c.x + k, y: c.y + k),
                      CGPoint(x: c.x - k, y: c.y + k), CGPoint(x: c.x - k, y: c.y - k)]
        var path = Path()
        path.move(to: tips[0])
        for i in 0..<4 { path.addQuadCurve(to: tips[(i + 1) % 4], control: waists[i]) }
        path.closeSubpath()
        return path
    }
}

/// Heavy upper eyelid (sleepy), in the eye's own frame; its edge sags toward the outer corner.
/// `closed` gives the visible lower part of the eye (used as a mask), otherwise just the edge to stroke.
private struct Eyelid: Shape {
    var innerOnRight: Bool
    var closed: Bool

    func path(in rect: CGRect) -> Path {
        let pad = rect.width / 15                                  // one design unit
        let outerX = innerOnRight ? rect.minX - pad : rect.maxX + pad
        let innerX = innerOnRight ? rect.maxX + pad : rect.minX - pad
        var path = Path()
        path.move(to: CGPoint(x: outerX, y: rect.minY + rect.height * 0.632))
        path.addQuadCurve(to: CGPoint(x: innerX, y: rect.minY + rect.height * 0.474),
                          control: CGPoint(x: rect.midX, y: rect.minY + rect.height * 0.616))
        if closed {
            path.addLine(to: CGPoint(x: innerX, y: rect.maxY + pad))
            path.addLine(to: CGPoint(x: outerX, y: rect.maxY + pad))
            path.closeSubpath()
        }
        return path
    }
}

// MARK: - Eye (frame 15 × 19 design units: sclera rx 7.5, ry 9.5)

private struct Eye: View {
    let mood: MascotMood
    let u: CGFloat          // points per design unit
    let isLeft: Bool

    var body: some View {
        ZStack {
            if mood == .happy {                                    // closed, happy "^"
                Path { p in
                    p.move(to: CGPoint(x: 2 * u, y: 10.5 * u))
                    p.addQuadCurve(to: CGPoint(x: 13 * u, y: 10.5 * u), control: CGPoint(x: 7.5 * u, y: 2.5 * u))
                }
                .stroke(MascotColor.pupil, style: StrokeStyle(lineWidth: 2.8 * u, lineCap: .round))
            } else {
                openEye.mask {
                    if mood == .sleepy { Eyelid(innerOnRight: isLeft, closed: true) } else { Rectangle() }
                }
                if mood == .sleepy {
                    Eyelid(innerOnRight: isLeft, closed: false)
                        .stroke(MascotColor.flameDeep, style: StrokeStyle(lineWidth: 2.4 * u, lineCap: .round))
                }
            }
        }
        .frame(width: 15 * u, height: 19 * u)
    }

    private var openEye: some View {
        let s = pupilShift
        return ZStack {
            Ellipse().fill(Color.white)
            if mood == .proud {
                Sparkle().fill(MascotColor.pupil)
                    .frame(width: 8.8 * u, height: 8.8 * u).offset(x: s.x * u, y: (s.y + 0.4) * u)
            } else {
                Ellipse().fill(MascotColor.pupil)
                    .frame(width: 8.4 * u, height: 10.8 * u).offset(x: s.x * u, y: s.y * u)
                Circle().fill(Color.white)                         // highlight
                    .frame(width: 3.2 * u, height: 3.2 * u).offset(x: (s.x - 1.3) * u, y: (s.y - 1.8) * u)
            }
        }
    }

    /// Where the pupil looks, in design units.
    private var pupilShift: CGPoint {
        switch mood {
        case .sad, .sleepy: return CGPoint(x: 0, y: 3.2)           // looking down
        case .thinking: return CGPoint(x: 1.8, y: -1.8)            // looking up and away
        default: return .zero
        }
    }
}

// MARK: - Mascot

struct FlameMascot: View {
    var mood: MascotMood = .idle
    var size: CGFloat = 120
    var glow: Bool = true

    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var bounce: CGFloat = 1
    @State private var born = Date()

    init(mood: MascotMood = .idle, size: CGFloat = 120, glow: Bool = true) {
        self.mood = mood
        self.size = size
        self.glow = glow
    }

    /// Points per design unit; the flame is `size` tall and 100/120 of that wide.
    private var u: CGFloat { size / 120 }

    var body: some View {
        // Ambient motion (breathing, sway, blink) is computed from the clock, frame by frame: no
        // SwiftUI animation transaction is ever started for it, so nothing can leak into the
        // transitions of the screen around the mascot.
        TimelineView(.animation(minimumInterval: 1.0 / 30.0, paused: reduceMotion)) { context in
            let t = context.date.timeIntervalSince(born)
            ZStack {
                if glow {
                    Circle().fill(MascotColor.flame.opacity(0.22))
                        .frame(width: size * 0.8, height: size * 0.8).blur(radius: size * 0.12)
                }
                flame(blink: blinkScale(at: t))
                    .frame(width: 100 * u, height: size)
                    .rotationEffect(.degrees(swayAngle(at: t)))
                    .scaleEffect(breathScale(at: t))
                    .scaleEffect(bounce)
                    .animation(reduceMotion ? nil : .spring(duration: 0.35, bounce: 0.4), value: bounce)
            }
        }
        .frame(width: size, height: size)
        .onChange(of: mood) { _, newMood in
            if newMood == .happy || newMood == .proud { bounceOnce() }
        }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("Mascotte CaseDuo")
        .accessibilityValue(mood.frenchDescription)
    }

    private func flame(blink: CGFloat) -> some View {
        ZStack(alignment: .topLeading) {
            FlameBody(droop: mood == .sleepy ? 8 : 0)
                .fill(LinearGradient(colors: [MascotColor.flameLight, MascotColor.flame, MascotColor.flameDeep],
                                     startPoint: .top, endPoint: .bottom))
            InnerFlame().fill(MascotColor.flameLight.opacity(0.9))
            Eye(mood: mood, u: u, isLeft: true).scaleEffect(x: 1, y: blink).position(d(38, 80))
            Eye(mood: mood, u: u, isLeft: false).scaleEffect(x: 1, y: blink).position(d(62, 80))
            if mood == .thinking {                                 // one raised eyebrow
                Capsule().fill(MascotColor.pupil).frame(width: 10 * u, height: 2.6 * u)
                    .rotationEffect(.degrees(-14)).position(d(63, 65))
            }
            mouth
        }
        .animation(reduceMotion ? nil : Animation.easeInOut(duration: 0.35), value: mood) // face and droop ease
    }

    @ViewBuilder private var mouth: some View {
        let stroke = StrokeStyle(lineWidth: 2.8 * u, lineCap: .round)
        switch mood {
        case .idle:
            curve(from: (44.5, 96.5), control: (50, 103.5), to: (55.5, 96.5)).stroke(MascotColor.pupil, style: stroke)
        case .proud:
            curve(from: (43.2, 96.5), control: (50, 105.5), to: (56.8, 96.5)).stroke(MascotColor.pupil, style: stroke)
        case .sad:
            curve(from: (44.4, 98.3), control: (50, 91.7), to: (55.6, 98.3)).stroke(MascotColor.pupil, style: stroke)
        case .happy:                                               // open laugh with a tongue
            Path { p in
                p.move(to: d(42, 94))
                p.addCurve(to: d(58, 94), control1: d(42, 104.7), control2: d(58, 104.7))
                p.closeSubpath()
            }
            .fill(MascotColor.pupil)
            Ellipse().fill(MascotColor.flameDeep).frame(width: 8 * u, height: 4.4 * u).position(d(50, 100.4))
        case .sleepy:                                              // flat
            Capsule().fill(MascotColor.pupil).frame(width: 8 * u, height: 2.8 * u).position(d(50, 95.8))
        case .thinking:                                            // small "o"
            Circle().fill(MascotColor.pupil).frame(width: 6.8 * u, height: 6.8 * u).position(d(52, 96))
        }
    }

    /// Design-box point in view points.
    private func d(_ x: CGFloat, _ y: CGFloat) -> CGPoint { CGPoint(x: x * u, y: y * u) }

    /// A quadratic curve in design units (smile, frown).
    private func curve(from a: (CGFloat, CGFloat), control c: (CGFloat, CGFloat), to b: (CGFloat, CGFloat)) -> Path {
        var path = Path()
        path.move(to: d(a.0, a.1))
        path.addQuadCurve(to: d(b.0, b.1), control: d(c.0, c.1))
        return path
    }

    // MARK: Motion, as functions of time (seconds since the view appeared). With Reduce Motion
    // the timeline is paused: everything stays at its rest value.

    /// A gentle 1.0 ↔ 1.03 breath every 3.2 s.
    private func breathScale(at t: TimeInterval) -> CGFloat {
        guard !reduceMotion else { return 1 }
        return 1.015 + 0.015 * CGFloat(sin(t * 2 * .pi / 3.2))
    }

    /// ±3° when sleepy, every 2.8 s.
    private func swayAngle(at t: TimeInterval) -> Double {
        guard mood == .sleepy, !reduceMotion else { return 0 }
        return 3 * sin(t * 2 * .pi / 2.8)
    }

    /// Eyes closed for 0.16 s every 3.6 s (not when they are already shut or heavy).
    private func blinkScale(at t: TimeInterval) -> CGFloat {
        guard mood.blinks, !reduceMotion else { return 1 }
        let phase = t.truncatingRemainder(dividingBy: 3.6)
        guard phase < 0.16 else { return 1 }
        return phase < 0.08 ? 1 - CGFloat(phase / 0.08) * 0.9 : 0.1 + CGFloat((phase - 0.08) / 0.08) * 0.9
    }

    /// One spring bounce when the mood turns happy or proud: a finite animation, scoped to the mascot.
    private func bounceOnce() {
        guard !reduceMotion else { return }
        bounce = 1.12
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.2) { bounce = 1 }
    }
}

#Preview("Mascotte") {
    VStack(spacing: 24) {
        HStack(spacing: 12) { ForEach(MascotMood.allCases, id: \.self) { FlameMascot(mood: $0, size: 100) } }
        HStack(spacing: 12) { ForEach(MascotMood.allCases, id: \.self) { FlameMascot(mood: $0, size: 40, glow: false) } }
    }
    .frame(maxWidth: .infinity, maxHeight: .infinity)
    .background(Color(red: 0.055, green: 0.059, blue: 0.071))
}
