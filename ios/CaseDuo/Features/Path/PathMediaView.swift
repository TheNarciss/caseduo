import CaseDuoCore
import SwiftUI

/// The small chart, table or tree an item carries, drawn from its data: a few bars, a line, a
/// grid, a root with its branches. Nothing to download.
struct PathMediaView: View {
    let media: PathMedia
    var tint: Color = Brand.flame

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            if let title = media.title {
                Text(title).font(.subheadline.weight(.bold))
            }
            switch media.type {
            case "bar": bars
            case "line": line
            case "table": table
            case "tree": tree
            default: Text("(\(media.type))").font(.caption).foregroundStyle(Brand.textTertiary)
            }
            if let unit = media.unit, media.type == "bar" || media.type == "line" {
                Text(unit).font(.caption2).foregroundStyle(Brand.textTertiary)
            }
        }
        .padding(14)
        .card(radius: 16)
        .accessibilityElement(children: .combine)
        .accessibilityLabel(spoken)
    }

    private var categories: [String] { media.categories ?? [] }
    private var series: [PathMedia.Series] { media.series ?? [] }
    private var maxValue: Double { max(1e-9, series.flatMap(\.values).max() ?? 1) }
    private var seriesColors: [Color] { [tint, Brand.marketSizing, Brand.cadrage, Brand.diagnostic] }

    // MARK: Bars

    private var bars: some View {
        VStack(spacing: 8) {
            HStack(alignment: .bottom, spacing: 8) {
                ForEach(Array(categories.enumerated()), id: \.offset) { index, category in
                    VStack(spacing: 4) {
                        HStack(alignment: .bottom, spacing: 3) {
                            ForEach(Array(series.enumerated()), id: \.offset) { s, serie in
                                let value = serie.values[safe: index] ?? 0
                                VStack(spacing: 2) {
                                    Text(Format.number(value))
                                        .font(.system(size: 9, weight: .semibold).monospacedDigit())
                                        .foregroundStyle(Brand.textSecondary)
                                        .lineLimit(1)
                                        .minimumScaleFactor(0.6)
                                    RoundedRectangle(cornerRadius: 4, style: .continuous)
                                        .fill(seriesColors[s % seriesColors.count].opacity(0.9))
                                        .frame(height: max(3, 90 * value / maxValue))
                                }
                            }
                        }
                        Text(category)
                            .font(.caption2)
                            .foregroundStyle(Brand.textSecondary)
                            .lineLimit(2)
                            .multilineTextAlignment(.center)
                            .minimumScaleFactor(0.7)
                    }
                    .frame(maxWidth: .infinity)
                }
            }
            if series.count > 1 { legend }
        }
    }

    private var legend: some View {
        HStack(spacing: 10) {
            ForEach(Array(series.enumerated()), id: \.offset) { s, serie in
                HStack(spacing: 4) {
                    Circle().fill(seriesColors[s % seriesColors.count]).frame(width: 7, height: 7)
                    Text(serie.name).font(.caption2).foregroundStyle(Brand.textSecondary)
                }
            }
        }
    }

    // MARK: Line

    private var line: some View {
        VStack(spacing: 6) {
            GeometryReader { geo in
                let w = geo.size.width
                let h = geo.size.height
                ForEach(Array(series.enumerated()), id: \.offset) { s, serie in
                    let n = max(1, serie.values.count - 1)
                    Path { p in
                        for (i, v) in serie.values.enumerated() {
                            let point = CGPoint(x: w * CGFloat(i) / CGFloat(n), y: h - h * CGFloat(v / maxValue))
                            if i == 0 { p.move(to: point) } else { p.addLine(to: point) }
                        }
                    }
                    .stroke(seriesColors[s % seriesColors.count], style: StrokeStyle(lineWidth: 2.5, lineCap: .round, lineJoin: .round))
                    ForEach(Array(serie.values.enumerated()), id: \.offset) { i, v in
                        Circle()
                            .fill(seriesColors[s % seriesColors.count])
                            .frame(width: 6, height: 6)
                            .position(x: w * CGFloat(i) / CGFloat(n), y: h - h * CGFloat(v / maxValue))
                    }
                }
            }
            .frame(height: 90)
            .padding(.horizontal, 4)
            HStack {
                ForEach(Array(categories.enumerated()), id: \.offset) { i, c in
                    Text(c).font(.caption2).foregroundStyle(Brand.textSecondary).lineLimit(1).minimumScaleFactor(0.7)
                    if i < categories.count - 1 { Spacer(minLength: 0) }
                }
            }
            if series.count > 1 { legend }
        }
    }

    // MARK: Table

    private var table: some View {
        let header = media.header ?? []
        let rows = media.rows ?? []
        return Grid(alignment: .leading, horizontalSpacing: 10, verticalSpacing: 6) {
            if !header.isEmpty {
                GridRow {
                    ForEach(Array(header.enumerated()), id: \.offset) { _, h in
                        Text(h).font(.caption.weight(.bold)).foregroundStyle(Brand.textSecondary)
                    }
                }
                Divider().overlay(Brand.stroke)
            }
            ForEach(Array(rows.enumerated()), id: \.offset) { _, row in
                GridRow {
                    ForEach(Array(row.enumerated()), id: \.offset) { i, cell in
                        Text(cell)
                            .font(i == 0 ? .caption.weight(.semibold) : .caption.monospacedDigit())
                            .lineLimit(2)
                            .minimumScaleFactor(0.8)
                    }
                }
            }
        }
    }

    // MARK: Tree

    private var tree: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(media.root ?? "")
                .font(.subheadline.weight(.bold))
                .padding(.horizontal, 12).padding(.vertical, 8)
                .background(tint.opacity(0.18), in: RoundedRectangle(cornerRadius: 10, style: .continuous))
            ForEach(Array((media.children ?? []).enumerated()), id: \.offset) { _, child in
                HStack(spacing: 8) {
                    Rectangle().fill(Brand.stroke).frame(width: 2, height: 22).padding(.leading, 14)
                    Text(child)
                        .font(.caption.weight(child == "?" ? .heavy : .regular))
                        .foregroundStyle(child == "?" ? tint : .white)
                        .padding(.horizontal, 10).padding(.vertical, 6)
                        .background(child == "?" ? tint.opacity(0.14) : Brand.cardRaised,
                                    in: RoundedRectangle(cornerRadius: 8, style: .continuous))
                }
            }
        }
    }

    private var spoken: String {
        var parts: [String] = [media.title ?? media.type]
        if let unit = media.unit { parts.append("en \(unit)") }
        for serie in series {
            parts.append(serie.name + " : " + zip(categories, serie.values).map { "\($0) \(Format.number($1))" }.joined(separator: ", "))
        }
        if let rows = media.rows { parts.append(rows.map { $0.joined(separator: " ") }.joined(separator: "; ")) }
        if let root = media.root { parts.append(root + " : " + (media.children ?? []).joined(separator: ", ")) }
        return parts.joined(separator: ". ")
    }
}

/// Tiles that wrap onto the next line, like words in a sentence.
struct FlowLayout: Layout {
    var spacing: CGFloat = 8

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        let width = proposal.width ?? 360
        return place(in: width, subviews: subviews).size
    }

    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        let result = place(in: bounds.width, subviews: subviews)
        for (subview, point) in zip(subviews, result.points) {
            subview.place(at: CGPoint(x: bounds.minX + point.x, y: bounds.minY + point.y), proposal: .unspecified)
        }
    }

    private func place(in width: CGFloat, subviews: Subviews) -> (size: CGSize, points: [CGPoint]) {
        var points: [CGPoint] = []
        var x: CGFloat = 0
        var y: CGFloat = 0
        var rowHeight: CGFloat = 0
        var maxX: CGFloat = 0
        for subview in subviews {
            let size = subview.sizeThatFits(.unspecified)
            if x > 0, x + size.width > width {
                x = 0
                y += rowHeight + spacing
                rowHeight = 0
            }
            points.append(CGPoint(x: x, y: y))
            x += size.width + spacing
            rowHeight = max(rowHeight, size.height)
            maxX = max(maxX, x - spacing)
        }
        return (CGSize(width: maxX, height: y + rowHeight), points)
    }
}
