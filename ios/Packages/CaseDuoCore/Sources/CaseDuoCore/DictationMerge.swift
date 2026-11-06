import Foundation

/// How dictation keeps what was said: the recogniser rewrites the current utterance with each
/// result, and after a silence starts a new one whose text no longer contains the previous
/// words. The previous utterance must then be committed before the new text replaces it.
public enum DictationMerge {
    /// Whether `text` (starting at `start` seconds into the audio) is a new utterance, not a
    /// rewrite of `previous` (which started at `previousStart`).
    ///
    /// A rewrite keeps the beginning of what was there, or still carries its ending: then it is
    /// never a new utterance, whatever the clock says (committing it would say the sentence
    /// twice). Otherwise the signs of a restart: the first segment's timestamp moved (a new
    /// utterance begins later in the audio, or the clock reset), or the text shrank to half or
    /// less (a correction rewrites a few words, never most of them; a new sentence starts with
    /// one or two).
    public static func isNewUtterance(previous: String, previousStart: TimeInterval?,
                                      text: String, start: TimeInterval?) -> Bool {
        guard !previous.isEmpty, !text.isEmpty else { return false }
        let before = previous.lowercased()
        let now = text.lowercased()
        if now.hasPrefix(String(before.prefix(8))) { return false }
        if now.count >= 8, before.hasPrefix(String(now.prefix(8))) { return false }
        if before.count >= 12, now.contains(String(before.suffix(12))) { return false }
        if let previousStart, let start, abs(start - previousStart) > 1.0 { return true }
        let beforeWords = before.split(separator: " ").count
        let nowWords = now.split(separator: " ").count
        if beforeWords >= 3, nowWords * 2 <= beforeWords { return true }
        return text.count * 2 < previous.count
    }

    /// `committed` plus the current utterance, with a single space between them.
    public static func join(committed: String, partial: String) -> String {
        guard !partial.isEmpty else { return committed }
        guard !committed.isEmpty else { return partial }
        return committed.hasSuffix(" ") || committed.hasSuffix("\n") ? committed + partial : committed + " " + partial
    }
}
