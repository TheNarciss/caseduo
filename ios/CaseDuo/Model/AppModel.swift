import CaseDuoCore
import Foundation
import Observation
import SwiftUI

/// App state, like SingaSmoke's AppModel: who is signed in, today's day, and what follows a
/// graded exercise (XP, streak, widget, badge, icon, celebrations).
@MainActor
@Observable
final class AppModel {
    enum Phase: Equatable {
        case launching
        case offline
        case serverDown
        case signedOut
        case ready
    }

    enum Tab: Hashable { case today, training, history, league, profile }

    private(set) var phase: Phase = .launching
    private(set) var me: Me?
    private(set) var today: Today?
    /// The Parcours (docs/PARCOURS.md): units, steps, what is open.
    private(set) var path: PathView?
    private(set) var pathError: String?
    private(set) var providers = Providers(apple: false)
    var errorMessage: String?
    var isRefreshing = false
    var tab: Tab = .today
    /// The Aujourd'hui tab's navigation stack.
    var homePath: [HomeRoute] = []
    /// The Entraîner tab's navigation stack.
    var trainingPath: [HomeRoute] = []
    /// Bumped after a grading so the Entraîner tab reloads its list.
    private(set) var trainingVersion = 0
    /// The full-screen « Journée complète » moment, once per day.
    var showDayComplete = false
    /// The mock interview, full screen.
    var showMock = false

    /// Bumped to throw confetti (streak +1, perfect week, league promotion only).
    private(set) var confettiTrigger = 0
    /// Shown once when a freeze saved the streak.
    var showFreezeUsed = false
    /// The last graded progress, for the result screen's streak line.
    private(set) var lastProgress: GradeProgress?

    let service: CaseDuoService
    @ObservationIgnored private let notifications = Notifications.shared

    init(service: CaseDuoService? = nil) {
        self.service = service ?? (AppConfig.isDemo ? DemoService() as CaseDuoService : LiveService())
        notifications.service = self.service
        notifications.onOpenToday = { [weak self] in
            self?.tab = .today
            self?.homePath = []
        }
    }

    // MARK: Derived

    var palette: Palette {
        guard let today else { return .standard }
        return AppIconChoice.perfectWeekActive(unlocks: today.unlocks, today: today.date) ? .perfectWeek : .standard
    }

    var isAdmin: Bool { today?.isAdmin ?? me?.isAdmin ?? false }
    var soundsEnabled: Bool { me?.soundsEnabled ?? true }
    var commitment: Commitment? { today?.commitment ?? me?.commitment }

    /// Back to the start of the tab on screen.
    func popToRoot() {
        if tab == .training { trainingPath = [] } else { homePath = [] }
    }

    /// Back to the day, from anywhere.
    func goHome() {
        trainingPath = []
        homePath = []
        tab = .today
    }
    var notificationsEnabled: Bool { me?.notificationsEnabled ?? true }
    var timeZone: TimeZone { userTimeZone(today?.timezone ?? me?.timezone) }

    // MARK: Launch and session

    func bootstrap() async {
        notifications.configure()
        phase = .launching
        do {
            providers = (try? await service.providers()) ?? Providers(apple: false)
            try await service.renewSession()
            try await loadAfterSignIn()
        } catch {
            if let api = error as? APIError, api.isUnreachable {
                // The session cannot be checked without the server: wait for it rather than ask to log in.
                notifications.lastCallWasOffline = true
                notifications.rescheduleStreakSaver(today: today, enabled: notificationsEnabled)
                phase = api == .offline ? .offline : .serverDown
            } else {
                phase = .signedOut
            }
        }
    }

    func signIn(email: String, password: String) async throws {
        try await service.login(email: email, password: password)
        try await loadAfterSignIn()
    }

    func signInWithApple(identityToken: String, nonce: String, displayName: String?) async throws {
        try await service.loginWithApple(AppleLogin(identityToken: identityToken, nonce: nonce, displayName: displayName))
        try await loadAfterSignIn()
    }

    private func loadAfterSignIn() async throws {
        me = try await service.me()
        Sounds.shared.isEnabled = soundsEnabled
        phase = .ready
        await refreshToday()
        await refreshPath()
        if notificationsEnabled, !AppConfig.isDemo {
            await notifications.requestAuthorizationAndRegister()
            await notifications.sendPendingToken()
        }
    }

    func signOut() async {
        try? await service.logout()
        clearSession()
    }

