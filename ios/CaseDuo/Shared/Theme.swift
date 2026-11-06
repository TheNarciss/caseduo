import CaseDuoCore
import SwiftUI
import UIKit

/// The look, like SingaSmoke's `Brand`: a dark background, a warm flame for the streak, green for
/// success, orange when something is in danger. Never an aggressive red.
enum Brand {
    // Surfaces
    static let background = Color(red: 0.055, green: 0.059, blue: 0.071)        // #0E0F12
    static let card = Color(red: 0.102, green: 0.110, blue: 0.129)              // #1A1C21
    static let cardRaised = Color(red: 0.137, green: 0.145, blue: 0.169)        // #23252B
    static let stroke = Color.white.opacity(0.08)

    // Meaning
    /// The streak flame, warm amber.
    static let flame = Color(red: 1.0, green: 0.62, blue: 0.10)                 // #FF9E1A
    static let flameDeep = Color(red: 1.0, green: 0.42, blue: 0.12)             // #FF6B1F
    static let flameLight = Color(red: 1.0, green: 0.82, blue: 0.35)            // #FFD159
    /// Success, a calm green.
    static let success = Color(red: 0.17, green: 0.85, blue: 0.49)              // #2BD97C
    /// "En danger": orange, not red.
    static let danger = Color(red: 1.0, green: 0.54, blue: 0.24)                // #FF8A3D
    /// Freezes: icy blue.
    static let freeze = Color(red: 0.45, green: 0.78, blue: 1.0)                // #73C7FF
    /// Revenge cards: violet.
    static let revenge = Color(red: 0.66, green: 0.52, blue: 1.0)               // #A885FF
    static let mbb = Color(red: 0.36, green: 0.62, blue: 1.0)                   // #5C9EFF

    static let textSecondary = Color.white.opacity(0.62)
    static let textTertiary = Color.white.opacity(0.4)

    // One colour per exercise family (D16): the card's icon and stripe, the section titles,
    // the Entraîner filters, the history curves. None is the flame, the green or the orange.
    static let brainteaser = Color(red: 1.0, green: 0.44, blue: 0.71)           // #FF70B5 rose
    static let fit = Color(red: 0.48, green: 0.55, blue: 1.0)                   // #7B8CFF indigo
    static let marketSizing = Color(red: 0.22, green: 0.78, blue: 0.96)         // #38C8F5 cyan
    static let cadrage = Color(red: 0.66, green: 0.52, blue: 1.0)               // #A885FF violet
    static let businessCase = Color(red: 0.15, green: 0.83, blue: 0.78)         // #27D3C8 turquoise
    static let diagnostic = Color(red: 0.78, green: 0.93, blue: 0.40)           // #C7ED66 citron
    static let techScreen = Color(red: 0.61, green: 0.72, blue: 1.0)            // #9BB7FF acier

    static func color(for type: ExerciseType) -> Color {
        switch type {
        case .brainteaser: return brainteaser
        case .fit: return fit
        case .marketSizing: return marketSizing
        case .cadrage, .cadrageHome: return cadrage
        case .businessCase: return businessCase
        case .diagnostic: return diagnostic
        case .techScreen: return techScreen
        case .unknown: return textSecondary
        }
    }

    static func color(for category: ExerciseCategory) -> Color {
        switch category {
        case .brainteasers: return brainteaser
        case .fit: return fit
        case .cases: return marketSizing
        case .homework: return cadrage
        }
    }

    static var flameGradient: LinearGradient {
        LinearGradient(colors: [flameLight, flame, flameDeep], startPoint: .top, endPoint: .bottom)
    }

    /// Score colour: green from 80, amber from 50, orange below. Never red.
    static func scoreColor(_ score: Int?) -> Color {
        guard let score else { return textSecondary }
        switch score {
        case 80...: return success
        case 50..<80: return flame
        default: return danger
        }
    }

    /// Animations stay under 300 ms (spec).
    static let quick = Animation.easeOut(duration: 0.22)
    static let spring = Animation.spring(duration: 0.28, bounce: 0.25)
}

/// The motion vocabulary (D18): a few named springs so every screen moves the same way.
/// Feedback is fast (under 150 ms to start), rewards bounce, surfaces settle without bounce.
enum Motion {
    /// A tap acknowledged: a quick, barely bouncy spring.
    static let snappy = Animation.spring(duration: 0.22, bounce: 0.2)
    /// A reward lands: a bouncy pop.
    static let bouncy = Animation.spring(duration: 0.45, bounce: 0.45)
    /// A panel or a card moves into place.
    static let settle = Animation.spring(duration: 0.38, bounce: 0.12)
    /// A card leaves the screen.
    static let fling = Animation.easeIn(duration: 0.28)
}

/// A horizontal shake, for a wrong answer: three quick wobbles that die out.
struct ShakeEffect: GeometryEffect {
    var amount: CGFloat = 10
    var shakes: CGFloat = 3
    var animatableData: CGFloat

    func effectValue(size: CGSize) -> ProjectionTransform {
        let progress = animatableData.truncatingRemainder(dividingBy: 1)
        let x = amount * sin(progress * .pi * shakes * 2) * (1 - progress)
        return ProjectionTransform(CGAffineTransform(translationX: x, y: 0))
    }
}

extension View {
    /// Shakes once each time `trigger` changes (no motion when the system asks for less).
    func shake(trigger: Int) -> some View { modifier(ShakeOnChange(trigger: trigger)) }
    /// Pops in (scale 0.6 → 1, bouncy) the first time it appears.
    func popIn(delay: Double = 0) -> some View { modifier(PopIn(delay: delay)) }
    /// Bounces (scale 1 → 1.18 → 1) each time `trigger` changes.
    func bounce(trigger: some Equatable) -> some View { modifier(BounceOnChange(trigger: trigger)) }
}

