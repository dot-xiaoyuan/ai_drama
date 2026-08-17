from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from .models import AppSettings, ConfigError


def load_settings(project_root: Path) -> AppSettings:
    settings_path = project_root / "config" / "settings.json"
    if not settings_path.exists():
        raise ConfigError(f"配置文件不存在：{settings_path}")

    try:
        data: dict[str, Any] = json.loads(settings_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"配置文件 JSON 格式错误：{settings_path}，{exc}") from exc

    try:
        return AppSettings(
            provider=str(data.get("provider", "seedance")),
            api_base_url=str(
                data.get("api_base_url", "https://ark.cn-beijing.volces.com/api/v3")
            ).rstrip("/"),
            default_model=str(data.get("default_model", "doubao-seedance-2-0-fast-260128")),
            poll_interval_seconds=int(data.get("poll_interval_seconds", 8)),
            task_timeout_seconds=int(data.get("task_timeout_seconds", 900)),
            max_reference_images=int(data.get("max_reference_images", 7)),
            max_reference_image_bytes=int(data.get("max_reference_image_bytes", 10485760)),
        )
    except (TypeError, ValueError) as exc:
        raise ConfigError("config/settings.json 中的数值配置格式不正确。") from exc


def load_vidu_api_key(project_root: Path) -> str:
    load_dotenv(project_root / ".env")
    api_key = os.getenv("VIDU_API_KEY", "").strip()
    if not api_key:
        raise ConfigError("VIDU_API_KEY 未配置，请复制 .env.example 为 .env 并填写 API Key。")
    return api_key


def load_seedance_api_key(project_root: Path) -> str:
    load_dotenv(project_root / ".env")
    api_key = os.getenv("ARK_API_KEY", "").strip()
    if not api_key:
        raise ConfigError("ARK_API_KEY 未配置，请在 .env 中填写火山方舟/BytePlus ModelArk API Key。")
    return api_key
