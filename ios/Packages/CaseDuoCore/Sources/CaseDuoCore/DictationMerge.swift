import Foundation

/// How dictation keeps what was said: the recogniser rewrites the current utterance with each
/// result, and after a silence starts a new one whose text no longer contains the previous
/// words. The previous utterance must then be committed before the new text replaces it.
public enum DictationMerge {
    /// Whether `text` (starting at `start` seconds into the audio) is a new utterance, not a
    /// rewrite of `previous` (which started at `previousStart`).
    ///
    /// If the new text still carries the previous words (same beginning, or the previous
    /// ending somewhere inside it), it is a rewrite, whatever the clock says: committing it
    /// would say the sentence twice. Otherwise two signs: the first segment's timestamp moved
    /// (a new utterance begins later in the audio, or the clock reset), or the text shrank to
    /// less than half (a correction rewrites a few words, never most of them).
    public static func isNewUtterance(previous: String, previousStart: TimeInterval?,
                                      text: String, start: TimeInterval?) -> Bool {
        guard !previous.isEmpty, !text.isEmpty else { return false }
        let before = previous.lowercased()
        let now = text.lowercased()
        let head = String(before.prefix(8))
        let tail = String(before.suffix(12))
        if now.hasPrefix(head) || now.contains(tail) || before.hasPrefix(String(now.prefix(8))) { return false }
        if let previousStart, let start, abs(start - previousStart) > 1.0 { return true }
        return text.count * 2 < previous.count
    }

    /// `committed` plus the current utterance, with a single space between them.
    public static func join(committed: String, partial: String) -> String {
        guard !partial.isEmpty else { return committed }
        guard !committed.isEmpty else { return partial }
        return committed.hasSuffix(" ") || committed.hasSuffix("\n") ? committed + partial : committed + " " + partial
    }
}
