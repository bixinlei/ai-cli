"""OpenAI 兼容 API 客户端(基于标准库 urllib,零依赖)。

支持:
- 流式输出(SSE 逐块解析)
- 非流式输出
- 自定义 base_url(兼容 DeepSeek / 通义千问 / Kimi 等)
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Callable, Iterable, Optional


class ApiError(Exception):
    """API 调用错误,携带状态码与错误信息。"""


def _build_messages(system_prompt: str, history: list[dict], user_text: str) -> list[dict]:
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_text})
    return messages


def _request_json(base_url: str, path: str, headers: dict, payload: dict) -> dict:
    url = base_url.rstrip("/") + path
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise ApiError(f"HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise ApiError(f"网络错误: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise ApiError(f"响应解析失败: {exc}") from exc


def _stream_lines(resp) -> Iterable[str]:
    """逐行读取 SSE 响应。"""
    for raw in resp:
        line = raw.decode("utf-8", errors="replace").strip()
        if line:
            yield line


def chat_stream(
    config,
    history: list[dict],
    user_text: str,
    on_delta: Optional[Callable[[str], None]] = None,
) -> tuple[str, dict]:
    """流式对话。返回 (完整回复, 用量信息)。"""
    payload = {
        "model": config.model,
        "messages": _build_messages(config.system_prompt, history, user_text),
        "temperature": float(config.temperature),
        "stream": True,
    }
    url = config.base_url.rstrip("/") + "/chat/completions"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=config.headers(),
        method="POST",
    )
    try:
        resp = urllib.request.urlopen(req, timeout=300)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise ApiError(f"HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise ApiError(f"网络错误: {exc.reason}") from exc

    full_text = ""
    usage: dict = {}
    for line in _stream_lines(resp):
        if not line.startswith("data:"):
            continue
        data = line[5:].strip()
        if data == "[DONE]":
            break
        try:
            chunk = json.loads(data)
        except json.JSONDecodeError:
            continue
        choices = chunk.get("choices") or []
        if choices:
            delta = choices[0].get("delta") or {}
            piece = delta.get("content") or ""
            if piece:
                full_text += piece
                if on_delta:
                    on_delta(piece)
        if chunk.get("usage"):
            usage = chunk["usage"]
    return full_text, usage


def chat_once(config, history: list[dict], user_text: str) -> tuple[str, dict]:
    """非流式单次对话。"""
    payload = {
        "model": config.model,
        "messages": _build_messages(config.system_prompt, history, user_text),
        "temperature": float(config.temperature),
        "stream": False,
    }
    data = _request_json(config.base_url, "/chat/completions", config.headers(), payload)
    content = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
    return content or "", data.get("usage") or {}
