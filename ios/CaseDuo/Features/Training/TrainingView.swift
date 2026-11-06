import CaseDuoCore
import SwiftUI

/// Entraîner: the bonus pack and the past days' leftovers, by category, outside the day's plan
/// (D16). Filter by family, see what is done and with what score, pick anything.
struct TrainingView: View {
    @Environment(AppModel.self) private var model
    @Environment(\.palette) private var palette
    @State private var training: Training?
    @State private var error: String?
    @State private var selected: ExerciseType?
    @State private var hideDone = false

    var body: some View {
        @Bindable var model = model
        NavigationStack(path: $model.trainingPath) {
            ScrollView {
                VStack(alignment: .leading, spacing: 14) {
                    if let training {
                        content(training)
                    } else if let error {
                        ErrorBanner(message: error)
                    } else {
                        LoadingView(message: "Chargement des exercices…").frame(height: 400)
                    }
                }
                .padding(.horizontal, 16)
                .padding(.bottom, 24)
                .containerRelativeFrame(.horizontal)  // exactly the screen width: no sideways panning
            }
            .background(Brand.background)
            .navigationTitle("Entraîner")
            .refreshable { await load() }
            .task { if training == nil { await load() } }
            .onChange(of: model.trainingVersion) { _, _ in Task { await load() } }
            .routeDestinations()
        }
        .environment(\.pushRoute, { model.trainingPath.append($0) })
    }

    private func load() async {
        do {
            training = try await model.service.training()
            error = nil
        } catch {
            model.handle(error)
            self.error = error.localizedDescription
        }
    }

    @ViewBuilder
    private func content(_ training: Training) -> some View {
        let total = training.exercises.count
        let done = training.exercises.filter(\.done).count
        HStack(alignment: .firstTextBaseline) {
            Text("\(total - done) à faire").font(.title3.weight(.bold))
            Text("· \(done) fait\(done > 1 ? "s" : "")").font(.subheadline).foregroundStyle(Brand.textSecondary)
            Spacer()
            Toggle(isOn: $hideDone) { Text("Masquer les faits").font(.caption) }
                .toggleStyle(.button)
                .buttonStyle(.plain)
                .foregroundStyle(hideDone ? palette.accent : Brand.textSecondary)
        }
        .padding(.top, 4)

        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                filter(nil, label: "Tout", count: total - done, tint: palette.accent)
                ForEach(training.types) { type in
                    filter(type.type, label: type.label, count: type.total - type.done, tint: Brand.color(for: type.type))
                }
            }
        }

        let visible = training.exercises.filter { card in
            (selected == nil || card.type == selected) && !(hideDone && card.done)
        }
        if visible.isEmpty {
            VStack(spacing: 10) {
                FlameMascot(mood: .proud, size: 90)
                Text(training.exercises.isEmpty ? "Le pack bonus arrive avec le prochain déploiement." : "Tout est fait ici. Bien joué.")
                    .foregroundStyle(Brand.textSecondary)
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, 40)
        } else {
            ForEach(training.types.map(\.type), id: \.self) { type in
                let cards = visible.filter { $0.type == type }
                if !cards.isEmpty {
                    SectionHeader(title: type.label, symbol: type.symbol, tint: Brand.color(for: type),
                                  done: cards.filter(\.done).count, total: cards.count)
                    ForEach(cards) { card in
                        NavigationLink(value: HomeRoute.exercise(id: card.exerciseId, revenge: false)) {
                            ExerciseCardView(card: card)
                        }
                        .buttonStyle(.plain)
                    }
                }
            }
        }
    }

    private func filter(_ type: ExerciseType?, label: String, count: Int, tint: Color) -> some View {
        let on = selected == type
        return Button {
            Haptics.shared.play(.tap)
            withAnimation(Brand.quick) { selected = type }
        } label: {
            HStack(spacing: 5) {
                Text(label)
                Text("\(count)").monospacedDigit().opacity(0.7)
            }
            .font(.caption.weight(.bold))
            .padding(.horizontal, 11)
            .padding(.vertical, 7)
            .foregroundStyle(on ? Color.black : tint)
            .background(on ? tint : tint.opacity(0.14), in: Capsule())
        }
        .buttonStyle(.plain)
    }
}

/// A section title with its family colour and a done count.
struct SectionHeader: View {
    let title: String
    let symbol: String
    let tint: Color
    let done: Int
    let total: Int
    var trailing: String?

    var body: some View {
        HStack(spacing: 8) {
            Image(systemName: symbol).font(.subheadline.weight(.bold)).foregroundStyle(tint)
            Text(title).font(.headline)
            Spacer()
            if let trailing {
                Text(trailing).font(.caption.weight(.semibold)).foregroundStyle(tint)
            }
            Text("\(done)/\(total)")
                .font(.caption.monospacedDigit().weight(.bold))
                .foregroundStyle(done == total ? Brand.success : Brand.textSecondary)
        }
        .padding(.top, 6)
        .accessibilityElement(children: .combine)
    }
}
