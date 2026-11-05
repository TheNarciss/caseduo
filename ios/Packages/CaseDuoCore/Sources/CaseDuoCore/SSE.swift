import Foundation

/// One server-sent event: a name and its data line.
public struct SSEMessage: Sendable, Equatable {
    public var event: String
    public var data: String

    public init(event: String, data: String) {
        self.event = event
        self.data = data
    }
}

/// Reads an SSE stream line by line.
///
/// `URLSession.AsyncBytes.lines` drops empty lines, so the blank line that normally ends an
/// event never arrives. The backend always writes `event:` then a single `data:` line, so an
/// event is dispatched on its `data:` line, under the last `event:` name seen (or "message").
/// Multi-line data, should it ever come, is handled when the blank line does arrive.
public struct SSELineParser: Sendable {
    private var pendingEvent: String?

    public init() {}

    /// Feeds one line (without its line break). Returns a message when one is complete.
    public mutating func consume(_ rawLine: String) -> SSEMessage? {
        let line = rawLine.hasSuffix("\r") ? String(rawLine.dropLast()) : rawLine
        if line.isEmpty {
            pendingEvent = nil
            return nil
        }
        if line.hasPrefix(":") { return nil } // comment / keep-alive
        let (field, value) = Self.split(line)
        switch field {
        case "event":
            pendingEvent = value
            return nil
        case "data":
            let message = SSEMessage(event: pendingEvent ?? "message", data: value)
            pendingEvent = nil
            return message
        default:
            return nil // id:, retry: — unused here
        }
    }

    static func split(_ line: String) -> (String, String) {
        guard let colon = line.firstIndex(of: ":") else { return (line, "") }
        let field = String(line[..<colon])
        var value = line[line.index(after: colon)...]
        if value.first == " " { value = value.dropFirst() }
        return (field, String(value))
    }
}

/// The events of `POST /grade/stream`, decoded.
public enum GradeStreamEvent: Sendable, Equatable {
    case scores(ScoresPayload)
    case feedback(String)
    case followUp(String)
    case done(GradeResult)
    case error(StreamError)
    case ignored(String)

    private struct Delta: Decodable { var delta: String }
    private struct Text: Decodable { var text: String }

    public static func decode(_ message: SSEMessage, decoder: JSONDecoder = CaseDuoJSON.decoder) throws -> GradeStreamEvent {
        let data = Data(message.data.utf8)
        switch message.event {
        case "scores": return .scores(try decoder.decode(ScoresPayload.self, from: data))
        case "feedback": return .feedback(try decoder.decode(Delta.self, from: data).delta)
        case "follow_up": return .followUp(try decoder.decode(Text.self, from: data).text)
        case "done": return .done(try decoder.decode(GradeResult.self, from: data))
        case "error": return .error(try decoder.decode(StreamError.self, from: data))
        default: return .ignored(message.event)
        }
    }
}

/// What the result screen shows while the stream arrives: a reducer, so it can be tested.
public struct GradeStreamState: Sendable, Equatable {
    public var score: Int?
    public var rubricScores: [RubricScore] = []
    public var feedback: String = ""
    public var followUp: String?
    public var result: GradeResult?
    public var error: StreamError?

    public init() {}

    public var isFinished: Bool { result != nil || error != nil }
    public var hasScores: Bool { score != nil }

    public mutating func apply(_ event: GradeStreamEvent) {
        switch event {
        case .scores(let payload):
            score = payload.score
            rubricScores = payload.rubricScores
        case .feedback(let delta):
            feedback += delta
        case .followUp(let text):
            followUp = text
        case .done(let result):
            self.result = result
            // The final attempt is the reference: it holds the server's own score and texts.
            score = result.attempt.score ?? score
            if let scores = result.attempt.rubricScores, !scores.isEmpty { rubricScores = scores }
            if let text = result.attempt.feedback, !text.isEmpty { feedback = text }
            followUp = result.attempt.followUp ?? followUp
        case .error(let error):
            self.error = error
        case .ignored:
            break
        }
    }
}
