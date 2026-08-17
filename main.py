from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config import load_seedance_api_key, load_settings, load_vidu_api_key
from src.downloader import download_video, next_output_path, write_metadata
from src.models import (
    ConfigError,
    DownloadError,
    DramaError,
    ReferenceImageError,
    SeedanceError,
    ShotError,
    ViduError,
)
from src.seedance_client import SeedanceClient
from src.shot_loader import encode_reference_images, find_reference_images, load_shot
from src.vidu_client import ViduClient


PROJECT_ROOT = Path(__file__).resolve().parent


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python main.py",
        description="AI 漫剧镜头生成 POC：读取 Shot 配置并调用视频生成 Provider。",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate", help="生成指定 Shot")
    generate.add_argument("shot_id", help="例如：shot_001")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "generate":
            return generate(args.shot_id)
    except KeyboardInterrupt:
        print("\n已取消。")
        return 130
    except DramaError as exc:
        print_user_error(exc)
        return 1

    parser.print_help()
    return 1


def generate(shot_id: str) -> int:
    settings = load_settings(PROJECT_ROOT)
    if settings.provider not in {"seedance", "vidu"}:
        raise ConfigError("当前仅支持 provider=seedance 或 provider=vidu。")

    shot = load_shot(PROJECT_ROOT, shot_id)
    api_key = load_api_key(settings.provider)
    reference_paths = find_reference_images(PROJECT_ROOT, shot.character, settings)
    reference_images = encode_reference_images(reference_paths)

    print_header(shot, settings.default_model, reference_paths)

    output_dir = PROJECT_ROOT / "outputs" / shot.id
    metadata: dict[str, Any] = {
        "shot_id": shot.id,
        "provider": settings.provider,
        "prompt": shot.prompt,
        "character": shot.character,
        "references": [str(path.relative_to(PROJECT_ROOT)) for path in reference_paths],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "candidates": [],
    }

    success_count = 0
    with create_provider_client(settings.provider, api_key, settings.api_base_url) as client:
        for candidate_index in range(1, shot.candidate_count + 1):
            candidate = run_candidate(
                client=client,
                shot=shot,
                settings=settings,
                reference_images=reference_images,
                output_dir=output_dir,
                candidate_index=candidate_index,
            )
            metadata["candidates"].append(candidate)
            write_metadata(output_dir, metadata)
            if candidate["status"] == "success":
                success_count += 1

    print()
    if success_count:
        print("生成完成。")
        print()
        print("Shot:")
        print(shot.id)
        print()
        print("Output:")
        for candidate in metadata["candidates"]:
            if candidate["status"] == "success":
                print(candidate["output"])
        if success_count != shot.candidate_count:
            print()
            print(f"注意：{shot.candidate_count - success_count} 个 candidate 失败，详情见 metadata.json。")
        return 0

    print("生成失败。所有 candidate 都未成功，详情见 metadata.json。")
    return 1


def run_candidate(
    *,
    client: Any,
    shot: Any,
    settings: Any,
    reference_images: list[str],
    output_dir: Path,
    candidate_index: int,
) -> dict[str, Any]:
    print()
    print(f"Submitting candidate {candidate_index}/{shot.candidate_count}...")
    candidate: dict[str, Any] = {
        "index": candidate_index,
        "status": "failed",
        "task_id": "",
        "output": "",
        "error": "",
    }

    try:
        create_response = client.create_reference_to_video(
            shot=shot,
            settings=settings,
            reference_images=reference_images,
            candidate_index=candidate_index,
        )
        task_id = str(create_response["task_id"])
        candidate["task_id"] = task_id
        candidate["create_response"] = sanitize_response(create_response)

        print(f"Task ID: {task_id}")
        print("Waiting...")

        result = client.wait_for_completion(task_id, settings)
        video_url = client.extract_video_url(result)

        print("Downloading...")
        output_path = next_output_path(output_dir, shot.id, candidate_index)
        download_video(str(video_url), output_path)

        relative_output = str(output_path.relative_to(PROJECT_ROOT))
        candidate.update(
            {
                "status": "success",
                "result": sanitize_response(result),
                "output": relative_output,
                "finished_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        print("Saved:")
        print(relative_output)
    except (ViduError, SeedanceError, DownloadError) as exc:
        candidate["error"] = format_error(exc)
        print_user_error(exc)

    return candidate


def load_api_key(provider: str) -> str:
    if provider == "seedance":
        return load_seedance_api_key(PROJECT_ROOT)
    if provider == "vidu":
        return load_vidu_api_key(PROJECT_ROOT)
    raise ConfigError(f"不支持的 provider：{provider}")


def create_provider_client(provider: str, api_key: str, api_base_url: str) -> Any:
    if provider == "seedance":
        return SeedanceClient(api_key, base_url=api_base_url)
    if provider == "vidu":
        return ViduClient(api_key, base_url=api_base_url)
    raise ConfigError(f"不支持的 provider：{provider}")


def sanitize_response(response: dict[str, Any]) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}
    for key, value in response.items():
        if key == "images" and isinstance(value, list):
            sanitized[key] = [
                "<base64 image omitted>" if isinstance(item, str) and item.startswith("data:image/")
                else item
                for item in value
            ]
        elif key == "content" and isinstance(value, list):
            sanitized[key] = sanitize_content(value)
        else:
            sanitized[key] = value
    return sanitized


def sanitize_content(content: list[Any]) -> list[Any]:
    sanitized: list[Any] = []
    for item in content:
        if not isinstance(item, dict):
            sanitized.append(item)
            continue
        clean = dict(item)
        image = clean.get("image_url")
        if isinstance(image, dict) and isinstance(image.get("url"), str):
            if image["url"].startswith("data:image/"):
                clean["image_url"] = {**image, "url": "<base64 image omitted>"}
        sanitized.append(clean)
    return sanitized


def print_header(shot: Any, default_model: str, reference_paths: list[Path]) -> None:
    print("=" * 50)
    print("AI Drama Generator")
    print("=" * 50)
    print()
    print(f"Shot       : {shot.id}")
    print(f"Character  : {shot.character}")
    print(f"References : {len(reference_paths)}")
    print(f"Model      : {shot.model or default_model}")
    print(f"Duration   : {shot.duration}s")
    print(f"Resolution : {shot.resolution}")
    print(f"Aspect     : {shot.aspect_ratio}")
    print(f"Candidates : {shot.candidate_count}")


def print_user_error(exc: DramaError) -> None:
    print()
    print("错误：")
    print(str(exc))
    if isinstance(exc, (ViduError, SeedanceError)):
        if exc.http_status is not None:
            print(f"HTTP Status: {exc.http_status}")
        if exc.api_code:
            print(f"API error code: {exc.api_code}")
        if exc.api_message:
            print(f"API error message: {exc.api_message}")


def format_error(exc: DramaError) -> str:
    parts = [str(exc)]
    if isinstance(exc, (ViduError, SeedanceError)):
        if exc.http_status is not None:
            parts.append(f"HTTP Status: {exc.http_status}")
        if exc.api_code:
            parts.append(f"API error code: {exc.api_code}")
        if exc.api_message:
            parts.append(f"API error message: {exc.api_message}")
    return " | ".join(parts)


if __name__ == "__main__":
    sys.exit(main())
