"""ai-cli 命令行入口与交互逻辑。

用法:
  ai-cli ask "问题"                    单次提问(不保存历史)
  ai-cli chat [--session 会话名]       交互式多轮对话
  ai-cli history                       查看历史会话
  ai-cli history show <会话名>         查看某会话内容
  ai-cli history delete <会话名>       删除某会话
  ai-cli config                        查看当前配置
  ai-cli config set <key> <value>      修改配置并保存
"""
from __future__ import annotations

import argparse
import sys

from . import __version__
from . import console
from . import history as hist
from .client import ApiError, chat_once, chat_stream
from .config import CONFIG_FILE, Config
from .md_render import render_markdown

MAX_CONTEXT_TURNS = 20  # 超出后丢弃最老的对话轮次


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ai-cli",
        description="零依赖的命令行 AI 助手,支持任意 OpenAI 兼容 API。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"ai-cli {__version__}")
    parser.add_argument("--api-key", help="API key(优先级最高)")
    parser.add_argument("--base-url", help="API base URL(如 https://api.deepseek.com/v1)")
    parser.add_argument("--model", help="模型名称(如 deepseek-chat)")
    sub = parser.add_subparsers(dest="command")

    p_ask = sub.add_parser("ask", help="单次提问,不保存历史")
    p_ask.add_argument("prompt", nargs="+", help="问题内容")
    p_ask.add_argument("--md", action="store_true", help="Markdown 渲染模式(非流式,适合代码等结构化内容)")

    p_battle = sub.add_parser("battle", help="🥊 多模型同题对比")
    p_battle.add_argument("prompt", nargs="+", help="问题内容")
    p_battle.add_argument("-m", "--models", help="逗号分隔的模型列表(默认读配置 models)")
    p_battle.add_argument("--judge", help="指定评委模型,对各家回答评分")
    p_battle.add_argument("--no-md", action="store_true", help="关闭 Markdown 高亮")

    p_chat = sub.add_parser("chat", help="交互式多轮对话")
    p_chat.add_argument("-s", "--session", default="default", help="会话名(默认: default)")
    p_chat.add_argument("-m", "--model", help="本次会话使用的模型")
    p_chat.add_argument("-t", "--temperature", type=float, help="采样温度")
    p_chat.add_argument("--no-stream", action="store_true", help="关闭流式输出")

    p_hist = sub.add_parser("history", help="管理对话历史")
    hist_sub = p_hist.add_subparsers(dest="hist_cmd")
    hist_sub.add_parser("list", help="列出所有会话")
    p_show = hist_sub.add_parser("show", help="查看会话内容")
    p_show.add_argument("session", help="会话名")
    p_del = hist_sub.add_parser("delete", help="删除会话")
    p_del.add_argument("session", help="会话名")

    p_cfg = sub.add_parser("config", help="查看/修改配置")
    cfg_sub = p_cfg.add_subparsers(dest="cfg_cmd")
    cfg_sub.add_parser("show", help="查看当前生效配置")
    p_set = cfg_sub.add_parser("set", help="设置配置项")
    p_set.add_argument("key", choices=["api_key", "base_url", "model", "temperature", "system_prompt"])
    p_set.add_argument("value", help="配置值(api_key 建议同时写入环境变量)")

    return parser


def _apply_overrides(cfg: Config, args) -> Config:
    """命令行参数覆盖配置。"""
    if getattr(args, "api_key", None):
        cfg.api_key = args.api_key
    if getattr(args, "base_url", None):
        cfg.base_url = args.base_url
    if getattr(args, "model", None):
        cfg.model = args.model
    if getattr(args, "temperature", None) is not None:
        cfg.temperature = args.temperature
    return cfg


def _check_key(cfg: Config) -> bool:
    if not cfg.api_key:
        console.print_error(
            "未配置 API key。请运行: ai-cli config set api_key <你的key>\n"
            "或设置环境变量 AI_CLI_API_KEY。"
        )
        return False
    return True


