import Foundation

// The Parcours (docs/PARCOURS.md, docs/API.md): the path, a lesson and its items, what the
// phone sends back. Items carry their key: grading happens on the phone (PathGrader), the
// server records the results at the end of the lesson.

// MARK: - The path

public struct PathView: Codable, Sendable, Equatable {
    public var units: [PathUnit]
    public var activeNode: String?
    public var done: Int
    public var total: Int

    public var allNodes: [PathNode] { units.flatMap(\.nodes) }
    public var active: PathNode? { allNodes.first { $0.status == .active } }
}

public struct PathUnit: Codable, Sendable, Equatable, Identifiable {
    public var code: String
    public var order: Int
    public var track: String
    public var title: String
    public var subtitle: String
    public var symbol: String
    public var done: Int
    public var total: Int
    public var nodes: [PathNode]
    public var id: String { code }
    public var isComplete: Bool { total > 0 && done >= total }
}

public enum PathNodeKind: String, Codable, Sendable, CaseIterable {
    case lesson, review, applied, checkpoint, legendary, unknown

    public init(from decoder: Decoder) throws {
        self = PathNodeKind(rawValue: try decoder.singleValueContainer().decode(String.self)) ?? .unknown
    }

    public var isOptional: Bool { self == .applied || self == .legendary }
}

public enum PathNodeStatus: String, Codable, Sendable {
    case done, active, available, locked, unknown

    public init(from decoder: Decoder) throws {
        self = PathNodeStatus(rawValue: try decoder.singleValueContainer().decode(String.self)) ?? .unknown
    }

    public var isOpen: Bool { self == .active || self == .available || self == .done }
}

public struct PathNode: Codable, Sendable, Equatable, Identifiable {
    public var code: String
    public var kind: PathNodeKind
    public var title: String
    public var objective: String?
    public var status: PathNodeStatus
    public var bestScore: Int?
    public var times: Int
    public var items: Int
    public var appliedType: String?
    public var xp: Int
    public var id: String { code }
}

// MARK: - A lesson

public struct LessonStart: Codable, Sendable, Equatable {
    public struct Node: Codable, Sendable, Equatable {
        public var code: String
        public var kind: PathNodeKind
        public var title: String
        public var objective: String?
    }

    public var node: Node
    public var items: [PathItem]
    public var xp: Int
    public var perfectBonus: Int
    public var passScore: Int?
}

public enum PathFormat: String, Codable, Sendable, CaseIterable {
    case conceptCard = "concept_card"
    case chooseStructure = "choose_structure"
    case pickSoWhat = "pick_so_what"
    case firstQuestion = "first_question"
    case treeComplete = "tree_complete"
    case swipeValid = "swipe_valid"
    case spotError = "spot_error"
    case orderSteps = "order_steps"
    case synthOrder = "synth_order"
    case headlineTiles = "headline_tiles"
    case mentalMath = "mental_math"
    case estimateRange = "estimate_range"
    case twoStepCalc = "two_step_calc"
    case fillBlank = "fill_blank"
    case meceSort = "mece_sort"
    case matchPairs = "match_pairs"
    case oralPrompt = "oral_prompt"
    case unknown

    public init(from decoder: Decoder) throws {
        self = PathFormat(rawValue: try decoder.singleValueContainer().decode(String.self)) ?? .unknown
    }

    /// The instruction shown above the item when the stem does not say it.
    public var label: String {
        switch self {
        case .conceptCard: return "À lire"
        case .chooseStructure: return "Choisis la structure"
        case .pickSoWhat: return "Trouve le so what"
        case .firstQuestion: return "Première question à poser"
        case .treeComplete: return "Complète l'arbre"
        case .swipeValid: return "Valide ou pas ?"
        case .spotError: return "Repère l'erreur"
        case .orderSteps: return "Remets dans l'ordre"
        case .synthOrder: return "Synthèse en 30 secondes"
        case .headlineTiles: return "Reconstruis le titre"
        case .mentalMath: return "Calcul chrono"
        case .estimateRange: return "Ordre de grandeur"
        case .twoStepCalc: return "Calcul en deux temps"
        case .fillBlank: return "Complète la phrase"
        case .meceSort: return "Trie dans les cases"
        case .matchPairs: return "Associe les paires"
        case .oralPrompt: return "À l'oral"
        case .unknown: return "Exercice"
        }
    }

