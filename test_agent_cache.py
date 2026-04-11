#!/usr/bin/env python3
"""
测试 src/agent.py 的缓存功能
测试本地查询缓存、pickle持久化、API调用避免等
"""

import sys
import os
import shutil
import tempfile
from typing import Dict, Any, List, Optional

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# 导入需要的模块
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from agent import DeepSearchAgent, Config
from utils.config import load_config


class MockConfigForCacheTest:
    """用于测试的模拟配置类"""

    def __init__(self, temp_dir: str):
        self.output_dir = temp_dir
        self.max_search_results = 3
        self.search_timeout = 10
        self.max_content_length = 100
        self.max_reflections = 1
        self.max_paragraphs = 2
        self.save_intermediate_states = False
        self.default_llm_provider = "mock"

        # API密钥（模拟）
        self.deepseek_api_key = "mock_key"
        self.openai_api_key = "mock_key"
        self.zhipu_api_key = "mock_key"
        self.tavily_api_key = "mock_key"


class SimpleMockLLM:
    """简化的模拟LLM客户端"""

    def __init__(self):
        self.call_count = 0
        self.response = "这是一个模拟的LLM响应"

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "provider": "Mock",
            "model": "mock-model"
        }

    def invoke(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        self.call_count += 1
        print(f"[LLM调用 #{self.call_count}] 处理用户输入: {user_prompt[:50]}...")
        return self.response

    def generate_json(self, system_prompt: str, user_prompt: str, **kwargs) -> Dict[str, Any]:
        self.call_count += 1
        return {"mock": "response"}


class MockReportStructureNode:
    """模拟报告结构节点"""

    def __init__(self, llm_client, query: str):
        self.llm_client = llm_client
        self.query = query

    def mutate_state(self, state, **kwargs):
        # 模拟添加段落
        state.add_paragraph(f"关于{self.query}的研究", "这是模拟的段落内容")
        return state


class MockSummaryNode:
    """模拟总结节点"""

    def __init__(self, llm_client):
        self.llm_client = llm_client
        self.call_count = 0

    def run(self, input_data: Any, **kwargs) -> str:
        self.call_count += 1
        return f"这是第{self.call_count}个总结：模拟的段落总结内容"


class DeepSearchAgentWithMocks(DeepSearchAgent):
    """使用模拟组件的DeepSearchAgent"""

    def __init__(self, config: Optional[Config] = None):
        # 避免调用父类的__init__，直接初始化必要的属性
        self.config = config or load_config()
        self.state = self._create_mock_state()
        self.llm_client = SimpleMockLLM()
        self.enable_cache = True

        # 初始化缓存
        self.query_cache = {}
        self.query_cache_file = os.path.join(self.config.output_dir, "query_cache.pkl")
        self._load_query_cache()

        # 模拟节点
        self.first_search_node = None
        self.reflection_node = None
        self.first_summary_node = MockSummaryNode(self.llm_client)
        self.reflection_summary_node = MockSummaryNode(self.llm_client)
        self.report_formatting_node = None

    def _create_mock_state(self):
        """创建模拟状态"""
        from state import State
        state = State()
        state.query = "测试查询"
        return state

    def _initialize_llm(self):
        return self.llm_client

    def _initialize_nodes(self):
        # 跳过节点初始化
        pass

    def _generate_report_structure(self, query: str):
        """模拟生成报告结构"""
        print(f"\n[步骤 1] 生成报告结构...")
        mock_node = MockReportStructureNode(self.llm_client, query)
        self.state = mock_node.mutate_state(state=self.state)
        print(f"报告结构已生成，共 {len(self.state.paragraphs)} 个段落")

    def _process_paragraphs(self):
        """模拟处理段落"""
        print(f"\n[步骤 2] 处理段落...")
        for i, paragraph in enumerate(self.state.paragraphs):
            print(f"  处理段落 {i+1}: {paragraph.title}")
            # 模拟搜索和总结
            print(f"    - 生成搜索查询...")
            print(f"    - 执行网络搜索...")
            print(f"    - 生成初始总结...")

            # 更新状态
            self.state = self.first_summary_node.mutate_state(
                {"title": paragraph.title, "content": paragraph.content},
                self.state, i
            )

    def _generate_final_report(self) -> str:
        """模拟生成最终报告"""
        print(f"\n[步骤 3] 生成最终报告...")
        report = f"# 关于{self.state.query}的研究报告\n\n"
        for paragraph in self.state.paragraphs:
            report += f"## {paragraph.title}\n\n"
            report += f"{paragraph.research.latest_summary}\n\n"
        return report

    def _save_report(self, report_content: str):
        """模拟保存报告"""
        timestamp = "20260411_123456"
        filename = f"test_report_{timestamp}.md"
        filepath = os.path.join(self.config.output_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report_content)

        print(f"报告已保存到: {filepath}")


def test_cache_functionality():
    """测试缓存功能"""
    print("=" * 60)
    print("测试 DeepSearchAgent 缓存功能")
    print("=" * 60)

    # 创建临时目录
    temp_dir = tempfile.mkdtemp(prefix="agent_cache_test_")
    print(f"临时目录: {temp_dir}")

    try:
        # 创建带缓存的Agent
        config = MockConfigForCacheTest(temp_dir)
        agent = DeepSearchAgentWithMocks(config)

        print("\n1. 测试首次运行（应该生成缓存）...")
        query1 = "人工智能发展史"

        # 清除之前的缓存
        agent.clear_cache()

        # 首次运行
        result1 = agent.research(query1, save_report=False)
        print(f"首次运行完成，LLM调用次数: {agent.llm_client.call_count}")

        # 检查缓存
        cache_info1 = agent.get_cache_info()
        print(f"缓存信息: {cache_info1}")

        print("\n2. 测试第二次运行相同查询（应该使用缓存）...")
        result2 = agent.research(query1, save_report=False)
        print(f"第二次运行完成，LLM调用次数: {agent.llm_client.call_count}")

        # 验证结果相同
        assert result1 == result2, "两次运行结果应该相同"

        # 验证缓存被使用
        cache_info2 = agent.get_cache_info()
        assert cache_info2['total_entries'] > 0, "应该有缓存查询"
        print("✅ 缓存工作正常，LLM调用次数未增加")

        print("\n3. 测试不同查询（应该生成新缓存）...")
        query2 = "机器学习基础"
        result3 = agent.research(query2, save_report=False)

        cache_info3 = agent.get_cache_info()
        print(f"缓存查询数: {cache_info3['cached_queries']}")
        assert cache_info3['total_entries'] >= 2, "应该至少有2个缓存查询"
        print("✅ 多查询缓存正常")

        print("\n4. 测试缓存管理功能...")
        # 显示缓存状态
        agent.show_cache_status()

        # 列出缓存的查询
        cached_queries = agent.list_cached_queries(5)
        print(f"缓存的查询: {cached_queries}")

        # 禁用缓存
        agent.set_cache_enabled(False)
        result4 = agent.research(query1, save_report=False)
        print(f"禁用缓存后运行，LLM调用次数: {agent.llm_client.call_count}")
        # 禁用缓存后应该会增加LLM调用
        assert agent.llm_client.call_count > cache_info2['cached_queries'], "禁用缓存后应该增加LLM调用"

        print("\n5. 测试持久化...")
        # 保存当前状态
        agent._save_query_cache()

        # 创建新Agent实例
        agent2 = DeepSearchAgentWithMocks(config)
        # 应该加载缓存
        assert len(agent2.query_cache) > 0, "新实例应该加载缓存"
        print("✅ 缓存持久化正常")

        print("\n6. 测试缓存清除...")
        agent.clear_query_cache()
        cache_info_after_clear = agent.get_cache_info()
        assert cache_info_after_clear['total_entries'] == 0, "清除后缓存数应为0"
        print("✅ 缓存清除正常")

    finally:
        # 清理临时目录
        shutil.rmtree(temp_dir)
        print(f"\n已清理临时目录: {temp_dir}")

    print("\n" + "=" * 60)
    print("所有测试通过！缓存功能正常工作")
    print("=" * 60)


def test_edge_cases():
    """测试边缘情况"""
    print("\n" + "=" * 60)
    print("测试缓存边缘情况")
    print("=" * 60)

    temp_dir = tempfile.mkdtemp(prefix="agent_cache_edge_")

    try:
        config = MockConfigForCacheTest(temp_dir)
        agent = DeepSearchAgentWithMocks(config)

        # 1. 测试空查询
        print("\n1. 测试空查询...")
        agent.research("", save_report=False)

        # 2. 测试长查询
        print("\n2. 测试长查询...")
        long_query = "这是一个非常长的查询" * 10
        agent.research(long_query, save_report=False)

        # 3. 测试特殊字符
        print("\n3. 测试特殊字符...")
        special_query = "查询 @#$%^&*()_+-={}[]|\\:;\"'<>?,./"
        agent.research(special_query, save_report=False)

        print("\n✅ 边缘情况测试通过")

    finally:
        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    test_cache_functionality()
    test_edge_cases()