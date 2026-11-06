import Foundation

/// The day screen's cards, grouped: the cadrage à domicile pinned, then brainteasers, fit, cases,
/// revenges. Inside a section the server's order stays (cases by difficulty, warm-up first).
public struct HomeSection: Identifiable, Equatable, Sendable {
    public enum Kind: String, Sendable, CaseIterable {
        case homework, brainteasers, fit, cases, revenges
    }

    public var kind: Kind
    public var cards: [ExerciseCard]

    public init(kind: Kind, cards: [ExerciseCard]) {
        self.kind = kind
        self.cards = cards
    }

    public var id: String { kind.rawValue }
    public var done: Int { cards.filter(\.done).count }
    public var xpLeft: Int { cards.filter { !$0.done }.compactMap(\.xpPotential).reduce(0, +) }
    public var isComplete: Bool { !cards.isEmpty && cards.allSatisfy(\.done) }

    public var title: String {
        switch kind {
        case .homework: return "À rendre"
        case .brainteasers: return "Brainteasers"
        case .fit: return "Fit"
        case .cases: return "Cases"
        case .revenges: return "Revanches"
        }
    }

    public var symbol: String {
        switch kind {
        case .homework: return "pin.fill"
        case .brainteasers: return "brain.head.profile"
        case .fit: return "person.crop.circle.badge.questionmark"
        case .cases: return "briefcase.fill"
        case .revenges: return "arrow.uturn.backward"
        }
    }

    /// The category whose colour the section takes (revenges keep their own).
    public var category: ExerciseCategory? {
        switch kind {
        case .homework: return .homework
        case .brainteasers: return .brainteasers
        case .fit: return .fit
        case .cases: return .cases
        case .revenges: return nil
        }
    }

    public static func build(_ cards: [ExerciseCard]) -> [HomeSection] {
        var buckets: [Kind: [ExerciseCard]] = [:]
        for card in cards {
            let kind: Kind
            if card.isRevenge {
                kind = .revenges
            } else if card.pinned == true || card.type == .cadrageHome {
                kind = .homework
            } else {
                switch card.type.category {
                case .brainteasers: kind = .brainteasers
                case .fit: kind = .fit
                case .cases, .homework: kind = .cases
                }
            }
            buckets[kind, default: []].append(card)
        }
        return Kind.allCases.compactMap { kind in
            guard let cards = buckets[kind], !cards.isEmpty else { return nil }
            return HomeSection(kind: kind, cards: cards)
        }
    }
}