    public var isGraded: Bool { self != .conceptCard && self != .unknown }
    public var isOral: Bool { self == .oralPrompt }
    public var isChoice: Bool { [.chooseStructure, .pickSoWhat, .firstQuestion, .treeComplete].contains(self) }
    public var isTiles: Bool { [.orderSteps, .synthOrder, .headlineTiles].contains(self) }
}

/// A small chart, table or tree, drawn by the app from data.
public struct PathMedia: Codable, Sendable, Equatable {
    public struct Series: Codable, Sendable, Equatable {
        public var name: String
        public var values: [Double]
    }

    public var type: String
    public var title: String?
    public var unit: String?
    public var categories: [String]?
    public var series: [Series]?
    public var header: [String]?
    public var rows: [[String]]?
    public var root: String?
    public var children: [String]?
}

public struct PathOption: Codable, Sendable, Equatable, Identifiable, Hashable {
    public var id: String
    public var text: String
    public var whyWrong: String?
}

public struct PathCard: Codable, Sendable, Equatable, Identifiable, Hashable {
    public var id: String
    public var text: String
    public var valid: Bool
    public var reason: String
}

public struct PathLine: Codable, Sendable, Equatable, Identifiable, Hashable {
    public var id: String
    public var text: String
}

public struct PathTile: Codable, Sendable, Equatable, Identifiable, Hashable {
    public var id: String
    public var text: String
}

public struct MathQuestion: Codable, Sendable, Equatable, Identifiable, Hashable {
    public var id: String
    public var stem: String
    public var computation: String
    public var answer: Double
    public var unit: String
    public var tolerancePct: Double
    public var hint: String?
}

public struct FillSlot: Codable, Sendable, Equatable, Identifiable, Hashable {
    public var id: Int
    public var options: [String]
    public var correct: Int
}

public struct SortBucket: Codable, Sendable, Equatable, Identifiable, Hashable {
    public var id: String
    public var label: String
}

public struct SortItem: Codable, Sendable, Equatable, Identifiable, Hashable {
    public var id: String
    public var text: String
    public var bucket: String
}

public struct MatchPair: Codable, Sendable, Equatable, Hashable {
    public var left: String
    public var right: String
}

public struct ConceptScreen: Codable, Sendable, Equatable, Hashable {
    public var title: String
    public var body: String
}

public struct RubricLine: Codable, Sendable, Equatable, Hashable {
    public var key: String
    public var label: String
    public var weight: Int
}

/// The format's own data, decoded by the item's format.
public enum PathPayload: Sendable, Equatable {
    case concept(screens: [ConceptScreen])
    case choice(options: [PathOption], correct: String, shuffle: Bool)
    case swipe(cards: [PathCard], passRatio: Double)
    case spotError(lines: [PathLine], wrongLine: String, fix: String)
    case tiles(tiles: [PathTile], solution: [String], distractors: [String], accepted: [[String]])
    case mentalMath(questions: [MathQuestion], seconds: Int)
    case estimate(range: ClosedRange<Double>, slider: ClosedRange<Double>, unit: String, log: Bool, reference: String)
    case twoStep(formulas: [PathOption], correctFormula: String, answer: Double, unit: String, tolerancePct: Double)
    case fillBlank(text: String, slots: [FillSlot])
    case meceSort(buckets: [SortBucket], items: [SortItem])
    case matchPairs(pairs: [MatchPair])
    case oral(seconds: Int, rubric: [RubricLine], modelAnswer: String)
    case unknown
}

