import CaseDuoCore
import Foundation

/// What can go wrong talking to the backend, in words the user can read.
enum APIError: LocalizedError, Equatable {
    case unauthorized
    case http(status: Int, detail: String?)
    case aiUnavailable(String?)
    case offline
    /// The phone has network, but the CaseDuo server does not answer (down, being deployed, DNS).
    case serverUnreachable
    case decoding(String)
    case stream(StreamError)

    var errorDescription: String? {
        switch self {
        case .unauthorized:
            return "Ta session a expiré. Reconnecte-toi."
        case .http(let status, let detail):
            return detail ?? "Le serveur a répondu \(status)."
        case .aiUnavailable(let detail):
            return detail ?? "Le correcteur IA est indisponible pour le moment. Réessaie dans quelques minutes."
        case .offline:
            return "Pas de connexion. Vérifie le réseau et réessaie."
        case .serverUnreachable:
            return "Le serveur CaseDuo ne répond pas. Ton réseau n'y est pour rien : réessaie dans quelques minutes."
        case .decoding:
            return "Réponse inattendue du serveur. Mets l'app à jour."
        case .stream(let error):
            switch error.reason {
            case "budget": return error.detail ?? "Budget IA du jour atteint. Réessaie demain."
            case "overloaded": return error.detail ?? "Le correcteur est surchargé. Réessaie dans une minute."
            default: return error.detail ?? "La correction s'est interrompue."
            }
        }
    }

    var isOffline: Bool { self == .offline }
    /// No answer from the server, whoever is at fault: the phone's network or the server.
    var isUnreachable: Bool { self == .offline || self == .serverUnreachable }
}

/// Every call the app makes (docs/API.md). Live and demo implementations.
protocol CaseDuoService: AnyObject, Sendable {
    func providers() async throws -> Providers
    func login(email: String, password: String) async throws
    func loginWithApple(_ body: AppleLogin) async throws
    func logout() async throws
    func renewSession() async throws
    func me() async throws -> Me
    func updateMe(_ patch: MePatch) async throws -> Me
    func updateStory(_ text: String) async throws -> Me
    func registerPushToken(_ body: PushTokenRegistration) async throws
    func deleteAccount() async throws

    func today() async throws -> Today
    func widget() async throws -> WidgetInfo
    func daySummary() async throws -> DaySummary

    func exercise(id: ID) async throws -> ExerciseDetail
    func reveal(id: ID) async throws -> RevealResponse
    func grade(_ request: GradeRequest) async throws -> GradeResult
    func gradeStream(_ request: GradeRequest) -> AsyncThrowingStream<GradeStreamEvent, Error>
    func attempts(limit: Int) async throws -> [AttemptSummary]
    func attempt(id: ID) async throws -> Attempt
    func training() async throws -> Training
    func commit(_ request: CommitmentRequest) async throws -> Me

    func history(days: Int) async throws -> History
    func league() async throws -> League
    func badges() async throws -> [Badge]

    func startMock(kind: String) async throws -> MockRun
    func mock(id: ID) async throws -> MockRun
    func finishMock(id: ID) async throws -> MockFinish

    func flag(exerciseId: ID, flagged: Bool, note: String?) async throws
}

/// The real backend, over URLSession. The session cookie (`caseduo_auth`) lives in the App
/// Group's cookie storage, so the widget can make the same calls; URLSession keeps it and sends
/// it back, exactly as the phone's HTTP stack does for Tangent.
final class LiveService: CaseDuoService, @unchecked Sendable {
    let baseURL: URL
    private let session: URLSession
    private let decoder = CaseDuoJSON.decoder
    private let encoder = CaseDuoJSON.encoder

    init(baseURL: URL = AppConfig.apiBaseURL) {
        self.baseURL = baseURL
        self.session = URLSession(configuration: Self.configuration())
    }

