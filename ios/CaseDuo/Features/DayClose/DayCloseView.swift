import CaseDuoCore
import SwiftUI

/// End of the day: the streak, the XP, the league position, and the day's weakest criterion in
/// one line, to know what to work on tomorrow.
struct DayCloseView: View {
    @Environment(AppModel.self) private var model
    @Environment(\.palette) private var palette
    @State private var summary: DaySummary?
    @State private var error: String?

    var body: some View {
        VStack(spacing: 0) {
            ScrollView {
                VStack(spacing: 22) {
                    if let summary {
                        FlameView(streak: summary.streak.current, lit: summary.streak.status == .extendedToday, size: 110)
                            .padding(.top, 20)
                        VStack(spacing: 4) {
                            Text("\(summary.streak.current)")
                                .font(.system(size: 64, weight: .heavy, design: .rounded))
                                .foregroundStyle(palette.linear)
                            Text(summary.streak.status == .extendedToday ? "jours de série, tenue aujourd'hui" : "jours de série")
                                .font(.headline)
                                .foregroundStyle(Brand.textSecondary)
                        }
                        HStack(spacing: 12) {
                            stat(value: Format.xp(summary.xpToday), label: "aujourd'hui")
                            stat(value: "\(summary.exercisesDone)", label: summary.exercisesDone > 1 ? "exercices" : "exercice")
                            if let rank = summary.leagueRank {
                                stat(value: "\(rank)e", label: "ligue \(Format.leagueTier(summary.leagueTier ?? ""))")
                            }
                        }
                        if let line = summary.line ?? summary.weakestCriterion.map({ "Point faible du jour : \($0.label.lowercased())." }) {
                            Label(line, systemImage: "scope")
                                .font(.headline)
                                .padding(16)
                                .frame(maxWidth: .infinity, alignment: .leading)
                                .card(fill: palette.accentSoft)
                        }
                        Text("Demain, la génération des exercices en tiendra compte.")
                            .font(.footnote)
                            .foregroundStyle(Brand.textSecondary)
                    } else if let error {
                        ErrorBanner(message: error)
                    } else {
                        LoadingView().frame(height: 300)
                    }
                }
                .padding(20)
            }
            BottomActions {
                Button("À demain") { model.homePath = [] }.buttonStyle(.pill)
            }
        }
        .background(Brand.background)
        .navigationTitle("Bilan du jour")
        .navigationBarTitleDisplayMode(.inline)
        .task {
            do { summary = try await model.service.daySummary() } catch {
                model.handle(error)
                self.error = error.localizedDescription
            }
        }
    }

    private func stat(value: String, label: String) -> some View {
        VStack(spacing: 4) {
            Text(value).font(.title2.weight(.heavy)).monospacedDigit()
            Text(label).font(.caption).foregroundStyle(Brand.textSecondary)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 14)
        .card(radius: 16)
    }
}

/// A freeze covered a missed day. No guilt: the streak goes on.
struct FreezeUsedView: View {
    @Environment(AppModel.self) private var model
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        VStack(spacing: 18) {
            Image(systemName: "snowflake")
                .font(.system(size: 64, weight: .bold))
                .foregroundStyle(Brand.freeze)
                .symbolEffect(.bounce, value: true)
                .padding(.top, 24)
            Text("Freeze utilisé").font(.title.weight(.heavy))
            if let streak = model.today?.streak {
                Text("Un jour sans exercice, ça arrive. Ta série de \(Format.streakDays(streak.current)) continue.")
                    .multilineTextAlignment(.center)
                Text(streak.freezes > 0
                     ? "Il te reste \(streak.freezes) freeze\(streak.freezes > 1 ? "s" : ""). Tu en gagnes un tous les 7 jours de série."
                     : "Plus de freeze en réserve : tu en regagnes un tous les 7 jours de série.")
                    .font(.subheadline)
                    .foregroundStyle(Brand.textSecondary)
                    .multilineTextAlignment(.center)
            }
            Spacer()
            Button("On reprend") { dismiss() }.buttonStyle(.pill)
        }
        .padding(24)
        .background(Brand.background)
    }
}
