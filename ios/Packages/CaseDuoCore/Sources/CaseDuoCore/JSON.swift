import Foundation

/// The JSON settings shared by every call: snake_case on the wire, camelCase in Swift, ISO 8601
/// instants with or without fractional seconds (Python writes six digits, Swift reads three).
public enum CaseDuoJSON {
    public static var decoder: JSONDecoder {
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .custom { decoder in
            let container = try decoder.singleValueContainer()
            let text = try container.decode(String.self)
            guard let date = ISODate.parse(text) else {
                throw DecodingError.dataCorruptedError(
                    in: container, debugDescription: "Date ISO 8601 illisible : \(text)")
            }
            return date
        }
        return decoder
    }

    public static var encoder: JSONEncoder {
        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        encoder.dateEncodingStrategy = .custom { date, encoder in
            var container = encoder.singleValueContainer()
            try container.encode(ISODate.format(date))
        }
        return encoder
    }
}

/// ISO 8601 instants as the backend writes them (`2026-11-04T08:00:00.123456+00:00`).
public enum ISODate {
    public static func parse(_ text: String) -> Date? {
        let normalized = normalizeFraction(text)
        let withFraction = ISO8601DateFormatter()
        withFraction.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        if let date = withFraction.date(from: normalized) { return date }
        let plain = ISO8601DateFormatter()
        plain.formatOptions = [.withInternetDateTime]
        if let date = plain.date(from: normalized) { return date }
        // A bare day ("2026-11-04"): midnight UTC.
        let day = ISO8601DateFormatter()
        day.formatOptions = [.withFullDate]
        return day.date(from: text)
    }

    public static func format(_ date: Date) -> String {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime]
        return formatter.string(from: date)
    }

    /// Fractional seconds cut or padded to three digits, the precision Foundation reads everywhere.
    static func normalizeFraction(_ text: String) -> String {
        guard let dot = text.firstIndex(of: ".") else { return text }
        let afterDot = text.index(after: dot)
        var end = afterDot
        while end < text.endIndex, text[end].isNumber { end = text.index(after: end) }
        let digits = String(text[afterDot..<end])
        guard !digits.isEmpty else { return text }
        let three = String((digits + "000").prefix(3))
        return String(text[..<afterDot]) + three + String(text[end...])
    }
}
