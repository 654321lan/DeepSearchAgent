"""
LLM客户端简化实现
提供极简的Prompt构建和LLM调用功能
"""

import time
import threading
from typing import Optional, Dict, Any, Callable
from .llms.base import BaseLLM


class RateLimiter:
    """固定时间窗口速率限制器"""

    def __init__(self, max_requests: int, time_window: float):
        """
        初始化速率限制器

        Args:
            max_requests: 时间窗口内最大请求数
            time_window: 时间窗口长度（秒）
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []  # 存储请求时间戳
        self.lock = threading.Lock()

    def is_allowed(self) -> bool:
        """
        检查是否允许请求

        Returns:
            bool: 是否允许通过
        """
        with self.lock:
            current_time = time.time()

            # 清理过期的请求记录
            self.requests = [req_time for req_time in self.requests
                           if current_time - req_time < self.time_window]

            # 检查是否超过限制
            if len(self.requests) >= self.max_requests:
                return False

            # 记录新请求
            self.requests.append(current_time)
            return True

    def get_wait_time(self) -> float:
        """
        获取需要等待的时间（秒）

        Returns:
            float: 需要等待的时间，如果不需要等待则为0
        """
        with self.lock:
            if not self.requests:
                return 0

            current_time = time.time()
            oldest_request = min(self.requests)

            # 计算距离窗口结束还有多久
            wait_time = self.time_window - (current_time - oldest_request)
            return max(0, wait_time)


def rate_limited(max_requests: int = None, time_window: float = None):
    """
    固定时间窗口速率限制装饰器

    Args:
        max_requests: 时间窗口内最大请求数（None表示使用全局设置）
        time_window: 时间窗口长度（秒，None表示使用全局设置）

    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            # 使用全局速率限制器
            global _rate_limiter

            # 如果指定了参数，创建临时限制器（用于装饰器参数覆盖）
            if max_requests is not None and time_window is not None:
                temp_limiter = RateLimiter(max_requests, time_window)
                limiter = temp_limiter
            else:
                limiter = _rate_limiter

            if not limiter.is_allowed():
                wait_time = limiter.get_wait_time()
                print(f"速率限制: 已达到 {limiter.max_requests}/{limiter.time_window}秒 限制，等待 {wait_time:.2f} 秒...")
                time.sleep(wait_time)
                # 再次检查（可能在等待期间有其他请求）
                if not limiter.is_allowed():
                    raise RuntimeError(f"速率限制达到上限，请稍后重试")

            return func(*args, **kwargs)

        return wrapper

    return decorator


def build_mini_prompt(instruction: str, context: str = "", input_text: str = "") -> str:
    """
    构建极简Prompt，无冗余，token最少

    Args:
        instruction: 核心指令
        context: 可选上下文
        input_text: 可选输入文本

    Returns:
        极简格式的Prompt
    """
    # 处理None值
    instruction = instruction if instruction is not None else ""
    context = context if context is not None else ""
    input_text = input_text if input_text is not None else ""

    # 构建基础instruction
    prompt = instruction.strip()

    # 如果有context，添加到instruction前
    if context.strip():
        if prompt:  # 如果instruction不为空
            prompt = f"Context: {context.strip()}\n\n{prompt}"
        else:  # 如果instruction为空，只显示context
            prompt = f"Context: {context.strip()}"

    # 如果有input_text，添加到prompt前
    if input_text.strip():
        if prompt:  # 如果prompt不为空
            prompt = f"Input: {input_text.strip()}\n\n{prompt}"
        else:  # 如果prompt为空，只显示input_text
            prompt = f"Input: {input_text.strip()}"

    return prompt


