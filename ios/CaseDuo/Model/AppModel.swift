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
        case signedOut
        case ready
    }

    enum Tab: Hashable { case today, history, league, profile }

    private(set) var phase: Phase = .launching
    private(set) var me: Me?
    private(set) var today: Today?
    private(set) var providers = Providers(apple: false)
    var errorMessage: String?
    var isRefreshing = false
    var tab: Tab = .today
    /// The Aujourd'hui tab's navigation stack.
    var homePath: [HomeRoute] = []
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
            if (error as? APIError) == .offline {
                // The session cannot be checked without network: wait for it rather than ask to log in.
                notifications.lastCallWasOffline = true
                notifications.rescheduleStreakSaver(today: today, enabled: notificationsEnabled)
                phase = .offline
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
        notifications.lastCallWasOffline = (error as? APIError) == .offline
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

        if progress.perfectWeek == true {
            celebrate(.perfectWeek)
        } else if progress.streakExtended {
            celebrate(.streakUp)
        } else if progress.goalJustMet == true {
            Sounds.shared.play(.success)
        }
        // Refresh in the background: revenge cards, unlocks, league position.
        Task { await refreshToday() }
    }

    enum Celebration { case streakUp, perfectWeek, promotion }

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
        }
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
    /// CI screenshots: `-uiTab history|league|profile`, `-uiOpen exercise|result|dayclose|mock`.
    func applyDebugLaunchArguments() {
        let defaults = UserDefaults.standard
        switch defaults.string(forKey: "uiTab") {
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
