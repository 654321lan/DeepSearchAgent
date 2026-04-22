"""
成本统计管理器
用于记录和计算LLM token消耗
"""

import time
from typing import Dict, List, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class TokenUsage:
    """单次API调用的token使用情况"""
    timestamp: datetime
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    operation: str = "unknown"
    cost: float = 0.0


@dataclass
class CostSummary:
    """成本统计摘要"""
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    api_calls: int = 0
    operations: Dict[str, int] = field(default_factory=dict)


class CostTracker:
    """成本跟踪器"""
    
    # 各提供商token价格（元/1K tokens）
    PRICING = {
        "zhipu": {
            "glm-4": 0.01,      # 0.01元/1K tokens
            "glm-4.5-air": 0.01,
            "glm-4-7": 0.01,
            "glm-4-6v": 0.01
        },
        "deepseek": {
            "deepseek-chat": 0.01
        },
        "openai": {
            "gpt-4o-mini": 0.01,
            "gpt-4o": 0.01
        }
    }
    
    def __init__(self):
        self.usage_records: List[TokenUsage] = []
        self.session_start_time = datetime.now()
        
    def record_usage(
        self, 
        provider: str, 
        model: str, 
        prompt_tokens: int, 
        completion_tokens: int,
        operation: str = "unknown"
    ) -> TokenUsage:
        """记录一次token使用"""
        total_tokens = prompt_tokens + completion_tokens
        
        # 计算成本
        cost = self._calculate_cost(provider, model, prompt_tokens, completion_tokens)
        
        usage = TokenUsage(
            timestamp=datetime.now(),
            provider=provider,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            operation=operation,
            cost=cost
        )
        
        self.usage_records.append(usage)
        return usage
    
    def record_from_response(self, response: Any, provider: str, model: str, operation: str = "unknown") -> TokenUsage:
        """从API响应对象记录token使用"""
        # 尝试从不同格式的响应中提取token使用信息
        prompt_tokens = 0
        completion_tokens = 0

        # 情况1: response 本身就是 usage 对象（直接有 prompt_tokens 属性）
        if hasattr(response, 'prompt_tokens') and hasattr(response, 'completion_tokens'):
            prompt_tokens = response.prompt_tokens
            completion_tokens = response.completion_tokens
        elif hasattr(response, 'usage'):
            # OpenAI兼容格式
            usage = response.usage
            if hasattr(usage, 'prompt_tokens'):
                prompt_tokens = usage.prompt_tokens
            if hasattr(usage, 'completion_tokens'):
                completion_tokens = usage.completion_tokens
        elif isinstance(response, dict) and 'usage' in response:
            # 字典格式
            usage = response['usage']
            prompt_tokens = usage.get('prompt_tokens', 0)
            completion_tokens = usage.get('completion_tokens', 0)

        return self.record_usage(provider, model, prompt_tokens, completion_tokens, operation)
    
    def _calculate_cost(self, provider: str, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """计算成本"""
        if provider in self.PRICING and model in self.PRICING[provider]:
            price_per_k = self.PRICING[provider][model]
            total_tokens = prompt_tokens + completion_tokens
            return (total_tokens / 1000) * price_per_k
        return 0.0
    
    def get_summary(self) -> CostSummary:
        """获取成本统计摘要"""
        summary = CostSummary()
        
        for usage in self.usage_records:
            summary.total_prompt_tokens += usage.prompt_tokens
            summary.total_completion_tokens += usage.completion_tokens
            summary.total_tokens += usage.total_tokens
            summary.total_cost += usage.cost
            summary.api_calls += 1
            
            # 统计操作类型
            if usage.operation not in summary.operations:
                summary.operations[usage.operation] = 0
            summary.operations[usage.operation] += 1
        
        return summary
    
    def get_formatted_summary(self) -> str:
        """获取格式化的成本统计"""
        summary = self.get_summary()
        
        # 计算会话时长
        session_duration = datetime.now() - self.session_start_time
        minutes = int(session_duration.total_seconds() / 60)
        seconds = int(session_duration.total_seconds() % 60)
        
        # 构建统计信息
        lines = [
            "## 💰 token使用统计",
            "",
            f"**会话时长**: {minutes}分{seconds}秒",
            f"**API调用次数**: {summary.api_calls}次",
            "",
            "### Token使用情况",
            f"- 提示Token: {summary.total_prompt_tokens:,}",
            f"- 补全Token: {summary.total_completion_tokens:,}",
            f"- 总Token: {summary.total_tokens:,}",
            "",
        ]
        
        # 添加操作分布
        for operation, count in summary.operations.items():
            lines.append(f"- {operation}: {count}次")
        
        
        return "\n".join(filter(None, lines))
    
    def clear(self):
        """清空记录"""
        self.usage_records.clear()
        self.session_start_time = datetime.now()
    
    def __str__(self) -> str:
        """字符串表示"""
        summary = self.get_summary()
        return f"CostTracker(api_calls={summary.api_calls}, total_tokens={summary.total_tokens:,}, cost={summary.total_cost:.4f})"


# 全局成本跟踪器实例
_global_cost_tracker = CostTracker()


def get_global_cost_tracker() -> CostTracker:
    """获取全局成本跟踪器"""
    return _global_cost_tracker


def record_cost(provider: str, model: str, prompt_tokens: int, completion_tokens: int, operation: str = "unknown") -> TokenUsage:
    """记录成本（便捷函数）"""
    return _global_cost_tracker.record_usage(provider, model, prompt_tokens, completion_tokens, operation)


def record_cost_from_response(response: Any, call_info: Dict = None, operation: str = "unknown") -> TokenUsage:
    """从响应记录成本（便捷函数）"""
    # 尝试从响应中提取 provider 和 model 信息
    provider = "unknown"
    model = "unknown"

    if call_info:
        provider = call_info.get('provider', 'unknown')
        model = call_info.get('model', 'unknown')

    return _global_cost_tracker.record_from_response(response, provider, model, operation)


def get_total_costs() -> CostSummary:
    """获取成本摘要（便捷函数）"""
    return _global_cost_tracker.get_summary()

def get_cost_summary() -> CostSummary:
    """获取成本摘要（便捷函数）"""
    return _global_cost_tracker.get_summary()


def get_formatted_cost_summary() -> str:
    """获取格式化的成本统计（便捷函数）"""
    return _global_cost_tracker.get_formatted_summary()


def reset_costs():
    """清空成本记录（便捷函数）"""
    _global_cost_tracker.clear()

def clear_cost_records():
    """清空成本记录（便捷函数）"""
    _global_cost_tracker.clear()