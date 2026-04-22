"""
DeepSeek LLM实现
使用DeepSeek API进行文本生成
"""

import os
import json
import re
from typing import Optional, Dict, Any, Union
from openai import OpenAI
from .base import BaseLLM


class DeepSeekLLM(BaseLLM):
    """DeepSeek LLM实现类"""

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        """
        初始化DeepSeek客户端

        Args:
            api_key: DeepSeek API密钥，如果不提供则从环境变量读取
            model_name: 模型名称，默认使用deepseek-chat
        """
        if api_key is None:
            api_key = os.getenv("DEEPSEEK_API_KEY")
            if not api_key:
                raise ValueError("DeepSeek API Key未找到！请设置DEEPSEEK_API_KEY环境变量或在初始化时提供")

        super().__init__(api_key, model_name)

        # 初始化OpenAI客户端，使用DeepSeek的endpoint
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://api.deepseek.com"
        )

        self.default_model = model_name or self.get_default_model()

        # 存储最后一次的响应和usage信息
        self._last_response = None
        self._last_usage = None

    def get_default_model(self) -> str:
        """获取默认模型名称"""
        return "deepseek-chat"

    def invoke(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        """
        调用DeepSeek API生成回复

        Args:
            system_prompt: 系统提示词
            user_prompt: 用户输入
            **kwargs: 其他参数，如temperature、max_tokens等

        Returns:
            DeepSeek生成的回复文本
        """
        try:
            # 构建消息
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]

            # 设置默认参数
            params = {
                "model": self.default_model,
                "messages": messages,
                "temperature": kwargs.get("temperature", 0.7),
                "max_tokens": kwargs.get("max_tokens", 4000),
                "stream": False
            }

            # 调用API
            response = self.client.chat.completions.create(**params)

            # 提取回复内容
            if response.choices and response.choices[0].message:
                content = response.choices[0].message.content

                # 存储响应和usage信息
                self._last_response = response
                self._last_usage = response.usage if hasattr(response, 'usage') else None

                return self.validate_response(content)
            else:
                return ""

        except Exception as e:
            print(f"DeepSeek API调用错误: {str(e)}")
            raise e

    def generate(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        """
        generate方法的实现（与invoke相同）

        Args:
            system_prompt: 系统提示词
            user_prompt: 用户输入
            **kwargs: 其他参数

        Returns:
            生成的回复文本
        """
        return self.invoke(system_prompt, user_prompt, **kwargs)

    def generate_json(self, system_prompt: str, user_prompt: str, **kwargs) -> Dict[str, Any]:
        """
        生成JSON格式的回复

        Args:
            system_prompt: 系统提示词
            user_prompt: 用户输入
            **kwargs: 其他参数

        Returns:
            解析后的JSON字典
        """
        # 获取原始响应
        response = self.invoke(system_prompt, user_prompt, **kwargs)

        # 尝试解析JSON
        try:
            # 尝试直接解析
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        # 尝试提取JSON代码块
        json_pattern = r'```(?:json)?\s*([\s\S]*?)```'
        matches = re.findall(json_pattern, response)

        for match in matches:
            try:
                return json.loads(match.strip())
            except json.JSONDecodeError:
                continue

        # 尝试提取花括号包围的JSON
        brace_pattern = r'\{[\s\S]*\}'
        brace_matches = re.findall(brace_pattern, response)

        for match in brace_matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue

        # 如果都失败，抛出异常
        raise ValueError(f"无法从响应中解析JSON: {response[:500]}...")

    def get_last_usage(self) -> Optional[Dict[str, Any]]:
        """
        获取最后一次API调用的usage信息

        Returns:
            usage信息字典，包含prompt_tokens, completion_tokens, total_tokens等
        """
        return self._last_usage

    def get_model_info(self) -> Dict[str, Any]:
        """
        获取当前模型信息

        Returns:
            模型信息字典
        """
        return {
            "provider": "DeepSeek",
            "model": self.default_model,
            "api_base": "https://api.deepseek.com"
        }
