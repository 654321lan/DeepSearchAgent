import unittest
from unittest.mock import Mock, patch, MagicMock
from src.agent import DeepSearchAgent
import json


class TestDeepSearchAgentMethods(unittest.TestCase):
    """DeepSearchAgent方法的单元测试"""

    def setUp(self):
        """测试前准备"""
        # 创建模拟的LLM客户端
        self.mock_llm_client = Mock()
        self.mock_llm_client.generate_json = Mock()

        # 创建模拟的配置
        self.mock_config = Mock()
        self.mock_config.default_llm_provider = "deepseek"
        self.mock_config.deepseek_api_key = "mock_key"
        self.mock_config.deepseek_model = "mock_model"
        self.mock_config.output_dir = "mock_output_dir"
        self.mock_config.max_search_results = 5
        self.mock_config.search_timeout = 30
        self.mock_config.tavily_api_key = "mock_tavily_key"
        self.mock_config.max_reflections = 2
        self.mock_config.max_content_length = 1000

        # 创建DeepSearchAgent实例
        self.agent = DeepSearchAgent(self.mock_config)
        self.agent.llm_client = self.mock_llm_client

    def test_decompose_query(self):
        """测试_decompose_query方法"""
        # 测试数据
        query = "分析2024新能源汽车销量及政策影响"

        # 模拟LLM返回
        mock_response = {
            "sub_tasks": [
                {"content": "2024年新能源汽车销量数据", "priority": 1, "type": "搜索"},
                {"content": "2024年新能源汽车政策影响", "priority": 2, "type": "分析"},
                {"content": "2024年新能源汽车市场趋势", "priority": 3, "type": "验证"}
            ]
        }

        self.mock_llm_client.generate_json.return_value = mock_response

        # 调用方法
        result = self.agent._decompose_query(query)

        # 验证结果
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]["content"], "2024年新能源汽车销量数据")
        self.assertEqual(result[0]["priority"], 1)
        self.assertEqual(result[0]["type"], "搜索")
        self.assertEqual(result[1]["content"], "2024年新能源汽车政策影响")
        self.assertEqual(result[1]["priority"], 2)
        self.assertEqual(result[1]["type"], "分析")
        self.assertEqual(result[2]["content"], "2024年新能源汽车市场趋势")
        self.assertEqual(result[2]["priority"], 3)
        self.assertEqual(result[2]["type"], "验证")

        # 验证LLM被调用
        self.mock_llm_client.generate_json.assert_called_once()

    def test_decompose_query_default(self):
        """测试_decompose_query方法的默认行为"""
        # 测试数据
        query = "简单查询"

        # 模拟LLM返回无效数据
        mock_response = {"invalid_key": "value"}

        self.mock_llm_client.generate_json.return_value = mock_response

        # 调用方法
        result = self.agent._decompose_query(query)

        # 验证结果（默认返回）
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["content"], "简单查询")
        self.assertEqual(result[0]["priority"], 1)
        self.assertEqual(result[0]["type"], "搜索")

    def test_generate_search_query(self):
        """测试_generate_search_query方法"""
        # 测试数据
        sub_task_content = "2024年新能源汽车销量数据"

        # 模拟LLM返回
        mock_response = {
            "keywords": [
                "2024年新能源汽车销量统计",
                "2024年电动车销量报告",
                "2024年新能源汽车市场数据"
            ]
        }

        self.mock_llm_client.generate_json.return_value = mock_response

        # 调用方法
        result = self.agent._generate_search_query(sub_task_content)

        # 验证结果
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0], "2024年新能源汽车销量统计")
        self.assertEqual(result[1], "2024年电动车销量报告")
        self.assertEqual(result[2], "2024年新能源汽车市场数据")

        # 验证LLM被调用
        self.mock_llm_client.generate_json.assert_called_once()

    def test_generate_search_query_default(self):
        """测试_generate_search_query方法的默认行为"""
        # 测试数据
        sub_task_content = "简单任务"

        # 模拟LLM返回无效数据
        mock_response = {"invalid_key": "value"}

        self.mock_llm_client.generate_json.return_value = mock_response

        # 调用方法
        result = self.agent._generate_search_query(sub_task_content)

        # 验证结果（默认返回）
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], "简单任务")

    def test_validate_content(self):
        """测试_validate_content方法"""
        # 测试数据
        search_content = "2024年新能源汽车销量达到100万辆，同比增长30%"
        original_query = "分析2024新能源汽车销量及政策影响"

        # 模拟LLM返回
        mock_response = {
            "score": 0.85,
            "conclusion": "内容与查询高度相关，包含销量数据"
        }

        self.mock_llm_client.generate_json.return_value = mock_response

        # 调用方法
        result = self.agent._validate_content(search_content, original_query)

        # 验证结果
        self.assertEqual(result["score"], 0.85)
        self.assertEqual(result["conclusion"], "内容与查询高度相关，包含销量数据")

        # 验证LLM被调用
        self.mock_llm_client.generate_json.assert_called_once()

    def test_validate_content_default(self):
        """测试_validate_content方法的默认行为"""
        # 测试数据
        search_content = "无关内容"
        original_query = "分析2024新能源汽车销量及政策影响"

        # 模拟LLM返回无效数据
        mock_response = {"invalid_key": "value"}

        self.mock_llm_client.generate_json.return_value = mock_response

        # 调用方法
        result = self.agent._validate_content(search_content, original_query)

        # 验证结果（默认返回）
        self.assertEqual(result["score"], 0.5)
        self.assertEqual(result["conclusion"], "验证失败")

    def test_integrate_results(self):
        """测试_integrate_results方法"""
        # 测试数据
        task_results = [
            {
                "sub_task": {"content": "销量数据", "priority": 1, "type": "搜索"},
                "search_results": [
                    {"title": "2024年销量报告", "url": "http://example.com/1"},
                    {"title": "2024年电动车销量", "url": "http://example.com/2"}
                ],
                "validation": {"score": 0.9, "conclusion": "相关"}
            },
            {
                "sub_task": {"content": "政策影响", "priority": 2, "type": "分析"},
                "search_results": [
                    {"title": "2024年政策分析", "url": "http://example.com/3"}
                ],
                "validation": {"score": 0.7, "conclusion": "相关"}
            },
            {
                "sub_task": {"content": "销量数据", "priority": 1, "type": "搜索"},  # 重复内容
                "search_results": [
                    {"title": "重复销量报告", "url": "http://example.com/4"}
                ],
                "validation": {"score": 0.8, "conclusion": "相关"}
            }
        ]

        # 调用方法
        result = self.agent._integrate_results(task_results)

        # 验证结果
        self.assertEqual(result["overview"], "共整合2个子任务，平均验证分数0.80")
        self.assertEqual(len(result["tasks"]), 2)

        # 验证第一个任务
        task1 = result["tasks"][0]
        self.assertEqual(task1["content"], "销量数据")
        self.assertEqual(task1["priority"], 1)
        self.assertEqual(task1["type"], "搜索")
        self.assertEqual(task1["search_count"], 2)
        self.assertEqual(task1["score"], 0.9)
        self.assertEqual(task1["conclusion"], "相关")

        # 验证第二个任务
        task2 = result["tasks"][1]
        self.assertEqual(task2["content"], "政策影响")
        self.assertEqual(task2["priority"], 2)
        self.assertEqual(task2["type"], "分析")
        self.assertEqual(task2["search_count"], 1)
        self.assertEqual(task2["score"], 0.7)
        self.assertEqual(task2["conclusion"], "相关")

        # 验证验证总结
        self.assertEqual(result["validation_summary"]["avg_score"], 0.8)
        self.assertEqual(len(result["validation_summary"]["conclusions"]), 1)
        self.assertEqual(result["validation_summary"]["conclusions"][0], "相关")

    def test_integrate_results_empty(self):
        """测试_integrate_results方法的空输入"""
        # 测试数据
        task_results = []

        # 调用方法
        result = self.agent._integrate_results(task_results)

        # 验证结果
        self.assertEqual(result["overview"], "整合失败")
        self.assertEqual(len(result["tasks"]), 0)
        self.assertEqual(result["validation_summary"]["avg_score"], 0.0)
        self.assertEqual(len(result["validation_summary"]["conclusions"]), 0)

    def test_integrate_results_invalid(self):
        """测试_integrate_results方法的无效输入"""
        # 测试数据 - 使用符合方法期望格式的数据
        task_results = [
            {
                "sub_task": {"content": "", "priority": 1, "type": "搜索"},
                "search_results": [],
                "validation": {"score": 0.0, "conclusion": "验证失败"}
            }
        ]

        # 调用方法
        result = self.agent._integrate_results(task_results)

        # 验证结果
        self.assertEqual(result["overview"], "共整合0个子任务，平均验证分数0.00")
        self.assertEqual(len(result["tasks"]), 0)
        self.assertEqual(result["validation_summary"]["avg_score"], 0.0)
        self.assertEqual(len(result["validation_summary"]["conclusions"]), 0)


if __name__ == '__main__':
    unittest.main()