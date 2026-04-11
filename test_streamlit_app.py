"""
测试 examples/streamlit_app.py 与优化后src代码的兼容性
不调用任何API，仅检查语法和导入
"""

import os
import sys
import ast

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))


def test_syntax():
    """测试代码语法"""
    print("\n" + "="*60)
    print("【测试1】语法检查")
    print("="*60)

    try:
        with open('examples/streamlit_app.py', 'r', encoding='utf-8') as f:
            code = f.read()

        # 编译检查语法
        ast.parse(code)
        print("  [OK] streamlit_app.py 语法正确")
        return True

    except SyntaxError as e:
        print(f"  [FAIL] 语法错误: {e}")
        return False


def test_imports():
    """测试导入兼容性"""
    print("\n" + "="*60)
    print("【测试2】导入兼容性")
    print("="*60)

    try:
        # 测试src模块导入
        from src import DeepSearchAgent, Config
        print("  [OK] src导入成功: DeepSearchAgent, Config")

        from src.utils import load_config
        print("  [OK] src.utils导入成功: load_config")

        # 检查Config的from_file方法是否存在
        if hasattr(Config, 'from_file'):
            print("  [OK] Config.from_file 方法存在")
        else:
            print("  [WARN] Config.from_file 方法不存在（streamlit_app.py使用了它）")

        return True

    except Exception as e:
        print(f"  [FAIL] 导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_config_attributes():
    """测试Config的属性是否匹配streamlit_app的使用"""
    print("\n" + "="*60)
    print("【测试3】Config属性匹配检查")
    print("="*60)

    try:
        from src.utils.config import Config
        import inspect

        # 检查__init__方法的参数
        sig = inspect.signature(Config.__init__)
        params = list(sig.parameters.keys())

        print("  Config.__init__ 参数:")
        for param in params[:15]:  # 显示前15个参数
            print(f"    - {param}")

        # streamlit_app.py中使用的属性
        required_attrs = [
            'default_llm_provider',
            'zhipu_api_key',
            'deepseek_api_key',
            'openai_api_key',
            'tavily_api_key',
            'zhipu_model',
            'deepseek_model',
            'openai_model',
            'max_reflections',
            'max_search_results',
            'max_content_length',
            'output_dir'
        ]

        print("\n  检查streamlit_app.py使用的属性:")
        all_ok = True
        for attr in required_attrs:
            if attr in params:
                print(f"    [OK] 参数存在: {attr}")
            else:
                print(f"    [FAIL] 参数缺失: {attr}")
                all_ok = False

        return all_ok

    except Exception as e:
        print(f"  [FAIL] 检查失败: {e}")
        return False


def test_agent_methods():
    """测试Agent方法是否匹配streamlit_app的使用"""
    print("\n" + "="*60)
    print("【测试4】Agent方法匹配检查")
    print("="*60)

    try:
        from src.agent import DeepSearchAgent
        import inspect

        # streamlit_app.py中使用的Agent方法
        required_methods = [
            '_generate_report_structure',
            '_initial_search_and_summary',
            '_reflection_loop',
            '_generate_final_report',
            '_save_report',
            'get_progress_summary'
        ]

        # 检查方法是否存在
        all_ok = True
        for method in required_methods:
            if hasattr(DeepSearchAgent, method):
                # 检查方法签名
                sig = inspect.signature(getattr(DeepSearchAgent, method))
                params = list(sig.parameters.keys())
                print(f"  [OK] 方法存在: {method} (参数: {params})")
            else:
                print(f"  [FAIL] 方法缺失: {method}")
                all_ok = False

        # 检查state属性
        print("\n  检查Agent.state属性:")
        if hasattr(DeepSearchAgent, '__init__'):
            init_source = inspect.getsource(DeepSearchAgent.__init__)
            if 'self.state = State()' in init_source:
                print("  [OK] Agent有state属性")
            else:
                print("  [WARN] Agent.state属性来源不明确")

        return all_ok

    except Exception as e:
        print(f"  [FAIL] 检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_state_methods():
    """测试State方法是否匹配使用"""
    print("\n" + "="*60)
    print("【测试5】State方法匹配检查")
    print("="*60)

    try:
        from src.state.state import State, Paragraph
        from dataclasses import fields

        # 创建实例来检查字段
        test_state = State()
        test_paragraph = Paragraph()

        # streamlit_app.py中使用的State相关方法/属性
        required_features = [
            ('to_json', '方法'),
            ('add_paragraph', '方法')
        ]

        all_ok = True
        for feature, feature_type in required_features:
            if hasattr(State, feature):
                print(f"  [OK] State.{feature_type}存在: {feature}")
            else:
                print(f"  [FAIL] State.{feature_type}缺失: {feature}")
                all_ok = False

        # 检查实例属性（paragraphs是dataclass字段，通过实例访问）
        if hasattr(test_state, 'paragraphs'):
            print(f"  [OK] State实例属性存在: paragraphs")
        else:
            print(f"  [FAIL] State实例属性缺失: paragraphs")
            all_ok = False

        # 检查Paragraph实例的research属性
        if hasattr(test_paragraph, 'research'):
            print(f"  [OK] Paragraph实例属性存在: research")
        else:
            print(f"  [FAIL] Paragraph实例属性缺失: research")
            all_ok = False

        return all_ok

    except Exception as e:
        print(f"  [FAIL] 检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_code_references():
    """测试代码中引用的类和方法"""
    print("\n" + "="*60)
    print("【测试6】代码引用检查")
    print("="*60)

    try:
        with open('examples/streamlit_app.py', 'r', encoding='utf-8') as f:
            code = f.read()

        # 检查关键导入
        imports_to_check = [
            'from src import DeepSearchAgent, Config',
            'from src.utils import load_config'
        ]

        for imp in imports_to_check:
            if imp in code:
                print(f"  [OK] 找到导入: {imp}")
            else:
                print(f"  [WARN] 未找到导入: {imp}")

        # 检查关键方法调用
        method_calls = [
            'agent._generate_report_structure(query)',
            'agent._initial_search_and_summary(i)',
            'agent._reflection_loop(i)',
            'agent._generate_final_report()',
            'agent._save_report(final_report)',
            'agent.get_progress_summary()',
            'agent.state.to_json()'
        ]

        print("\n  检查方法调用:")
        for call in method_calls:
            if call in code:
                print(f"  [OK] 找到调用: {call}")
            else:
                print(f"  [WARN] 未找到调用: {call}")

        return True

    except Exception as e:
        print(f"  [FAIL] 检查失败: {e}")
        return False


def test_with_mock():
    """使用mock测试Agent初始化"""
    print("\n" + "="*60)
    print("【测试7】Mock初始化测试")
    print("="*60)

    try:
        from src.agent import DeepSearchAgent
        from src.utils.config import Config
        import unittest.mock as mock

        config = Config(
            deepseek_api_key="mock_key",
            openai_api_key="mock_key",
            zhipu_api_key="mock_key",
            tavily_api_key="mock_key",
            default_llm_provider="zhipu",
            zhipu_model="glm-4",
            max_reflections=1,
            max_search_results=2,
            max_content_length=1000,
            output_dir="test_streamlit_output"
        )

        # Mock LLM
        with mock.patch('src.agent.ZhipuLLM') as mock_llm:
            mock_instance = mock.Mock()
            mock_instance.get_model_info.return_value = "Mock"
            mock_instance.generate_json.return_value = {
                "title": "Test",
                "sections": [
                    {"title": "P1", "description": "D1"}
                ]
            }
            mock_llm.return_value = mock_instance

        # Mock搜索
        with mock.patch('src.agent.tavily_search') as mock_search:
            mock_search.return_value = []

            # 初始化Agent（不调用API）
            agent = DeepSearchAgent(config)

            print("  [OK] Agent初始化成功（Mock模式）")
            print(f"    state属性: {type(agent.state).__name__}")
            print(f"    domain_tags: {agent.domain_tags}")
            print(f"    enable_cache: {agent.enable_cache}")

            return True

    except Exception as e:
        print(f"  [FAIL] Mock初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有兼容性测试"""
    print("\n" + "="*60)
    print("Streamlit App 兼容性测试 (不调用API)")
    print("="*60)
    print("检查 examples/streamlit_app.py 与优化后src代码的兼容性")

    results = []

    results.append(("语法检查", test_syntax()))
    results.append(("导入兼容性", test_imports()))
    results.append(("Config属性", test_config_attributes()))
    results.append(("Agent方法", test_agent_methods()))
    results.append(("State方法", test_state_methods()))
    results.append(("代码引用", test_code_references()))
    results.append(("Mock初始化", test_with_mock()))

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
        print("streamlit_app.py 可以正常使用优化后的src代码")
    else:
        print("[FAIL] 部分测试失败，请检查错误信息")
    print("="*60)

    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