def cmd_ask(args) -> int:
    cfg = _apply_overrides(Config.load(), args)
    if not _check_key(cfg):
        return 1
    text = " ".join(args.prompt)
    try:
        if args.md:
            # 渲染模式:一次性获取完整回复并做 Markdown 高亮
            reply, usage = chat_once(cfg, [], text)
            print(render_markdown(reply))
        else:
            # 默认流式输出,像 ChatGPT 一样逐字显示
            reply, usage = chat_stream(cfg, [], text, on_delta=lambda p: print(p, end="", flush=True))
            print()
        if usage:
            console.print_system(f"tokens: {usage.get('total_tokens', '?')} 模型: {cfg.model}")
        return 0
    except ApiError as exc:
        console.print_error(str(exc))
        return 1


def cmd_battle(args) -> int:
    """多模型同题对比:让多个模型回答同一个问题,可选评委评分。"""
    cfg = _apply_overrides(Config.load(), args)
    if not _check_key(cfg):
        return 1

    question = " ".join(args.prompt)
    models = [m.strip() for m in (args.models or "").split(",") if m.strip()]
    if not models:
        models = [m.strip() for m in getattr(cfg, "models", []) if m.strip()]
    if not models:
        models = [cfg.model]

    judge = getattr(args, "judge", None)

    print(console.color("=" * 52, "dim"))
    print(console.color(f"🥊 BATTLE  {len(models)} 模型同台竞技", "bold", "yellow"))
    print(console.color(f"问题: {question}", "bold"))
    print(console.color("=" * 52, "dim"))

    replies: list[tuple[str, str]] = []
    for i, model in enumerate(models, 1):
        session_cfg = Config(**{**cfg.__dict__, "model": model})
        print()
        print(console.color(f"┌─ [{i}/{len(models)}] {model} " + "─" * max(4, 26 - len(model)), "cyan", "bold"))
        try:
            reply, _ = chat_stream(session_cfg, [], question, on_delta=lambda p: print(p, end="", flush=True))
            print()
        except ApiError as exc:
            console.print_error(f"{model} 调用失败: {exc}")
            reply = f"(调用失败: {exc})"
        print(console.color("└" + "─" * 40, "cyan", "bold"))
        replies.append((model, reply))

    if judge:
        print()
        print(console.color(f"⚖️ 评委 {judge} 正在评分...", "bold", "magenta"))
        summary = _judge_review(cfg, judge, question, replies)
        print(console.color("=" * 52, "dim"))
        print(console.color("📊 评委点评", "bold", "yellow"))
        print(render_markdown(summary) if not args.no_md else summary)
        print(console.color("=" * 52, "dim"))
    return 0


def _judge_review(cfg: Config, judge: str, question: str, replies: list[tuple[str, str]]) -> str:
    """把各模型回答打包交给评委模型,返回点评。"""
    parts = [f"问题: {question}\n\n"]
    for i, (model, reply) in enumerate(replies, 1):
        parts.append(f"--- 回答 {i}(模型: {model}) ---\n{reply}\n")
    prompt = (
        "你是严格的 AI 模型评委。以下是多个模型对同一问题的回答,请从准确性、"
        "清晰度、实用性三方面评分(每项满分 10 分),并用 Markdown 输出对比表和冠军模型。\n\n"
        + "\n".join(parts)
    )
    session_cfg = Config(**{**cfg.__dict__, "model": judge, "temperature": 0.2})
    reply, _ = chat_once(session_cfg, [], prompt)
    return reply


