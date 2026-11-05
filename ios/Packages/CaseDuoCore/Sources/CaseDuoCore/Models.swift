import Foundation

// The API's shapes (docs/API.md is the contract). Identifiers stay strings: the app never does
// anything with a UUID but send it back. Calendar days stay strings too ("2026-11-04"): they are
// the user's local days, computed by the server in the user's time zone, and a `Date` would
// silently move them across midnight.

public typealias ID = String

// MARK: - Enumerations

/// The kinds of exercise. Unknown values from a newer backend decode as `.unknown`.
public enum ExerciseType: String, Codable, CaseIterable, Sendable, Hashable {
    case marketSizing = "market_sizing"
    case cadrage
    case businessCase = "business_case"
    case diagnostic
    case brainteaser
    case fit
    case cadrageHome = "cadrage_home"
    case techScreen = "tech_screen"
    case unknown

    public init(from decoder: Decoder) throws {
        let raw = try decoder.singleValueContainer().decode(String.self)
        self = ExerciseType(rawValue: raw) ?? .unknown
    }

    /// The label used when the server did not send one.
    public var label: String {
        switch self {
        case .marketSizing: return "Market sizing"
        case .cadrage: return "Note de cadrage"
        case .businessCase: return "Business case"
        case .diagnostic: return "Diagnostic"
        case .brainteaser: return "Brainteaser"
        case .fit: return "Fit"
        case .cadrageHome: return "Cadrage à domicile"
        case .techScreen: return "Tech screen"
        case .unknown: return "Exercice"
        }
    }

    /// SF Symbol for the card.
    public var symbol: String {
        switch self {
        case .marketSizing: return "chart.bar.xaxis"
        case .cadrage: return "list.bullet.rectangle"
        case .businessCase: return "eurosign.circle"
        case .diagnostic: return "stethoscope"
        case .brainteaser: return "brain.head.profile"
        case .fit: return "person.crop.circle.badge.questionmark"
        case .cadrageHome: return "rectangle.stack"
        case .techScreen: return "cpu"
        case .unknown: return "questionmark.circle"
        }
    }
}

public enum AttemptKind: String, Codable, Sendable {
    case main
    case retry2min = "retry_2min"
    case followUp = "follow_up"
}

public enum InputMode: String, Codable, Sendable {
    case text
    case voice
}

public enum StreakStatus: String, Codable, Sendable {
    case extendedToday = "extended_today"
    case atRisk = "at_risk"
    case safe
    case unknown

    public init(from decoder: Decoder) throws {
        let raw = try decoder.singleValueContainer().decode(String.self)
        self = StreakStatus(rawValue: raw) ?? .unknown
    }
}

// MARK: - Auth & profile

public struct Providers: Codable, Sendable, Equatable {
    public var apple: Bool
    public init(apple: Bool) { self.apple = apple }
}

public struct AppleLogin: Codable, Sendable {
    public var identityToken: String
    public var nonce: String
    public var displayName: String?
    public init(identityToken: String, nonce: String, displayName: String?) {
        self.identityToken = identityToken
        self.nonce = nonce
        self.displayName = displayName
    }
}

public struct Me: Codable, Sendable, Equatable {
    public var id: ID
    public var email: String
    public var displayName: String?
    public var isAdmin: Bool?
    public var timezone: String
    public var dailyGoalXp: Int
    public var soundsEnabled: Bool
    public var notificationsEnabled: Bool
    public var streakCurrent: Int
    public var streakLongest: Int
    public var streakFreezes: Int
    public var xpTotal: Int
    public var league: String?
    public var storyText: String?
    public var storyUpdatedAt: Date?
    public var createdAt: Date?
}

/// `PATCH /me`: only the fields set are sent.
public struct MePatch: Codable, Sendable, Equatable {
    public var displayName: String?
    public var timezone: String?
    public var dailyGoalXp: Int?
    public var soundsEnabled: Bool?
    public var notificationsEnabled: Bool?

    public init(displayName: String? = nil, timezone: String? = nil, dailyGoalXp: Int? = nil,
                soundsEnabled: Bool? = nil, notificationsEnabled: Bool? = nil) {
        self.displayName = displayName
        self.timezone = timezone
        self.dailyGoalXp = dailyGoalXp
        self.soundsEnabled = soundsEnabled
        self.notificationsEnabled = notificationsEnabled
    }
}

public struct StoryUpdate: Codable, Sendable {
    public var storyText: String
    public init(storyText: String) { self.storyText = storyText }
}

public struct PushTokenRegistration: Codable, Sendable {
    public var token: String
    public var environment: String
    public init(token: String, environment: String) {
        self.token = token
        self.environment = environment
    }
}

// MARK: - Today

