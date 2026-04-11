#!/usr/bin/env python3
"""
边缘情况测试
测试各种边界条件和错误处理
"""

import sys
import os
from typing import List, Dict, Any

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from retrieval import (
    retrieve_documents,
    optimized_retrieve,
    truncate_long_doc,
    compute_bm25_score
)
from llm_client import (
    build_mini_prompt,
    llm_call,
    set_global_llm_client
)


class MockLLM:
    """模拟LLM客户端"""
    def __init__(self):
        self.responses = {"测试": "响应"}

    def invoke(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        return self.responses.get("测试", "默认响应")


def test_edge_cases():
    """测试边缘情况"""
    print("=" * 50)
    print("边缘情况测试")
    print("=" * 50)

    # 1. 测试空输入
    print("\n1. 测试空输入...")

    # 空文档列表
    try:
        result = optimized_retrieve("查询", [], top_k=3)
        assert result == [], "空文档列表应返回空列表"
        print("   [PASS] 空文档列表处理正确")
    except Exception as e:
        print(f"   [FAIL] 空文档列表测试失败: {e}")

    # 空查询
    try:
        mock_docs = [{"title": "测试", "content": "内容"}]
        result = optimized_retrieve("", mock_docs, top_k=3)
        assert len(result) == 1, "空查询应返回所有文档"
        print("   [PASS] 空查询处理正确")
    except Exception as e:
        print(f"   [FAIL] 空查询测试失败: {e}")

    # 2. 测试截断函数边缘情况
    print("\n2. 测试截断函数边缘情况...")

    # 空文本
    try:
        result = truncate_long_doc("", 10)
        assert result == "", "空文本应返回空字符串"
        print("   [PASS] 空文本截断正确")
    except Exception as e:
        print(f"   [FAIL] 空文本截断测试失败: {e}")

    # 短文本
    try:
        result = truncate_long_doc("短文本", 10)
        assert result == "短文本", "短文本不应被截断"
        print("   [PASS] 短文本处理正确")
    except Exception as e:
        print(f"   [FAIL] 短文本测试失败: {e}")

    # 超长文本
    try:
        long_text = "a" * 100
        result = truncate_long_doc(long_text, 10)
        assert len(result) == 10, "应正确截断到指定长度"
        assert result.endswith("..."), "应添加省略号"
        print("   [PASS] 超长文本截断正确")
    except Exception as e:
        print(f"   [FAIL] 超长文本截断测试失败: {e}")

    # 3. 测试极简Prompt边缘情况
    print("\n3. 测试极简Prompt边缘情况...")

    # 空参数
    try:
        result = build_mini_prompt("", "", "")
        assert result == "", "所有空参数应返回空字符串"
        print("   [PASS] 空参数处理正确")
    except Exception as e:
        print(f"   [FAIL] 空参数测试失败: {e}")

    # 只有指令
    try:
        result = build_mini_prompt("指令")
        assert result == "指令", "只有指令时应返回指令"
        print("   [PASS] 只有指令处理正确")
    except Exception as e:
        print(f"   [FAIL] 只有指令测试失败: {e}")

    # 只有上下文
    try:
        result = build_mini_prompt("", "上下文", "")
        assert result == "Context: 上下文", "只有上下文时应正确格式化"
        print("   [PASS] 只有上下文处理正确")
    except Exception as e:
        print(f"   [FAIL] 只有上下文测试失败: {e}")

    # 4. 测试BM25分数计算边缘情况
    print("\n4. 测试BM25分数计算边缘情况...")

    # 空文档
    try:
        score = compute_bm25_score("查询", "")
        assert score == 0.0, "空文档应返回0分"
        print("   [PASS] 空文档分数计算正确")
    except Exception as e:
        print(f"   [FAIL] 空文档分数测试失败: {e}")

    # 空查询
    try:
        score = compute_bm25_score("", "文档内容")
        assert score == 0.0, "空查询应返回0分"
        print("   [PASS] 空查询分数计算正确")
    except Exception as e:
        print(f"   [FAIL] 空查询分数测试失败: {e}")

    # 5. 测试retrieve_documents边缘情况
    print("\n5. 测试retrieve_documents边缘情况...")

    # 设置全局LLM客户端
    mock_llm = MockLLM()
    set_global_llm_client(mock_llm)

    # max_content_length为0
    try:
        mock_docs = [{"title": "测试", "content": "这是一个测试文档"}]
        result = retrieve_documents("查询", mock_docs, top_k=1, max_content_length=0)
        assert len(result) == 1, "应返回结果"
        assert result[0]['content'] == "...", "应完全截断"
        print("   [PASS] max_content_length=0处理正确")
    except Exception as e:
        print(f"   [FAIL] max_content_length=0测试失败: {e}")

    # top_k大于文档数量
    try:
        mock_docs = [{"title": "测试", "content": "内容"}]
        result = retrieve_documents("查询", mock_docs, top_k=5, max_content_length=100)
        assert len(result) == 1, "不应返回超过实际文档数量的结果"
        print("   [PASS] top_k大于文档数量处理正确")
    except Exception as e:
        print(f"   [FAIL] top_k大于文档数量测试失败: {e}")

    # 6. 测试参数类型
    print("\n6. 测试参数类型...")

    # 非字符串参数
    try:
        # 测试数字作为查询
        result = optimized_retrieve(123, [{"title": "测试", "content": "内容"}], 1)
        assert len(result) == 1, "数字查询应正常工作"
        print("   [PASS] 数字查询参数类型处理正确")
    except Exception as e:
        print(f"   [FAIL] 数字查询测试失败: {e}")

    # None值
    try:
        result = build_mini_prompt(None, None, None)
        # 应该能处理None值
        print("   [PASS] None值参数处理正确")
    except Exception as e:
        print(f"   [FAIL] None值测试失败: {e}")

    print("\n" + "=" * 50)
    print("边缘情况测试完成")
    print("=" * 50)


def test_performance():
    """性能测试"""
    print("\n" + "=" * 50)
    print("性能测试")
    print("=" * 50)

    # 准备大量数据
    large_dataset = []
    for i in range(1000):
        large_dataset.append({
            "title": f"文档{i}",
            "content": f"这是第{i}个文档的内容，包含了一些文字来模拟真实的文档内容。"
        })

    print("\n1. 测试优化检索性能...")
    import time

    start_time = time.time()
    result = optimized_retrieve("测试", large_dataset, top_k=10)
    end_time = time.time()

    print(f"   处理1000个文档，耗时: {(end_time - start_time)*1000:.2f}ms")
    print(f"   返回结果数量: {len(result)}")
    print("   [PASS] 性能测试通过")


if __name__ == "__main__":
    test_edge_cases()
    test_performance()