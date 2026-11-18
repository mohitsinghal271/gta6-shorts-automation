"""
Voice Generator Module
Generates engaging gaming commentary voiceovers in Hindi, English, and Hinglish.
Supports Edge-TTS neural voices when online with instantaneous offline fallback (Windows SAPI / synthetic timing)
and provides an option for gameplay-only audio.
"""

import os
import sys
import socket
import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from dataclasses import dataclass
from config import config

logger = logging.getLogger("gta6_agent.voice_generator")


def is_internet_available(host: str = "8.8.8.8", port: int = 53, timeout: float = 0.4) -> bool:
    """Fast check to verify if external network is reachable before calling cloud TTS."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            s.connect((host, port))
            return True
    except Exception:
        return False


@dataclass
class TimedWord:
    word: str
    start: float
    end: float


@dataclass
class VoiceoverResult:
    audio_path: Optional[Path]
    script_text: str
    language: str
    voice_name: str
    duration: float
    timed_words: List[TimedWord]
    is_silent: bool = False
    audio_status: str = "SUCCESS"


COMMENTARY_SCRIPTS = {
    "hindi": {
        "high_speed_chase": {
            "hook": "भाई ये GTA 6 की पुलिस बिल्कुल पागल हो चुकी है!",
            "body": "वाइस सिटी की सड़कों पर 200 की स्पीड में भागना आसान नहीं है। क्या हम बच पाएंगे?",
            "climax": "सामने बैरिकेड है और गाड़ियां ब्लास्ट हो रही हैं!",
            "outro": "क्या लगता है, क्या जेसन और लूसिया जेल से बच पाएंगे? कमेंट में बताओ!",
        },
        "car_crash_explosion": {
            "hook": "GTA 6 का नेक्स्ट-जेन क्रैश फिजिक्स देखकर आपके होश उड़ जाएंगे!",
            "body": "गाड़ी हवा में तीन बार पलटी और सीधा पेट्रोल पंप में जा घुसी!",
            "climax": "भाई ये ग्राफिक्स देखो, असली दुनिया से भी खतरनाक लग रहा है!",
            "outro": "अगर ये सीन तगड़ा लगा तो अभी सब्सक्राइब करो!",
        },
        "default": {
            "hook": "GTA 6 का सबसे खतरनाक मिशन फाइनली रिवील हो गया!",
            "body": "वाइस सिटी में लूसिया का यह स्टंट देखकर पुलिस भी दंग रह गई।",
            "climax": "लास्ट सेकंड में जो हुआ वो किसी ने नहीं सोचा था!",
            "outro": "GTA 6 का वेट कौन-कौन कर रहा है? सब्सक्राइब जरूर करना!",
        },
    },
    "english": {
        "high_speed_chase": {
            "hook": "The police AI in GTA 6 is absolutely insane!",
            "body": "We are flying through Vice City at 150 miles per hour and they won't stop chasing us.",
            "climax": "Look at the road block ahead, this is pure chaos!",
            "outro": "Will Lucia and Jason make it out alive? Drop your thoughts below!",
        },
        "car_crash_explosion": {
            "hook": "GTA 6 crash physics just blew my mind!",
            "body": "The vehicle flip and deformation is on a whole different level.",
            "climax": "Straight into the fuel tank and boom!",
            "outro": "Subscribe if you can't wait to play GTA 6 on day one!",
        },
        "default": {
            "hook": "You won't believe this insane moment in GTA 6!",
            "body": "Exploring the neon streets of Leonida when suddenly everything goes crazy.",
            "climax": "Watch closely what happens in the final seconds!",
            "outro": "Smash that subscribe button for daily GTA 6 clips!",
        },
    },
    "hinglish": {
        "high_speed_chase": {
            "hook": "Bhai GTA 6 ki police literally next level aggressive hai!",
            "body": "Vice City ke neon highways pe 180 ki speed aur 5-star wanted level!",
            "climax": "Barricade todte hi jo blast hua, epic scene ban gaya!",
            "outro": "Jason bachega ya busted hoga? Jaldi comment karo aur subscribe maaro!",
        },
        "car_crash_explosion": {
            "hook": "Bhai yeh crash physics dekh ke dimaag hil jayega!",
            "body": "Full speed car crash hui aur vehicle deformation itna realistic hai!",
            "climax": "Poori gaadi hawa mein ghoom ke blast ho gayi!",
            "outro": "GTA 6 ka gameplay kaisa laga? Subscribe karna mat bhoolna!",
        },
        "default": {
            "hook": "GTA 6 Vice City ka yeh crazy moment bilkul miss mat karna!",
            "body": "Lucia aur Jason ka yeh heist mission literally insane ban chuka hai.",
            "climax": "End tak dekho, scene poora twist hone wala hai!",
            "outro": "GTA 6 ke daily epic shorts ke liye subscribe karo!",
        },
    },
}


class VoiceGenerator:
    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = Path(output_dir or config.ASSETS_DIR / "voiceovers")
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_commentary_with_qwen(
        self,
        event_summary: str,
        why_entertaining: str,
        hook_text: str,
        language: str,
    ) -> Optional[str]:
        """
        Query local Qwen LLM for dynamic gaming commentary when Ollama backend is active.
        Falls back to template scripts if unreachable or slow.
        """
        try:
            import requests

            endpoint = getattr(
                getattr(config, "semantic", None),
                "vlm_endpoint",
                "http://localhost:11434/api/generate",
            )
            prompt = (
                f"You are an energetic gaming commentator for GTA 6 YouTube Shorts.\n"
                f"Language: {language}.\n"
                f"Event: {event_summary}.\n"
                f"Why Entertaining: {why_entertaining}.\n"
                f"Hook idea: {hook_text}.\n"
                f"Write a punchy, spoken commentary script under 45 words suitable for a 30-second Short.\n"
                f"Output ONLY the spoken commentary text."
            )
            payload = {
                "model": "qwen2.5:latest",
                "prompt": prompt,
                "stream": False,
            }
            conn_timeout = getattr(getattr(config, "semantic", None), "connect_timeout_seconds", 5.0)
            infer_timeout = getattr(getattr(config, "semantic", None), "inference_timeout_seconds", 60.0)
            resp = requests.post(endpoint, json=payload, timeout=(conn_timeout, infer_timeout))
            if resp.status_code == 200:
                text = resp.json().get("response", "").strip()
                if len(text) > 20:
                    return text
        except Exception:
            pass
        return None

    def assemble_script(
        self,
        language: str,
        tags: List[str],
        semantic_info: Optional[Dict[str, Any]] = None,
        is_fallback: bool = False,
    ) -> str:
        # Check if fallback is signaled
        fallback = is_fallback
        if not fallback and semantic_info:
            if isinstance(semantic_info, dict):
                fallback = bool(semantic_info.get("is_fallback", False))
            else:
                fallback = bool(getattr(semantic_info, "is_fallback", False))

        if fallback:
            # Factual, neutral commentary without fabricating events
            if language == "hindi":
                return "GTA 6 वाइस सिटी का यह शानदार गेमप्ले सीन देखिए। बेहतरीन ग्राफिक्स और एक्शन मोमेंट। GTA 6 से जुड़े अपडेट्स के लिए सब्सक्राइब जरूर करें!"
            elif language == "english":
                return "Check out this gameplay sequence from GTA 6 in Vice City. Take in the dynamic action and atmosphere. Subscribe for more GTA 6 gameplay!"
            else:  # hinglish
                return "GTA 6 Vice City ka yeh gameplay scene dekho. Dynamic action aur graphics truly next level hain. Aise hi GTA 6 videos ke liye subscribe karo!"

        # Contextual semantic commentary generation when event summary is available
        if semantic_info:
            def _extract_field(key: str, alt_key: Optional[str] = None) -> str:
                if isinstance(semantic_info, dict):
                    val = semantic_info.get(key) or (semantic_info.get(alt_key) if alt_key else None)
                elif hasattr(semantic_info, "to_dict"):
                    d = semantic_info.to_dict()
                    val = d.get(key) or (d.get(alt_key) if alt_key else None)
                else:
                    val = getattr(semantic_info, key, None) or (getattr(semantic_info, alt_key, None) if alt_key else None)
                return str(val or "").strip()

            event_summary = _extract_field("event_summary")
            why_ent = _extract_field("why_entertaining", "entertainment_value")
            hook_text = _extract_field("suggested_hook")

            if event_summary:
                # Try local Qwen LLM first
                llm_script = self.generate_commentary_with_qwen(event_summary, why_ent, hook_text, language)
                if llm_script:
                    return llm_script

                if language == "hindi":
                    hook = f"GTA 6 का यह जबरदस्त सीन देखिए! {hook_text}" if hook_text else "GTA 6 का सबसे खतरनाक मिशन देखिए!"
                    body = f"वाइस सिटी में क्या हुआ: {event_summary}।"
                    climax = f"यह मोमेंट इतना खास क्यों है: {why_ent}" if why_ent else "लास्ट सेकंड में जो हुआ वो किसी ने नहीं सोचा था!"
                    outro = "GTA 6 का वेट कौन-कौन कर रहा है? सब्सक्राइब जरूर करना!"
                    return f"{hook} {body} {climax} {outro}"

                elif language == "english":
                    hook = hook_text if hook_text else "You won't believe this insane moment in GTA 6!"
                    body = f"In this sequence, {event_summary}."
                    climax = f"What makes this crazy: {why_ent}." if why_ent else "Watch closely what happens in the final seconds!"
                    outro = "Smash that subscribe button for daily GTA 6 clips!"
                    return f"{hook} {body} {climax} {outro}"

                else:  # hinglish
                    hook = f"Bhai yeh dekho: {hook_text}!" if hook_text else "Bhai GTA 6 ka yeh moment miss mat karna!"
                    body = f"Vice City mein scene dekho: {event_summary}."
                    climax = f"Yeh scene itna crazy kyun hai: {why_ent}!" if why_ent else "Poora scene next-level epic ban gaya!"
                    outro = "GTA 6 ke daily epic shorts ke liye subscribe karo!"
                    return f"{hook} {body} {climax} {outro}"

        lang_scripts = COMMENTARY_SCRIPTS.get(language, COMMENTARY_SCRIPTS["hinglish"])
        theme = "default"
        for t in tags:
            if "chase" in t or "police" in t:
                theme = "high_speed_chase"
                break
            elif "crash" in t or "explosion" in t:
                theme = "car_crash_explosion"
                break

        parts = lang_scripts.get(theme, lang_scripts["default"])
        full_text = f"{parts['hook']} {parts['body']} {parts['climax']} {parts['outro']}"
        return full_text


    async def _synthesize_edge_tts(
        self, text: str, voice: str, out_path: Path
    ) -> List[TimedWord]:
        import edge_tts

        communicate = edge_tts.Communicate(text, voice)
        timed_words: List[TimedWord] = []

        submaker = edge_tts.SubMaker()
        with open(out_path, "wb") as file:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    file.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    submaker.feed(chunk)
                    offset_sec = chunk["offset"] / 10_000_000
                    duration_sec = chunk["duration"] / 10_000_000
                    timed_words.append(
                        TimedWord(
                            word=chunk["text"],
                            start=round(offset_sec, 2),
                            end=round(offset_sec + duration_sec, 2),
                        )
                    )
        return timed_words

    def _is_audio_file_audible(self, audio_path: Path) -> bool:
        """
        Detects whether an audio file exists, has content, and contains actual audible audio.
        Returns False for non-existent, 0-byte, or pure silence files (such as anullsrc).
        """
        if not audio_path.exists() or audio_path.stat().st_size == 0:
            return False
        try:
            import subprocess
            import re

            cmd = [
                config.FFMPEG_PATH,
                "-hide_banner",
                "-i",
                str(audio_path),
                "-af",
                "volumedetect",
                "-f",
                "null",
                "-",
            ]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5.0)
            if "max_volume: -inf" in res.stderr:
                return False
            match = re.search(r"max_volume:\s*([-\d\.]+)\s*dB", res.stderr)
            if match:
                max_vol = float(match.group(1))
                if max_vol <= -90.0:
                    return False
                return True
            return audio_path.stat().st_size > 1024
        except Exception:
            return audio_path.stat().st_size > 1024

    def _synthesize_sapi_fallback(
        self, text: str, out_path: Path
    ) -> Tuple[float, List[TimedWord], bool, str]:
        """
        Local offline Windows SAPI fallback synthesis.
        Returns (duration, timed_words, is_silent, audio_status).
        """
        is_silent = False
        audio_status = "SUCCESS"
        try:
            import win32com.client

            speaker = win32com.client.Dispatch("SAPI.SpVoice")
            filestream = win32com.client.Dispatch("SAPI.SpFileStream")
            filestream.Open(str(out_path), 3, False)
            speaker.AudioOutputStream = filestream
            speaker.Speak(text)
            filestream.Close()
            duration = self._get_audio_duration(out_path)
            if not self._is_audio_file_audible(out_path):
                is_silent = True
                audio_status = "SILENT_FALLBACK"
        except Exception:
            is_silent = True
            audio_status = "SILENT_FALLBACK"
            duration = min(20.0, max(5.0, len(text.split()) * 0.4))
            import subprocess

            cmd = [
                config.FFMPEG_PATH,
                "-y",
                "-f",
                "lavfi",
                "-i",
                f"anullsrc=r=44100:cl=stereo",
                "-t",
                f"{duration:.2f}",
                "-c:a",
                "aac",
                str(out_path),
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        words = text.split()
        word_dur = duration / max(1, len(words))
        timed_words = []
        for i, w in enumerate(words):
            timed_words.append(
                TimedWord(
                    word=w,
                    start=round(i * word_dur, 2),
                    end=round((i + 1) * word_dur, 2),
                )
            )
        return duration, timed_words, is_silent, audio_status

    def _get_audio_duration(self, audio_path: Path) -> float:
        import subprocess
        import re

        cmd = [config.FFMPEG_PATH, "-hide_banner", "-i", str(audio_path)]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        dur_match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.?\d*)", res.stderr)
        if dur_match:
            h, m, s = dur_match.groups()
            return int(h) * 3600 + int(m) * 60 + float(s)
        return 15.0

    def generate_voiceover(
        self,
        clip_id: int,
        language: str = "hinglish",
        tags: Optional[List[str]] = None,
        custom_script: Optional[str] = None,
        voice_override: Optional[str] = None,
        include_voiceover: bool = True,
        semantic_info: Optional[Dict[str, Any]] = None,
    ) -> VoiceoverResult:
        language = language.lower()
        if language not in config.language.supported_languages:
            language = "hinglish"

        fallback_flag = False
        if semantic_info:
            if isinstance(semantic_info, dict):
                fallback_flag = bool(semantic_info.get("is_fallback", False))
            else:
                fallback_flag = bool(getattr(semantic_info, "is_fallback", False))

        script = custom_script or self.assemble_script(
            language, tags or [], semantic_info=semantic_info, is_fallback=fallback_flag
        )

        if not include_voiceover:
            return VoiceoverResult(
                audio_path=None,
                script_text=script,
                language=language,
                voice_name="gameplay_only",
                duration=0.0,
                timed_words=[],
                is_silent=True,
                audio_status="NO_VOICEOVER",
            )

        lang_voices = config.language.voice_map.get(language, {})
        voice_name = voice_override or lang_voices.get("default", "hi-IN-MadhurNeural")

        out_path = self.output_dir / f"voice_clip_{clip_id}_{language}.mp3"

        timed_words = []
        duration = 0.0
        is_silent = False
        audio_status = "SUCCESS"

        # Check internet connection first to avoid DNS blocking in offline environments
        online = is_internet_available()

        if online:
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                timed_words = loop.run_until_complete(
                    asyncio.wait_for(
                        self._synthesize_edge_tts(script, voice_name, out_path), timeout=4.0
                    )
                )
                loop.close()
                duration = self._get_audio_duration(out_path)
                is_audible = self._is_audio_file_audible(out_path)
                is_silent = not is_audible
                audio_status = "SUCCESS" if is_audible else "SILENT_FALLBACK"
                logger.info(f"Edge-TTS synthesized voiceover for clip {clip_id} ({duration:.1f}s)")
            except Exception as e:
                logger.warning(f"Edge-TTS failed ({e}). Falling back to SAPI.")
                online = False

        if not online:
            fallback_wav = self.output_dir / f"voice_clip_{clip_id}_{language}_sapi.wav"
            duration, timed_words, is_silent, audio_status = self._synthesize_sapi_fallback(script, fallback_wav)
            out_path = fallback_wav

        return VoiceoverResult(
            audio_path=out_path,
            script_text=script,
            language=language,
            voice_name=voice_name,
            duration=duration,
            timed_words=timed_words,
            is_silent=is_silent,
            audio_status=audio_status,
        )


voice_generator = VoiceGenerator()