public struct StreakInfo: Codable, Sendable, Equatable {
    public var current: Int
    public var longest: Int
    public var freezes: Int
    public var status: StreakStatus
    public var freezeUsedOn: [String]?
    public var freezeJustUsed: Bool?

    public init(current: Int, longest: Int, freezes: Int, status: StreakStatus,
                freezeUsedOn: [String]? = nil, freezeJustUsed: Bool? = nil) {
        self.current = current
        self.longest = longest
        self.freezes = freezes
        self.status = status
        self.freezeUsedOn = freezeUsedOn
        self.freezeJustUsed = freezeJustUsed
    }
}

public struct GoalInfo: Codable, Sendable, Equatable {
    public var targetXp: Int
    public var xpToday: Int
    public var met: Bool

    public init(targetXp: Int, xpToday: Int, met: Bool) {
        self.targetXp = targetXp
        self.xpToday = xpToday
        self.met = met
    }

    /// 0…1, for the progress bar.
    public var fraction: Double {
        guard targetXp > 0 else { return met ? 1 : 0 }
        return min(1, max(0, Double(xpToday) / Double(targetXp)))
    }
}

public struct MockInfo: Codable, Sendable, Equatable {
    public var kind: String
    public var mbb: Bool?
    public var language: String?
    public var done: Bool
    public var runId: ID?
}

public struct ExerciseCard: Codable, Sendable, Equatable, Identifiable, Hashable {
    public var exerciseId: ID
    public var type: ExerciseType
    public var typeLabel: String?
    public var title: String
    public var difficulty: Int
    public var language: String
    public var style: String?
    public var sector: String?
    public var estimatedMinutes: Int?
    public var isRevenge: Bool
    public var revengeStep: Int?
    public var pinned: Bool?
    public var done: Bool
    public var bestScore: Int?
    public var xpPotential: Int?
    public var dueLabel: String?

    public var id: String { exerciseId + (isRevenge ? "#revenge" : "") }
    public var displayType: String { typeLabel ?? type.label }
    public var isMBB: Bool { style == "mbb" }
}

public struct Unlocks: Codable, Sendable, Equatable {
    public var streak30Icon: Bool
    public var perfectWeekUntil: String?

    public init(streak30Icon: Bool, perfectWeekUntil: String?) {
        self.streak30Icon = streak30Icon
        self.perfectWeekUntil = perfectWeekUntil
    }
}

public struct LeagueSummary: Codable, Sendable, Equatable {
    public var tier: String
    public var tierLabel: String?
    public var rank: Int
    public var size: Int
    public var xpWeek: Int
}

public struct Today: Codable, Sendable, Equatable {
    public var date: String
    public var weekday: Int?
    public var timezone: String?
    public var streak: StreakInfo
    public var goal: GoalInfo
    public var remaining: Int
    public var dayComplete: Bool
    public var easyMode: Bool?
    public var mock: MockInfo?
    public var cards: [ExerciseCard]
    public var unlocks: Unlocks?
    public var league: LeagueSummary?
    public var isAdmin: Bool?
}

public struct WidgetInfo: Codable, Sendable, Equatable {
    public var date: String
    public var streak: Int
    public var status: StreakStatus
    public var remaining: Int
    public var xpToday: Int
    public var goalXp: Int
}

public struct CriterionAverage: Codable, Sendable, Equatable, Identifiable, Hashable {
    public var key: String
    public var label: String
    public var average: Double
    public var count: Int?
    public var id: String { key }
}

public struct DaySummary: Codable, Sendable, Equatable {
    public var date: String
    public var streak: StreakInfo
    public var xpToday: Int
    public var goal: GoalInfo?
    public var exercisesDone: Int
    public var leagueTier: String?
    public var leagueRank: Int?
    public var weakestCriterion: CriterionAverage?
    public var line: String?
}

// MARK: - Exercise

public struct ExercisePart: Codable, Sendable, Equatable, Hashable {
    public var question: String
    public var data: String?
    public init(question: String, data: String? = nil) {
        self.question = question
        self.data = data
    }
}

public struct Fact: Codable, Sendable, Equatable, Hashable {
    public var label: String
    public var value: String
    public var sourceUrl: String?
    public var hypothesis: Bool?
}

public struct ContextDocument: Codable, Sendable, Equatable, Hashable {
    public var title: String
    public var body: String
}

public struct ContextData: Codable, Sendable, Equatable, Hashable {
    public var facts: [Fact]?
    public var constraints: [String]?
    public var documents: [ContextDocument]?

    public var isEmpty: Bool {
        (facts ?? []).isEmpty && (constraints ?? []).isEmpty && (documents ?? []).isEmpty
    }
}

public struct RevealResponse: Codable, Sendable, Equatable {
    public var contextData: ContextData
    public var xpPenalty: Int
}

