"""
Subtitle timing and ASS generation.

Subtitles are built from the TTS engine's own word boundaries, so a word
lights up on the frame it is spoken. The previous approach — dividing the
total audio duration evenly across words — drifted by a second or more by the
end of a 20-second clip, which is exactly where the call to action sits.

ASS rather than SRT: ffmpeg renders SRT at a default PlayRes of 384x288, so
every pixel value in force_style gets scaled ~6.7x and a 420px bottom margin
lands off-frame on a 1920px canvas.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable, Optional

from config.settings import settings

_PUNCT = ".,!?;:—–\"'()«»…"
_SENTENCE_END = re.compile(r"[.!?…]$")


@dataclass
class WordTiming:
    word: str
    start: float
    duration: float
    is_highlight: bool = False

    @property
    def end(self) -> float:
        return self.start + self.duration


@dataclass
class SubtitleTrack:
    word_timings: list[WordTiming] = field(default_factory=list)
    total_duration: float = 0.0


@dataclass
class Cue:
    """A group of words shown together, one of which is active at a time."""
    words: list[WordTiming]

    @property
    def start(self) -> float:
        return self.words[0].start

    @property
    def end(self) -> float:
        return self.words[-1].end


def normalise(word: str) -> str:
    return word.strip(_PUNCT).strip().lower()


def build_cues(
    words: Iterable[WordTiming],
    max_words: Optional[int] = None,
    max_gap: float = 0.45,
) -> list[Cue]:
    """Split a word stream into on-screen groups.

    Breaks on three signals, in priority order: end of sentence, a pause
    longer than `max_gap` (the speaker took a breath — so should the text),
    and the word cap.
    """
    max_words = settings.subtitle_words_per_chunk if max_words is None else max_words
    cues: list[Cue] = []
    current: list[WordTiming] = []

    for word in words:
        if current:
            gap = word.start - current[-1].end
            sentence_over = bool(_SENTENCE_END.search(current[-1].word))
            if sentence_over or gap > max_gap or len(current) >= max_words:
                cues.append(Cue(words=current))
                current = []
        current.append(word)

    if current:
        cues.append(Cue(words=current))
    return cues


def _ass_color(hex_color: str) -> str:
    """#RRGGBB -> ASS &H00BBGGRR."""
    h = hex_color.lstrip("#")
    r, g, b = h[0:2], h[2:4], h[4:6]
    return f"&H00{b}{g}{r}".upper()


def _ass_time(seconds: float) -> str:
    seconds = max(0.0, seconds)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:d}:{m:02d}:{s:05.2f}"


def _escape(text: str) -> str:
    return (text.replace("\\", "\\\\")
                .replace("{", "\\{")
                .replace("}", "\\}")
                .replace("\n", " ")
                .strip())


def render_ass(
    words: list[WordTiming],
    total_duration: float,
    max_words: Optional[int] = None,
) -> str:
    """Render karaoke-style ASS: the whole group visible, active word lit."""
    W, H = settings.video_width, settings.video_height
    fs = settings.subtitle_font_size
    main = _ass_color(settings.subtitle_main_color)
    hl = _ass_color(settings.subtitle_highlight_color)

    header = (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        f"PlayResX: {W}\n"
        f"PlayResY: {H}\n"
        "ScaledBorderAndShadow: yes\n"
        "WrapStyle: 0\n"
        "YCbCr Matrix: TV.709\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Default,{settings.subtitle_font},{fs},{main},{main},"
        f"&H00000000,&HB0000000,-1,0,0,0,100,100,0,0,1,6,4,2,"
        f"120,120,{settings.subtitle_margin_v},204\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, "
        "MarginV, Effect, Text\n"
    )

    lines: list[str] = []
    for cue in build_cues(words, max_words=max_words):
        n = len(cue.words)
        for i, word in enumerate(cue.words):
            start = word.start
            # Hold the group on screen until the next word starts so there
            # is never a one-frame gap between events.
            end = cue.words[i + 1].start if i + 1 < n else min(cue.end + 0.12,
                                                               total_duration)
            if end <= start:
                continue

            rendered = []
            for j, other in enumerate(cue.words):
                text = _escape(other.word)
                if not text:
                    continue
                if j == i:
                    # Active word is always lit; a keyword gets extra size.
                    scale = 118 if word.is_highlight else 108
                    rendered.append(
                        f"{{\\c{hl}\\fscx{scale}\\fscy{scale}}}{text}{{\\r}}"
                    )
                else:
                    rendered.append(text)

            body = " ".join(rendered)
            if i == 0:
                body = "{\\fad(90,0)}" + body
            lines.append(
                f"Dialogue: 0,{_ass_time(start)},{_ass_time(end)},"
                f"Default,,0,0,0,,{body}"
            )

    return header + "\n".join(lines) + "\n"


class SubtitleTimingGenerator:
    """Builds a word track, preferring real TTS boundaries over estimates."""

    def from_speech(
        self,
        words: list,
        total_duration: float,
        highlight_words: Optional[list[str]] = None,
    ) -> SubtitleTrack:
        """Convert TTS SpokenWord objects (already globally offset)."""
        highlights = {normalise(w) for w in (highlight_words or []) if w.strip()}
        track = SubtitleTrack(total_duration=total_duration)
        for w in words:
            text = getattr(w, "text", None) or getattr(w, "word", "")
            track.word_timings.append(WordTiming(
                word=text,
                start=w.start,
                duration=w.duration,
                is_highlight=normalise(text) in highlights,
            ))
        return track

    def generate(
        self,
        text: str,
        audio_duration: float,
        highlight_words: Optional[list[str]] = None,
        words_per_chunk: int = 2,
    ) -> SubtitleTrack:
        """Even-split estimate — only used when no boundaries are available."""
        highlights = {normalise(w) for w in (highlight_words or []) if w.strip()}
        words = text.split()
        if not words:
            return SubtitleTrack()

        # Weight by characters so long words are not rushed.
        lengths = [max(1, len(w)) for w in words]
        total_chars = sum(lengths)
        track = SubtitleTrack(total_duration=audio_duration)
        cursor = 0.0
        for word, length in zip(words, lengths):
            dur = audio_duration * length / total_chars
            track.word_timings.append(WordTiming(
                word=word,
                start=cursor,
                duration=dur,
                is_highlight=normalise(word) in highlights,
            ))
            cursor += dur
        return track

    def estimate_word_durations(
        self, text: str, audio_duration: float
    ) -> list[float]:
        words = text.split()
        if not words:
            return []
        char_counts = [len(w) for w in words]
        total_chars = sum(char_counts)
        if total_chars == 0:
            return [audio_duration / len(words)] * len(words)
        return [(c / total_chars) * audio_duration for c in char_counts]
