import XCTest

/// The Aujourd'hui and Entraîner pages must not pan sideways: a horizontal drag leaves every
/// element where it was. Runs on the simulator in CI with the demo data (`-uiDemo YES`).
final class HorizontalStabilityUITests: XCTestCase {
    func testPagesDoNotSlideSideways() {
        let app = XCUIApplication()
        app.launchArguments = ["-uiDemo", "YES"]
        app.launch()

        assertStaysPut(app, anchor: app.staticTexts["Engagement"], page: "Aujourd'hui")

        let training = app.tabBars.buttons["Entraîner"]
        XCTAssertTrue(training.waitForExistence(timeout: 10), "no Entraîner tab")
        training.tap()
        // The first card of the demo pack (a NavigationLink, read as one button).
        let card = app.buttons.matching(NSPredicate(format: "label CONTAINS %@", "Huit bagues")).firstMatch
        assertStaysPut(app, anchor: card, page: "Entraîner")
    }

    private func assertStaysPut(_ app: XCUIApplication, anchor: XCUIElement, page: String) {
        XCTAssertTrue(anchor.waitForExistence(timeout: 15), "\(page): anchor not on screen")
        let before = anchor.frame.minX
        let scroll = app.scrollViews.firstMatch
        XCTAssertTrue(scroll.waitForExistence(timeout: 5), "\(page): no scroll view")
        // A quick swipe, then a slow drag, both sideways.
        scroll.swipeLeft()
        let from = scroll.coordinate(withNormalizedOffset: CGVector(dx: 0.85, dy: 0.55))
        let to = scroll.coordinate(withNormalizedOffset: CGVector(dx: 0.15, dy: 0.55))
        from.press(forDuration: 0.15, thenDragTo: to)
        sleep(1)
        let after = anchor.frame.minX
        XCTAssertEqual(before, after, accuracy: 2, "\(page) slid sideways: x \(before) → \(after)")
    }
}
