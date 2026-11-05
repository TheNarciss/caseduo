import AVFoundation

/// Short sounds on success, can be turned off in Profil. Ambient session: they mix with music and
/// stay silent when the ring switch is off.
@MainActor
final class Sounds {
    enum Effect: String, CaseIterable {
        case send = "send"
        case success = "success"
        case streak = "streak"
    }

    static let shared = Sounds()

    var isEnabled = true
    private var players: [Effect: AVAudioPlayer] = [:]

    private init() {
        try? AVAudioSession.sharedInstance().setCategory(.ambient, options: [.mixWithOthers])
        for effect in Effect.allCases {
            guard let url = Bundle.main.url(forResource: effect.rawValue, withExtension: "wav") else { continue }
            if let player = try? AVAudioPlayer(contentsOf: url) {
                player.volume = 0.6
                player.prepareToPlay()
                players[effect] = player
            }
        }
    }

    func play(_ effect: Effect) {
        guard isEnabled, let player = players[effect] else { return }
        player.currentTime = 0
        player.play()
    }
}
