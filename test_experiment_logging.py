import unittest
from unittest.mock import Mock, patch, MagicMock
from src.agent import DeepSearchAgent
from datetime import datetime
import json


class TestExperimentLogging(unittest.TestCase):
    """测试实验日志功能"""

    def setUp(self):
        """测试前准备"""
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
        self.agent.llm_client = Mock()
        self.agent.llm_client.generate_json = Mock()

    def test_log_experiment(self):
        """测试_log_experiment方法"""
        # 测试数据
        query = "测试查询"
        score = 0.85
        mode = "normal"
        duration = 12.34

        # 调用方法
        result = self.agent._log_experiment(query, score, mode, duration)

        # 验证返回类型
        self.assertIsInstance(result, dict)

        # 验证数据结构
        self.assertIn("query", result)
        self.assertIn("score", result)
        self.assertIn("mode", result)
        self.assertIn("duration", result)
        self.assertIn("timestamp", result)
        self.assertIn("agent_info", result)

        # 验证数据内容
        self.assertEqual(result["query"], query)
        self.assertEqual(result["score"], score)
        self.assertEqual(result["mode"], mode)
        self.assertEqual(result["duration"], duration)

        # 验证时间戳格式
        try:
            datetime.fromisoformat(result["timestamp"])
        except ValueError:
            self.fail("时间戳格式不正确")

        # 验证agent_info
        self.assertIn("domain_tags", result["agent_info"])
        self.assertIn("history_score", result["agent_info"])
        self.assertIn("is_busy", result["agent_info"])

        # 验证agent_info内容
        self.assertEqual(result["agent_info"]["domain_tags"], ["科技", "综合"])
        self.assertEqual(result["agent_info"]["history_score"], 0.5)
        self.assertEqual(result["agent_info"]["is_busy"], False)

    def test_log_experiment_edge_cases(self):
        """测试边界情况"""
        # 测试分数为0
        result1 = self.agent._log_experiment("查询1", 0.0, "fast", 5.67)
        self.assertEqual(result1["score"], 0.0)

        # 测试分数为1
        result2 = self.agent._log_experiment("查询2", 1.0, "detailed", 23.45)
        self.assertEqual(result2["score"], 1.0)

        # 测试不同模式
        result3 = self.agent._log_experiment("查询3", 0.7, "normal", 10.0)
        self.assertEqual(result3["mode"], "normal")

        # 测试不同耗时
        result4 = self.agent._log_experiment("查询4", 0.6, "fast", 0.0)
        self.assertEqual(result4["duration"], 0.0)


if __name__ == '__main__':
    unittest.main()