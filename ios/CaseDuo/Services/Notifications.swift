import CaseDuoCore
import UIKit
import UserNotifications

/// Push (APNs), the local streak-saver fallback, and the icon badge.
///
/// The server sends the 20:00 streak saver and the 7-day goodbye (never more than one push a
/// day). The phone schedules its own copy of the streak saver only when push cannot reach it:
/// no token registered with the server, or the last call failed for lack of network.
@MainActor
final class Notifications: NSObject, UNUserNotificationCenterDelegate {
    static let shared = Notifications()

    private let center = UNUserNotificationCenter.current()
    private let defaults = UserDefaults.standard
    private let tokenKey = "push.registeredToken"

    /// Set by the app model: sends the token once the user is signed in.
    var service: CaseDuoService?
    /// The last call failed for lack of network: push may not be reaching the server's records.
    var lastCallWasOffline = false
    /// Tapping a notification opens the day.
    var onOpenToday: (() -> Void)?

    private var pendingToken: String?

    var pushUsable: Bool { registeredToken != nil && !lastCallWasOffline }

    private var registeredToken: String? {
        get { defaults.string(forKey: tokenKey) }
        set { defaults.set(newValue, forKey: tokenKey) }
    }

    func configure() {
        center.delegate = self
    }

    /// Asks once (when notifications are on in Profil), then registers with APNs.
    func requestAuthorizationAndRegister() async {
        let settings = await center.notificationSettings()
        switch settings.authorizationStatus {
        case .notDetermined:
            let granted = (try? await center.requestAuthorization(options: [.alert, .sound, .badge])) ?? false
            if granted { UIApplication.shared.registerForRemoteNotifications() }
        case .authorized, .provisional, .ephemeral:
            UIApplication.shared.registerForRemoteNotifications()
        default:
            break
        }
    }

    // MARK: APNs token

    func didRegister(deviceToken: Data) {
        let hex = deviceToken.map { String(format: "%02x", $0) }.joined()
        pendingToken = hex
        Task { await sendPendingToken() }
    }

    func didFailToRegister() {
        registeredToken = nil
    }

    /// Sends the token to the server if it is new (or the server never got it).
    func sendPendingToken() async {
        guard let token = pendingToken, let service else { return }
        guard token != registeredToken else { pendingToken = nil; return }
        do {
            try await service.registerPushToken(PushTokenRegistration(token: token, environment: AppConfig.pushEnvironment))
            registeredToken = token
            pendingToken = nil
        } catch {
            if (error as? APIError) == .offline { lastCallWasOffline = true }
        }
    }

    func forgetToken() {
        registeredToken = nil
    }

    // MARK: Badge and local fallback

    /// The icon badge: exercises left today.
    func updateBadge(remaining: Int) {
        center.setBadgeCount(max(0, remaining)) { _ in }
    }

    /// Re-plans the local streak saver from the latest day state.
    func rescheduleStreakSaver(today: Today?, enabled: Bool) {
        center.removePendingNotificationRequests(withIdentifiers: [StreakSaverPlan.identifier])
        guard enabled, let today else { return }
        let zone = userTimeZone(today.timezone)
        guard let fire = StreakSaverPlan.fireDate(today: today, pushUsable: pushUsable, now: Date(), timeZone: zone) else { return }
        let content = UNMutableNotificationContent()
        content.title = StreakSaverPlan.title()
        content.body = StreakSaverPlan.body(streak: today.streak.current)
        content.sound = .default
        content.badge = NSNumber(value: today.remaining)
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = zone
        var components = calendar.dateComponents([.year, .month, .day, .hour, .minute], from: fire)
        components.timeZone = zone
        let trigger = UNCalendarNotificationTrigger(dateMatching: components, repeats: false)
        center.add(UNNotificationRequest(identifier: StreakSaverPlan.identifier, content: content, trigger: trigger))
    }

    func cancelAll() {
        center.removeAllPendingNotificationRequests()
        center.setBadgeCount(0) { _ in }
    }

    // MARK: UNUserNotificationCenterDelegate

    nonisolated func userNotificationCenter(_ center: UNUserNotificationCenter, willPresent notification: UNNotification) async -> UNNotificationPresentationOptions {
        [.banner, .sound, .badge]
    }

    nonisolated func userNotificationCenter(_ center: UNUserNotificationCenter, didReceive response: UNNotificationResponse) async {
        await MainActor.run { self.onOpenToday?() }
    }
}
