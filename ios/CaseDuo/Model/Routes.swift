import CaseDuoCore
import Foundation
import SwiftUI

/// Where the Aujourd'hui and Entraîner tabs can go. Kept in the model so a result screen can
/// go back to the start of its tab.
enum HomeRoute: Hashable {
    case exercise(id: ID, revenge: Bool)
    case result(GradingSession)
    case attempt(id: ID)
    case dayClose
}

/// How a screen pushes the next one, whichever tab's stack it lives in: the tab's root view
/// sets it to append to its own path (Aujourd'hui or Entraîner).
private struct PushRouteKey: EnvironmentKey {
    static let defaultValue: (HomeRoute) -> Void = { _ in }
}

extension EnvironmentValues {
    var pushRoute: (HomeRoute) -> Void {
        get { self[PushRouteKey.self] }
        set { self[PushRouteKey.self] = newValue }
    }
}

/// The destinations both tabs share.
struct RouteDestinations: ViewModifier {
    func body(content: Content) -> some View {
        content.navigationDestination(for: HomeRoute.self) { route in
            switch route {
            case .exercise(let id, let revenge):
                ExerciseView(exerciseId: id, isRevenge: revenge)
            case .result(let session):
                ResultView(session: session)
            case .attempt(let id):
                AttemptDetailView(attemptId: id)
            case .dayClose:
                DayCloseView()
            }
        }
    }
}

extension View {
    func routeDestinations() -> some View { modifier(RouteDestinations()) }
}
