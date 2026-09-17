"""
LLM 客户端封装
统一 OpenAI API 调用，支持重试和错误处理
"""
import time
from openai import OpenAI
from app.config import Config


def create_client() -> OpenAI:
    """创建 OpenAI 客户端"""
    return OpenAI(
        api_key=Config.OPENAI_API_KEY,
        base_url=Config.OPENAI_BASE_URL,
    )


def chat_completion(
    messages: list[dict],
    model: str | None = None,
    temperature: float = 0.1,
    max_tokens: int = 2000,
    max_retries: int = 3,
    retry_delay: float = 2.0,
) -> str:
    """
    调用 LLM 并返回文本结果，带重试机制

    Args:
        messages: 消息列表
        model: 模型名称，默认使用配置中的模型
        temperature: 温度参数
        max_tokens: 最大 token 数
        max_retries: 最大重试次数
        retry_delay: 重试间隔（秒）

    Returns:
        LLM 返回的文本内容
    """
    client = create_client()
    model_name = model or Config.OPENAI_MODEL

    last_error = None
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            content = response.choices[0].message.content or ""

            # 记录 token 消耗
            usage = response.usage
            if usage:
                print(f"[LLM] tokens: prompt={usage.prompt_tokens}, "
                      f"completion={usage.completion_tokens}, "
                      f"total={usage.total_tokens}")

            return content
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                print(f"[LLM] 第 {attempt + 1} 次调用失败，{retry_delay}秒后重试: {e}")
                time.sleep(retry_delay)
            else:
                raise RuntimeError(f"LLM 调用失败（已重试 {max_retries} 次）: {last_error}")

    raise RuntimeError(f"LLM 调用失败: {last_error}")
