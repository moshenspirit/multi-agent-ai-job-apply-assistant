r"""
LLM 客户端 — AI 投递助手 2.0

设计目标（用户 2026-08-26 拍板）：
- "以后 Agent 接哪个 LLM，要随时更换" → **provider 抽象 + 环境变量切换**
- 当前实现：DeepSeek（OpenAI 兼容端点，JSON-mode 100% 稳定）
- 未来切换：改 .env 的 LLM_PROVIDER 即可（不需要改 Agent 代码）

支持的 provider（按 user-level MEMORY 已验证）：
- "deepseek" — DeepSeek-chat（OpenAI 兼容端点，JSON-mode 100% 稳定）✅ 默认
- "minimax" — MiniMax-M3（OpenAI 兼容 /v1 端点，sk-cp- key；需 `<think>` 过滤）
- "ollama" — 本地 qwen2.5:3b（OpenAI 兼容 http://localhost:11434/v1）

使用：
    from agents.llm_client import LLMClient
    client = LLMClient.from_env()   # 自动从环境变量读 provider + key
    text = client.chat([{"role": "user", "content": "hi"}])
    data = client.chat_json([{"role": "user", "content": "..."}])   # 强制 JSON 输出
"""
from __future__ import annotations

import json
import os
import re
from typing import Any

# === Provider 配置（来自 user-level MEMORY 的已知端点）===
PROVIDER_CONFIG = {
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
        "api_key_env": "DEEPSEEK_API_KEY",
    },
    "minimax": {
        "base_url": "https://api.minimaxi.com/v1",
        "model": "MiniMax-M3",
        "api_key_env": "MINIMAX_API_KEY",  # sk-cp- key
    },
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "model": "qwen2.5:3b",
        "api_key_env": "OLLAMA_API_KEY",  # ollama 一般不要 key
    },
}

# MiniMax 通病：`<think>` 标签会泄漏到 content（user-level MEMORY 已知）
THINK_TAG_RE = re.compile(r"<think>.*?</think>\s*", re.DOTALL)


def _strip_think_tags(text: str) -> str:
    """过滤 MiniMax-M3 泄漏的 <think> 标签（其他 provider 不会有，但过滤是幂等的）"""
    return THINK_TAG_RE.sub("", text or "")


class LLMClient:
    """
    LLM 客户端抽象 — 所有 Agent 通过这个类调用，不直接依赖某个 provider。

    加新 provider 只需在 PROVIDER_CONFIG 加一行 + 在 .env 配 api key。
    """

    def __init__(self, provider: str, base_url: str, model: str, api_key: str):
        self.provider = provider
        self.base_url = base_url
        self.model = model
        self.api_key = api_key
        self._client = None  # 延迟 import openai（避免 collector 不需要 LLM 时也加载）

    @classmethod
    def from_env(cls, provider: str | None = None) -> "LLMClient":
        """
        从环境变量加载配置。
        优先级：参数 provider > LLM_PROVIDER 环境变量 > 默认 "deepseek"

        自动尝试加载 .env 文件（从以下位置，按顺序）：
        1. 当前目录的 .env
        2. 仓库根 web/backend/.env（web backend 的 .env，2.0 复用）
        """
        # 尝试加载 .env（如果用户没装 dotenv 就静默跳过）
        try:
            from dotenv import load_dotenv
            # 1. 当前目录
            load_dotenv()
            # 2. web backend 目录（关键：web 已有 .env）
            backend_env = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),  # core/agents/
                "..", "..", "..", "web", "backend", ".env",
            )
            backend_env = os.path.normpath(backend_env)
            if os.path.exists(backend_env):
                load_dotenv(backend_env, override=False)  # 不覆盖已有 env
        except ImportError:
            pass

        provider = provider or os.getenv("LLM_PROVIDER", "deepseek")
        if provider not in PROVIDER_CONFIG:
            raise ValueError(
                f"未知 LLM provider: {provider}。可选: {list(PROVIDER_CONFIG.keys())}"
            )
        cfg = PROVIDER_CONFIG[provider]
        api_key = os.getenv(cfg["api_key_env"], "")
        if provider != "ollama" and not api_key:
            raise RuntimeError(
                f"未配置 {cfg['api_key_env']} 环境变量。\n"
                f"  当前 provider = {provider}\n"
                f"  请在 .env 或系统环境变量中设置 key"
            )
        return cls(
            provider=provider,
            base_url=cfg["base_url"],
            model=cfg["model"],
            api_key=api_key or "ollama",  # ollama 不需要真 key
        )

    def _get_client(self):
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError as e:
                raise RuntimeError(
                    "需要 openai 库（pip install openai）"
                ) from e
            self._client = OpenAI(base_url=self.base_url, api_key=self.api_key)
        return self._client

    def chat(self, messages: list[dict], temperature: float = 0.3) -> str:
        """普通对话，返回纯文本"""
        client = self._get_client()
        resp = client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
        )
        text = resp.choices[0].message.content or ""
        return _strip_think_tags(text)

    def chat_json(self, messages: list[dict], temperature: float = 0.3) -> dict | list:
        """
        JSON 模式对话（DeepSeek 100% 稳定；其他 provider 回退到 chat + 解析）

        返回 dict 或 list（按模型实际返回的 JSON 结构）。
        失败时抛 ValueError（带原始文本方便排查）。
        """
        client = self._get_client()
        try:
            resp = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                response_format={"type": "json_object"},
            )
            text = _strip_think_tags(resp.choices[0].message.content or "")
            return json.loads(text)
        except Exception as e:
            # 回退：不用 response_format，让模型自由返回
            try:
                resp = client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                )
                text = _strip_think_tags(resp.choices[0].message.content or "")
                # 尝试从 markdown ```json ... ``` 块中提取
                m = re.search(r"```(?:json)?\s*([\[{].*?[\]}])\s*```", text, re.DOTALL)
                if m:
                    return json.loads(m.group(1))
                # 直接解析
                return json.loads(text)
            except json.JSONDecodeError as je:
                raise ValueError(
                    f"LLM JSON 解析失败（provider={self.provider}）。原始文本: {text[:500]}"
                ) from je


# === Agent 使用示例 ===
#
# class SkirmishAgent(BaseAgent):
#     def __init__(self, **kwargs):
#         super().__init__(**kwargs)
#         self.llm = LLMClient.from_env()   # 自动读 .env
#
#     def run(self, state):
#         data = self.llm.chat_json([{"role": "user", "content": "分析这家公司..."}])
#         # ...