public struct ExerciseDetail: Codable, Sendable, Equatable, Identifiable {
    public var id: ID
    public var date: String
    public var type: ExerciseType
    public var typeLabel: String?
    public var style: String?
    public var language: String
    public var difficulty: Int
    public var sector: String?
    public var title: String
    public var prompt: String
    public var estimatedMinutes: Int?
    public var parts: [ExercisePart]?
    public var contextDataAvailable: Bool?
    public var revealed: Bool?
    public var contextData: ContextData?
    public var isRevenge: Bool?
    public var flagged: Bool?
    public var attempts: [AttemptSummary]?

    public var displayType: String { typeLabel ?? type.label }
    public var isMBB: Bool { style == "mbb" }
    public var hasParts: Bool { !(parts ?? []).isEmpty }
}

// MARK: - Grading

public struct Slide: Codable, Sendable, Equatable, Hashable {
    public var title: String
    public var lines: [String]
    public init(title: String, lines: [String]) {
        self.title = title
        self.lines = lines
    }
}

public struct GradeRequest: Codable, Sendable, Equatable {
    public var exerciseId: ID
    public var kind: AttemptKind
    public var answerText: String
    public var durationSeconds: Int
    public var inputMode: InputMode
    public var parentAttemptId: ID?
    public var mockRunId: ID?
    public var partAnswers: [String]?
    public var slides: [Slide]?

    public init(exerciseId: ID, kind: AttemptKind, answerText: String, durationSeconds: Int,
                inputMode: InputMode, parentAttemptId: ID? = nil, mockRunId: ID? = nil,
                partAnswers: [String]? = nil, slides: [Slide]? = nil) {
        self.exerciseId = exerciseId
        self.kind = kind
        self.answerText = answerText
        self.durationSeconds = durationSeconds
        self.inputMode = inputMode
        self.parentAttemptId = parentAttemptId
        self.mockRunId = mockRunId
        self.partAnswers = partAnswers
        self.slides = slides
    }
}

public struct RubricScore: Codable, Sendable, Equatable, Hashable, Identifiable {
    public var key: String
    public var label: String
    public var weight: Int
    public var score: Int
    public var justification: String?
    public var quote: String?
    public var id: String { key }

    /// 0…1, for the bar.
    public var fraction: Double { Double(min(2, max(0, score))) / 2 }
}

public struct RubricCriterion: Codable, Sendable, Equatable, Hashable, Identifiable {
    public var key: String
    public var label: String
    public var weight: Int
    public var levels: [String: String]?
    public var id: String { key }
}

public struct Source: Codable, Sendable, Equatable, Hashable {
    public var url: String
    public var title: String?
    public var verified: Bool?
}

public struct AttemptExercise: Codable, Sendable, Equatable {
    public var id: ID
    public var title: String
    public var type: ExerciseType
    public var typeLabel: String?
    public var language: String?
    public var modelAnswer: String?
    public var sources: [Source]?
    public var rubric: [RubricCriterion]?
    public var flagged: Bool?
}

public struct Attempt: Codable, Sendable, Equatable, Identifiable {
    public var id: ID
    public var exerciseId: ID
    public var kind: AttemptKind
    public var parentAttemptId: ID?
    public var answerText: String?
    public var durationSeconds: Int?
    public var inputMode: InputMode?
    public var score: Int?
    public var rubricScores: [RubricScore]?
    public var feedback: String?
    public var followUp: String?
    public var xpEarned: Int
    public var isRevenge: Bool?
    public var revealedData: Bool?
    public var mockRunId: ID?
    public var createdAt: Date?
    public var exercise: AttemptExercise?
}

public struct AttemptSummary: Codable, Sendable, Equatable, Identifiable, Hashable {
    public var id: ID
    public var exerciseId: ID
    public var kind: AttemptKind
    public var score: Int?
    public var xpEarned: Int
    public var createdAt: Date?
    public var title: String?
    public var type: ExerciseType?
    public var typeLabel: String?
}

public struct XPLine: Codable, Sendable, Equatable, Hashable {
    public var label: String
    public var xp: Int
}

public struct XPInfo: Codable, Sendable, Equatable {
    public var earned: Int
    public var breakdown: [XPLine]?

    public init(earned: Int, breakdown: [XPLine]? = nil) {
        self.earned = earned
        self.breakdown = breakdown
    }
}

public struct Badge: Codable, Sendable, Equatable, Identifiable, Hashable {
    public var code: String
    public var name: String
    public var description: String?
    public var symbol: String?
    public var earnedAt: Date?
    public var id: String { code }
}

