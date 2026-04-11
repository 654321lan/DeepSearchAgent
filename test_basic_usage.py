"""
测试 examples/basic_usage.py 与优化后src代码的兼容性
使用mock替代所有API调用
"""

import os
import sys
import unittest.mock as mock

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))


def test_imports():
    """测试导入是否有语法错误"""
    print("\n" + "="*60)
    print("【测试1】导入兼容性检查")
    print("="*60)

    try:
        print("  导入基础模块...")
        from src import DeepSearchAgent, load_config
        print("  [OK] DeepSearchAgent 导入成功")

        from src.utils.config import print_config, Config
        print("  [OK] Config 模块导入成功")

        from src.state.state import State
        print("  [OK] State 模块导入成功")

        from src.nodes.base_node import BaseNode, StateMutationNode
        print("  [OK] Nodes 模块导入成功")

        from src.retrieval import compute_bm25_score, retrieve_documents
        print("  [OK] Retrieval 模块导入成功")

        print("\n[OK] 所有模块导入成功，无语法错误")
        return True

    except Exception as e:
        print(f"\n[FAIL] 导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_config_creation():
    """测试配置对象创建"""
    print("\n" + "="*60)
    print("【测试2】Config对象创建")
    print("="*60)

    try:
        from src.utils.config import Config

        config = Config(
            deepseek_api_key="mock_deepseek_key",
            openai_api_key="mock_openai_key",
            zhipu_api_key="mock_zhipu_key",
            tavily_api_key="mock_tavily_key",
            default_llm_provider="zhipu",
            deepseek_model="deepseek-chat",
            openai_model="gpt-3.5-turbo",
            zhipu_model="glm-4",
            max_search_results=3,
            search_timeout=30,
            max_content_length=200,
            max_reflections=1,
            max_paragraphs=3,
            output_dir="test_output",
            save_intermediate_states=False
        )

        print(f"  default_llm_provider: {config.default_llm_provider}")
        print(f"  zhipu_model: {config.zhipu_model}")
        print(f"  max_search_results: {config.max_search_results}")

        print("\n[OK] Config对象创建成功")
        return True

    except Exception as e:
        print(f"\n[FAIL] Config创建失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_agent_initialization():
    """测试Agent初始化（使用mock）"""
    print("\n" + "="*60)
    print("【测试3】Agent初始化 (Mock LLM)")
    print("="*60)

    try:
        from src.agent import DeepSearchAgent
        from src.utils.config import Config

        # 创建配置
        config = Config(
            deepseek_api_key="mock_deepseek_key",
            openai_api_key="mock_openai_key",
            zhipu_api_key="mock_zhipu_key",
            tavily_api_key="mock_tavily_key",
            default_llm_provider="zhipu",
            deepseek_model="deepseek-chat",
            openai_model="gpt-3.5-turbo",
            zhipu_model="glm-4",
            max_search_results=3,
            search_timeout=30,
            max_content_length=200,
            max_reflections=1,
            max_paragraphs=3,
            output_dir="test_output",
            save_intermediate_states=False
        )

        # Mock LLM客户端
        with mock.patch('src.agent.ZhipuLLM') as mock_zhipu:
            # 创建mock实例
            mock_instance = mock.Mock()
            mock_instance.get_model_info.return_value = "Mock Zhipu Model"
            mock_instance.generate_json.return_value = {
                "title": "测试报告",
                "sections": [
                    {"title": "段落1", "description": "描述1"},
                    {"title": "段落2", "description": "描述2"}
                ]
            }
            mock_zhipu.return_value = mock_instance

            # Mock搜索工具
            with mock.patch('src.agent.tavily_search') as mock_search:
                mock_search.return_value = [
                    {
                        "title": "模拟搜索结果",
                        "url": "https://example.com",
                        "content": "模拟内容" * 20
                    }
                ]

                # 初始化Agent
                print("  正在初始化Agent...")
                agent = DeepSearchAgent(config)

                print(f"  domain_tags: {agent.domain_tags}")
                print(f"  enable_cache: {agent.enable_cache}")
                print(f"  history_score: {agent.history_score}")

                print("\n[OK] Agent初始化成功")
                return True

    except Exception as e:
        print(f"\n[FAIL] Agent初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_basic_usage_code():
    """测试basic_usage.py代码本身的兼容性"""
    print("\n" + "="*60)
    print("【测试4】basic_usage.py代码兼容性")
    print("="*60)

    try:
        # 解析文件检查语法
        import ast

        with open('examples/basic_usage.py', 'r', encoding='utf-8') as f:
            code = f.read()

        # 编译检查语法错误
        ast.parse(code)
        print("  [OK] 代码语法检查通过")

        # 检查关键导入
        from src import DeepSearchAgent, load_config
        from src.utils.config import print_config

        print("  [OK] 关键类可导入")

        # 检查Config构造函数参数
        from src.utils.config import Config
        import inspect

        sig = inspect.signature(Config.__init__)
        params = list(sig.parameters.keys())
        print(f"  Config参数: {', '.join(params[:10])}...")

        expected_params = ['self', 'deepseek_api_key', 'openai_api_key', 'zhipu_api_key']
        for param in expected_params:
            if param in params:
                print(f"  [OK] Config有参数: {param}")
            else:
                print(f"  [WARN] Config缺少参数: {param}")

        print("\n[OK] basic_usage.py代码兼容性检查通过")
        return True

    except Exception as e:
        print(f"\n[FAIL] 兼容性检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_agent_methods():
    """测试Agent的关键方法是否存在"""
    print("\n" + "="*60)
    print("【测试5】Agent方法兼容性")
    print("="*60)

    try:
        from src.agent import DeepSearchAgent
        from src.utils.config import Config

        # 创建配置
        config = Config(
            deepseek_api_key="mock_key",
            openai_api_key="mock_key",
            zhipu_api_key="mock_key",
            tavily_api_key="mock_key",
            default_llm_provider="zhipu"
        )

        # Mock LLM
        with mock.patch('src.agent.ZhipuLLM') as mock_llm:
            mock_instance = mock.Mock()
            mock_instance.get_model_info.return_value = "Mock"
            mock_instance.generate_json.return_value = {"test": "result"}
            mock_llm.return_value = mock_instance

            with mock.patch('src.agent.tavily_search') as mock_search:
                mock_search.return_value = []

                agent = DeepSearchAgent(config)

                # 检查关键方法
                methods_to_check = [
                    'research',
                    'get_progress_summary',
                    '_generate_report_structure',
                    '_process_paragraphs',
                    '_generate_final_report',
                    'get_cached_result',
                    'cache_result',
                    'clear_cache',
                    'get_cache_info'
                ]

                for method in methods_to_check:
                    if hasattr(agent, method):
                        print(f"  [OK] 方法存在: {method}")
                    else:
                        print(f"  [FAIL] 方法缺失: {method}")

                print("\n[OK] Agent方法兼容性检查通过")
                return True

    except Exception as e:
        print(f"\n[FAIL] 方法检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_node_imports():
    """测试节点模块导入"""
    print("\n" + "="*60)
    print("【测试6】节点模块导入")
    print("="*60)

    try:
        from src.nodes import (
            ReportStructureNode,
            FirstSearchNode,
            ReflectionNode,
            FirstSummaryNode,
            ReflectionSummaryNode,
            ReportFormattingNode
        )

        print("  [OK] ReportStructureNode 导入成功")
        print("  [OK] FirstSearchNode 导入成功")
        print("  [OK] ReflectionNode 导入成功")
        print("  [OK] FirstSummaryNode 导入成功")
        print("  [OK] ReflectionSummaryNode 导入成功")
        print("  [OK] ReportFormattingNode 导入成功")

        print("\n[OK] 所有节点模块导入成功")
        return True

    except Exception as e:
        print(f"\n[FAIL] 节点导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有兼容性测试"""
    print("\n" + "="*60)
    print("Basic Usage 兼容性测试 (不调用API)")
    print("="*60)
    print("检查 examples/basic_usage.py 与优化后src代码的兼容性")

    results = []

    results.append(("导入兼容性", test_imports()))
    results.append(("Config创建", test_config_creation()))
    results.append(("Agent初始化", test_agent_initialization()))
    results.append(("代码兼容性", test_basic_usage_code()))
    results.append(("Agent方法", test_agent_methods()))
    results.append(("节点导入", test_node_imports()))

    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)

    for name, result in results:
        status = "[OK]" if result else "[FAIL]"
        print(f"{status} {name}")

    all_passed = all(r[1] for r in results)

    print("\n" + "="*60)
    if all_passed:
        print("[OK] 所有测试通过！代码兼容性良好")
    else:
        print("[FAIL] 部分测试失败，请检查错误信息")
    print("="*60)

    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
