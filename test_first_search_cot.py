"""
测试首次搜索CoT推理功能
"""

import json
import sys
import os

# 修复Windows控制台编码问题
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.nodes.search_node import FirstSearchNode
from src.llms import BaseLLM


class MockLLM(BaseLLM):
    """模拟LLM客户端用于测试"""

    def __init__(self, response_type="cot"):
        super().__init__("mock_api_key", "mock_model")
        self.response_type = response_type

    def get_model_info(self) -> str:
        return "MockLLM (for testing)"

    def get_default_model(self) -> str:
        return "mock_model"

    def invoke(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        """模拟LLM调用"""
        # 从用户提示词中提取标题
        import re
        title_match = re.search(r'段落标题[:：](.*?)(?=\n|$)', user_prompt)
        title = title_match.group(1).strip() if title_match else "测试标题"

        if self.response_type == "cot":
            # CoT格式响应
            return f"""推理：该段落标题为"{title}"，需要获取基础概念、发展历程和应用案例等核心信息，以确保内容的全面性和准确性。选择这个查询能获取到权威的背景资料和实际应用情况。

搜索查询：{title} 概念 原理 案例"""
        else:
            # JSON格式响应（原有格式）
            return f"""```json
{{
  "search_query": "{title} 深度研究",
  "reasoning": "基于当前段落主题，需要深入研究相关内容。"
}}
```"""


def test_first_search_with_cot():
    """测试CoT推理格式"""
    print("=" * 60)
    print("测试1: 首次搜索CoT推理格式")
    print("=" * 60)

    mock_llm = MockLLM(response_type="cot")
    search_node = FirstSearchNode(mock_llm)

    # 测试输入
    test_input = {
        "title": "量子计算基础",
        "content": "介绍量子计算的基本原理、量子比特、量子门等核心概念"
    }

    print("\n输入数据:")
    print(json.dumps(test_input, ensure_ascii=False, indent=2))

    print("\n执行首次搜索...")
    result = search_node.run(test_input)

    print("\n输出结果:")
    print(json.dumps(result, ensure_ascii=False, indent=2))

    # 验证结果
    assert "search_query" in result, "缺少 search_query 字段"
    assert "reasoning" in result, "缺少 reasoning 字段"
    assert result["search_query"], "search_query 为空"
    assert "量子计算" in result["search_query"], "搜索查询中应包含关键词"

    print("\n[OK] 测试1通过：CoT格式正确解析")


def test_first_search_with_json():
    """测试JSON格式（向后兼容）"""
    print("\n" + "=" * 60)
    print("测试2: 首次搜索JSON格式（向后兼容）")
    print("=" * 60)

    mock_llm = MockLLM(response_type="json")
    search_node = FirstSearchNode(mock_llm)

    # 测试输入
    test_input = {
        "title": "生物多样性保护",
        "content": "探讨生物多样性的重要性、面临的威胁及保护措施"
    }

    print("\n输入数据:")
    print(json.dumps(test_input, ensure_ascii=False, indent=2))

    print("\n执行首次搜索...")
    result = search_node.run(test_input)

    print("\n输出结果:")
    print(json.dumps(result, ensure_ascii=False, indent=2))

    # 验证结果
    assert "search_query" in result, "缺少 search_query 字段"
    assert "reasoning" in result, "缺少 reasoning 字段"
    assert result["search_query"], "search_query 为空"

    print("\n[OK] 测试2通过：JSON格式正确解析")


def test_first_search_edge_cases():
    """测试边缘情况"""
    print("\n" + "=" * 60)
    print("测试3: 边缘情况")
    print("=" * 60)

    mock_llm = MockLLM(response_type="cot")
    search_node = FirstSearchNode(mock_llm)

    # 测试空描述
    print("\n3.1 测试空描述...")
    test_input = {
        "title": "测试标题",
        "content": ""
    }

    result = search_node.run(test_input)
    assert "search_query" in result, "空描述时缺少 search_query"
    print("[OK] 空描述处理正常")

    # 测试特殊字符
    print("\n3.2 测试特殊字符...")
    test_input = {
        "title": "AI与ML：深度学习算法",
        "content": "探索<特殊>符号的处理"
    }

    result = search_node.run(test_input)
    assert result["search_query"], "特殊字符处理失败"
    print("[OK] 特殊字符处理正常")

    # 测试长标题
    print("\n3.3 测试长标题...")
    test_input = {
        "title": "这是一个非常非常非常非常非常长的段落标题用于测试系统的处理能力",
        "content": "测试内容"
    }

    result = search_node.run(test_input)
    assert result["search_query"], "长标题处理失败"
    print("[OK] 长标题处理正常")

    print("\n[OK] 测试3通过：边缘情况处理正常")


if __name__ == "__main__":
    try:
        test_first_search_with_cot()
        test_first_search_with_json()
        test_first_search_edge_cases()

        print("\n" + "=" * 60)
        print("所有测试通过！首次搜索CoT推理功能实现成功。")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n[X] 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[X] 测试出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