class SimpleLLMClient:
    """简化的LLM客户端包装器"""

    def __init__(self, llm_client: BaseLLM):
        """
        初始化简化客户端

        Args:
            llm_client: 原始LLM客户端
        """
        self.llm_client = llm_client

    def llm_call(self, instruction: str, context: str = "", input_text: str = "", **kwargs) -> str:
        """
        极简LLM调用，保持与原有接口完全一致

        Args:
            instruction: 核心指令
            context: 可选上下文
            input_text: 可选输入文本
            **kwargs: 其他参数（与原始invoke方法一致）

        Returns:
            LLM生成的回复文本
        """
        # 使用极简prompt构建
        mini_prompt = build_mini_prompt(instruction, context, input_text)

        # 直接调用原始llm_client的invoke方法
        # 为了保持兼容性，这里假设原始llm_client有invoke方法
        if hasattr(self.llm_client, 'invoke'):
            return self.llm_client.invoke(
                system_prompt="",  # 不需要系统prompt，极简模式
                user_prompt=mini_prompt,
                **kwargs
            )
        else:
            # 如果没有invoke方法，尝试其他调用方式
            return self._call_llm_fallback(mini_prompt, **kwargs)

    def _call_llm_fallback(self, prompt: str, **kwargs) -> str:
        """
        回退调用方法，兼容不同LLM客户端

        Args:
            prompt: 提示词
            **kwargs: 其他参数

        Returns:
            LLM生成的回复文本
        """
        # 尝试直接调用
        try:
            return self.llm_client.invoke("", prompt, **kwargs)
        except Exception:
            # 如果还是失败，尝试其他方法
            if hasattr(self.llm_client, 'chat'):
                return self.llm_client.chat(prompt, **kwargs)
            elif hasattr(self.llm_client, 'generate'):
                return self.llm_client.generate(prompt, **kwargs)
            else:
                raise RuntimeError("无法调用LLM客户端，请检查接口")


# 全局客户端实例
_global_llm_client = None

# 全局速率限制器
_rate_limiter = RateLimiter(max_requests=10, time_window=60)


def get_llm_client(llm_client: Optional[BaseLLM] = None) -> SimpleLLMClient:
    """
    获取全局简化LLM客户端

    Args:
        llm_client: 可选的LLM客户端，如果提供则创建新实例

    Returns:
        简化的LLM客户端
    """
    global _global_llm_client

    if llm_client is not None:
        _global_llm_client = SimpleLLMClient(llm_client)
    elif _global_llm_client is None:
        raise ValueError("需要提供LLM客户端或先调用set_global_llm_client")

    return _global_llm_client


def set_global_llm_client(llm_client: BaseLLM):
    """
    设置全局LLM客户端

    Args:
        llm_client: LLM客户端
    """
    global _global_llm_client
    _global_llm_client = SimpleLLMClient(llm_client)


def set_rate_limit(max_requests: int, time_window: float):
    """
    设置全局速率限制

    Args:
        max_requests: 时间窗口内最大请求数
        time_window: 时间窗口长度（秒）
    """
    global _rate_limiter
    _rate_limiter = RateLimiter(max_requests, time_window)
    print(f"速率限制已更新: {max_requests}次请求/{time_window}秒")


def get_rate_limit_info() -> Dict[str, Any]:
    """
    获取当前速率限制信息

    Returns:
        速率限制信息字典
    """
    return {
        "max_requests": _rate_limiter.max_requests,
        "time_window": _rate_limiter.time_window,
        "current_requests": len(_rate_limiter.requests),
        "next_available_in": _rate_limiter.get_wait_time()
    }


def disable_rate_limit():
    """禁用速率限制"""
    global _rate_limiter
    # 创建一个允许无限请求的速率限制器
    _rate_limiter = RateLimiter(float('inf'), 1)
    print("速率限制已禁用")


def enable_rate_limit(max_requests: int = 10, time_window: float = 60):
    """
    启用速率限制

    Args:
        max_requests: 时间窗口内最大请求数（默认10）
        time_window: 时间窗口长度（秒，默认60）
    """
    set_rate_limit(max_requests, time_window)


@rate_limited(max_requests=10, time_window=60)  # 默认限制：每60秒最多10次请求
def llm_call(instruction: str, context: str = "", input_text: str = "", **kwargs) -> str:
    """
    全局极简LLM调用函数

    Args:
        instruction: 核心指令
        context: 可选上下文
        input_text: 可选输入文本
        **kwargs: 其他参数

    Returns:
        LLM生成的回复文本
    """
    return get_llm_client().llm_call(instruction, context, input_text, **kwargs)


# 示例使用
if __name__ == "__main__":
    # 示例演示（需要实际的LLM客户端才能运行）
    print("=== 极简Prompt构建示例 ===")

    # 示例1: 只有指令
    prompt1 = build_mini_prompt("翻译成英文")
    print(f"示例1: {prompt1}")

    # 示例2: 指令+上下文
    prompt2 = build_mini_prompt("总结要点", "这是一篇关于人工智能的文章")
    print(f"示例2: {prompt2}")

    # 示例3: 完整用法
    prompt3 = build_mini_prompt("回答问题", "背景：2025年AI发展趋势", "问题：什么是大语言模型？")
    print(f"示例3: {prompt3}")

    print("\n=== 极简Prompt优势 ===")
    print("- token最少，无冗余内容")
    print("- 结构清晰，易于理解")
    print("- 灵活组合，可按需添加信息")
    print("- 保持与原有LLM接口兼容")