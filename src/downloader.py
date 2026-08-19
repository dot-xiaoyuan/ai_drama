from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx

from .models import DownloadError


def next_output_path(output_dir: Path, shot_id: str, candidate_index: int) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    clean_name = Path(shot_id).as_posix().replace("/", "_").replace("\\", "_")
    base_index = candidate_index
    while True:
        path = output_dir / f"{clean_name}_v{base_index}.mp4"
        if not path.exists():
            return path
        base_index += 1


def download_video(url: str, destination: Path) -> None:
    temp_path = destination.with_suffix(destination.suffix + ".tmp")
    try:
        with httpx.stream("GET", url, timeout=120.0, follow_redirects=True) as response:
            response.raise_for_status()
            with temp_path.open("wb") as file:
                for chunk in response.iter_bytes():
                    if chunk:
                        file.write(chunk)
        temp_path.replace(destination)
    except httpx.HTTPStatusError as exc:
        _cleanup_temp(temp_path)
        raise DownloadError(f"视频下载失败，HTTP Status: {exc.response.status_code}") from exc
    except httpx.HTTPError as exc:
        _cleanup_temp(temp_path)
        raise DownloadError(f"视频下载失败：{exc}") from exc
    except OSError as exc:
        _cleanup_temp(temp_path)
        raise DownloadError(f"视频保存失败：{destination}，{exc}") from exc


def write_metadata(output_dir: Path, metadata: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = output_dir / "metadata.json"
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _cleanup_temp(path: Path) -> None:
    if path.exists():
        path.unlink()
