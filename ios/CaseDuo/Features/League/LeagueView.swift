import CaseDuoCore
import SwiftUI

/// The weekly league, bronze → argent → or. Promotion and relegation on Sunday evening. For now
/// the other members are five bots with believable XP curves; real people will take their place.
struct LeagueView: View {
    @Environment(AppModel.self) private var model
    @Environment(\.palette) private var palette
    @State private var league: League?
    @State private var error: String?
    @AppStorage("league.celebratedWeek") private var celebratedWeek = ""

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    if let league {
                        header(league)
                        VStack(spacing: 0) {
                            ForEach(league.members) { member in
                                MemberRow(member: member, zone: league.zone(of: member.rank))
                                if member.id != league.members.last?.id { Divider().overlay(Brand.stroke) }
                            }
                        }
                        .padding(.horizontal, 14)
                        .card()
                        legend(league)
                    } else if let error {
                        ErrorBanner(message: error)
                    } else {
                        LoadingView().frame(height: 400)
                    }
                }
                .padding(16)
            }
            .background(Brand.background)
            .navigationTitle("Ligue")
            .refreshable { await load() }
            .task { await load() }
        }
    }

    private func load() async {
        do {
            let fresh = try await model.service.league()
            league = fresh
            error = nil
            // Confetti once for a promotion: league promotion is one of the three moments.
            if fresh.lastOutcome == "promoted", celebratedWeek != fresh.weekStart {
                celebratedWeek = fresh.weekStart
                model.celebrate(.promotion)
            }
        } catch {
            model.handle(error)
            self.error = error.localizedDescription
        }
    }

    private func header(_ league: League) -> some View {
        HStack(spacing: 14) {
            Image(systemName: "trophy.fill")
                .font(.system(size: 40, weight: .bold))
                .foregroundStyle(tierColor(league.tier))
                .frame(width: 64, height: 64)
                .background(tierColor(league.tier).opacity(0.16), in: Circle())
            VStack(alignment: .leading, spacing: 4) {
                Text("Ligue \(league.tierLabel ?? Format.leagueTier(league.tier))").font(.title2.weight(.heavy))
                if let end = league.endsAt {
                    TimelineView(.periodic(from: .now, by: 60)) { context in
                        Label("Fin dans \(Format.countdown(to: end, from: context.date))", systemImage: "hourglass")
                            .font(.subheadline)
                            .foregroundStyle(Brand.textSecondary)
                    }
                }
                outcomeLine(league)
            }
            Spacer(minLength: 0)
        }
    }

    @ViewBuilder private func outcomeLine(_ league: League) -> some View {
        switch league.lastOutcome {
        case "promoted"?: Label("Promu la semaine dernière", systemImage: "arrow.up.circle.fill").font(.footnote).foregroundStyle(Brand.success)
        case "relegated"?: Label("Redescendu la semaine dernière", systemImage: "arrow.down.circle").font(.footnote).foregroundStyle(Brand.danger)
        default: EmptyView()
        }
    }

    private func legend(_ league: League) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            if league.tier != "gold" {
                Label("Les \(league.promoteTop) premiers montent dimanche soir.", systemImage: "arrow.up").foregroundStyle(Brand.success)
            }
            if league.tier != "bronze" {
                Label("Les \(league.relegateBottom) derniers descendent.", systemImage: "arrow.down").foregroundStyle(Brand.danger)
            }
            Text("Tes XP de la semaine comptent, revanches et mocks compris.").foregroundStyle(Brand.textSecondary)
        }
        .font(.footnote)
    }

    private func tierColor(_ tier: String) -> Color {
        switch tier {
        case "gold": return Color(red: 1.0, green: 0.82, blue: 0.3)
        case "silver": return Color(red: 0.8, green: 0.84, blue: 0.9)
        default: return Color(red: 0.86, green: 0.55, blue: 0.33)
        }
    }
}

private struct MemberRow: View {
    let member: LeagueMember
    let zone: League.Zone
    @Environment(\.palette) private var palette

    var body: some View {
        HStack(spacing: 12) {
            Text("\(member.rank)")
                .font(.headline.monospacedDigit())
                .foregroundStyle(zoneColor)
                .frame(width: 26)
            Circle()
                .fill(member.isMe ? palette.accent : Brand.cardRaised)
                .frame(width: 34, height: 34)
                .overlay(Text(String(member.name.prefix(1))).font(.subheadline.weight(.bold))
                    .foregroundStyle(member.isMe ? .black : .white))
            Text(member.isMe ? "\(member.name) (toi)" : member.name)
                .font(member.isMe ? .headline : .body)
            Spacer()
            Text(Format.xp(member.xp)).font(.subheadline.monospacedDigit().weight(.semibold))
        }
        .padding(.vertical, 12)
        .background(member.isMe ? palette.accentSoft.opacity(0.6) : .clear)
    }

    private var zoneColor: Color {
        switch zone {
        case .promotion: return Brand.success
        case .relegation: return Brand.danger
        case .safe: return Brand.textSecondary
        }
    }
}
