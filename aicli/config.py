"""配置管理:API key、base URL、模型等。

配置优先级(从低到高):
1. 配置文件 ~/.aicli/config.json
2. 环境变量 AI_CLI_API_KEY / AI_CLI_BASE_URL / AI_CLI_MODEL
3. 命令行参数(--api-key / --base-url / --model)
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

CONFIG_DIR = Path.home() / ".aicli"
CONFIG_FILE = CONFIG_DIR / "config.json"
HISTORY_DIR = CONFIG_DIR / "history"

DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4o-mini"


@dataclass
class Config:
    api_key: str = ""
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    temperature: float = 0.7
    system_prompt: str = "You are a helpful assistant."
    models: list = field(default_factory=list)  # battle 模式使用的模型列表
    extra: dict = field(default_factory=dict)

    @classmethod
    def load(cls) -> "Config":
        """按优先级合并加载配置。"""
        cfg = cls()

        # 1. 配置文件
        if CONFIG_FILE.exists():
            try:
                data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
                for key in ("api_key", "base_url", "model", "temperature", "system_prompt", "models"):
                    if key in data:
                        setattr(cfg, key, data[key])
                cfg.extra = {k: v for k, v in data.items() if k not in cfg.__dataclass_fields__}
            except (json.JSONDecodeError, OSError) as exc:
                print(f"[warn] 配置文件解析失败,已忽略: {exc}")

        # 2. 环境变量
        env_map = {
            "AI_CLI_API_KEY": "api_key",
            "AI_CLI_BASE_URL": "base_url",
            "AI_CLI_MODEL": "model",
            "AI_CLI_TEMPERATURE": "temperature",
        }
        for env_name, attr in env_map.items():
            value = os.environ.get(env_name)
            if value:
                setattr(cfg, attr, value)
        if os.environ.get("AI_CLI_SYSTEM_PROMPT"):
            cfg.system_prompt = os.environ["AI_CLI_SYSTEM_PROMPT"]

        return cfg

    def save(self) -> None:
        """把当前配置写入配置文件。"""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            "api_key": self.api_key,
            "base_url": self.base_url,
            "model": self.model,
            "temperature": self.temperature,
            "system_prompt": self.system_prompt,
            "models": self.models,
        }
        data.update(self.extra)
        CONFIG_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def headers(self) -> dict:
        """构造请求头。"""
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h