    static func configuration() -> URLSessionConfiguration {
        let configuration = URLSessionConfiguration.default
        configuration.httpCookieStorage = HTTPCookieStorage.sharedCookieStorage(forGroupContainerIdentifier: AppConfig.appGroup)
        configuration.httpCookieAcceptPolicy = .always
        configuration.httpShouldSetCookies = true
        // Grading without streaming can take a minute; the stream sends data as it goes.
        configuration.timeoutIntervalForRequest = 120
        configuration.waitsForConnectivity = false
        return configuration
    }

    // MARK: Plumbing

    private func makeRequest(_ method: String, _ path: String, body: (any Encodable)? = nil) throws -> URLRequest {
        guard let url = URL(string: baseURL.absoluteString.trimmingCharacters(in: CharacterSet(charactersIn: "/")) + path) else {
            throw APIError.http(status: 0, detail: "Adresse invalide : \(path)")
        }
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        if let body {
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.httpBody = try encoder.encode(AnyEncodable(body))
        }
        return request
    }

    private func perform(_ request: URLRequest) async throws -> Data {
        let data: Data
        let response: URLResponse
        do {
            (data, response) = try await session.data(for: request)
        } catch {
            throw Self.map(error)
        }
        try Self.check(response, body: data, decoder: decoder)
        return data
    }

    private func call<T: Decodable>(_ method: String, _ path: String, body: (any Encodable)? = nil) async throws -> T {
        let data = try await perform(try makeRequest(method, path, body: body))
        do {
            return try decoder.decode(T.self, from: data)
        } catch {
            throw APIError.decoding(String(describing: error))
        }
    }

    private func callNoContent(_ method: String, _ path: String, body: (any Encodable)? = nil) async throws {
        _ = try await perform(try makeRequest(method, path, body: body))
    }

    static func map(_ error: Error) -> Error {
        if let api = error as? APIError { return api }
        if let url = error as? URLError {
            switch url.code {
            case .notConnectedToInternet, .networkConnectionLost, .timedOut, .dataNotAllowed,
                 .internationalRoamingOff:
                return APIError.offline
            case .cannotFindHost, .cannotConnectToHost, .dnsLookupFailed, .secureConnectionFailed:
                return APIError.serverUnreachable
            default:
                return error
            }
        }
        return error
    }

    static func check(_ response: URLResponse, body: Data, decoder: JSONDecoder) throws {
        guard let http = response as? HTTPURLResponse else { return }
        guard !(200..<300).contains(http.statusCode) else { return }
        let detail = (try? decoder.decode(APIErrorBody.self, from: body))?.detail
        switch http.statusCode {
        case 401: throw APIError.unauthorized
        case 503: throw APIError.aiUnavailable(detail)
        // The proxy in front of the backend (Caddy, Cloudflare) answers for it when it is down.
        case 502, 504, 520...530: throw APIError.serverUnreachable
        default: throw APIError.http(status: http.statusCode, detail: detail)
        }
    }

    // MARK: Auth & profile

    func providers() async throws -> Providers { try await call("GET", "/auth/providers") }

    func login(email: String, password: String) async throws {
        var request = try makeRequest("POST", "/auth/login")
        request.setValue("application/x-www-form-urlencoded", forHTTPHeaderField: "Content-Type")
        request.httpBody = Self.formBody(["username": email, "password": password])
        do {
            _ = try await perform(request)
        } catch APIError.http(status: 400, detail: _) {
            throw APIError.http(status: 400, detail: "E-mail ou mot de passe incorrect.")
        }
    }

    static func formBody(_ fields: [String: String]) -> Data {
        var allowed = CharacterSet.alphanumerics
        allowed.insert(charactersIn: "-._~")
        let pairs = fields.sorted { $0.key < $1.key }.map { key, value in
            "\(key)=\(value.addingPercentEncoding(withAllowedCharacters: allowed) ?? value)"
        }
        return Data(pairs.joined(separator: "&").utf8)
    }

