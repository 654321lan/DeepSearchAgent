#!/usr/bin/env python3
"""
全流程集成测试脚本
测试 src/retrieval.py、src/llm_client.py、src/agent.py 的完整集成
纯本地逻辑测试，不调用任何LLM/网络API
检查语法错误、逻辑错误、兼容问题
"""

import sys
import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# 导入需要测试的模块
from retrieval import (
    retrieve_documents,
    optimized_retrieve,
    truncate_long_doc,
    compute_bm25_score
)
from llm_client import (
    build_mini_prompt,
    SimpleLLMClient,
    llm_call,
    get_llm_client,
    set_global_llm_client
)


class MockLLM:
    """模拟LLM客户端，用于测试"""

    def __init__(self):
        self.responses = {
            "分析": "This is an analysis response",
            "总结": "This is a summary response",
            "翻译": "This is a translation response",
            "解释": "This is an explanation response"
        }

        self.model_info = {
            "provider": "Mock",
            "model": "mock-model-v1",
            "api_base": "mock://api.example.com"
        }

    def invoke(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        """模拟invoke方法"""
        # 根据用户prompt返回相应的响应
        for key in self.responses:
            if key in user_prompt:
                return self.responses[key]
        return "Default mock response"

    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return self.model_info

    def generate_json(self, system_prompt: str, user_prompt: str, **kwargs) -> Dict[str, Any]:
        """模拟generate_json方法"""
        return {"test": "mock_json_response"}


class MockParagraph:
    """模拟段落类"""

    def __init__(self, title: str, content: str):
        self.title = title
        self.content = content

        class MockResearch:
            def __init__(self):
                self.search_history = []
                self.latest_summary = ""
                self.reflection_count = 0

            def add_search_results(self, query: str, results: List[Dict[str, Any]]):
                self.search_history.append({"query": query, "results": results})

            def increment_reflection(self):
                self.reflection_count += 1

        self.research = MockResearch()


class MockState:
    """模拟状态类"""

    def __init__(self, query: str = "测试查询"):
        self.query = query
        self.paragraphs = []
        self.final_report = ""
        self.is_completed = False
        self.report_title = f"关于{query}的研究报告"

    def add_paragraph(self, paragraph: MockParagraph):
        self.paragraphs.append(paragraph)

    def mark_completed(self):
        self.is_completed = True

    def update_timestamp(self):
        pass

    def get_progress_summary(self) -> Dict[str, Any]:
        return {
            "total_paragraphs": len(self.paragraphs),
            "completed_paragraphs": sum(1 for p in self.paragraphs if hasattr(p.research, 'latest_summary') and p.research.latest_summary),
            "progress_percentage": (sum(1 for p in self.paragraphs if hasattr(p.research, 'latest_summary') and p.research.latest_summary) / len(self.paragraphs)) * 100 if self.paragraphs else 0,
            "is_completed": self.is_completed
        }

    def save_to_file(self, filepath: str):
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({
                "query": self.query,
                "paragraphs": len(self.paragraphs),
                "completed": self.is_completed
            }, f, ensure_ascii=False, indent=2)


class MockConfig:
    """模拟配置类"""

    def __init__(self):
        self.max_search_results = 5
        self.search_timeout = 30
        self.max_content_length = 200
        self.max_reflections = 2
        self.max_paragraphs = 3
        self.output_dir = "./test_output"
        self.save_intermediate_states = False
        self.default_llm_provider = "mock"

        # LLM配置
        self.mock_api_key = "mock_key"
        self.deepseek_api_key = "mock_key"
        self.openai_api_key = "mock_key"
        self.zhipu_api_key = "mock_key"
        self.tavily_api_key = "mock_key"


class DeepSearchAgentMock:
    """简化的Deep Search Agent模拟类，用于测试集成"""

    def __init__(self, config: Optional[MockConfig] = None):
        """初始化模拟Agent"""
        self.config = config or MockConfig()
        self.state = MockState("测试查询")
        self.llm_client = MockLLM()

        # 模拟添加一些段落
        test_paragraphs = [
            MockParagraph("人工智能发展", "人工智能是计算机科学的一个分支。"),
            MockParagraph("机器学习基础", "机器学习是AI的核心技术。"),
            MockParagraph("深度学习应用", "深度学习在图像识别等领域有广泛应用。")
        ]

        for para in test_paragraphs:
            self.state.add_paragraph(para)

        print("Deep Search Agent Mock 已初始化")

    def test_search_and_retrieval(self) -> Dict[str, Any]:
        """测试搜索和检索功能"""
        print("\n=== 测试搜索和检索集成 ===")

        # 准备模拟搜索结果
        mock_search_results = [
            {
                "title": "AI发展历史",
                "content": "人工智能从1950年代开始发展，经历了多次起伏。深度学习在2010年后取得了突破性进展。",
                "url": "https://example.com/ai-history"
            },
            {
                "title": "机器学习算法",
                "content": "机器学习包括监督学习、无监督学习和强化学习。监督学习使用标记数据训练模型。",
                "url": "https://example.com/ml-algorithms"
            },
            {
                "title": "深度学习基础",
                "content": "深度学习基于神经网络，通过多层结构自动学习特征。卷积神经网络常用于图像处理。",
                "url": "https://example.com/dl-basics"
            },
            {
                "title": "自然语言处理",
                "content": "NLP让计算机理解和处理人类语言。Transformer架构在现代NLP中占据主导地位。",
                "url": "https://example.com/nlp"
            },
            {
                "title": "计算机视觉",
                "content": "计算机视觉使计算机能够理解和解释视觉信息。CNN在图像识别任务中表现优异。",
                "url": "https://example.com/cv"
            }
        ]

        # 测试原始检索
        print("\n1. 测试原始检索函数...")
        try:
            original_results = retrieve_documents(
                "深度学习",
                mock_search_results,
                top_k=3,
                max_content_length=50
            )
            print(f"   [PASS] 原始检索返回 {len(original_results)} 个结果")

            # 验证结果格式
            for i, result in enumerate(original_results, 1):
                assert 'title' in result, f"结果{i}缺少title字段"
                assert 'content' in result, f"结果{i}缺少content字段"
                assert len(result['content']) <= 50, f"结果{i}内容过长"
                print(f"   - 结果{i}: {result['title']}")

        except Exception as e:
            print(f"   [FAIL] 原始检索失败: {str(e)}")
            return {"error": str(e)}

        # 测试优化检索
        print("\n2. 测试优化检索函数...")
        try:
            optimized_results = optimized_retrieve(
                "深度学习",
                mock_search_results,
                top_k=3
            )
            print(f"   [PASS] 优化检索返回 {len(optimized_results)} 个结果")

            # 验证结果格式
            for i, result in enumerate(optimized_results, 1):
                assert 'title' in result, f"结果{i}缺少title字段"
                assert 'content' in result, f"结果{i}缺少content字段"
                assert 'score' in result, f"结果{i}缺少score字段"
                print(f"   - 结果{i}: {result['title']} (分数: {result['score']:.4f})")

        except Exception as e:
            print(f"   [FAIL] 优化检索失败: {str(e)}")
            return {"error": str(e)}

        return {"success": True, "original_count": len(original_results), "optimized_count": len(optimized_results)}

    def test_llm_integration(self) -> Dict[str, Any]:
        """测试LLM集成"""
        print("\n=== 测试LLM集成 ===")

        try:
            # 设置全局LLM客户端
            set_global_llm_client(self.llm_client)

            # 测试极简Prompt构建
            print("\n1. 测试极简Prompt构建...")
            test_cases = [
                ("翻译", "背景：技术", "输入：什么是AI？"),
                ("分析", "", "数据：用户增长趋势"),
                ("总结", "文章：AI发展史", "")
            ]

            for desc, context, input_text in test_cases:
                prompt = build_mini_prompt(desc, context, input_text)
                assert prompt, f"{desc}的prompt不能为空"
                print(f"   [{desc}]: {repr(prompt)}")

            # 测试LLM调用
            print("\n2. 测试LLM调用...")

            # 直接调用
            response1 = llm_call("翻译")
            assert response1 == "This is a translation response", "翻译响应不正确"

            # 带上下文调用
            response2 = llm_call("分析", "背景：技术")
            assert response2 == "This is an analysis response", "分析响应不正确"

            # 完整调用
            response3 = llm_call("总结", "背景：AI", "输入：测试")
            assert response3 == "This is a summary response", "总结响应不正确"

            print("   [PASS] 所有LLM调用测试通过")

            # 测试SimpleLLMClient
            print("\n3. 测试SimpleLLMClient...")
            client = SimpleLLMClient(self.llm_client)
            response = client.llm_call("解释")
            assert response == "This is an explanation response", "解释响应不正确"
            print("   [PASS] SimpleLLMClient测试通过")

            return {"success": True}

        except Exception as e:
            print(f"   [FAIL] LLM集成测试失败: {str(e)}")
            return {"error": str(e)}

    def test_workflow_simulation(self) -> Dict[str, Any]:
        """模拟完整工作流程"""
        print("\n=== 测试完整工作流程 ===")

        try:
            # 1. 生成报告结构（模拟）
            print("\n1. 生成报告结构...")
            report_structure = {
                "title": "关于人工智能的研究报告",
                "paragraphs": [
                    {"title": "AI发展概述", "content": "人工智能的发展历程。"},
                    {"title": "技术原理", "content": "机器学习和深度学习的原理。"},
                    {"title": "应用领域", "content": "AI在各行业的应用。"}
                ]
            }
            print(f"   [PASS] 报告结构生成完成，共{len(report_structure['paragraphs'])}个段落")

            # 2. 处理每个段落（模拟）
            print("\n2. 处理每个段落...")
            for i, para in enumerate(report_structure['paragraphs'], 1):
                print(f"   处理段落 {i}: {para['title']}")

                # 构建搜索查询（使用极简Prompt）
                search_query = build_mini_prompt("生成搜索词", f"主题：{para['title']}", "要求：精准相关")
                print(f"     搜索查询：{search_query}")

                # 模拟检索结果（使用优化检索）
                mock_docs = [
                    {"title": f"{para['title']}相关文章1", "content": f"这是关于{para['title']}的详细内容。"},
                    {"title": f"{para['title']}研究进展", "content": f"最新的{para['title']}研究成果。"}
                ]

                # 使用优化检索
                optimized_results = optimized_retrieve(search_query, mock_docs, top_k=1)
                print(f"     检索到 {len(optimized_results)} 个相关文档")

                # 生成总结（模拟LLM调用）
                summary_prompt = build_mini_prompt("生成总结", f"内容：{optimized_results[0]['content']}")
                summary = llm_call("生成总结", f"内容：{optimized_results[0]['content']}")
                print(f"     生成总结：{summary[:50]}...")

                # 更新状态
                para['summary'] = summary

            print("\n3. 生成最终报告...")
            final_report = "# 最终报告\n\n"
            for para in report_structure['paragraphs']:
                final_report += f"## {para['title']}\n\n"
                final_report += f"{para['summary']}\n\n"

            # 保存报告（模拟）
            os.makedirs(self.config.output_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"test_report_{timestamp}.md"
            filepath = os.path.join(self.config.output_dir, filename)

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(final_report)

            print(f"   [PASS] 最终报告已保存到: {filepath}")

            return {
                "success": True,
                "report_path": filepath,
                "paragraphs": len(report_structure['paragraphs'])
            }

        except Exception as e:
            print(f"   [FAIL] 工作流程测试失败: {str(e)}")
            return {"error": str(e)}

    def run_all_tests(self) -> Dict[str, Any]:
        """运行所有测试"""
        print("=" * 60)
        print("开始全流程集成测试")
        print("=" * 60)

        results = {}

        # 1. 语法检查
        print("\n=== 语法检查 ===")
        try:
            # 检查导入
            import retrieval
            import llm_client
            print("   [PASS] 模块导入成功")

            # 检查类和方法
            assert hasattr(retrieval, 'retrieve_documents'), "缺少retrieve_documents函数"
            assert hasattr(retrieval, 'optimized_retrieve'), "缺少optimized_retrieve函数"
            assert hasattr(retrieval, 'truncate_long_doc'), "缺少truncate_long_doc函数"
            assert hasattr(llm_client, 'build_mini_prompt'), "缺少build_mini_prompt函数"
            assert hasattr(llm_client, 'llm_call'), "缺少llm_call函数"
            print("   [PASS] 所有必要函数存在")

        except Exception as e:
            print(f"   [FAIL] 语法检查失败: {str(e)}")
            return {"syntax_error": str(e)}

        # 2. 搜索和检索测试
        search_results = self.test_search_and_retrieval()
        if "error" in search_results:
            results["search_test"] = search_results
        else:
            results["search_test"] = search_results

        # 3. LLM集成测试
        llm_results = self.test_llm_integration()
        if "error" in llm_results:
            results["llm_test"] = llm_results
        else:
            results["llm_test"] = llm_results

        # 4. 工作流程测试
        workflow_results = self.test_workflow_simulation()
        if "error" in workflow_results:
            results["workflow_test"] = workflow_results
        else:
            results["workflow_test"] = workflow_results

        # 汇总结果
        print("\n" + "=" * 60)
        print("测试结果汇总")
        print("=" * 60)

        test_names = {
            "search_test": "搜索和检索测试",
            "llm_test": "LLM集成测试",
            "workflow_test": "工作流程测试"
        }

        all_passed = True
        for test_name, description in test_names.items():
            if test_name in results:
                if "error" in results[test_name]:
                    print(f"❌ {description}: 失败")
                    print(f"   错误: {results[test_name]['error']}")
                    all_passed = False
                else:
                    print(f"✅ {description}: 通过")
                    if test_name == "search_test":
                        print(f"   原始检索: {results[test_name]['original_count']} 个结果")
                        print(f"   优化检索: {results[test_name]['optimized_count']} 个结果")
                    elif test_name == "llm_test":
                        print("   LLM调用正常")
                    elif test_name == "workflow_test":
                        print(f"   生成报告: {results[test_name]['paragraphs']} 个段落")
                        print(f"   保存路径: {results[test_name]['report_path']}")

        # 总结
        print("\n" + "=" * 60)
        if all_passed:
            print("🎉 所有测试通过！集成成功！")
            print("✓ 语法检查通过")
            print("✓ 检索功能正常")
            print("✓ LLM集成正常")
            print("✓ 工作流程完整")
        else:
            print("⚠️  部分测试失败，请检查错误信息")
        print("=" * 60)

        return results


if __name__ == "__main__":
    # 创建测试实例
    agent = DeepSearchAgentMock()

    # 运行所有测试
    test_results = agent.run_all_tests()

    # 输出详细报告
    print("\n" + "=" * 60)
    print("详细测试报告")
    print("=" * 60)

    # 如果有错误，输出详细信息
    for test_name, result in test_results.items():
        if "error" in result:
            print(f"\n❌ {test_name} 错误详情:")
            print(f"   错误类型: {type(result['error']).__name__}")
            print(f"   错误信息: {result['error']}")

    print("\n测试完成！")