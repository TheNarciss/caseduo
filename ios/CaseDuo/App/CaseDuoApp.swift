import CaseDuoCore
import SwiftUI
import UIKit

@main
struct CaseDuoApp: App {
    @UIApplicationDelegateAdaptor(AppDelegate.self) private var appDelegate
    @State private var model = AppModel()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environment(model)
                .environment(\.palette, model.palette)
                .fontDesign(.rounded)
                .preferredColorScheme(.dark)
                .tint(model.palette.accent)
                .task {
                    await model.bootstrap()
                    #if DEBUG
                    if AppConfig.isDemo { model.applyDebugLaunchArguments() }
                    #endif
                }
                .onOpenURL { url in
                    // caseduo://today (the widget), caseduo://history, caseduo://league
                    switch url.host {
                    case "history": model.tab = .history
                    case "league": model.tab = .league
                    default: model.tab = .today
                    }
                }
        }
    }
}

/// APNs registration lands here (UIKit), then goes to `Notifications`.
final class AppDelegate: NSObject, UIApplicationDelegate {
    func application(_ application: UIApplication,
                     didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil) -> Bool {
        Task { @MainActor in Notifications.shared.configure() }
        return true
    }

    func application(_ application: UIApplication, didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data) {
        Task { @MainActor in Notifications.shared.didRegister(deviceToken: deviceToken) }
    }

    func application(_ application: UIApplication, didFailToRegisterForRemoteNotificationsWithError error: Error) {
        Task { @MainActor in Notifications.shared.didFailToRegister() }
    }
}

struct RootView: View {
    @Environment(AppModel.self) private var model
    @Environment(\.scenePhase) private var scenePhase

    var body: some View {
        ZStack {
            Brand.background.ignoresSafeArea()
            switch model.phase {
            case .launching:
                VStack(spacing: 18) {
                    FlameView(streak: 0, lit: true, size: 72)
                    ProgressView().tint(Brand.flame)
                }
            case .offline:
                OfflineView(serverDown: false)
            case .serverDown:
                OfflineView(serverDown: true)
            case .signedOut:
                LoginView()
            case .ready:
                MainTabs()
            }
        }
        .animation(Brand.quick, value: model.phase)
        .onChange(of: scenePhase) { _, phase in
            // Back in the app after a while: the day may have changed.
            if phase == .active, model.phase == .ready {
                Task { await model.refreshToday() }
            }
        }
    }
}

struct MainTabs: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        @Bindable var model = model
        TabView(selection: $model.tab) {
            HomeView()
                .tabItem { Label("Aujourd'hui", systemImage: "flame.fill") }
                .tag(AppModel.Tab.today)
            HistoryView()
                .tabItem { Label("Historique", systemImage: "chart.line.uptrend.xyaxis") }
                .tag(AppModel.Tab.history)
            LeagueView()
                .tabItem { Label("Ligue", systemImage: "trophy.fill") }
                .tag(AppModel.Tab.league)
            ProfileView()
                .tabItem { Label("Profil", systemImage: "person.crop.circle") }
                .tag(AppModel.Tab.profile)
        }
        .overlay { ConfettiView(trigger: model.confettiTrigger, colors: model.palette.gradient + [Brand.success, .white]) }
        .sheet(isPresented: Binding(get: { model.showFreezeUsed }, set: { model.showFreezeUsed = $0 })) {
            FreezeUsedView()
                .presentationDetents([.medium])
        }
    }
}

/// No answer at launch: either the phone has no network, or it has one and the server is down.
struct OfflineView: View {
    @Environment(AppModel.self) private var model
    let serverDown: Bool

    var body: some View {
        VStack(spacing: 18) {
            Spacer()
            Image(systemName: serverDown ? "server.rack" : "wifi.slash")
                .font(.system(size: 44)).foregroundStyle(Brand.textSecondary)
            Text(serverDown ? "Serveur injoignable" : "Pas de connexion").font(.title2.weight(.bold))
            Text(serverDown
                 ? "Ton réseau fonctionne, mais le serveur CaseDuo ne répond pas. Réessaie dans quelques minutes."
                 : "Tes exercices du jour t'attendent. Reconnecte-toi au réseau pour les charger.")
                .multilineTextAlignment(.center)
                .foregroundStyle(Brand.textSecondary)
            Spacer()
            Button("Réessayer") { Task { await model.bootstrap() } }
                .buttonStyle(.pill)
        }
        .padding(24)
    }
}
