"""
测试CoT推理反思功能
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

from src.nodes.search_node import ReflectionNode
from src.llms import BaseLLM


class MockLLM(BaseLLM):
    """模拟LLM客户端用于测试"""

    def __init__(self, response_type="cot"):
        """
        初始化模拟LLM

        Args:
            response_type: "cot" 表示CoT格式响应，"json" 表示纯JSON格式响应
        """
        super().__init__("mock_api_key", "mock_model")
        self.response_type = response_type

    def get_model_info(self) -> str:
        return "MockLLM (for testing)"

    def get_default_model(self) -> str:
        return "mock_model"

    def invoke(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        """模拟LLM调用"""
        # 读取输入数据
        try:
            input_data = json.loads(user_prompt)
            title = input_data.get("title", "测试标题")
        except:
            title = "测试标题"

        if self.response_type == "cot":
            # CoT格式响应
            return f"""推理过程：
1. 分析当前段落已有信息：段落标题是"{title}"，当前内容涉及基本概念介绍
2. 识别遗漏方面：可能缺少具体的案例研究、最新数据支持、实际应用效果等
3. 确定补充搜索方向：需要查找具体的实例和实际应用数据

```json
{{
  "search_query": "{title} 案例研究 实际应用 数据支持",
  "reasoning": "通过分析现有内容，发现缺少具体案例和实际数据支撑，需要搜索相关实例来增强段落的说服力。"
}}
```"""
        else:
            # 纯JSON格式响应（原有格式）
            return f"""```json
{{
  "search_query": "{title} 深度研究",
  "reasoning": "基于当前段落内容，需要进一步深入研究以补充关键信息。"
}}
```"""


def test_reflection_with_cot():
    """测试CoT推理格式"""
    print("=" * 60)
    print("测试1: CoT推理格式响应")
    print("=" * 60)

    mock_llm = MockLLM(response_type="cot")
    reflection_node = ReflectionNode(mock_llm)

    # 测试输入
    test_input = {
        "title": "人工智能在教育中的应用",
        "content": "介绍AI技术如何改变传统教育模式",
        "paragraph_latest_state": "人工智能正在通过个性化学习、智能辅导系统等方式改变教育领域。自适应学习平台能够根据学生的表现调整教学内容和难度。"
    }

    print("\n输入数据:")
    print(json.dumps(test_input, ensure_ascii=False, indent=2))

    print("\n执行反思...")
    result = reflection_node.run(test_input)

    print("\n输出结果:")
    print(json.dumps(result, ensure_ascii=False, indent=2))

    # 验证结果
    assert "search_query" in result, "缺少 search_query 字段"
    assert "reasoning" in result, "缺少 reasoning 字段"
    assert result["search_query"], "search_query 为空"

    print("\n✓ 测试1通过：CoT格式正确解析")


def test_reflection_with_json_only():
    """测试纯JSON格式（向后兼容）"""
    print("\n" + "=" * 60)
    print("测试2: 纯JSON格式响应（向后兼容）")
    print("=" * 60)

    mock_llm = MockLLM(response_type="json")
    reflection_node = ReflectionNode(mock_llm)

    # 测试输入
    test_input = {
        "title": "区块链技术",
        "content": "介绍区块链的基本原理和应用场景",
        "paragraph_latest_state": "区块链是一种去中心化的分布式账本技术，通过加密算法保证数据的安全性和不可篡改性。"
    }

    print("\n输入数据:")
    print(json.dumps(test_input, ensure_ascii=False, indent=2))

    print("\n执行反思...")
    result = reflection_node.run(test_input)

    print("\n输出结果:")
    print(json.dumps(result, ensure_ascii=False, indent=2))

    # 验证结果
    assert "search_query" in result, "缺少 search_query 字段"
    assert "reasoning" in result, "缺少 reasoning 字段"
    assert result["search_query"], "search_query 为空"

    print("\n✓ 测试2通过：纯JSON格式正确解析")


def test_reflection_edge_cases():
    """测试边缘情况"""
    print("\n" + "=" * 60)
    print("测试3: 边缘情况")
    print("=" * 60)

    # 测试空段落最新状态
    print("\n3.1 测试空段落最新状态...")
    mock_llm = MockLLM(response_type="json")
    reflection_node = ReflectionNode(mock_llm)

    test_input = {
        "title": "测试标题",
        "content": "测试内容",
        "paragraph_latest_state": ""
    }

    result = reflection_node.run(test_input)
    assert "search_query" in result, "空状态时缺少 search_query"
    print("✓ 空状态处理正常")

    # 测试特殊字符
    print("\n3.2 测试特殊字符...")
    test_input = {
        "title": "人工智能与机器学习：深度学习算法",
        "content": "探索<特殊>符号的处理",
        "paragraph_latest_state": "测试'引号'和\"双引号\"的处理"
    }

    result = reflection_node.run(test_input)
    assert result["search_query"], "特殊字符处理失败"
    print("✓ 特殊字符处理正常")

    print("\n✓ 测试3通过：边缘情况处理正常")


if __name__ == "__main__":
    try:
        test_reflection_with_cot()
        test_reflection_with_json_only()
        test_reflection_edge_cases()

        print("\n" + "=" * 60)
        print("所有测试通过！CoT推理功能实现成功。")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n[X] 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[X] 测试出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
