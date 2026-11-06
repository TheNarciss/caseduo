import Foundation

/// The haptic moments of the app, decided here and played by the app (CoreHaptics).
public enum HapticPattern: String, Sendable, Equatable, CaseIterable {
    /// An answer leaves for grading: one light tap.
    case answerSent
    /// Score below 50: one heavy hit.
    case scoreLow
    /// Score 50–79: two hits.
    case scoreMid
    /// Score 80 and above: three hits, then the success notification.
    case scoreHigh
    /// The streak grows by one: a custom rising pattern.
    case streakUp
    /// Seven days in a row: a long pattern.
    case perfectWeek
    /// A card or a tab pressed: one very light tick.
    case tap
    /// The day's goal just met: two warm pulses, then the success notification.
    case goalMet
    /// Every card of the day done: four rising taps and a swell, then success.
    case dayComplete
    /// « Je m'engage » : two firm taps, a handshake.
    case commit

    public static func forScore(_ score: Int) -> HapticPattern {
        switch score {
        case ..<50: return .scoreLow
        case 50..<80: return .scoreMid
        default: return .scoreHigh
        }
    }

    /// Whether the system success notification follows the pattern.
    public var endsWithSuccess: Bool {
        self == .scoreHigh || self == .perfectWeek || self == .goalMet || self == .dayComplete
    }

    /// The pattern as pulses: what CoreHaptics plays, and what the fallback imitates.
    public var pulses: [HapticPulse] {
        switch self {
        case .answerSent:
            return [HapticPulse(time: 0, intensity: 0.4, sharpness: 0.6)]
        case .scoreLow:
            return [HapticPulse(time: 0, intensity: 1.0, sharpness: 0.3)]
        case .scoreMid:
            return [HapticPulse(time: 0, intensity: 0.8, sharpness: 0.5),
                    HapticPulse(time: 0.14, intensity: 0.8, sharpness: 0.5)]
        case .scoreHigh:
            return [HapticPulse(time: 0, intensity: 0.7, sharpness: 0.6),
                    HapticPulse(time: 0.12, intensity: 0.85, sharpness: 0.7),
                    HapticPulse(time: 0.24, intensity: 1.0, sharpness: 0.8)]
        case .streakUp:
            // Five taps getting stronger and sharper, then a short swell: the flame catching.
            let taps = (0..<5).map { i in
                HapticPulse(time: Double(i) * 0.07,
                            intensity: 0.3 + 0.15 * Double(i),
                            sharpness: 0.2 + 0.18 * Double(i))
            }
            return taps + [HapticPulse(time: 0.38, intensity: 1.0, sharpness: 0.5, duration: 0.25)]
        case .perfectWeek:
            return [HapticPulse(time: 0, intensity: 0.5, sharpness: 0.3, duration: 0.5),
                    HapticPulse(time: 0.55, intensity: 0.8, sharpness: 0.5, duration: 0.45),
                    HapticPulse(time: 1.05, intensity: 1.0, sharpness: 0.8)]
        case .tap:
            return [HapticPulse(time: 0, intensity: 0.3, sharpness: 0.8)]
        case .goalMet:
            return [HapticPulse(time: 0, intensity: 0.6, sharpness: 0.3, duration: 0.12),
                    HapticPulse(time: 0.2, intensity: 0.9, sharpness: 0.4, duration: 0.16)]
        case .dayComplete:
            let taps = (0..<4).map { i in
                HapticPulse(time: Double(i) * 0.08,
                            intensity: 0.4 + 0.2 * Double(i),
                            sharpness: 0.5 + 0.1 * Double(i))
            }
            return taps + [HapticPulse(time: 0.36, intensity: 1.0, sharpness: 0.4, duration: 0.3)]
        case .commit:
            return [HapticPulse(time: 0, intensity: 0.8, sharpness: 0.7),
                    HapticPulse(time: 0.16, intensity: 0.8, sharpness: 0.7)]
        }
    }
}

/// One haptic event. `duration == 0` is a transient tap, otherwise a continuous buzz.
public struct HapticPulse: Sendable, Equatable {
    public var time: Double
    public var intensity: Double
    public var sharpness: Double
    public var duration: Double

    public init(time: Double, intensity: Double, sharpness: Double, duration: Double = 0) {
        self.time = time
        self.intensity = intensity
        self.sharpness = sharpness
        self.duration = duration
    }

    public var isContinuous: Bool { duration > 0 }
}
