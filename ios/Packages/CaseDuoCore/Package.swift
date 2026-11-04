// swift-tools-version: 5.9
// Everything the app decides without a screen lives here: the API models, the SSE reader, the
// haptic patterns, the widget snapshot, the dates. Foundation only, so it builds and tests on
// macOS and Linux alike (`swift test`), like SingaSmokeCore.
import PackageDescription

let package = Package(
    name: "CaseDuoCore",
    defaultLocalization: "fr",
    platforms: [.iOS(.v17), .macOS(.v14)],
    products: [
        .library(name: "CaseDuoCore", targets: ["CaseDuoCore"]),
    ],
    targets: [
        .target(name: "CaseDuoCore"),
        .testTarget(name: "CaseDuoCoreTests", dependencies: ["CaseDuoCore"]),
    ]
)
