import CaseDuoCore
import SwiftUI

/// Earned badges in colour, the others greyed out with what it takes.
struct BadgesView: View {
    @Environment(AppModel.self) private var model
    @Environment(\.palette) private var palette
    @State private var badges: [Badge] = []
    @State private var loaded = false

    var body: some View {
        ScrollView {
            LazyVGrid(columns: [GridItem(.adaptive(minimum: 104), spacing: 12)], spacing: 12) {
                ForEach(badges) { badge in
                    let earned = badge.earnedAt != nil
                    VStack(spacing: 8) {
                        Image(systemName: badge.symbol ?? "rosette")
                            .font(.system(size: 30, weight: .bold))
                            .foregroundStyle(earned ? AnyShapeStyle(palette.linear) : AnyShapeStyle(Brand.textTertiary))
                            .frame(width: 58, height: 58)
                            .background((earned ? palette.accentSoft : Color.white.opacity(0.05)), in: Circle())
                        Text(badge.name).font(.subheadline.weight(.semibold)).multilineTextAlignment(.center)
                        if let description = badge.description {
                            Text(description).font(.caption2).foregroundStyle(Brand.textSecondary)
                                .multilineTextAlignment(.center).lineLimit(3)
                        }
                    }
                    .padding(12)
                    .frame(maxWidth: .infinity, minHeight: 170, alignment: .top)
                    .card(radius: 16)
                    .opacity(earned ? 1 : 0.6)
                    .accessibilityElement(children: .combine)
                    .accessibilityLabel("\(badge.name), \(earned ? "obtenu" : "à obtenir")")
                }
            }
            .padding(16)
            if loaded && badges.isEmpty {
                Text("Pas encore de badge.").foregroundStyle(Brand.textSecondary)
            } else if !loaded {
                LoadingView().frame(height: 300)
            }
        }
        .background(Brand.background)
        .navigationTitle("Badges")
        .task {
            do { badges = try await model.service.badges() } catch { model.handle(error) }
            loaded = true
        }
    }
}