    func deleteAccount() async throws {
        try await service.deleteAccount()
        clearSession()
    }

    private func clearSession() {
        let storage = HTTPCookieStorage.sharedCookieStorage(forGroupContainerIdentifier: AppConfig.appGroup)
        storage.cookies?.forEach { storage.deleteCookie($0) }
        me = nil
        today = nil
        path = nil
        notifications.forgetToken()
        notifications.cancelAll()
        WidgetBridge.clear()
        phase = .signedOut
        tab = .today
        homePath = []
    }

    /// Any call that comes back 401 sends the user to the login screen.
    func handle(_ error: Error) {
        if (error as? APIError) == .unauthorized {
            clearSession()
            return
        }
        notifications.lastCallWasOffline = (error as? APIError)?.isUnreachable ?? false
        errorMessage = error.localizedDescription
    }

    // MARK: Today

    func refreshToday() async {
        isRefreshing = true
        defer { isRefreshing = false }
        do {
            let fresh = try await service.today()
            notifications.lastCallWasOffline = false
            apply(today: fresh)
        } catch {
            handle(error)
            notifications.rescheduleStreakSaver(today: today, enabled: notificationsEnabled)
        }
    }

    private func apply(today fresh: Today) {
        today = fresh
        if fresh.streak.freezeJustUsed == true { showFreezeUsed = true }
        WidgetBridge.update(from: fresh)
        notifications.updateBadge(remaining: fresh.remaining)
        notifications.rescheduleStreakSaver(today: fresh, enabled: notificationsEnabled)
        IconManager.apply(unlocks: fresh.unlocks, today: fresh.date)
    }

    /// What follows a graded exercise: numbers, widget, badge, haptics, sounds, confetti.
    func didGrade(_ result: GradeResult) {
        let progress = result.progress
        lastProgress = progress
        if var day = today {
            day.goal.xpToday = progress.xpToday
            day.goal.met = progress.goalMet
            if let target = progress.goalTarget { day.goal.targetXp = target }
            day.streak = progress.streak
            day.remaining = progress.remaining
            day.dayComplete = progress.dayComplete
            if let index = day.cards.firstIndex(where: { $0.exerciseId == result.attempt.exerciseId }),
               result.attempt.kind == .main {
                day.cards[index].done = true
                day.cards[index].bestScore = max(day.cards[index].bestScore ?? 0, result.attempt.score ?? 0)
            }
            today = day
        }
        WidgetBridge.update(from: progress)
        notifications.updateBadge(remaining: progress.remaining)
        notifications.rescheduleStreakSaver(today: today, enabled: notificationsEnabled)
        trainingVersion += 1

        if progress.perfectWeek == true {
            celebrate(.perfectWeek)
        } else if progress.streakExtended {
            celebrate(.streakUp)
        } else if progress.goalJustMet == true {
            Haptics.shared.play(.goalMet)
            Sounds.shared.play(.success)
        }
        if let bonus = progress.dayCompleteBonus, bonus > 0 {
            // After the score has had its moment.
            DispatchQueue.main.asyncAfter(deadline: .now() + 1.6) { [weak self] in
                self?.celebrate(.dayComplete)
            }
        }
        // Refresh in the background: revenge cards, unlocks, league position.
        Task { await refreshToday() }
        Task { await completeAppliedStep(with: result.attempt) }
    }

    // MARK: Parcours

    func refreshPath() async {
        do {
            path = try await service.path()
            pathError = nil
        } catch {
            if (error as? APIError) == .unauthorized { clearSession(); return }
            pathError = error.localizedDescription
        }
    }

    /// What follows a lesson: XP into the day, streak, celebrations, then the path again.
    func didCompleteLesson(_ done: LessonCompletion) {
        if let progress = done.progress {
            lastProgress = progress
            if var day = today {
                day.goal.xpToday = progress.xpToday
                day.goal.met = progress.goalMet
                if let target = progress.goalTarget { day.goal.targetXp = target }
                day.streak = progress.streak
                day.dayComplete = progress.dayComplete
                today = day
            }
            WidgetBridge.update(from: progress)
            notifications.rescheduleStreakSaver(today: today, enabled: notificationsEnabled)
            if progress.perfectWeek == true {
                celebrate(.perfectWeek)
            } else if progress.streakExtended {
                celebrate(.streakUp)
            } else if progress.goalJustMet == true {
                Haptics.shared.play(.goalMet)
                Sounds.shared.play(.success)
            }
        }
        if done.unitDone == true, done.passed { confettiTrigger += 1 }
        Task { await refreshPath() }
    }