public struct PathItem: Codable, Sendable, Equatable, Identifiable {
    public var id: String
    public var format: PathFormat
    public var skill: String
    public var difficulty: Int
    public var lang: String
    public var sector: String?
    public var stem: String
    public var media: PathMedia?
    public var explanation: String
    public var payload: PathPayload

    enum CodingKeys: String, CodingKey {
        case id, format, skill, difficulty, lang, sector, stem, media, explanation, payload
    }

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        id = try c.decode(String.self, forKey: .id)
        format = try c.decode(PathFormat.self, forKey: .format)
        skill = try c.decode(String.self, forKey: .skill)
        difficulty = try c.decodeIfPresent(Int.self, forKey: .difficulty) ?? 1
        lang = try c.decodeIfPresent(String.self, forKey: .lang) ?? "fr"
        sector = try c.decodeIfPresent(String.self, forKey: .sector)
        stem = try c.decodeIfPresent(String.self, forKey: .stem) ?? ""
        media = try c.decodeIfPresent(PathMedia.self, forKey: .media)
        explanation = try c.decodeIfPresent(String.self, forKey: .explanation) ?? ""
        payload = try PathPayload.decode(format: format, from: c.superDecoder(forKey: .payload))
    }

    public func encode(to encoder: Encoder) throws {
        // Items are never sent back whole: results reference them by id.
        var c = encoder.container(keyedBy: CodingKeys.self)
        try c.encode(id, forKey: .id)
        try c.encode(format, forKey: .format)
        try c.encode(skill, forKey: .skill)
        try c.encode(difficulty, forKey: .difficulty)
        try c.encode(lang, forKey: .lang)
        try c.encodeIfPresent(sector, forKey: .sector)
        try c.encode(stem, forKey: .stem)
        try c.encodeIfPresent(media, forKey: .media)
        try c.encode(explanation, forKey: .explanation)
    }

    public init(id: String, format: PathFormat, skill: String = "", difficulty: Int = 1, stem: String = "",
                media: PathMedia? = nil, explanation: String = "", payload: PathPayload) {
        self.id = id
        self.format = format
        self.skill = skill
        self.difficulty = difficulty
        self.lang = "fr"
        self.sector = nil
        self.stem = stem
        self.media = media
        self.explanation = explanation
        self.payload = payload
    }
}

extension PathPayload {
    private struct Concept: Decodable { var screens: [ConceptScreen] }
    private struct Choice: Decodable { var options: [PathOption]; var correct: String; var shuffle: Bool? }
    private struct Swipe: Decodable { var cards: [PathCard]; var passRatio: Double? }
    private struct Spot: Decodable { var lines: [PathLine]; var wrongLine: String; var fix: String }
    private struct Tiles: Decodable { var tiles: [PathTile]; var solution: [String]; var distractors: [String]?; var accepted: [[String]]? }
    private struct Math: Decodable { var questions: [MathQuestion]; var seconds: Int? }
    private struct Estimate: Decodable { var range: [Double]; var slider: [Double]; var unit: String?; var scale: String?; var reference: String }
    private struct TwoStep: Decodable { var formulas: [PathOption]; var correctFormula: String; var answer: Double; var unit: String?; var tolerancePct: Double? }
    private struct Fill: Decodable { var text: String; var slots: [FillSlot] }
    private struct Sort: Decodable { var buckets: [SortBucket]; var items: [SortItem] }
    private struct Pairs: Decodable { var pairs: [MatchPair] }
    private struct Oral: Decodable { var seconds: Int?; var rubric: [RubricLine]; var modelAnswer: String }

