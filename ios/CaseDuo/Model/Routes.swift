import CaseDuoCore
import Foundation

/// Where the Aujourd'hui tab can go. Kept in the model so a result screen can go back to the day.
enum HomeRoute: Hashable {
    case exercise(id: ID, revenge: Bool)
    case result(GradingSession)
    case attempt(id: ID)
    case dayClose
}