def cmd_chat(args) -> int:
    cfg = _apply_overrides(Config.load(), args)
    if not _check_key(cfg):
        return 1

    console.init()
    session = args.session
    messages = hist.load_messages(session)
    if messages:
        console.print_system(f"恢复会话 '{session}' 共 {len(messages)} 条消息")
    print(console.color("输入 /quit 退出, /new 清空历史, /model 切换模型, /help 查看帮助", "dim"))
    print(console.color("=" * 56, "dim"))

    model = args.model or cfg.model
    temperature = args.temperature if args.temperature is not None else cfg.temperature

    while True:
        try:
            raw = input(console.color("❯ You:  ", "green", "bold")).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not raw:
            continue

        if raw.startswith("/"):
            if raw == "/quit":
                break
            elif raw == "/new":
                messages = []
                hist.delete_session(session)
                console.print_system("已清空当前会话")
                continue
            elif raw == "/help":
                print(console.color("/quit 退出  /new 清空历史  /model <名称> 切换模型", "dim"))
                continue
            elif raw.startswith("/model"):
                parts = raw.split(maxsplit=1)
                if len(parts) == 2:
                    model = parts[1].strip()
                    console.print_system(f"已切换模型: {model}")
                else:
                    console.print_system(f"当前模型: {model}")
                continue
            else:
                console.print_error(f"未知命令: {raw}")
                continue

        # 控制上下文长度:只保留最近 MAX_CONTEXT_TURNS*2 条消息
        context = messages[-MAX_CONTEXT_TURNS * 2 :]
        print(console.color("AI:   ", "cyan", "bold"), end="", flush=True)

        # 临时配置(会话级模型/温度)
        session_cfg = Config(**{**cfg.__dict__, "model": model, "temperature": temperature})

        try:
            if args.no_stream:
                reply, _ = chat_once(session_cfg, context, raw)
                console.print_assistant(reply)
            else:
                reply, _ = chat_stream(session_cfg, context, raw, on_delta=lambda p: print(p, end="", flush=True))
                print()
        except ApiError as exc:
            console.print_error(str(exc))
            continue

        messages.append({"role": "user", "content": raw})
        messages.append({"role": "assistant", "content": reply})
        hist.append_message(session, "user", raw)
        hist.append_message(session, "assistant", reply)
    return 0


def cmd_history(args) -> int:
    cmd = getattr(args, "hist_cmd", None) or "list"
    if cmd == "list":
        sessions = hist.list_sessions()
        if not sessions:
            console.print_system("暂无历史会话")
            return 0
        for name, count, first in sessions:
            preview = (first[:40] + "…") if len(first) > 40 else first
            print(f"  {name:<20} {count:>3} 条  {preview}")
        return 0
    if cmd == "show":
        messages = hist.load_messages(args.session)
        if not messages:
            console.print_error(f"会话 '{args.session}' 不存在或为空")
            return 1
        for m in messages:
            role = m["role"]
            content = m["content"]
            if role == "user":
                print(console.color(f"❯ You: {content}", "green"))
            else:
                print(console.color(f"AI: {content}", "cyan"))
            print()
        return 0
    if cmd == "delete":
        ok = hist.delete_session(args.session)
        if ok:
            console.print_system(f"已删除会话 '{args.session}'")
        else:
            console.print_error(f"会话 '{args.session}' 不存在")
        return 0 if ok else 1
    return 0


def cmd_config(args) -> int:
    cmd = getattr(args, "cfg_cmd", None) or "show"
    cfg = Config.load()
    if cmd == "show":
        print(f"配置文件: {CONFIG_FILE}")
        print(f"base_url : {cfg.base_url}")
        print(f"model    : {cfg.model}")
        print(f"api_key  : {cfg.api_key[:6] + '…' if cfg.api_key else '(未设置)'}")
        print(f"temperature: {cfg.temperature}")
        print(f"system_prompt: {cfg.system_prompt[:50] + ('…' if len(cfg.system_prompt) > 50 else '')}")
        return 0
    if cmd == "set":
        value = args.value
        if args.key in ("temperature",):
            value = float(value)
        setattr(cfg, args.key, value)
        cfg.save()
        console.print_system(f"已保存 {args.key}")
        return 0
    return 0


def main(argv=None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 0
    if args.command == "ask":
        return cmd_ask(args)
    if args.command == "battle":
        return cmd_battle(args)
    if args.command == "chat":
        return cmd_chat(args)
    if args.command == "history":
        return cmd_history(args)
    if args.command == "config":
        return cmd_config(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