    static func decode(format: PathFormat, from decoder: Decoder) throws -> PathPayload {
        switch format {
        case .conceptCard:
            return .concept(screens: try Concept(from: decoder).screens)
        case .chooseStructure, .pickSoWhat, .firstQuestion, .treeComplete:
            let p = try Choice(from: decoder)
            return .choice(options: p.options, correct: p.correct, shuffle: p.shuffle ?? true)
        case .swipeValid:
            let p = try Swipe(from: decoder)
            return .swipe(cards: p.cards, passRatio: p.passRatio ?? 0.8)
        case .spotError:
            let p = try Spot(from: decoder)
            return .spotError(lines: p.lines, wrongLine: p.wrongLine, fix: p.fix)
        case .orderSteps, .synthOrder, .headlineTiles:
            let p = try Tiles(from: decoder)
            return .tiles(tiles: p.tiles, solution: p.solution, distractors: p.distractors ?? [], accepted: p.accepted ?? [])
        case .mentalMath:
            let p = try Math(from: decoder)
            return .mentalMath(questions: p.questions, seconds: p.seconds ?? 90)
        case .estimateRange:
            let p = try Estimate(from: decoder)
            guard p.range.count == 2, p.slider.count == 2, p.range[0] <= p.range[1], p.slider[0] <= p.slider[1] else {
                throw DecodingError.dataCorrupted(.init(codingPath: decoder.codingPath, debugDescription: "estimate range"))
            }
            return .estimate(range: p.range[0]...p.range[1], slider: p.slider[0]...p.slider[1],
                             unit: p.unit ?? "", log: (p.scale ?? "log") == "log", reference: p.reference)
        case .twoStepCalc:
            let p = try TwoStep(from: decoder)
            return .twoStep(formulas: p.formulas, correctFormula: p.correctFormula, answer: p.answer,
                            unit: p.unit ?? "", tolerancePct: p.tolerancePct ?? 3)
        case .fillBlank:
            let p = try Fill(from: decoder)
            return .fillBlank(text: p.text, slots: p.slots)
        case .meceSort:
            let p = try Sort(from: decoder)
            return .meceSort(buckets: p.buckets, items: p.items)
        case .matchPairs:
            return .matchPairs(pairs: try Pairs(from: decoder).pairs)
        case .oralPrompt:
            let p = try Oral(from: decoder)
            return .oral(seconds: p.seconds ?? 75, rubric: p.rubric, modelAnswer: p.modelAnswer)
        case .unknown:
            return .unknown
        }
    }
}

// MARK: - What goes back

/// One answered item, as `POST /path/nodes/{code}/complete` takes it.
public struct PathItemResult: Codable, Sendable, Equatable {
    public var itemId: String
    public var correct: Bool
    public var firstTry: Bool
    public var ms: Int
    public var response: [String: String]?
    public var transcript: String?

    public init(itemId: String, correct: Bool, firstTry: Bool = true, ms: Int = 0,
                response: [String: String]? = nil, transcript: String? = nil) {
        self.itemId = itemId
        self.correct = correct
        self.firstTry = firstTry
        self.ms = ms
        self.response = response
        self.transcript = transcript
    }
}

public struct LessonCompletionRequest: Codable, Sendable, Equatable {
    public var results: [PathItemResult]
    public var attemptId: String?

    public init(results: [PathItemResult], attemptId: String? = nil) {
        self.results = results
        self.attemptId = attemptId
    }
}

public struct OralVerdict: Codable, Sendable, Equatable {
    public struct Criterion: Codable, Sendable, Equatable {
        public var key: String
        public var label: String
        public var weight: Int
        public var score: Int
        public var justification: String?
    }

    public var itemId: String
    public var score: Int?
    public var feedback: String
    public var criteria: [Criterion]
}

public struct LessonCompletion: Codable, Sendable, Equatable {
    public var node: String
    public var passed: Bool
    public var score: Int
    public var xp: Int
    public var replay: Bool?
    public var oral: [OralVerdict]?
    public var progress: GradeProgress?
    public var nextNode: String?
    public var unitDone: Bool?
}

public struct FlagResult: Codable, Sendable, Equatable {
    public var id: String
    public var flagCount: Int
    public var retired: Bool
}