    /// The day's exercise that an « en situation » step opens: a card of the wanted family not
    /// done yet, else the first card left.
    func exerciseCard(forApplied type: String?) -> ExerciseCard? {
        guard let cards = today?.cards else { return nil }
        let wanted = type ?? "case"
        let fits: (ExerciseCard) -> Bool = { card in
            switch wanted {
            case "case": return ![.brainteaser, .fit, .cadrageHome, .unknown].contains(card.type)
            default: return card.type.rawValue == wanted
            }
        }
        return cards.first { !$0.done && fits($0) } ?? cards.first { fits($0) } ?? cards.first { !$0.done }
    }

    /// After a grading, an open « en situation » step of the matching family is ticked.
    private func completeAppliedStep(with attempt: Attempt) async {
        guard attempt.kind == .main, let path else { return }
        let open = path.allNodes.filter { $0.kind == .applied && ($0.status == .active || $0.status == .available) }
        guard let node = open.first(where: { node in
            let wanted = node.appliedType ?? "case"
            guard let type = attempt.exercise?.type else { return wanted == "case" }
            return wanted == "case" ? ![.brainteaser, .fit].contains(type) : type.rawValue == wanted
        }) else { return }
        do {
            let done = try await service.completeNode(code: node.code, LessonCompletionRequest(results: [], attemptId: attempt.id))
            if done.passed { Haptics.shared.play(.goalMet) }
            await refreshPath()
        } catch {
            // The step stays open; the next grading tries again.
        }
    }

    enum Celebration { case streakUp, perfectWeek, promotion, dayComplete }

    func celebrate(_ celebration: Celebration) {
        confettiTrigger += 1
        switch celebration {
        case .streakUp:
            Haptics.shared.play(.streakUp)
            Sounds.shared.play(.streak)
        case .perfectWeek:
            Haptics.shared.play(.perfectWeek)
            Sounds.shared.play(.streak)
        case .promotion:
            Haptics.shared.play(.scoreHigh)
            Sounds.shared.play(.success)
        case .dayComplete:
            showDayComplete = true
            Haptics.shared.play(.dayComplete)
            Sounds.shared.play(.streak)
        }
    }

    /// « Je m'engage » : the goal for a period (D16). Throws the server's refusal as is.
    func commit(_ request: CommitmentRequest) async throws {
        me = try await service.commit(request)
        Haptics.shared.play(.commit)
        Sounds.shared.play(.success)
        await refreshToday()
    }

    // MARK: Profile

    func update(_ patch: MePatch) async {
        do {
            me = try await service.updateMe(patch)
            Sounds.shared.isEnabled = soundsEnabled
            if patch.notificationsEnabled == true { await notifications.requestAuthorizationAndRegister() }
            if patch.dailyGoalXp != nil || patch.timezone != nil { await refreshToday() }
            if patch.notificationsEnabled == false {
                notifications.rescheduleStreakSaver(today: today, enabled: false)
            }
        } catch {
            handle(error)
        }
    }

    func saveStory(_ text: String) async throws {
        me = try await service.updateStory(text)
    }

    #if DEBUG
    /// CI screenshots: `-uiTab history|league|profile`, `-uiOpen exercise|result|dayclose|mock|lesson`.
    func applyDebugLaunchArguments() {
        let defaults = UserDefaults.standard
        switch defaults.string(forKey: "uiTab") {
        case "training": tab = .training
        case "history": tab = .history
        case "league": tab = .league
        case "profile": tab = .profile
        default: break
        }
        switch defaults.string(forKey: "uiOpen") {
        case "exercise":
            homePath = [.exercise(id: "ex-ms", revenge: false)]
        case "result":
            let session = GradingSession(
                request: GradeRequest(exerciseId: "ex-ms", kind: .main, answerText: "…", durationSeconds: 300, inputMode: .voice),
                title: "Combien de passagers transitent chaque jour par Changi ?", type: .marketSizing,
                language: "fr", isRevenge: false, model: self)
            session.start()
            homePath = [.result(session)]
        case "dayclose":
            homePath = [.dayClose]
        case "lesson":
            homePath = [.lesson(code: "d1.showcase")]
        case "daycomplete":
            showDayComplete = true
        case "mock":
            showMock = true
        default:
            break
        }
    }
    #endif

    func reloadMe() async {
        do { me = try await service.me() } catch { handle(error) }
    }
}
