"""
LLM 调用包装器
用于记录每次 LLM 调用的 Token 消耗，同时保持与现有代码的兼容性
"""

from typing import Optional, Dict, Any, Union
from .cost_tracker import record_cost_from_response, get_total_costs, reset_costs, get_formatted_cost_summary
from ..llms.base import BaseLLM


class LLMTokenTracker:
    """LLM Token 消耗跟踪器"""

    def __init__(self, original_llm: BaseLLM):
        """
        初始化包装器

        Args:
            original_llm: 原始的 LLM 实例
        """
        self.original_llm = original_llm
        self._cost_tracker_enabled = True

    def invoke_with_tracking(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        """
        调用 LLM 并记录 Token 消耗

        Args:
            system_prompt: 系统提示词
            user_prompt: 用户输入
            **kwargs: 其他参数

        Returns:
            LLM 生成的回复文本（与原始 invoke 完全兼容）
        """
        if not self._cost_tracker_enabled:
            return self.original_llm.invoke(system_prompt, user_prompt, **kwargs)

        # 记录本次调用信息（用于后续从响应中提取 usage）
        call_info = {
            'provider': self.original_llm.__class__.__name__.lower().replace('llm', ''),
            'model': kwargs.get('model', self.original_llm.default_model),
            'operation': kwargs.get('operation', 'general')
        }

        # 调用原始 LLM
        response = self.original_llm.invoke(system_prompt, user_prompt, **kwargs)

        # 记录 Token 消耗和成本
        # 尝试从原始 LLM 实例中获取 usage 信息
        if hasattr(self.original_llm, '_last_usage') and self.original_llm._last_usage:
            # 如果 LLM 实例存储了 usage 信息，直接使用
            usage = self.original_llm._last_usage
            if usage:
                record_cost_from_response(usage, call_info, operation=call_info['operation'])
        elif hasattr(self.original_llm, '_last_response') and self.original_llm._last_response:
            # 检查 _last_response 是否是 usage 对象（有 prompt_tokens 属性）
            if hasattr(self.original_llm._last_response, 'prompt_tokens') and hasattr(self.original_llm._last_response, 'completion_tokens'):
                record_cost_from_response(self.original_llm._last_response, call_info, operation=call_info['operation'])
            # 兼容旧的方式：从 _last_response 中提取 usage
            elif isinstance(self.original_llm._last_response, dict) and 'usage' in self.original_llm._last_response:
                usage = self.original_llm._last_response.get('usage')
                if usage:
                    record_cost_from_response(usage, call_info, operation=call_info['operation'])
            # 如果 _last_response 是字典但没有 usage 字段，尝试直接使用
            elif isinstance(self.original_llm._last_response, dict) and 'prompt_tokens' in self.original_llm._last_response:
                record_cost_from_response(self.original_llm._last_response, call_info, operation=call_info['operation'])
        else:
            # 如果没有 usage，记录基本信息
            from .cost_tracker import record_cost
            record_cost(
                call_info['provider'],
                call_info['model'],
                0,  # prompt_tokens
                len(response),  # 使用响应长度作为 completion_tokens 的估计
                call_info['operation']
            )

        return response

    def invoke(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        """
        向后兼容的 invoke 方法，调用带跟踪的版本

        Args:
            system_prompt: 系统提示词
            user_prompt: 用户输入
            **kwargs: 其他参数

        Returns:
            LLM 生成的回复文本
        """
        return self.invoke_with_tracking(system_prompt, user_prompt, **kwargs)

    def generate(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        """
        generate 方法的包装（与原始接口兼容）

        Args:
            system_prompt: 系统提示词
            user_prompt: 用户输入
            **kwargs: 其他参数

        Returns:
            生成的回复文本
        """
        return self.invoke_with_tracking(system_prompt, user_prompt, **kwargs)

    def generate_json(self, system_prompt: str, user_prompt: str, **kwargs) -> Dict[str, Any]:
        """
        generate_json 方法的包装（与原始接口兼容）

        Args:
            system_prompt: 系统提示词
            user_prompt: 用户输入
            **kwargs: 其他参数

        Returns:
            解析后的 JSON 字典
        """
        # invoke_with_tracking 会自动记录token消耗
        response = self.invoke_with_tracking(system_prompt, user_prompt, **kwargs)

        # 调用原始的 generate_json 方法（它有自己的 JSON 解析逻辑）
        return self.original_llm.generate_json(system_prompt, user_prompt, **kwargs)

    def get_total_tokens(self) -> Dict[str, int]:
        """
        获取当前会话的总 Token 统计

        Returns:
            包含 token 统计的字典
        """
        costs = get_total_costs()
        return {
            'prompt_tokens': costs.total_prompt_tokens,
            'completion_tokens': costs.total_completion_tokens,
            'total_tokens': costs.total_tokens
        }

    def get_total_cost(self) -> float:
        """
        获取当前会话的总成本（人民币元）

        Returns:
            总成本（元）
        """
        costs = get_total_costs()
        return costs.total_cost

    def get_formatted_summary(self) -> str:
        """
        获取格式化的成本统计报告

        Returns:
            格式化的成本统计字符串
        """
        from .cost_tracker import get_formatted_cost_summary
        return get_formatted_cost_summary()

    def reset_tracking(self):
        """重置 Token 统计"""
        reset_costs()

    def enable_tracking(self, enabled: bool = True):
        """
        启用或禁用跟踪

        Args:
            enabled: 是否启用跟踪
        """
        self._cost_tracker_enabled = enabled

    def get_model_info(self) -> Dict[str, Any]:
        """
        获取模型信息

        Returns:
            模型信息字典
        """
        return self.original_llm.get_model_info()


# 创建包装器的便捷函数
def create_tracked_llm(llm: BaseLLM) -> LLMTokenTracker:
    """
    创建带跟踪的 LLM 实例

    Args:
        llm: 原始的 LLM 实例

    Returns:
        带跟踪的 LLM 实例
    """
    return LLMTokenTracker(llm)


# 替换原始 LLM 实例的便捷函数
def patch_llm_instance(llm: BaseLLM) -> LLMTokenTracker:
    """
    直接替换 LLM 实例的方法，使其支持跟踪

    Args:
        llm: 原始的 LLM 实例

    Returns:
        带跟踪的 LLM 实例
    """
    if hasattr(llm, '__original_invoke'):
        # 已经被包装过的实例，直接返回
        return llm

    # 保存原始方法
    original_invoke = llm.invoke
    original_generate = llm.generate
    original_generate_json = llm.generate_json

    # 创建跟踪器
    tracker = LLMTokenTracker(llm)

    # 替换方法
    llm.invoke = tracker.invoke
    llm.generate = tracker.generate
    llm.generate_json = tracker.generate_json

    # 保存引用，避免重复包装
    llm.__original_invoke = original_invoke
    llm.__original_generate = original_generate
    llm.__original_generate_json = original_generate_json
    llm.__tracker = tracker

    return tracker