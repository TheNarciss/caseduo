"""Incremental parser for the grader's three tagged sections.

The model writes `<scores>{json}</scores><feedback>markdown</feedback>
<follow_up>question</follow_up>` (prompts/grade.md, DEVIATIONS D12). Text
arrives in arbitrary chunks; this turns it into events as early as possible:
the scores the moment `</scores>` closes, the feedback chunk by chunk, the
follow-up when its tag closes.
"""

from __future__ import annotations

from dataclasses import dataclass

TAGS = ("scores", "feedback", "follow_up")


@dataclass
class Event:
    kind: str  # "scores" | "feedback" | "follow_up"
    text: str


class TaggedStreamParser:
    def __init__(self) -> None:
        self._buffer = ""
        self._current: str | None = None
        self._section = ""
        self.sections: dict[str, str] = {}

    def feed(self, chunk: str) -> list[Event]:
        self._buffer += chunk
        events: list[Event] = []
        while True:
            if self._current is None:
                opened = self._find_open()
                if opened is None:
                    # keep a tail that could be the start of a tag
                    keep = max(len(f"<{t}>") for t in TAGS)
                    self._buffer = self._buffer[-keep:]
                    return events
                tag, start = opened
                self._buffer = self._buffer[start + len(f"<{tag}>") :]
                self._current, self._section = tag, ""
                continue
            close = f"</{self._current}>"
            idx = self._buffer.find(close)
            if idx < 0:
                safe = len(self._buffer) - len(close)
                if safe > 0:
                    piece = self._buffer[:safe]
                    self._buffer = self._buffer[safe:]
                    self._section += piece
                    if self._current == "feedback" and piece:
                        events.append(Event("feedback", piece))
                return events
            piece = self._buffer[:idx]
            self._section += piece
            self._buffer = self._buffer[idx + len(close) :]
            if self._current == "feedback":
                if piece:
                    events.append(Event("feedback", piece))
            else:
                events.append(Event(self._current, self._section.strip()))
            self.sections[self._current] = self._section.strip()
            self._current, self._section = None, ""

    def close(self) -> list[Event]:
        """End of stream: an unclosed section is taken as is."""
        events: list[Event] = []
        if self._current is not None:
            rest = self._section + self._buffer
            if self._current == "feedback":
                tail = self._buffer
                if tail:
                    events.append(Event("feedback", tail))
            else:
                events.append(Event(self._current, rest.strip()))
            self.sections[self._current] = rest.strip()
            self._current, self._buffer, self._section = None, "", ""
        return events

    def _find_open(self) -> tuple[str, int] | None:
        found = [(self._buffer.find(f"<{t}>"), t) for t in TAGS]
        found = [(i, t) for i, t in found if i >= 0]
        if not found:
            return None
        i, t = min(found)
        return t, i


def parse_complete(text: str) -> dict[str, str]:
    """All sections of a complete answer (non-streaming path, tests)."""
    parser = TaggedStreamParser()
    parser.feed(text)
    parser.close()
    return parser.sections
