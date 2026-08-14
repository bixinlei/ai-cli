"""终端输出工具:彩色文本 + Windows ANSI 支持(零依赖)。"""
from __future__ import annotations

import os
import sys

_RESET = "\033[0m"
_COLORS = {
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
    "bold": "\033[1m",
    "dim": "\033[2m",
}

_ENABLED = sys.stdout.isatty()


def _enable_windows_vt() -> None:
    """在 Windows 上启用 ANSI 转义序列(VT 模式)。"""
    if os.name != "nt":
        return
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        mode = ctypes.c_uint32()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            kernel32.SetConsoleMode(handle, mode.value | 0x0004)  # ENABLE_VIRTUAL_TERMINAL_PROCESSING
    except Exception:
        pass


def init() -> None:
    _enable_windows_vt()


def color(text: str, *names: str) -> str:
    if not _ENABLED:
        return text
    codes = "".join(_COLORS.get(n, "") for n in names)
    return f"{codes}{text}{_RESET}"


def print_user(text: str) -> None:
    print(color("❯ You:  ", "green", "bold") + text)


def print_assistant(text: str, end: str = "\n") -> None:
    print(color(text, "cyan"), end=end)


def print_system(text: str) -> None:
    print(color(f"[{text}]", "yellow"))


def print_error(text: str) -> None:
    print(color(f"错误: {text}", "red"), file=sys.stderr)
