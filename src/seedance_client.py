from __future__ import annotations

import time
from datetime import datetime
from typing import Any

import httpx

from .models import AppSettings, SeedanceError, ShotConfig


class SeedanceClient:
    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://ark.cn-beijing.volces.com/api/v3",
        timeout_seconds: float = 60.0,
    ) -> None:
        self._client = httpx.Client(
            base_url=base_url,
            timeout=timeout_seconds,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "SeedanceClient":
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
        first_frame: str | None = None,
    ) -> dict[str, Any]:
        content: list[dict[str, Any]] = [{"type": "text", "text": shot.prompt}]
        if first_frame:
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": first_frame},
                    "role": "first_frame",
                }
            )
        else:
            content.extend(
                {
                    "type": "image_url",
                    "image_url": {"url": image},
                    "role": "reference_image",
                }
                for image in reference_images
            )

        payload: dict[str, Any] = {
            "model": shot.model or settings.default_model,
            "content": content,
            "resolution": shot.resolution,
            "ratio": shot.aspect_ratio,
            "duration": shot.duration,
            "generate_audio": False if shot.audio is None else shot.audio,
            "watermark": False,
        }
        if shot.seed is not None:
            payload["seed"] = shot.seed + candidate_index - 1

        response = self._request("POST", "/contents/generations/tasks", json=payload)
        task_id = response.get("id")
        if not task_id:
            raise SeedanceError("Seedance 创建任务成功返回中没有 id。")

        normalized = dict(response)
        normalized["task_id"] = str(task_id)
        return normalized

    def get_creation(self, task_id: str) -> dict[str, Any]:
        return self._request("GET", f"/contents/generations/tasks/{task_id}")

    def wait_for_completion(self, task_id: str, settings: AppSettings) -> dict[str, Any]:
        started_at = time.monotonic()
        while True:
            try:
                response = self.get_creation(task_id)
            except SeedanceError as exc:
                if "网络异常" in str(exc) or "请求超时" in str(exc):
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] 遇到临时网络抖动，正在自动重试查询...")
                    time.sleep(settings.poll_interval_seconds)
                    continue
                raise

            status = str(response.get("status", "unknown"))
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {status}")

            if status == "succeeded":
                return response
            if status in {"failed", "expired", "cancelled"}:
                error = response.get("error") if isinstance(response.get("error"), dict) else {}
                raise SeedanceError(
                    f"Seedance 任务结束但未成功：{status}。",
                    api_code=str(error.get("code") or ""),
                    api_message=str(error.get("message") or ""),
                )

            elapsed = time.monotonic() - started_at
            if elapsed >= settings.task_timeout_seconds:
                raise SeedanceError(
                    f"Seedance 任务超时，已等待 {settings.task_timeout_seconds} 秒。"
                )

            time.sleep(settings.poll_interval_seconds)

    def extract_video_url(self, result: dict[str, Any]) -> str:
        content = result.get("content")
        if not isinstance(content, dict):
            raise SeedanceError("Seedance 任务成功但没有返回 content。")

        video_url = content.get("video_url")
        if not video_url:
            raise SeedanceError("Seedance 任务成功但没有返回 content.video_url。")
        return str(video_url)

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        max_retries = 3
        last_exc: Exception | None = None
        for attempt in range(max_retries):
            try:
                response = self._client.request(method, path, **kwargs)
                break
            except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPError) as exc:
                last_exc = exc
                if attempt < max_retries - 1:
                    time.sleep(2 * (attempt + 1))
                    continue
                if isinstance(exc, httpx.TimeoutException):
                    raise SeedanceError("Seedance API 请求超时，请稍后重试。") from exc
                if isinstance(exc, httpx.NetworkError):
                    raise SeedanceError(f"Seedance API 网络异常：{exc}") from exc
                raise SeedanceError(f"Seedance API 请求异常：{exc}") from exc
        else:
            raise SeedanceError(f"Seedance API 请求失败：{last_exc}")

        try:
            body = response.json()
        except ValueError:
            body = {}

        if response.status_code >= 400:
            code = _pick_string(body, "code", "err_code", "error_code")
            message = _pick_string(body, "message", "error", "err_msg", "detail")
            if response.status_code in {401, 403}:
                message = message or "Seedance 认证失败，请检查 ARK_API_KEY 和模型开通状态。"
            elif response.status_code == 429:
                message = message or "Seedance API 限流，请稍后重试。"
            raise SeedanceError(
                "Seedance API 返回错误。",
                http_status=response.status_code,
                api_code=code,
                api_message=message,
            )

        if not isinstance(body, dict):
            raise SeedanceError("Seedance API 返回格式不是 JSON object。")

        error = body.get("error")
        if isinstance(error, dict) and error:
            raise SeedanceError(
                "Seedance API 返回业务错误。",
                api_code=str(error.get("code") or ""),
                api_message=str(error.get("message") or ""),
            )

        return body


def _pick_string(data: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = data.get(key)
        if value:
            return str(value)
    return ""
