from __future__ import annotations

import base64
import json
import mimetypes
from pathlib import Path

from .models import AppSettings, ReferenceImageError, ShotConfig, ShotError

VALID_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def load_shot(project_root: Path, shot_id: str) -> ShotConfig:
    shot_path = project_root / "shots" / shot_id / "shot.json"
    if not shot_path.exists():
        raise ShotError(f"Shot 不存在：{shot_id}。请创建 {shot_path}")

    try:
        data = json.loads(shot_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ShotError(f"shot.json 格式错误：{shot_path}，{exc}") from exc

    if not isinstance(data, dict):
        raise ShotError(f"shot.json 根节点必须是 JSON object：{shot_path}")

    shot = ShotConfig.from_dict(data, path=shot_path)
    if shot.id != shot_id:
        raise ShotError(f"shot.json 中的 id 是 {shot.id}，但当前命令请求的是 {shot_id}。")
    return shot


def find_reference_images(project_root: Path, character: str, settings: AppSettings) -> list[Path]:
    character_dir = project_root / "characters" / character
    if not character_dir.exists() or not character_dir.is_dir():
        raise ReferenceImageError(f"角色目录不存在：{character_dir}")

    images = sorted(
        path
        for path in character_dir.iterdir()
        if path.is_file() and path.suffix.lower() in VALID_IMAGE_EXTENSIONS
    )
    if not images:
        raise ReferenceImageError(
            f"角色 {character} 没有参考图片。请把 png/jpg/jpeg/webp 放到 {character_dir}"
        )

    if len(images) > settings.max_reference_images:
        raise ReferenceImageError(
            f"角色 {character} 有 {len(images)} 张参考图，超过当前限制 "
            f"{settings.max_reference_images} 张。请删减后重试。"
        )

    too_large = [
        path.name
        for path in images
        if path.stat().st_size > settings.max_reference_image_bytes
    ]
    if too_large:
        max_mb = settings.max_reference_image_bytes / 1024 / 1024
        raise ReferenceImageError(
            f"以下参考图超过 {max_mb:.0f}MB，不适合 base64 直传：{', '.join(too_large)}"
        )

    return images


def encode_reference_images(paths: list[Path]) -> list[str]:
    encoded: list[str] = []
    for path in paths:
        mime_type = mimetypes.guess_type(path.name)[0]
        if not mime_type:
            if path.suffix.lower() == ".webp":
                mime_type = "image/webp"
            else:
                raise ReferenceImageError(f"无法识别参考图 MIME 类型：{path}")
        data = base64.b64encode(path.read_bytes()).decode("ascii")
        encoded.append(f"data:{mime_type};base64,{data}")
    return encoded
