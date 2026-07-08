# transcript_service.py

from typing import List, Optional
from urllib.parse import urlparse, parse_qs

from pydantic import BaseModel, HttpUrl

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable
)


# ==========================
# Pydantic Models
# ==========================

class TranscriptSegment(BaseModel):
    text: str
    start: float
    duration: float


class TranscriptResponse(BaseModel):
    video_id: str
    language: List[str] = []
    source: HttpUrl
    transcript_available: bool
    transcript: List[TranscriptSegment] = []
    full_text: Optional[str] = None
    message: Optional[str] = None


# ==========================
# Exceptions
# ==========================

class InvalidYoutubeUrl(Exception):
    pass


# ==========================
# Service
# ==========================

class YoutubeTranscriptService:

    def __init__(self, languages: List[str] = ["en"]):
        self.languages = languages
        self.api = YouTubeTranscriptApi()

    def extract_video_id(self, url: HttpUrl) -> str:

        parsed = urlparse(str(url))

        if parsed.netloc == "youtu.be":
            return parsed.path.lstrip("/")

        if "youtube.com" in parsed.netloc:

            if parsed.path == "/watch":
                vid = parse_qs(parsed.query).get("v", [None])[0]
                if not vid:
                    raise InvalidYoutubeUrl(
                        "Unable to extract YouTube video id from watch URL."
                    )
                return vid

            if parsed.path.startswith("/shorts/"):
                return parsed.path.split("/")[2]

            if parsed.path.startswith("/embed/"):
                return parsed.path.split("/")[2]

        raise InvalidYoutubeUrl(
            "Unable to extract YouTube video id."
        )

    def fetch_transcript(
        self,
        url: HttpUrl
    ) -> TranscriptResponse:

        video_id = self.extract_video_id(url)

        try:

            raw = self.api.fetch(  # type: ignore[attr-defined]
                video_id=video_id,
                languages=self.languages
            )

            segments = [
                TranscriptSegment(
                    text=item.text,
                    start=item.start,
                    duration=item.duration
                )
                for item in raw
            ]

            return TranscriptResponse(
                video_id=video_id,
                language=self.languages,
                source=url,
                transcript_available=True,
                transcript=segments,
                full_text=" ".join(
                    s.text for s in segments
                )
            )

        except VideoUnavailable:

            return TranscriptResponse(
                video_id=video_id,
                source=url,
                transcript_available=False,
                message="Video unavailable."
            )

        except TranscriptsDisabled:

            return TranscriptResponse(
                video_id=video_id,
                source=url,
                transcript_available=False,
                message="Captions are disabled for this video."
            )

        except NoTranscriptFound:

            return TranscriptResponse(
                video_id=video_id,
                source=url,
                transcript_available=False,
                message=(
                    "No transcript found. "
                    "Video may not provide captions."
                )
            )

        except Exception as e:

            return TranscriptResponse(
                video_id=video_id,
                source=url,
                transcript_available=False,
                message=str(e)
            )