private struct ShakeOnChange: ViewModifier {
    let trigger: Int
    @State private var shakes: CGFloat = 0
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    func body(content: Content) -> some View {
        content
            .modifier(ShakeEffect(animatableData: shakes))
            .onChange(of: trigger) { _, _ in
                guard !reduceMotion else { return }
                withAnimation(.linear(duration: 0.45)) { shakes += 1 }
            }
    }
}

private struct PopIn: ViewModifier {
    let delay: Double
    @State private var shown = false
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    func body(content: Content) -> some View {
        content
            .scaleEffect(shown || reduceMotion ? 1 : 0.6)
            .opacity(shown || reduceMotion ? 1 : 0)
            .onAppear { withAnimation(Motion.bouncy.delay(delay)) { shown = true } }
    }
}

private struct BounceOnChange<T: Equatable>: ViewModifier {
    let trigger: T
    @State private var up = false
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    func body(content: Content) -> some View {
        content
            .scaleEffect(up ? 1.18 : 1)
            .onChange(of: trigger) { _, _ in
                guard !reduceMotion else { return }
                withAnimation(.spring(duration: 0.18, bounce: 0.3)) { up = true }
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.16) {
                    withAnimation(Motion.bouncy) { up = false }
                }
            }
    }
}

/// The accent of the moment: the usual flame, or the perfect-week theme for seven days.
struct Palette: Equatable {
    var accent: Color
    var accentSoft: Color
    var gradient: [Color]
    var isPerfectWeek: Bool

    static let standard = Palette(accent: Brand.flame, accentSoft: Brand.flame.opacity(0.16),
                                  gradient: [Brand.flameLight, Brand.flame, Brand.flameDeep], isPerfectWeek: false)

    /// Gold and violet, the reward for seven days out of seven.
    static let perfectWeek = Palette(accent: Color(red: 1.0, green: 0.80, blue: 0.30),
                                     accentSoft: Color(red: 0.66, green: 0.52, blue: 1.0).opacity(0.18),
                                     gradient: [Color(red: 1.0, green: 0.88, blue: 0.45),
                                                Color(red: 1.0, green: 0.70, blue: 0.30),
                                                Color(red: 0.66, green: 0.42, blue: 1.0)],
                                     isPerfectWeek: true)

    var linear: LinearGradient { LinearGradient(colors: gradient, startPoint: .top, endPoint: .bottom) }
}

private struct PaletteKey: EnvironmentKey {
    static let defaultValue = Palette.standard
}

extension EnvironmentValues {
    var palette: Palette {
        get { self[PaletteKey.self] }
        set { self[PaletteKey.self] = newValue }
    }
}

// MARK: - Surfaces

/// A raised surface: the fill, a faint light from the top (glass, not a flat grey square), a
/// hairline, and a soft shadow that lifts it off the background.
struct CardBackground: ViewModifier {
    var radius: CGFloat
    var fill: Color

    func body(content: Content) -> some View {
        let shape = RoundedRectangle(cornerRadius: radius, style: .continuous)
        return content
            .background {
                shape.fill(fill)
                    .overlay(shape.fill(LinearGradient(colors: [Color.white.opacity(0.07), Color.white.opacity(0.0)],
                                                       startPoint: .top, endPoint: .center)))
                    .overlay(shape.stroke(LinearGradient(colors: [Color.white.opacity(0.14), Brand.stroke],
                                                         startPoint: .top, endPoint: .bottom), lineWidth: 1))
                    .shadow(color: Color.black.opacity(0.35), radius: 14, y: 6)
            }
    }
}

extension View {
    func card(radius: CGFloat = 24, fill: Color = Brand.card) -> some View {
        modifier(CardBackground(radius: radius, fill: fill))
    }
}

// MARK: - Buttons

/// Capsule buttons, as in SingaSmoke: the flame for the main action, grey for the rest.
struct PillButtonStyle: ButtonStyle {
    enum Kind { case primary, secondary, success, quiet }
    var kind: Kind = .primary
    var compact = false
    @Environment(\.palette) private var palette
    @Environment(\.isEnabled) private var isEnabled

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(compact ? .subheadline.weight(.bold) : .headline)
            .lineLimit(1)
            .padding(.vertical, compact ? 9 : 16)
            .padding(.horizontal, compact ? 16 : 22)
            .frame(maxWidth: compact ? nil : .infinity)
            .foregroundStyle(foreground)
            .background(background, in: Capsule())
            .opacity(isEnabled ? (configuration.isPressed ? 0.85 : 1) : 0.4)
            .scaleEffect(configuration.isPressed ? 0.97 : 1)
            .animation(.spring(duration: 0.2), value: configuration.isPressed)
    }

    private var foreground: Color {
        switch kind {
        case .primary, .success: return .black
        case .secondary, .quiet: return .white
        }
    }

    private var background: Color {
        switch kind {
        case .primary: return palette.accent
        case .success: return Brand.success
        case .secondary: return Brand.cardRaised
        case .quiet: return .clear
        }
    }
}

extension ButtonStyle where Self == PillButtonStyle {
    static var pill: PillButtonStyle { PillButtonStyle() }
    static func pill(_ kind: PillButtonStyle.Kind, compact: Bool = false) -> PillButtonStyle {
        PillButtonStyle(kind: kind, compact: compact)
    }
}
