<div align="center">

```
   _____  _____   ______ __     __
  /  _  \|  _  \ /  ___/|  \   /  |
 /  /_\  \  / \  |  |___ |   \_/   |
/  |_|  \  | |  |\___  \|   _   _  |
\  \___/  \__|__/ ___|  ||  | | |  |
 \______/         \____/ |__| |_|__|

   Your AI Assistant in the Terminal · Zero Dependencies · Chat in One Command
```

# 🤖 ai-cli

**ChatGPT, right inside your terminal.** Zero third-party dependencies, works with any OpenAI-compatible API, streaming output, multi-turn conversations with auto-save — clone it and you're ready in 30 seconds.

[![Python](https://img.shields.io/badge/Python-3.8%2B-3776AB?logo=python&logoColor=white)](https://www.python.org)
[![Dependencies](https://img.shields.io/badge/dependencies-ZERO-2ea44f?logo=leaflet)](requirements.txt)
[![CI](https://github.com/bixinlei/ai-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/bixinlei/ai-cli/actions)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)](#)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](#contributing)
[![GitHub stars](https://img.shields.io/github/stars/bixinlei/ai-cli?style=social&label=Star)](https://github.com/bixinlei/ai-cli)

> 🚀 **Ready to use** · 🧩 **Works with anything** · ⚡ **Silky streaming** · 💾 **Remembers chats** · 🎨 **Beautiful terminal**

**[中文文档](README.md)** | **English**

---

</div>

## ✨ Why ai-cli?

| | ai-cli | Other CLI tools |
|---|---|---|
| 🪶 **Dependencies** | **Zero** — pure Python stdlib | Usually 10+ packages |
| 🌐 **Providers** | Any OpenAI-compatible API | Often locked to one vendor |
| 💬 **Multi-turn** | Auto-save + one-key resume | Many don't support |
| ⚡ **Streaming** | Character-by-character output | Spinner waiting |
| 📦 **Size** | ~50KB | Multiple MB |
| 🔧 **Scriptable** | `ai-cli ask "translate: hello"` | Hard to integrate |

## 🚀 Quick Start (30 seconds)

```bash
# 1. Clone
git clone https://github.com/bixinlei/ai-cli.git && cd ai-cli

# 2. Set your API key (any one of these)
python -m aicli config set api_key sk-xxxx     # write to config file
export AI_CLI_API_KEY=sk-xxxx                  # environment variable (macOS/Linux)
$env:AI_CLI_API_KEY = "sk-xxxx"                # environment variable (Windows)

# 3. Start chatting!
python -m aicli ask "Explain recursion in one sentence"
```

## 🥊 Battle Mode (NEW)

Compare multiple models on the same question — the ultimate model showdown:

```bash
# Compare models
ai-cli battle "Write a Python quick sort" --models gpt-4o-mini,deepseek-chat,qwen-plus

# Add a judge model to score all answers
ai-cli battle "Design a REST API" --models gpt-4o-mini,deepseek-chat --judge claude-3-5-sonnet

# Or set your default comparison lineup in config
ai-cli config set models '["gpt-4o-mini","deepseek-chat"]'
```

Each model streams its answer side-by-side; with `--judge`, a referee model scores
accuracy / clarity / usefulness and picks a champion.

## 🎨 Markdown Highlighting

Beautiful syntax-colored output with **zero dependencies** — headings, bold, inline code,
fenced code blocks, quotes, lists:

```bash
ai-cli ask "Explain how async/await works with a code example" --md
```

> Rendering is pure ANSI escapes. When output is piped/redirected, it falls back to
> plain text automatically.

## 🧩 Compatible Providers (any OpenAI-format API)

| Provider | base_url | Recommended model |
|---|---|---|
| 🌟 **OpenAI** | `https://api.openai.com/v1` (default) | `gpt-4o-mini` |
| 🐋 **DeepSeek** | `https://api.deepseek.com/v1` | `deepseek-chat` |
| 🌸 **Qwen** | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-plus` |
| 🚀 **Kimi** | `https://api.moonshot.cn/v1` | `moonshot-v1-8k` |
| 🧠 **Zhipu GLM** | `https://open.bigmodel.cn/api/paas/v4` | `glm-4-flash` |
| 🔓 **Ollama (local!)** | `http://localhost:11434/v1` | `qwen2.5:7b` |

> 💡 Any OpenAI-compatible API works — including **free local models** via Ollama / vLLM / LM Studio!

```bash
# Switch to DeepSeek in one line
ai-cli config set base_url https://api.deepseek.com/v1
ai-cli config set model deepseek-chat
```

## 📖 Command Reference

| Command | Description |
|---|---|
| `ai-cli ask "question"` | 💨 One-shot Q&A (no history, script-friendly) |
| `ai-cli battle "question" --models a,b` | 🥊 Model showdown |
| `ai-cli chat` | 💬 Interactive multi-turn (auto-saved) |
| `ai-cli chat -s work` | 🗂️ Multiple sessions |
| `ai-cli history list` | 📜 List all sessions |
| `ai-cli history show <session>` | 🔍 View a session |
| `ai-cli config show` | ⚙️ Show config |
| `ai-cli config set <key> <value>` | 🛠️ Change config |

**In-chat commands**: `/quit` exit · `/new` clear · `/model <name>` switch model · `/help` help

## ⚙️ Config Precedence

```
CLI arguments  >  Environment variables (AI_CLI_*)  >  Config file (~/.aicli/config.json)
```

Config file fields: `api_key` / `base_url` / `model` / `temperature` / `system_prompt` / `models`

## 🧪 Built-in Tests (offline)

```bash
python -m unittest discover -s tests -v
# 8 tests ... OK  ← built-in mock server, no real API needed
```

## 📁 Project Structure

```
ai-cli/
├── aicli/                  # 🧠 Core code
│   ├── cli.py              #    CLI & interactive logic
│   ├── client.py           #    OpenAI-compatible client (SSE streaming)
│   ├── config.py           #    3-level config precedence
│   ├── console.py          #    Colored output + Windows VT support
│   ├── md_render.py        #    Zero-dependency Markdown highlighting
│   └── history.py          #    JSONL session storage
├── tests/test_e2e.py       # 🧪 End-to-end tests (mock server)
├── .github/workflows/ci.yml# 🤖 CI (Python 3.9–3.13)
├── README.md               # 📖 Docs (Chinese)
├── README.en.md            # 📖 Docs (English)
└── LICENSE                 # 📄 MIT
```

## ❓ FAQ

**Q: Do I need an OpenAI account?**
No! Use DeepSeek / Kimi / Qwen, or run free local models with Ollama.

**Q: Really zero dependencies?**
Yes. Pure Python stdlib — no pip install needed, `clone` and run.

**Q: Windows support?**
Full support across platforms; Windows colors enabled via VT mode.

**Q: Where is my chat history stored?**
Locally at `~/.aicli/history/` as plain JSONL. Never uploads anywhere.

**Q: How to use it globally?**
```bash
pip install .                # installs the `ai-cli` command
alias ai='python -m aicli'   # or create an alias
```

## 🤝 Contributing

All contributions welcome! Just:

1. Fork → new branch
2. Make changes (with tests)
3. Open a Pull Request

Ideas (see [issues](https://github.com/bixinlei/ai-cli/issues)):
- [ ] Rendered Markdown in chat mode
- [ ] Token usage dashboard
- [ ] Session export/import (JSON/Markdown)
- [ ] Multi-provider streaming comparison

## 📄 License

[MIT License](LICENSE) © 2025 bixinlei

---

<div align="center">

### ⭐ Enjoying it?

**A Star is the best thank-you to open-source authors!**

[![GitHub stars](https://img.shields.io/github/stars/bixinlei/ai-cli?style=for-the-badge&label=⭐%20Star%20this%20repo)](https://github.com/bixinlei/ai-cli)

</div>
