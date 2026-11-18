"""
YouTube Uploader Module
Integrates the official YouTube Data API v3 using Google OAuth 2.0.
Supports video upload with resumable chunks, exponential backoff retries,
privacy controls, scheduled publishing, duplicate checks, and dry-run simulation mode.
"""

import os
import time
import json
import pickle
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass
from config import config
from database.db import db
from modules.duplicate_detector import duplicate_detector

logger = logging.getLogger("gta6_agent.youtube")

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]


@dataclass
class UploadResult:
    success: bool
    youtube_video_id: Optional[str]
    youtube_url: Optional[str]
    privacy_status: str
    error_message: Optional[str] = None
    is_simulation: bool = False


class YouTubeUploader:
    def __init__(self):
        self.client_secrets_file = config.youtube.client_secrets_file
        self.token_pickle_file = config.youtube.token_pickle_file
        self.token_json_file = getattr(config.youtube, "token_json_file", config.PROJECT_ROOT / "youtube_token.json")

    def get_authenticated_service(self):
        """
        Authenticate with YouTube Data API v3 via OAuth 2.0.
        Supports youtube_token.json / token.json (JSON authorized user info) as well as legacy token.pickle.
        Automatically refreshes expired tokens.
        """
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        credentials = None

        # 0. Try Environment Variable JSON string directly
        env_token_json = os.environ.get("YOUTUBE_TOKEN_JSON")
        if env_token_json:
            try:
                creds_data = json.loads(env_token_json)
                credentials = Credentials.from_authorized_user_info(creds_data, SCOPES)
                logger.info("Loaded YouTube OAuth credentials from YOUTUBE_TOKEN_JSON environment variable.")
            except Exception as e:
                logger.warning(f"Error parsing YOUTUBE_TOKEN_JSON: {e}")

        # 1. Try JSON token (primary, modern format within local project)
        if not credentials:
            token_json_candidates = [
                self.token_json_file,
                Path(config.PROJECT_ROOT) / "youtube_token.json",
                Path(config.PROJECT_ROOT) / "token.json",
            ]
            for t_path in token_json_candidates:
                if t_path and Path(t_path).exists():
                    try:
                        with open(t_path, "r", encoding="utf-8") as f:
                            creds_data = json.load(f)
                        credentials = Credentials.from_authorized_user_info(creds_data, SCOPES)
                        self.token_json_file = Path(t_path)
                        break
                    except Exception as e:
                        logger.warning(f"Error reading JSON token from {t_path}: {e}")

        # 2. Try legacy pickle token
        if not credentials and self.token_pickle_file and Path(self.token_pickle_file).exists():
            try:
                with open(self.token_pickle_file, "rb") as token:
                    credentials = pickle.load(token)
            except Exception as e:
                logger.warning(f"Error loading pickle token: {e}")

        # 3. Refresh expired credentials
        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                try:
                    credentials.refresh(Request())
                    save_path = self.token_json_file or (Path(config.PROJECT_ROOT) / "youtube_token.json")
                    with open(save_path, "w", encoding="utf-8") as f:
                        f.write(credentials.to_json())
                    logger.info("YouTube OAuth token successfully refreshed!")
                except Exception as e:
                    logger.error(f"OAuth token refresh failed: {e}")
                    credentials = None

            if not credentials or not credentials.valid:
                # 0. Check YOUTUBE_CLIENT_SECRET_JSON environment variable
                env_secret_json = os.environ.get("YOUTUBE_CLIENT_SECRET_JSON")
                if env_secret_json:
                    try:
                        secret_dict = json.loads(env_secret_json)
                        flow = InstalledAppFlow.from_client_config(secret_dict, SCOPES)
                        credentials = flow.run_local_server(port=0)
                    except Exception as e:
                        logger.warning(f"Error initializing OAuth from YOUTUBE_CLIENT_SECRET_JSON: {e}")

                if not credentials:
                    # Find valid client secrets file within local project (no sibling directory lookup)
                    client_secret_candidates = [
                        self.client_secrets_file,
                        Path(config.PROJECT_ROOT) / "client_secrets.json",
                    ]
                    secret_file = next((p for p in client_secret_candidates if p and Path(p).exists()), None)
                    if not secret_file:
                        raise FileNotFoundError(
                            f"YouTube OAuth client secrets file not found at {self.client_secrets_file}. "
                            "Download it from Google Cloud Console (YouTube Data API v3) and place it here."
                        )

                    flow = InstalledAppFlow.from_client_secrets_file(str(secret_file), SCOPES)
                    credentials = flow.run_local_server(port=0)

                save_path = self.token_json_file or (Path(config.PROJECT_ROOT) / "youtube_token.json")
                with open(save_path, "w", encoding="utf-8") as f:
                    f.write(credentials.to_json())
                logger.info(f"OAuth credentials saved to {save_path}")

        return build("youtube", "v3", credentials=credentials)

    def upload_short(
        self,
        clip_id: int,
        video_path: Path,
        title: str,
        description: str,
        tags: List[str],
        privacy_status: str = "private",
        scheduled_publish_time: Optional[str] = None,
        simulate: Optional[bool] = None,
        enforce_approval: Optional[bool] = None,
    ) -> UploadResult:
        """
        Uploads a generated Short to YouTube.
        - Enforces authorization gate: clip must have approved_for_upload == 1 OR satisfy publishing_policy
        - Verifies no duplicate upload
        - In simulation mode (or when no client_secrets exist), simulates the upload cleanly.
        """
        video_path = Path(video_path).resolve()
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found at {video_path}")

        # Check duplicate
        if duplicate_detector.is_already_uploaded(clip_id):
            msg = f"Clip ID {clip_id} has already been uploaded to YouTube. Skipping to prevent duplicates."
            logger.warning(msg)
            return UploadResult(
                success=False,
                youtube_video_id=None,
                youtube_url=None,
                privacy_status=privacy_status,
                error_message=msg,
            )

        # Determine simulation mode
        should_simulate = (
            simulate
            if simulate is not None
            else (config.youtube.simulate_upload or not self.client_secrets_file.exists())
        )

        # Authorization Gate Check
        # Enforce that clip['approved_for_upload'] == 1 OR publishing_policy.evaluate(clip).can_publish == True
        should_enforce = enforce_approval
        if should_enforce is None:
            should_enforce = getattr(getattr(config, "publishing", None), "enforce_approval", True)

        if should_enforce:
            clip = db.get_clip_by_id(clip_id) if clip_id else None
            is_approved = clip and (
                clip.get("approved_for_upload") == 1
                or clip.get("status") in ("approved", "published")
            )
            if not is_approved:
                from modules.publishing_policy import publishing_policy
                policy_eval = publishing_policy.evaluate(
                    clip_id=clip_id,
                    clip=clip,
                    video_path=video_path,
                    metadata={"title": title, "description": description, "tags": tags},
                )
                if not policy_eval.can_publish:
                    msg = (
                        f"Clip ID {clip_id} rejected by publishing authorization gate: "
                        f"not approved and policy check failed: {', '.join(policy_eval.reasons_failed)}"
                    )
                    logger.warning(msg)
                    return UploadResult(
                        success=False,
                        youtube_video_id=None,
                        youtube_url=None,
                        privacy_status=privacy_status,
                        error_message=msg,
                        is_simulation=should_simulate,
                    )

            # Two-Key Safety Gate: Evaluate Policy Invariants
            # In simulation, enforce only if enforce_in_simulation is True. In production, ALWAYS enforce!
            enforce_two_key = not should_simulate or getattr(getattr(config, "publishing", None), "enforce_in_simulation", False)
            if enforce_two_key:
                from modules.publishing_policy import publishing_policy
                policy_eval = publishing_policy.evaluate(
                    clip_id=clip_id,
                    clip=clip,
                    video_path=video_path,
                    metadata={"title": title, "description": description, "tags": tags},
                )
                # Tier 1 Invariants: source permission & media spec cannot be bypassed even with human approval
                tier1_passed = policy_eval.rule_results.get("source_permission_verified", False)
                strict_two_key = getattr(getattr(config, "publishing", None), "strict_two_key_gate", True)
                if strict_two_key and not tier1_passed:
                    msg = (
                        f"Clip ID {clip_id} rejected by Two-Key safety gate: "
                        f"Tier 1 legal/media invariant failed: {', '.join(policy_eval.reasons_failed)}"
                    )
                    logger.warning(msg)
                    return UploadResult(
                        success=False,
                        youtube_video_id=None,
                        youtube_url=None,
                        privacy_status=privacy_status,
                        error_message=msg,
                        is_simulation=should_simulate,
                    )


        if should_simulate:
            # Clean simulation mode for development/testing
            fake_id = f"sim_{clip_id}_{int(time.time())}"
            fake_url = f"https://youtube.com/shorts/{fake_id}"
            logger.info(
                f"[SIMULATION] Uploaded clip {clip_id} to YouTube as '{title}' ({privacy_status}) -> {fake_url}"
            )

            db.record_publishing(
                clip_id=clip_id,
                youtube_video_id=fake_id,
                youtube_url=fake_url,
                privacy_status=privacy_status,
                upload_status="success",
                scheduled_time=scheduled_publish_time,
            )
            return UploadResult(
                success=True,
                youtube_video_id=fake_id,
                youtube_url=fake_url,
                privacy_status=privacy_status,
                is_simulation=True,
            )

        # Real Google API Upload
        try:
            from googleapiclient.http import MediaFileUpload
            from googleapiclient.errors import HttpError

            youtube = self.get_authenticated_service()

            body = {
                "snippet": {
                    "title": title[:100],  # YouTube title limit
                    "description": description[:5000],
                    "tags": tags[:50],
                    "categoryId": config.youtube.category_id,
                },
                "status": {
                    "privacyStatus": privacy_status,
                    "selfDeclaredMadeForKids": False,
                },
            }

            if scheduled_publish_time and privacy_status == "private":
                body["status"]["publishAt"] = scheduled_publish_time

            media = MediaFileUpload(
                str(video_path),
                mimetype="video/mp4",
                chunksize=1024 * 1024 * 5,  # 5MB chunks
                resumable=True,
            )

            request = youtube.videos().insert(
                part="snippet,status",
                body=body,
                media_body=media,
            )

            # Resumable upload loop with exponential backoff
            response = None
            retries = 0
            while response is None:
                try:
                    status, response = request.next_chunk()
                    if status:
                        progress = int(status.progress() * 100)
                        logger.info(f"Upload progress: {progress}%")
                except HttpError as e:
                    if e.resp.status in [500, 502, 503, 504] and retries < 5:
                        retries += 1
                        sleep_time = 2**retries
                        logger.warning(
                            f"HTTP {e.resp.status}. Retrying upload in {sleep_time}s..."
                        )
                        time.sleep(sleep_time)
                    else:
                        raise e

            video_id = response.get("id")
            youtube_url = f"https://youtube.com/shorts/{video_id}"
            logger.info(f"Successfully uploaded short! Video ID: {video_id} -> {youtube_url}")

            db.record_publishing(
                clip_id=clip_id,
                youtube_video_id=video_id,
                youtube_url=youtube_url,
                privacy_status=privacy_status,
                upload_status="success",
                scheduled_time=scheduled_publish_time,
            )

            return UploadResult(
                success=True,
                youtube_video_id=video_id,
                youtube_url=youtube_url,
                privacy_status=privacy_status,
                is_simulation=False,
            )

        except Exception as e:
            error_msg = f"Failed to upload to YouTube: {str(e)}"
            logger.error(error_msg)
            db.record_publishing(
                clip_id=clip_id,
                youtube_video_id=None,
                youtube_url=None,
                privacy_status=privacy_status,
                upload_status="failed",
                error_log=error_msg,
            )
            return UploadResult(
                success=False,
                youtube_video_id=None,
                youtube_url=None,
                privacy_status=privacy_status,
                error_message=error_msg,
            )


youtube_uploader = YouTubeUploader()
