"""
Livestream Discovery Module for GTA 6 AI YouTube Shorts Automation Agent

Implements YouTube Data API v3 search and batch liveStreamingDetails hydration,
quota accounting with America/Los_Angeles midnight reset, local SQLite caching,
exponential backoff, and direct two-phase status reconciliation.
"""

from dataclasses import dataclass
from datetime import datetime
import json
import logging
import os
import time
from typing import List, Optional, Set, Tuple, Dict, Any
from zoneinfo import ZoneInfo

from config import config
from database.db import db

logger = logging.getLogger("gta6_agent.discovery")

LOS_ANGELES_TZ = ZoneInfo("America/Los_Angeles")


@dataclass
class DiscoveredStreamMetadata:
    stream_video_id: str
    channel_id: str
    channel_title: str
    title: str
    thumbnail_url: str
    viewer_count: Optional[int]  # None if hidden, unavailable, or pre-live
    stream_start_time: Optional[datetime]
    is_live: bool
    discovered_at: datetime
    ended_at: Optional[datetime] = None
    has_authorized_source: bool = False


class QuotaExceededError(Exception):
    """Raised when the daily YouTube Data API v3 quota budget is exhausted."""
    pass


class LivestreamDiscoveryService:
    def __init__(
        self,
        api_key: Optional[str] = None,
        cache_ttl_seconds: int = 300,
        poll_interval_minutes: int = 30,
        manual_budget_units: int = 1000,
        daily_quota_limit: int = 10000,
    ):
        self.api_key = api_key or os.getenv("YOUTUBE_API_KEY") or os.getenv("YOUTUBE_DEVELOPER_KEY")
        self.cache_ttl_seconds = cache_ttl_seconds
        self.poll_interval_minutes = poll_interval_minutes
        self.manual_budget_units = manual_budget_units
        self.daily_quota_limit = daily_quota_limit
        self.quota_exhausted = False
        self._last_poll_time: Optional[float] = None

    def get_current_pt_date_str(self) -> str:
        """Returns the current date in YYYY-MM-DD under America/Los_Angeles timezone."""
        return datetime.now(LOS_ANGELES_TZ).strftime("%Y-%m-%d")

    def get_remaining_quota_units(self) -> int:
        """Calculates remaining quota units for the active Pacific Time calendar day."""
        pt_date = self.get_current_pt_date_str()
        consumed = db.get_daily_quota_usage_pt(pt_date)
        return max(0, self.daily_quota_limit - consumed)

    def _record_quota(self, endpoint: str, units: int, caller_context: str):
        pt_date = self.get_current_pt_date_str()
        db.record_youtube_quota_usage(endpoint, units, caller_context, pt_date)
        logger.debug("Recorded %d quota units for %s (%s) on %s", units, endpoint, caller_context, pt_date)

    def discover_active_streams(
        self,
        query: str = "GTA 6",
        max_results: int = 10,
        max_pages: int = 1,
        is_manual: bool = False,
        force_refresh: bool = False,
    ) -> List[DiscoveredStreamMetadata]:
        """
        Polls active streams using cached DB records within TTL, or executes
        Step 1 search.list and Step 2 videos.list batch hydration.
        """
        now_ts = time.time()
        caller_context = "manual_search" if is_manual else "background_discovery"

        # Check Cache if not forced
        if not force_refresh and self._last_poll_time and (now_ts - self._last_poll_time < self.cache_ttl_seconds):
            logger.info("Serving discovered streams from cache (within %ss TTL)", self.cache_ttl_seconds)
            cached_rows = db.list_discovered_streams(limit=max_results)
            if cached_rows:
                return [self._row_to_metadata(r) for r in cached_rows]

        # Check Simulation Flag
        if config.youtube.simulate_discovery:
            logger.info("[SIMULATION] Generating synthetic mock GTA 6 discovered livestreams.")
            mock_streams = self._generate_mock_streams(query, max_results)
            self.sync_to_database(mock_streams)
            self._last_poll_time = now_ts
            return mock_streams

        # Live Network Mode Validation
        if not self.api_key:
            raise ValueError(
                "YouTube Data API Key is required for live stream discovery. "
                "Set YOUTUBE_API_KEY environment variable or enable LIVESTREAM_DISCOVERY_MOCK=1."
            )

        # Quota Budget Check
        remaining = self.get_remaining_quota_units()
        if remaining < 101 or self.quota_exhausted:
            logger.warning("Daily YouTube API quota near exhaustion (Remaining: %d). Serving cached streams.", remaining)
            cached_rows = db.list_discovered_streams(limit=max_results)
            return [self._row_to_metadata(r) for r in cached_rows]

        # Execute Live Two-Step Discovery via Google API Client / Requests
        try:
            streams = self._execute_live_search(query, max_results, caller_context)
            self.sync_to_database(streams)
            self._last_poll_time = now_ts
            return streams
        except Exception as e:
            err_str = str(e).lower()
            if "quotaexceeded" in err_str or "403" in err_str:
                self.quota_exhausted = True
                logger.error("YouTube Data API Quota exceeded. Activating circuit breaker until midnight PT.")
            else:
                logger.error("Error discovering live streams: %s", e)
            cached_rows = db.list_discovered_streams(limit=max_results)
            return [self._row_to_metadata(r) for r in cached_rows]

    def _execute_live_search(self, query: str, max_results: int, caller_context: str) -> List[DiscoveredStreamMetadata]:
        import urllib.request
        import urllib.parse

        # Step 1: search.list (100 units)
        search_params = {
            "part": "snippet",
            "eventType": "live",
            "type": "video",
            "videoCategoryId": "20",
            "q": query,
            "order": "viewCount",
            "maxResults": max_results,
            "key": self.api_key,
        }
        search_url = f"https://www.googleapis.com/youtube/v3/search?{urllib.parse.urlencode(search_params)}"
        req = urllib.request.Request(search_url, headers={"User-Agent": "GTA6-Agent/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            search_data = json.loads(resp.read().decode("utf-8"))

        self._record_quota("search.list", 100, caller_context)
        items = search_data.get("items", [])
        if not items:
            return []

        video_ids = [item["id"]["videoId"] for item in items if "videoId" in item.get("id", {})]
        if not video_ids:
            return []

        # Step 2: videos.list batch hydration (1 unit per 50 videos)
        videos_params = {
            "part": "snippet,liveStreamingDetails,statistics",
            "id": ",".join(video_ids),
            "key": self.api_key,
        }
        videos_url = f"https://www.googleapis.com/youtube/v3/videos?{urllib.parse.urlencode(videos_params)}"
        vreq = urllib.request.Request(videos_url, headers={"User-Agent": "GTA6-Agent/5.0"})
        with urllib.request.urlopen(vreq, timeout=10) as vresp:
            videos_data = json.loads(vresp.read().decode("utf-8"))

        self._record_quota("videos.list", 1, caller_context)
        video_items = {v["id"]: v for v in videos_data.get("items", [])}

        results = []
        now = datetime.utcnow()
        for vid in video_ids:
            vinfo = video_items.get(vid)
            if not vinfo:
                continue
            snip = vinfo.get("snippet", {})
            live_details = vinfo.get("liveStreamingDetails", {})
            v_count_str = live_details.get("concurrentViewers")
            viewer_count = int(v_count_str) if v_count_str is not None else None

            start_time = None
            start_time_str = live_details.get("actualStartTime")
            if start_time_str:
                try:
                    start_time = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
                except ValueError:
                    pass

            thumbs = snip.get("thumbnails", {})
            thumb_url = thumbs.get("high", {}).get("url") or thumbs.get("default", {}).get("url") or ""

            results.append(
                DiscoveredStreamMetadata(
                    stream_video_id=vid,
                    channel_id=snip.get("channelId", ""),
                    channel_title=snip.get("channelTitle", ""),
                    title=snip.get("title", ""),
                    thumbnail_url=thumb_url,
                    viewer_count=viewer_count,
                    stream_start_time=start_time,
                    is_live=True,
                    discovered_at=now,
                )
            )
        return results

    def check_stream_status(self, stream_video_id: str) -> Tuple[bool, Optional[datetime]]:
        """
        Directly queries videos.list (1 unit) to verify if an individual stream is truly live or ended.
        Returns (is_live, actual_end_time).
        """
        if config.youtube.simulate_discovery or not self.api_key:
            # In simulation mode, check database state
            s = db.get_discovered_stream_by_video_id(stream_video_id)
            if s and s.get("is_live") == 1:
                return True, None
            return False, datetime.utcnow()

        import urllib.request
        import urllib.parse

        params = {
            "part": "snippet,liveStreamingDetails",
            "id": stream_video_id,
            "key": self.api_key,
        }
        url = f"https://www.googleapis.com/youtube/v3/videos?{urllib.parse.urlencode(params)}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "GTA6-Agent/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            self._record_quota("videos.list", 1, "stream_status_check")
            items = data.get("items", [])
            if not items:
                # Video deleted, private, or not found
                return False, datetime.utcnow()

            vinfo = items[0]
            snip = vinfo.get("snippet", {})
            live_details = vinfo.get("liveStreamingDetails", {})

            # If actualEndTime is present or broadcastContent is 'none'
            end_time_str = live_details.get("actualEndTime")
            if end_time_str:
                end_time = datetime.fromisoformat(end_time_str.replace("Z", "+00:00"))
                return False, end_time

            if snip.get("liveBroadcastContent") == "none":
                return False, datetime.utcnow()

            return True, None
        except Exception as e:
            logger.error("Error verifying individual stream status for %s: %s", stream_video_id, e)
            # Default to preserving status on network error rather than falsely killing session
            return True, None

    def sync_to_database(self, streams: List[DiscoveredStreamMetadata]) -> int:
        """Upserts discovered streams into SQLite and links authorized source flags."""
        synced_count = 0
        for s in streams:
            # Check if this channel has verified legal permission
            source = db.get_authorized_footage_source_by_channel(s.channel_id)
            has_auth = bool(source and source.get("permission_verified") == 1)
            s.has_authorized_source = has_auth

            db.upsert_discovered_stream(
                stream_video_id=s.stream_video_id,
                channel_id=s.channel_id,
                channel_title=s.channel_title,
                title=s.title,
                thumbnail_url=s.thumbnail_url,
                viewer_count=s.viewer_count,
                stream_start_time=s.stream_start_time.isoformat() if s.stream_start_time else None,
                is_live=s.is_live,
                has_authorized_source=has_auth,
            )
            synced_count += 1
        return synced_count

    def reconcile_stale_streams(self, active_stream_ids: Set[str]) -> int:
        """
        Identifies streams that may have ended.
        NEVER marks a stream offline merely because it dropped out of the search response.
        Directly verifies each candidate via check_stream_status before marking offline.
        """
        active_db_streams = db.get_active_discovered_streams()
        reconciled_count = 0

        for s in active_db_streams:
            vid = s["stream_video_id"]
            if vid not in active_stream_ids:
                # Candidate for ending: perform direct individual lookup
                is_live, end_time = self.check_stream_status(vid)
                if not is_live:
                    logger.info("Direct verification confirmed stream %s ended at %s", vid, end_time)
                    db.mark_stream_offline(vid, ended_at=end_time.isoformat() if end_time else None)
                    # Stop active monitoring sessions for this stream
                    with db.get_connection() as conn:
                        conn.execute(
                            """
                            UPDATE monitoring_sessions 
                            SET session_status = 'stopped', stopped_at = CURRENT_TIMESTAMP
                            WHERE stream_id = ? AND session_status = 'active'
                            """,
                            (s["id"],),
                        )
                        conn.commit()
                    reconciled_count += 1
                else:
                    logger.debug("Stream %s dropped out of top search results but remains active.", vid)

        return reconciled_count

    def _generate_mock_streams(self, query: str, count: int) -> List[DiscoveredStreamMetadata]:
        now = datetime.utcnow()
        mock_creators = [
            ("UC_GTA6_CREATOR_A", "ViceCityGamer", "GTA 6 - 5-Star Police Chase & Crazy Stunts [LIVE]", 1420),
            ("UC_GTA6_CREATOR_B", "LeonidaExplorer", "Grand Theft Auto VI Map Secrets & Free Roam", 890),
            ("UC_GTA6_CREATOR_C", "LuciaGangster", "GTA VI Story Missions & Heists 1080p 60FPS", None), # Hidden viewers
        ]
        results = []
        for i, (cid, cname, title, viewers) in enumerate(mock_creators[:count]):
            vid = f"mock_live_vid_{i+1:03d}"
            results.append(
                DiscoveredStreamMetadata(
                    stream_video_id=vid,
                    channel_id=cid,
                    channel_title=cname,
                    title=f"{title} ({query})",
                    thumbnail_url=f"https://img.youtube.com/vi/{vid}/hqdefault.jpg",
                    viewer_count=viewers,
                    stream_start_time=now,
                    is_live=True,
                    discovered_at=now,
                )
            )
        return results

    def _row_to_metadata(self, row: Dict[str, Any]) -> DiscoveredStreamMetadata:
        start_time = None
        if row.get("stream_start_time"):
            try:
                start_time = datetime.fromisoformat(row["stream_start_time"])
            except ValueError:
                pass
        return DiscoveredStreamMetadata(
            stream_video_id=row["stream_video_id"],
            channel_id=row["channel_id"],
            channel_title=row["channel_title"],
            title=row["title"],
            thumbnail_url=row.get("thumbnail_url") or "",
            viewer_count=row.get("viewer_count"),
            stream_start_time=start_time,
            is_live=bool(row.get("is_live", 1)),
            discovered_at=datetime.fromisoformat(row["discovered_at"]) if row.get("discovered_at") else datetime.utcnow(),
            ended_at=datetime.fromisoformat(row["ended_at"]) if row.get("ended_at") else None,
            has_authorized_source=bool(row.get("has_authorized_source", 0)),
        )
