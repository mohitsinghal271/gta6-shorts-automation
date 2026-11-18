"""
Metadata Generator Module
"""

import json
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from config import config
from database.db import db

logger = logging.getLogger("gta6_agent.metadata")


@dataclass
class ClipMetadataResult:
    title_recommended: str
    titles: List[str]
    description: str
    hashtags: List[str]
    tags: List[str]
    thumbnail_concept: str
    pinned_comment: str
    disclaimer: str


METADATA_TEMPLATES = {
    "hindi": {
        "titles_chase": [
            "GTA 6 में 5-Star Wanted Level पर क्या हुआ?! 😱",
            "वाइस सिटी पुलिस से बचना नामुमकिन है! | GTA 6",
            "GTA 6 का सबसे खतरनाक कार चेस मिशन 🔥",
        ],
        "titles_crash": [
            "GTA 6 का नेक्स्ट-लेवल क्रैश फिजिक्स! 🤯",
            "200 KM/H की स्पीड पर कार ब्लास्ट | GTA 6",
            "GTA 6 में ये क्या हो गया?! हैरान कर देने वाला मोमेंट!",
        ],
        "titles_default": [
            "GTA 6 का सबसे क्रेजी गेमप्ले मोमेंट! 🎮",
            "वाइस सिटी में लूसिया का खतरनाक स्टंट | GTA 6",
            "GTA 6 गेमप्ले देखकर होश उड़ जाएंगे! 🔥",
        ],
        "pinned_comment": "👇 क्या आप GTA 6 के लिए एक्साइटेड हैं? अपनी फेवरेट गाड़ी का नाम कमेंट करें! और हां, सब्सक्राइब करना न भूलें! ❤️",
    },
    "english": {
        "titles_chase": [
            "GTA 6 Police AI Is Unstoppable! 😱",
            "Surviving a 5-Star Wanted Level in Vice City! 🔥",
            "The Most Insane Car Chase in GTA 6!",
        ],
        "titles_crash": [
            "GTA 6 Next-Gen Crash Physics Are Mind-Blowing! 🤯",
            "Total Vehicle Annihilation at 150 MPH | GTA 6",
            "This GTA 6 Crash Went Horribly Wrong!",
        ],
        "titles_default": [
            "The Craziest GTA 6 Gameplay Moment Yet! 🎮",
            "Vice City Open World Details You Missed! 🔥",
            "Lucia & Jason Pull Off The Impossible | GTA 6",
        ],
        "pinned_comment": "👇 What feature are you most hyped for in GTA 6? Drop a comment below and hit Subscribe for daily clips! 🚀",
    },
    "hinglish": {
        "titles_chase": [
            "GTA 6 Ki Police Literally Pagal Ho Chuki Hai! 😱",
            "Vice City Mein 5-Star Wanted Level Survival! 🔥",
            "GTA 6 Ka Sabse Dangerous Car Chase! 🏎️💨",
        ],
        "titles_crash": [
            "GTA 6 Ka Next-Gen Crash Physics Dimaag Hila Dega! 🤯",
            "Full Speed Pe Car Blast Ho Gayi | GTA 6",
            "Yeh GTA 6 Moment Miss Mat Karna!",
        ],
        "titles_default": [
            "GTA 6 Vice City Ka Craziest Gameplay Moment! 🎮",
            "Lucia Ka Epic Stunt Scene | GTA 6",
            "GTA 6 Ke Next-Level Graphics Dekho! 🔥",
        ],
        "pinned_comment": "👇 GTA 6 console pe kheloge ya PC pe? Comment karke batao aur daily gaming shorts ke liye Subscribe maaro! ❤️",
    },
}


