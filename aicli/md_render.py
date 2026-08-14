"""轻量 Markdown 高亮渲染(纯 ANSI 转义,零依赖)。

支持:标题、加粗、斜体、行内代码、代码块、引用、分隔线、列表。
逐行处理,流式友好;终端不支持颜色时自动回退为纯文本。
"""
from __future__ import annotations

import re

from . import console
from .console import color

_CODE_BLOCK_RE = re.compile(r"^```(\w*)\s*$")
_TITLE_RE = re.compile(r"^(#{1,6})\s+(.*)$")
_BOLD_ITALIC_RE = re.compile(r"\*\*\*(.+?)\*\*\*")
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_ITALIC_RE = re.compile(r"\*(.+?)\*")
_INLINE_CODE_RE = re.compile(r"`([^`]+)`")
_QUOTE_RE = re.compile(r"^>\s?(.*)$")
_RULE_RE = re.compile(r"^\s*([-*_])\1{2,}\s*$")
_LIST_RE = re.compile(r"^\s*([-*+]|\d+\.)\s+(.*)$")


def _render_inline(text: str) -> str:
    """渲染行内语法:行内代码 / 加粗斜体 / 加粗 / 斜体。"""
    text = _BOLD_ITALIC_RE.sub(lambda m: color(m.group(1), "bold", "magenta"), text)
    text = _BOLD_RE.sub(lambda m: color(m.group(1), "bold"), text)
    text = _ITALIC_RE.sub(lambda m: color(m.group(1), "3"), text)
    text = _INLINE_CODE_RE.sub(lambda m: color(m.group(1), "green"), text)
    return text


def render_markdown(md: str) -> str:
    """把 Markdown 文本渲染为带 ANSI 颜色的文本(不改变行数)。

    终端不支持颜色时直接返回原文,保证重定向/管道输出与输入一致。
    """
    if not console._ENABLED:
        return md

    out: list[str] = []
    in_code_block = False
    code_lang = ""

    for line in md.splitlines():
        m = _CODE_BLOCK_RE.match(line)
        if m:
            in_code_block = not in_code_block
            code_lang = m.group(1) or "code"
            if in_code_block:
                out.append(color(f"┌─ {code_lang} ─" + "─" * max(4, 24 - len(code_lang)), "dim"))
            else:
                out.append(color("└" + "─" * 30, "dim"))
            continue

        if in_code_block:
            out.append(color(line, "dim", "3"))
            continue

        m = _TITLE_RE.match(line)
        if m:
            level = len(m.group(1))
            text = _render_inline(m.group(2))
            if level <= 2:
                out.append(color(text, "bold", "yellow"))
            else:
                out.append(color(text, "bold", "cyan"))
            continue

        m = _QUOTE_RE.match(line)
        if m:
            out.append(color("▎ " + _render_inline(m.group(1)), "magenta"))
            continue

        if _RULE_RE.match(line):
            out.append(color("─" * 30, "dim"))
            continue

        m = _LIST_RE.match(line)
        if m:
            marker = color("• " if m.group(1) in ("-", "*", "+") else f"{m.group(1)} ", "cyan")
            out.append(marker + _render_inline(m.group(2)))
            continue

        out.append(_render_inline(line))

    return "\n".join(out)
