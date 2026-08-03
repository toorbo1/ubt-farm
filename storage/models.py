from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class VideoTask:
    id: str
    topic: Optional[str] = None
    script: Optional[str] = None
    background_path: Optional[Path] = None
    output_path: Optional[Path] = None
    status: str = "pending"  # pending | processing | done | failed
    platform: str = "tiktok"
    hashtags: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    error: Optional[str] = None


@dataclass
class UploadResult:
    video_path: Path
    platform: str
    success: bool
    url: Optional[str] = None
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
