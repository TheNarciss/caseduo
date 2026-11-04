import CaseDuoCore
import SwiftUI

/// The cadrage à domicile answer: five slides, each a title-message and three to five lines.
/// Graded like a presentation.
struct SlidesEditor: View {
    @Binding var slides: [SlideDraft]
    @Environment(\.palette) private var palette

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Text("Cinq slides : un titre-message qui dit la conclusion, puis trois à cinq lignes qui la prouvent.")
                    .font(.subheadline)
                    .foregroundStyle(Brand.textSecondary)
                ForEach($slides) { $slide in
                    SlideCard(slide: $slide, number: slide.id + 1)
                }
                let ready = slides.filter(\.isComplete).count
                Label("\(ready)/5 slides prêtes", systemImage: ready == 5 ? "checkmark.circle.fill" : "circle.dashed")
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(ready == 5 ? Brand.success : palette.accent)
            }
            .padding(16)
        }
        .scrollDismissesKeyboard(.interactively)
    }
}

private struct SlideCard: View {
    @Binding var slide: SlideDraft
    let number: Int

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Text("Slide \(number)").font(.caption.weight(.bold)).foregroundStyle(Brand.textSecondary)
                Spacer()
                if let issue = slide.issue {
                    Text(issue).font(.caption).foregroundStyle(Brand.danger)
                } else {
                    Image(systemName: "checkmark.circle.fill").foregroundStyle(Brand.success)
                }
            }
            TextField("Titre-message", text: $slide.title, axis: .vertical)
                .font(.headline)
                .lineLimit(1...3)
            ForEach(slide.lines.indices, id: \.self) { index in
                HStack(alignment: .firstTextBaseline, spacing: 8) {
                    Text("•").foregroundStyle(Brand.flame)
                    TextField("Ligne \(index + 1)", text: Binding(
                        get: { slide.lines[safe: index] ?? "" },
                        set: { if slide.lines.indices.contains(index) { slide.lines[index] = $0 } }
                    ), axis: .vertical)
                    .lineLimit(1...4)
                }
                .font(.subheadline)
            }
            HStack {
                if slide.lines.count < 5 {
                    Button { slide.lines.append("") } label: { Label("Ligne", systemImage: "plus") }
                }
                if slide.lines.count > 3 {
                    Button { slide.lines.removeLast() } label: { Label("Retirer", systemImage: "minus") }
                }
            }
            .font(.caption.weight(.semibold))
            .buttonStyle(.borderless)
        }
        .padding(14)
        .card(radius: 16)
    }
}
