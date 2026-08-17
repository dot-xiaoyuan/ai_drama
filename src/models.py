from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


class DramaError(Exception):
    """Base class for user-facing errors."""


class ConfigError(DramaError):
    pass


class ShotError(DramaError):
    pass


class ReferenceImageError(DramaError):
    pass


class ViduError(DramaError):
    def __init__(
        self,
        message: str,
        *,
        http_status: int | None = None,
        api_code: str | None = None,
        api_message: str | None = None,
    ) -> None:
        super().__init__(message)
        self.http_status = http_status
        self.api_code = api_code
        self.api_message = api_message


class SeedanceError(DramaError):
    def __init__(
        self,
        message: str,
        *,
        http_status: int | None = None,
        api_code: str | None = None,
        api_message: str | None = None,
    ) -> None:
        super().__init__(message)
        self.http_status = http_status
        self.api_code = api_code
        self.api_message = api_message


class DownloadError(DramaError):
    pass


@dataclass(frozen=True)
class AppSettings:
    provider: str
    api_base_url: str
    default_model: str
    poll_interval_seconds: int
    task_timeout_seconds: int
    max_reference_images: int
    max_reference_image_bytes: int


@dataclass(frozen=True)
class ShotConfig:
    id: str
    character: str
    prompt: str
    duration: int
    resolution: str
    aspect_ratio: str
    candidate_count: int
    model: str | None = None
    seed: int | None = None
    movement_amplitude: str | None = None
    audio: bool | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any], *, path: Path) -> "ShotConfig":
        required = ["id", "character", "prompt"]
        missing = [field for field in required if not data.get(field)]
        if missing:
            raise ShotError(f"{path} 缺少必填字段：{', '.join(missing)}")

        try:
            duration = int(data.get("duration", 5))
            candidate_count = int(data.get("candidate_count", 1))
        except (TypeError, ValueError) as exc:
            raise ShotError("duration 和 candidate_count 必须是整数。") from exc

        if duration < 1:
            raise ShotError("duration 必须大于 0。")
        if candidate_count < 1:
            raise ShotError("candidate_count 必须大于 0。")

        seed = data.get("seed")
        if seed is not None:
            try:
                seed = int(seed)
            except (TypeError, ValueError) as exc:
                raise ShotError("seed 必须是整数。") from exc

        audio = data.get("audio")
        if audio is not None and not isinstance(audio, bool):
            raise ShotError("audio 必须是 true 或 false。")

        return cls(
            id=str(data["id"]),
            character=str(data["character"]),
            prompt=str(data["prompt"]),
            duration=duration,
            resolution=str(data.get("resolution", "720p")),
            aspect_ratio=str(data.get("aspect_ratio", "16:9")),
            candidate_count=candidate_count,
            model=str(data["model"]) if data.get("model") else None,
            seed=seed,
            movement_amplitude=str(data["movement_amplitude"])
            if data.get("movement_amplitude")
            else None,
            audio=audio,
        )
