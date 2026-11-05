import CaseDuoCore
import CoreHaptics
import UIKit

/// Plays the app's haptic patterns (decided in CaseDuoCore). CoreHaptics when the phone has a
/// Taptic Engine, the UIKit generators otherwise.
@MainActor
final class Haptics {
    static let shared = Haptics()

    private var engine: CHHapticEngine?
    private let supportsCoreHaptics = CHHapticEngine.capabilitiesForHardware().supportsHaptics

    private init() {
        prepareEngine()
    }

    private func prepareEngine() {
        guard supportsCoreHaptics else { return }
        do {
            let engine = try CHHapticEngine()
            engine.isAutoShutdownEnabled = true
            engine.resetHandler = { [weak self] in
                Task { @MainActor in try? self?.engine?.start() }
            }
            try engine.start()
            self.engine = engine
        } catch {
            engine = nil
        }
    }

    func play(_ pattern: HapticPattern) {
        if let engine, supportsCoreHaptics {
            do {
                try engine.start()
                let player = try engine.makePlayer(with: try Self.coreHapticsPattern(pattern))
                try player.start(atTime: CHHapticTimeImmediate)
                if pattern.endsWithSuccess {
                    let delay = (pattern.pulses.last?.time ?? 0) + 0.18
                    DispatchQueue.main.asyncAfter(deadline: .now() + delay) {
                        UINotificationFeedbackGenerator().notificationOccurred(.success)
                    }
                }
                return
            } catch {
                // Fall through to the UIKit generators.
            }
        }
        playFallback(pattern)
    }

    static func coreHapticsPattern(_ pattern: HapticPattern) throws -> CHHapticPattern {
        let events = pattern.pulses.map { pulse in
            CHHapticEvent(
                eventType: pulse.isContinuous ? .hapticContinuous : .hapticTransient,
                parameters: [
                    CHHapticEventParameter(parameterID: .hapticIntensity, value: Float(pulse.intensity)),
                    CHHapticEventParameter(parameterID: .hapticSharpness, value: Float(pulse.sharpness)),
                ],
                relativeTime: pulse.time,
                duration: pulse.isContinuous ? pulse.duration : 0
            )
        }
        return try CHHapticPattern(events: events, parameters: [])
    }

    private func playFallback(_ pattern: HapticPattern) {
        for pulse in pattern.pulses {
            DispatchQueue.main.asyncAfter(deadline: .now() + pulse.time) {
                let style: UIImpactFeedbackGenerator.FeedbackStyle =
                    pulse.intensity >= 0.9 ? .heavy : pulse.intensity >= 0.6 ? .medium : .light
                UIImpactFeedbackGenerator(style: style).impactOccurred(intensity: CGFloat(pulse.intensity))
            }
        }
        if pattern.endsWithSuccess {
            let delay = (pattern.pulses.last?.time ?? 0) + 0.18
            DispatchQueue.main.asyncAfter(deadline: .now() + delay) {
                UINotificationFeedbackGenerator().notificationOccurred(.success)
            }
        }
    }
}
