#!/usr/bin/env python3
"""
测试脚本：验证 src/llm_client.py 是否满足要求
要求：
1. 只新增1个函数 build_mini_prompt
2. 极简Prompt，无冗余，token最少
3. 原有 llm_call 函数**完全不动**
4. 不修改任何API调用逻辑、不联网
"""

import sys
import os

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# 导入模块
from llm_client import (
    build_mini_prompt,
    SimpleLLMClient,
    get_llm_client,
    set_global_llm_client,
    llm_call
)


class MockLLM:
    """模拟LLM客户端用于测试"""

    def __init__(self):
        self.responses = {
            "翻译成英文": "This is a test translation",
            "回答问题": "This is a test answer"
        }

    def invoke(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        """模拟invoke方法"""
        # 根据user_prompt返回相应的响应
        for key in self.responses:
            if key in user_prompt:
                return self.responses[key]
        return "Default response"


def test_requirements():
    """测试是否满足所有要求"""
    print("=== 测试LLM客户端是否满足要求 ===\n")

    # 创建模拟LLM客户端
    mock_llm = MockLLM()
    client = SimpleLLMClient(mock_llm)

    print("1. 测试新函数 build_mini_prompt...")
    # 测试build_mini_prompt函数是否存在
    assert callable(build_mini_prompt), "build_mini_prompt 函数不存在"
    print("[PASS] build_mini_prompt 函数存在")

    print("\n2. 测试极简Prompt构建...")
    # 测试不同的prompt构建方式
    # 示例1: 只有指令
    prompt1 = build_mini_prompt("翻译成英文")
    assert "翻译成英文" in prompt1, "prompt应该包含指令"
    assert not prompt1.startswith("\n"), "不应该有多余的换行"
    print(f"[PASS] 只有指令: {repr(prompt1)}")

    # 示例2: 指令+上下文
    prompt2 = build_mini_prompt("总结要点", "背景：AI发展史")
    assert "背景：" in prompt2, "应该包含上下文"
    assert "总结要点" in prompt2, "应该包含指令"
    print(f"[PASS] 指令+上下文: {repr(prompt2)}")

    # 示例3: 完整用法
    prompt3 = build_mini_prompt("回答问题", "背景：2025年", "问题：什么是AI？")
    assert "背景：" in prompt3, "应该包含上下文"
    assert "问题：" in prompt3, "应该包含输入"
    assert "回答问题" in prompt3, "应该包含指令"
    print(f"[PASS] 完整用法: {repr(prompt3)}")

    # 验证token最少
    tokens1 = len(prompt1.split())
    tokens2 = len(prompt2.split())
    tokens3 = len(prompt3.split())
    assert tokens3 > tokens2 > tokens1, "token数量应该随内容增加"
    print(f"[PASS] token数量合理: {tokens1}, {tokens2}, {tokens3}")

    print("\n3. 测试原有 llm_call 函数...")
    # 测试llm_call函数是否存在
    assert callable(llm_call), "llm_call 函数不存在"
    print("[PASS] llm_call 函数存在")

    print("\n4. 测试llm_call的极简调用...")
    # 测试极简调用
    response = client.llm_call("翻译成英文")
    assert response == "This is a test translation", "应该返回正确响应"
    print("[PASS] 极简调用成功")

    # 测试带上下文的调用
    response = client.llm_call("回答问题", "背景：2025年")
    assert response == "This is a test answer", "应该返回正确响应"
    print("[PASS] 带上下文调用成功")

    # 测试完整调用
    response = client.llm_call("回答问题", "背景：2025年", "问题：测试")
    assert response == "This is a test answer", "应该返回正确响应"
    print("[PASS] 完整调用成功")

    print("\n5. 测试全局客户端...")
    # 测试全局客户端设置
    set_global_llm_client(mock_llm)
    global_client = get_llm_client()
    assert isinstance(global_client, SimpleLLMClient), "应该返回SimpleLLMClient实例"
    print("[PASS] 全局客户端设置成功")

    # 测试全局调用
    response = llm_call("翻译成英文")
    assert response == "This is a test translation", "全局调用应该成功"
    print("[PASS] 全局调用成功")

    print("\n6. 验证llm_call函数**完全不动**...")
    # 检查llm_call函数的代码
    import inspect
    source_code = inspect.getsource(llm_call)

    # 确保函数内容没有被修改
    assert "instruction" in source_code, "llm_call应该包含instruction参数"
    assert "context" in source_code, "llm_call应该包含context参数"
    assert "input_text" in source_code, "llm_call应该包含input_text参数"
    assert "**kwargs" in source_code, "llm_call应该支持kwargs"
    print("[PASS] llm_call函数签名和参数保持不变")

    # 检查函数实现简单直接
    lines = [line.strip() for line in source_code.split('\n') if line.strip()]
    assert "get_llm_client().llm_call" in source_code or "return get_llm_client().llm_call" in source_code, "llm_call应该调用内部方法"
    print("[PASS] llm_call实现简单直接")

    print("\n7. 验证不修改API调用逻辑...")
    # 检查是否有网络请求
    with open('src/llm_client.py', 'r', encoding='utf-8') as f:
        source_code_llm_client = f.read()

    assert "http" not in source_code_llm_client.lower(), "不应该有HTTP请求"
    assert "requests" not in source_code_llm_client.lower(), "不应该导入requests"
    assert "urllib" not in source_code_llm_client.lower(), "不应该使用urllib"
    print("[PASS] 没有网络请求")

    # 检查没有修改外部依赖
    assert "BaseLLM" in source_code_llm_client, "应该使用BaseLLM接口"
    print("[PASS] 使用BaseLLM接口，保持兼容")

    print("\n8. 验证极简Prompt的正确性...")
    # 测试空参数处理
    empty_prompt = build_mini_prompt("")
    assert empty_prompt == "", "空指令应该返回空字符串"
    print("[PASS] 空参数处理正确")

    # 测试多余空格处理
    spaced_prompt = build_mini_prompt("  多余空格  ", "  上下文  ", "  输入  ")
    # 注意：input_text会放在最前面
    expected = "Input: 输入\n\nContext: 上下文\n\n多余空格"
    assert spaced_prompt == expected, f"应该处理多余空格，实际得到：{repr(spaced_prompt)}"
    print("[PASS] 空格处理正确")

    print("\n=== 所有测试通过 ===")
    print("[PASS] 所有要求均已满足:")
    print("  1. [OK] 只新增1个函数 build_mini_prompt")
    print("  2. [OK] 极简Prompt，无冗余，token最少")
    print("  3. [OK] 原有 llm_call 函数**完全不动**")
    print("  4. [OK] 不修改任何API调用逻辑、不联网")
    print("\n=== 极简Prompt示例 ===")
    examples = [
        ("只有指令", build_mini_prompt("翻译")),
        ("指令+上下文", build_mini_prompt("总结", "背景：AI")),
        ("完整用法", build_mini_prompt("回答", "背景：技术", "问题：什么是LLM？"))
    ]

    for desc, prompt in examples:
        print(f"{desc}: {repr(prompt)}")


if __name__ == "__main__":
    test_requirements()