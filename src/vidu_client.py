from __future__ import annotations

import time
from datetime import datetime
from typing import Any

import httpx

from .models import AppSettings, ShotConfig, ViduError


class ViduClient:
    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://api.vidu.com",
        timeout_seconds: float = 60.0,
    ) -> None:
        self._client = httpx.Client(
            base_url=base_url,
            timeout=timeout_seconds,
            headers={
                "Authorization": f"Token {api_key}",
                "Content-Type": "application/json",
            },
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "ViduClient":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def create_reference_to_video(
        self,
        *,
        shot: ShotConfig,
        settings: AppSettings,
        reference_images: list[str],
        candidate_index: int,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": shot.model or settings.default_model,
            "images": reference_images,
            "prompt": shot.prompt,
            "duration": shot.duration,
            "aspect_ratio": shot.aspect_ratio,
            "resolution": shot.resolution,
            "audio": False if shot.audio is None else shot.audio,
        }
        if shot.seed is not None:
            payload["seed"] = shot.seed + candidate_index - 1
        if shot.movement_amplitude:
            payload["movement_amplitude"] = shot.movement_amplitude

        response = self._request("POST", "/ent/v2/reference2video", json=payload)
        task_id = response.get("task_id")
        if not task_id:
            raise ViduError("Vidu 创建任务成功返回中没有 task_id。")
        return response

    def get_creation(self, task_id: str) -> dict[str, Any]:
        return self._request("GET", f"/ent/v2/tasks/{task_id}/creations")

    def wait_for_completion(self, task_id: str, settings: AppSettings) -> dict[str, Any]:
        started_at = time.monotonic()
        while True:
            response = self.get_creation(task_id)
            state = str(response.get("state", "unknown"))
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {state}")

            if state == "success":
                return response
            if state == "failed":
                raise ViduError(
                    "Vidu 任务生成失败。",
                    api_code=str(response.get("err_code") or ""),
                    api_message=str(response.get("message") or response.get("err_msg") or ""),
                )

            elapsed = time.monotonic() - started_at
            if elapsed >= settings.task_timeout_seconds:
                raise ViduError(
                    f"Vidu 任务超时，已等待 {settings.task_timeout_seconds} 秒。"
                )

            time.sleep(settings.poll_interval_seconds)

    def extract_video_url(self, result: dict[str, Any]) -> str:
        creations = result.get("creations")
        if not isinstance(creations, list) or not creations:
            raise ViduError("Vidu 任务成功但没有返回 creations。")

        video_url = creations[0].get("url") if isinstance(creations[0], dict) else None
        if not video_url:
            raise ViduError("Vidu 任务成功但没有返回视频 URL。")
        return str(video_url)

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        try:
            response = self._client.request(method, path, **kwargs)
        except httpx.TimeoutException as exc:
            raise ViduError("Vidu API 请求超时，请稍后重试。") from exc
        except httpx.NetworkError as exc:
            raise ViduError(f"Vidu API 网络异常：{exc}") from exc
        except httpx.HTTPError as exc:
            raise ViduError(f"Vidu API 请求异常：{exc}") from exc

        try:
            body = response.json()
        except ValueError:
            body = {}

        if response.status_code >= 400:
            code = _pick_string(body, "err_code", "code", "error_code")
            message = _pick_string(body, "message", "error", "err_msg", "detail")
            if response.status_code == 401:
                message = message or "Vidu 认证失败，请检查 VIDU_API_KEY。"
            elif response.status_code == 429:
                message = message or "Vidu API 限流，请稍后重试。"
            raise ViduError(
                "Vidu API 返回错误。",
                http_status=response.status_code,
                api_code=code,
                api_message=message,
            )

        if not isinstance(body, dict):
            raise ViduError("Vidu API 返回格式不是 JSON object。")

        code = _pick_string(body, "err_code", "code", "error_code")
        if code:
            message = _pick_string(body, "message", "error", "err_msg", "detail")
            raise ViduError("Vidu API 返回业务错误。", api_code=code, api_message=message)

        return body


def _pick_string(data: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = data.get(key)
        if value:
            return str(value)
    return ""
