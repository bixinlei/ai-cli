"""对话历史管理:按会话 ID 保存为 JSONL,支持列表/查看/恢复/删除。"""
from __future__ import annotations

import json
import time
from pathlib import Path

from .config import HISTORY_DIR


def _safe_name(session: str) -> str:
    return "".join(c if c.isalnum() or c in "-_." else "_" for c in session)


def session_file(session: str) -> Path:
    return HISTORY_DIR / f"{_safe_name(session)}.jsonl"


def list_sessions() -> list[tuple[str, int, str]]:
    """返回 [(会话名, 消息数, 首条用户消息), ...],按修改时间倒序。"""
    if not HISTORY_DIR.exists():
        return []
    results = []
    for path in sorted(HISTORY_DIR.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True):
        messages = load_messages(path.stem)
        if not messages:
            continue
        first_user = next((m["content"] for m in messages if m["role"] == "user"), "")
        results.append((path.stem, len(messages), first_user))
    return results


def load_messages(session: str) -> list[dict]:
    path = session_file(session)
    if not path.exists():
        return []
    messages = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            messages.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return messages


def append_message(session: str, role: str, content: str) -> None:
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    record = {"role": role, "content": content, "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    with open(session_file(session), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def delete_session(session: str) -> bool:
    path = session_file(session)
    if path.exists():
        path.unlink()
        return True
    return False