    func loginWithApple(_ body: AppleLogin) async throws { try await callNoContent("POST", "/auth/apple/native", body: body) }
    func logout() async throws { try await callNoContent("POST", "/auth/logout") }
    func renewSession() async throws { try await callNoContent("GET", "/users/me") }
    func me() async throws -> Me { try await call("GET", "/me") }
    func updateMe(_ patch: MePatch) async throws -> Me { try await call("PATCH", "/me", body: patch) }
    func updateStory(_ text: String) async throws -> Me { try await call("PUT", "/me/story", body: StoryUpdate(storyText: text)) }
    func registerPushToken(_ body: PushTokenRegistration) async throws { try await callNoContent("POST", "/me/push-token", body: body) }

    func deleteAccount() async throws {
        try await callNoContent("DELETE", "/me")
        session.configuration.httpCookieStorage?.cookies?.forEach { session.configuration.httpCookieStorage?.deleteCookie($0) }
    }

    // MARK: Today

    func today() async throws -> Today { try await call("GET", "/today") }
    func widget() async throws -> WidgetInfo { try await call("GET", "/widget") }
    func daySummary() async throws -> DaySummary { try await call("GET", "/day/summary") }

    // MARK: Exercises and grading

    func exercise(id: ID) async throws -> ExerciseDetail { try await call("GET", "/exercises/\(id)") }
    func reveal(id: ID) async throws -> RevealResponse { try await call("POST", "/exercises/\(id)/reveal") }
    func grade(_ request: GradeRequest) async throws -> GradeResult { try await call("POST", "/grade", body: request) }
    func attempts(limit: Int) async throws -> [AttemptSummary] { try await call("GET", "/attempts?limit=\(limit)") }
    func attempt(id: ID) async throws -> Attempt { try await call("GET", "/attempts/\(id)") }
    func training() async throws -> Training { try await call("GET", "/training") }
    func commit(_ request: CommitmentRequest) async throws -> Me { try await call("POST", "/me/commitment", body: request) }

    func gradeStream(_ gradeRequest: GradeRequest) -> AsyncThrowingStream<GradeStreamEvent, Error> {
        AsyncThrowingStream { continuation in
            let task = Task {
                do {
                    var request = try makeRequest("POST", "/grade/stream", body: gradeRequest)
                    request.setValue("text/event-stream", forHTTPHeaderField: "Accept")
                    let (bytes, response) = try await session.bytes(for: request)
                    if let http = response as? HTTPURLResponse, !(200..<300).contains(http.statusCode) {
                        var body = Data()
                        for try await byte in bytes {
                            body.append(byte)
                            if body.count > 16_384 { break }
                        }
                        try Self.check(response, body: body, decoder: decoder)
                    }
                    var parser = SSELineParser()
                    for try await line in bytes.lines {
                        guard let message = parser.consume(line) else { continue }
                        let event = try GradeStreamEvent.decode(message, decoder: decoder)
                        continuation.yield(event)
                        if case .done = event { break }
                        if case .error = event { break }
                    }
                    continuation.finish()
                } catch {
                    continuation.finish(throwing: Self.map(error))
                }
            }
            continuation.onTermination = { _ in task.cancel() }
        }
    }

    // MARK: History, league, badges, mock

    func history(days: Int) async throws -> History { try await call("GET", "/history?days=\(days)") }
    func league() async throws -> League { try await call("GET", "/league") }
    func badges() async throws -> [Badge] { try await call("GET", "/badges") }
    func startMock(kind: String) async throws -> MockRun { try await call("POST", "/mocks", body: MockStart(kind: kind)) }
    func mock(id: ID) async throws -> MockRun { try await call("GET", "/mocks/\(id)") }
    func finishMock(id: ID) async throws -> MockFinish { try await call("POST", "/mocks/\(id)/finish") }

    func flag(exerciseId: ID, flagged: Bool, note: String?) async throws {
        try await callNoContent("POST", "/admin/exercises/\(exerciseId)/flag", body: FlagRequest(flagged: flagged, note: note))
    }
}

/// Lets `makeRequest` take any Encodable.
private struct AnyEncodable: Encodable {
    let value: any Encodable
    init(_ value: any Encodable) { self.value = value }
    func encode(to encoder: Encoder) throws { try value.encode(to: encoder) }
}
