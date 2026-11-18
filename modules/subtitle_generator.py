"""
Subtitle Generator Module
Generates SRT and ASS (Advanced SubStation Alpha) subtitles with word-by-word dynamic karaoke highlighting,
full Hindi Unicode (Devanagari) support, and safe-zone positioning tailored for YouTube Shorts.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass
from modules.voice_generator import TimedWord
from config import config

logger = logging.getLogger("gta6_agent.subtitles")


class SubtitleGenerator:
    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = Path(output_dir or config.ASSETS_DIR / "subtitles")
        os.makedirs(self.output_dir, exist_ok=True)

    def _format_srt_time(self, seconds: float) -> str:
        """Format seconds to SRT timecode 00:00:00,000"""
        hrs = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int(round((seconds - int(seconds)) * 1000))
        return f"{hrs:02d}:{mins:02d}:{secs:02d},{millis:03d}"

    def _format_ass_time(self, seconds: float) -> str:
        """Format seconds to ASS timecode 0:00:00.00"""
        hrs = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        centis = int(round((seconds - int(seconds)) * 100))
        return f"{hrs}:{mins:02d}:{secs:02d}.{centis:02d}"

    def generate_srt(
        self, timed_words: List[TimedWord], clip_id: int, words_per_chunk: int = 4
    ) -> Path:
        """
        Generate standard SRT subtitles chunked into punchy 3-5 word groups.
        """
        srt_path = self.output_dir / f"clip_{clip_id}.srt"
        if not timed_words:
            # Empty SRT
            srt_path.write_text("", encoding="utf-8")
            return srt_path

        chunks = []
        for i in range(0, len(timed_words), words_per_chunk):
            chunk = timed_words[i : i + words_per_chunk]
            start_t = chunk[0].start
            end_t = chunk[-1].end
            text = " ".join(w.word for w in chunk)
            chunks.append((start_t, end_t, text))

        lines = []
        for idx, (s, e, text) in enumerate(chunks, start=1):
            lines.append(f"{idx}")
            lines.append(f"{self._format_srt_time(s)} --> {self._format_srt_time(e)}")
            lines.append(f"{text}\n")

        content = "\n".join(lines)
        srt_path.write_text(content, encoding="utf-8")
        logger.info(f"Generated SRT subtitles at {srt_path.name}")
        return srt_path

    def generate_ass_karaoke(
        self,
        timed_words: List[TimedWord],
        clip_id: int,
        words_per_group: int = 4,
        font_name: str = "Arial",
    ) -> Path:
        """
        Generate ASS subtitle file with animated word-level highlighting (Karaoke style).
        Uses bright yellow highlighting for the spoken word and crisp white for remaining words.
        Centered horizontally at 72% height (Shorts safe-zone).
        """
        ass_path = self.output_dir / f"clip_{clip_id}.ass"

        # ASS Header with YouTube Shorts 1080x1920 layout and high-visibility styling
        header = f"""[Script Info]
Title: GTA 6 Shorts Dynamic Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.601
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: ShortsDefault,{font_name},72,&H00FFFFFF,&H0000FFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,5,4,2,40,40,480,1
Style: ShortsActive,{font_name},76,&H0000FFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,105,105,0,0,1,6,5,2,40,40,480,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        dialogue_lines = []

        if timed_words:
            # Group into small readable phrases
            for i in range(0, len(timed_words), words_per_group):
                group = timed_words[i : i + words_per_group]
                # For each word in the group, create a highlighted sub-frame
                for active_idx, target_word in enumerate(group):
                    start_t = self._format_ass_time(target_word.start)
                    end_t = self._format_ass_time(target_word.end)

                    # Build text where target_word is highlighted yellow, others are white
                    parts = []
                    for w_idx, w in enumerate(group):
                        if w_idx == active_idx:
                            # Highlighted yellow with slight zoom: {\c&H0000FFFF&}
                            parts.append(f"{{\\c&H0000FFFF&\\b1}}{w.word}{{\\r}}")
                        else:
                            parts.append(f"{{\\c&H00FFFFFF&}}{w.word}{{\\r}}")

                    phrase = " ".join(parts)
                    dialogue_lines.append(
                        f"Dialogue: 0,{start_t},{end_t},ShortsDefault,,0,0,0,,{phrase}"
                    )

        full_ass = header + "\n".join(dialogue_lines) + "\n"
        ass_path.write_text(full_ass, encoding="utf-8")
        logger.info(f"Generated ASS karaoke subtitles at {ass_path.name}")
        return ass_path


subtitle_generator = SubtitleGenerator()
