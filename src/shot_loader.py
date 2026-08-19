from __future__ import annotations

import base64
import json
import mimetypes
from pathlib import Path

from .models import AppSettings, ReferenceImageError, ShotConfig, ShotError

VALID_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def load_shot(project_root: Path, shot_id: str) -> ShotConfig:
    normalized_id = shot_id.strip("/\\").replace("\\", "/")
    shot_path = project_root / "shots" / Path(normalized_id) / "shot.json"
    if not shot_path.exists():
        raise ShotError(f"Shot 不存在：{shot_id}。请创建 {shot_path}")

    try:
        data = json.loads(shot_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ShotError(f"shot.json 格式错误：{shot_path}，{exc}") from exc

    if not isinstance(data, dict):
        raise ShotError(f"shot.json 根节点必须是 JSON object：{shot_path}")

    shot = ShotConfig.from_dict(data, path=shot_path)
    if shot.id.strip("/\\").replace("\\", "/") != normalized_id:
        raise ShotError(f"shot.json 中的 id 是 {shot.id}，但当前命令请求的是 {shot_id}。")
    return shot


def find_reference_images(
    project_root: Path,
    character: str,
    settings: AppSettings,
    scene: str | None = None,
) -> list[Path]:
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

    if scene:
        scene_images: list[Path] = []
        scenes_dir = project_root / "scenes"
        if (scenes_dir / scene).is_dir():
            scene_images = sorted(
                p for p in (scenes_dir / scene).iterdir()
                if p.is_file() and p.suffix.lower() in VALID_IMAGE_EXTENSIONS
            )
        else:
            for ext in VALID_IMAGE_EXTENSIONS:
                candidate = scenes_dir / f"{scene}{ext}"
                if candidate.is_file():
                    scene_images.append(candidate)
                    break
        if not scene_images:
            raise ReferenceImageError(
                f"场景参考图不存在：{scene}。请确保 scenes/{scene}.png 或 scenes/{scene}/ 存在。"
            )
        images.extend(scene_images)

    if len(images) > settings.max_reference_images:
        raise ReferenceImageError(
            f"镜头参考图总计 {len(images)} 张，超过当前限制 "
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


def encode_image(path: Path) -> str:
    mime_type = mimetypes.guess_type(path.name)[0]
    if not mime_type:
        if path.suffix.lower() == ".webp":
            mime_type = "image/webp"
        elif path.suffix.lower() == ".png":
            mime_type = "image/png"
        elif path.suffix.lower() in {".jpg", ".jpeg"}:
            mime_type = "image/jpeg"
        else:
            raise ReferenceImageError(f"无法识别参考图 MIME 类型：{path}")
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{data}"


def encode_reference_images(paths: list[Path]) -> list[str]:
    return [encode_image(p) for p in paths]


def extract_last_frame(video_path: Path, output_image_path: Path) -> Path:
    import subprocess
    import imageio_ffmpeg

    if not video_path.exists():
        raise ShotError(f"无法从视频抽取首帧，视频文件不存在：{video_path}")

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    output_image_path.parent.mkdir(parents=True, exist_ok=True)

    # 从倒数第 0.1 秒提取 1 帧
    cmd = [
        ffmpeg, "-y",
        "-sseof", "-0.1",
        "-i", str(video_path),
        "-vframes", "1",
        "-q:v", "2",
        str(output_image_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0 or not output_image_path.exists():
        # 如果 sseof 失败，尝试常规提取
        cmd_fallback = [
            ffmpeg, "-y",
            "-i", str(video_path),
            "-vframes", "1",
            "-q:v", "2",
            str(output_image_path),
        ]
        subprocess.run(cmd_fallback, check=True)

    return output_image_path


def resolve_first_frame(project_root: Path, shot: ShotConfig) -> Path | None:
    if shot.first_frame_path:
        first_frame = project_root / shot.first_frame_path
        if not first_frame.exists():
            raise ReferenceImageError(f"首帧参考图不存在：{first_frame}")
        return first_frame

    if shot.first_frame_from_shot:
        clean_target = shot.first_frame_from_shot.strip("/\\").replace("\\", "/")
        output_dir = project_root / "outputs" / Path(clean_target)
        if not output_dir.exists():
            raise ShotError(
                f"前置镜头输出目录不存在：{output_dir}。请先生成前置 Shot {shot.first_frame_from_shot}"
            )

        mp4_files = sorted(
            [p for p in output_dir.iterdir() if p.is_file() and p.suffix.lower() == ".mp4"],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not mp4_files:
            raise ShotError(
                f"前置镜头没有生成的 MP4 视频：{output_dir}。请先生成 {shot.first_frame_from_shot}"
            )

        latest_video = mp4_files[0]
        last_frame_path = output_dir / "last_frame.png"
        extract_last_frame(latest_video, last_frame_path)
        return last_frame_path

    return None