class MetadataGenerator:
    def __init__(self):
        self.disclaimer_text = (
            "Disclaimer: Footage represents gameplay capture and fan commentary under Fair Use. "
            "All game assets, trademarks, and copyrights belong to Rockstar Games / Take-Two Interactive. "
            "This channel is not affiliated with or endorsed by Rockstar Games."
        )

    def generate_metadata(
        self,
        clip_id: int,
        language: str = "hinglish",
        tags: Optional[List[str]] = None,
        attribution_credit: Optional[str] = None,
        save_to_db: bool = True,
        semantic_info: Optional[Dict[str, Any]] = None,
    ) -> ClipMetadataResult:
        language = language.lower()
        if language not in METADATA_TEMPLATES:
            language = "hinglish"

        tags = tags or ["action"]
        lang_data = METADATA_TEMPLATES[language]

        if any("chase" in t or "police" in t for t in tags):
            candidate_titles = list(lang_data["titles_chase"])
            hook_summary = "High-speed police pursuit through the neon-lit highways of Vice City."
        elif any("crash" in t or "explosion" in t for t in tags):
            candidate_titles = list(lang_data["titles_crash"])
            hook_summary = "High-velocity collision testing the next-generation vehicle damage physics."
        else:
            candidate_titles = list(lang_data["titles_default"])
            hook_summary = "An intense, unexpected moment captured in the open world of Leonida."

        if semantic_info and isinstance(semantic_info, dict):
            s_hook = (semantic_info.get("suggested_hook") or "").strip()
            s_summary = (semantic_info.get("event_summary") or "").strip()
            if s_hook:
                candidate_titles = [f"{s_hook} | GTA 6", candidate_titles[0], candidate_titles[1]]
            if s_summary:
                hook_summary = s_summary

        recommended_title = candidate_titles[0]


        game_tags = [
            "GTA 6",
            "GTA VI",
            "Grand Theft Auto 6",
            "Vice City",
            "GTA 6 Gameplay",
            "GTA 6 Shorts",
            "Gaming Shorts",
            "Lucia GTA 6",
            "Jason GTA 6",
            "Rockstar Games",
            "GTA 6 Graphics",
            "Gaming",
            "Viral Gaming",
            "GTA 6 Official",
            "GTA 6 Police",
        ]

        hashtags = ["#GTA6", "#GTA6Shorts", "#Gaming", "#ViceCity", "#RockstarGames", "#Shorts"]

        desc_lines = [
            f"{recommended_title}\n",
            f"{hook_summary}\n",
            "🎮 Game: Grand Theft Auto VI (Leonida / Vice City)",
            "🔥 Subscribe for daily cinematic GTA 6 gameplay clips, tips, and easter eggs!",
            "",
            "📌 Socials & Community:",
            "• Turn on notifications 🔔 to never miss a short!",
            "• Leave a like if you enjoyed the clip!",
            "",
            attribution_credit or "Footage reviewed under fair use commentary.",
            "",
            f"--- LEGAL DISCLAIMER ---",
            self.disclaimer_text,
            "",
            " ".join(hashtags),
        ]
        description = "\n".join(desc_lines)

        thumbnail_concept = (
            f"High-contrast split image: Close-up of Lucia or Jason with Vice City palm trees and neon sunset in the background. "
            f"Big bold yellow text overlay: '{recommended_title[:30]}...' with a shocked emoji."
        )

        pinned_comment = lang_data.get("pinned_comment", "Subscribe for daily GTA 6 clips!")

        result = ClipMetadataResult(
            title_recommended=recommended_title,
            titles=candidate_titles,
            description=description,
            hashtags=hashtags,
            tags=game_tags,
            thumbnail_concept=thumbnail_concept,
            pinned_comment=pinned_comment,
            disclaimer=self.disclaimer_text,
        )

        if save_to_db:
            try:
                db.insert_or_update_metadata(
                    clip_id=clip_id,
                    title_recommended=result.title_recommended,
                    titles=result.titles,
                    description=result.description,
                    hashtags=result.hashtags,
                    tags=result.tags,
                    thumbnail_concept=result.thumbnail_concept,
                    pinned_comment=result.pinned_comment,
                    disclaimer=result.disclaimer,
                )
            except Exception as e:
                logger.warning(f"Could not persist metadata to DB for clip {clip_id}: {e}")

        return result


metadata_generator = MetadataGenerator()