public struct GradeProgress: Codable, Sendable, Equatable {
    public var xpToday: Int
    public var goalTarget: Int?
    public var goalMet: Bool
    public var goalJustMet: Bool?
    public var streak: StreakInfo
    public var streakExtended: Bool
    public var freezeEarned: Bool?
    public var dayComplete: Bool
    public var dayCompleteBonus: Int?
    public var perfectWeek: Bool?
    public var remaining: Int
    public var newBadges: [Badge]?
}

public struct GradeResult: Codable, Sendable, Equatable {
    public var attempt: Attempt
    public var xp: XPInfo
    public var progress: GradeProgress
}

public struct ScoresPayload: Codable, Sendable, Equatable {
    public var rubricScores: [RubricScore]
    public var score: Int

    public init(rubricScores: [RubricScore], score: Int) {
        self.rubricScores = rubricScores
        self.score = score
    }
}

public struct StreamError: Codable, Sendable, Equatable, Error {
    public var reason: String
    public var detail: String?

    public init(reason: String, detail: String?) {
        self.reason = reason
        self.detail = detail
    }
}

public struct FlagRequest: Codable, Sendable {
    public var flagged: Bool
    public var note: String?
    public init(flagged: Bool, note: String?) {
        self.flagged = flagged
        self.note = note
    }
}

// MARK: - History, league, badges

public struct ScorePoint: Codable, Sendable, Equatable, Hashable {
    public var date: String
    public var score: Int
}

public struct ScoreSeries: Codable, Sendable, Equatable, Hashable, Identifiable {
    public var type: ExerciseType
    public var label: String
    public var points: [ScorePoint]
    public var id: String { label }
}

public struct CalendarDay: Codable, Sendable, Equatable, Hashable, Identifiable {
    public var date: String
    public var goalMet: Bool
    public var freezeUsed: Bool
    public var xp: Int
    public var id: String { date }
}

public struct MockScore: Codable, Sendable, Equatable, Hashable, Identifiable {
    public var id: ID
    public var date: String
    public var kind: String
    public var score: Int?
}

public struct History: Codable, Sendable, Equatable {
    public var series: [ScoreSeries]
    public var weaknesses: [CriterionAverage]
    public var criteria: [CriterionAverage]?
    public var calendar: [CalendarDay]
    public var recentAttempts: [AttemptSummary]?
    public var mocks: [MockScore]?
}

public struct LeagueMember: Codable, Sendable, Equatable, Hashable, Identifiable {
    public var name: String
    public var xp: Int
    public var isMe: Bool
    public var rank: Int
    public var id: String { "\(rank)-\(name)" }
}

public struct League: Codable, Sendable, Equatable {
    public var tier: String
    public var tierLabel: String?
    public var weekStart: String
    public var endsAt: Date?
    public var members: [LeagueMember]
    public var promoteTop: Int
    public var relegateBottom: Int
    public var lastOutcome: String?

    public enum Zone: Sendable, Equatable { case promotion, safe, relegation }

    /// Which zone a rank falls in. Nobody is relegated from the lowest tier.
    public func zone(of rank: Int) -> Zone {
        if rank <= promoteTop && tier != "gold" { return .promotion }
        if rank > members.count - relegateBottom && tier != "bronze" { return .relegation }
        return .safe
    }
}

// MARK: - Mock interview

public struct MockStep: Codable, Sendable, Equatable, Hashable, Identifiable {
    public var index: Int
    public var exerciseId: ID
    public var type: ExerciseType
    public var title: String
    public var prompt: String
    public var parts: [ExercisePart]?
    public var contextData: ContextData?
    public var timeLimitSeconds: Int?
    public var followUpAfter: Bool
    public var id: Int { index }
}

public struct MockRun: Codable, Sendable, Equatable, Identifiable {
    public var id: ID
    public var kind: String
    public var mbb: Bool?
    public var language: String?
    public var status: String
    public var timeLimitSeconds: Int
    public var startedAt: Date?
    public var steps: [MockStep]
}

public struct MockStart: Codable, Sendable {
    public var kind: String
    public init(kind: String) { self.kind = kind }
}

public struct MockPrevious: Codable, Sendable, Equatable, Hashable {
    public var date: String
    public var kind: String
    public var score: Int?
}

public struct MockFinish: Codable, Sendable, Equatable {
    public var id: ID
    public var score: Int?
    public var xpEarned: Int
    public var attempts: [AttemptSummary]
    public var previous: [MockPrevious]?
    public var feedback: String?
}

// MARK: - Errors

/// FastAPI's error body. `detail` is a string for our errors and a list for validation errors.
public struct APIErrorBody: Decodable, Sendable, Equatable {
    public var detail: String?
    public var type: String?

    enum CodingKeys: String, CodingKey { case detail, type }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        type = try container.decodeIfPresent(String.self, forKey: .type)
        if let text = try? container.decodeIfPresent(String.self, forKey: .detail) {
            detail = text
        } else {
            detail = nil
        }
    }
}
